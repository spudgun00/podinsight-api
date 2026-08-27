#!/usr/bin/env python3
"""
Load episode transcripts + embeddings from S3 into MongoDB.

Source layout (bucket defaults to pod-insights-stage):

    s3://{bucket}/{slug}/{episode_id}/segments/{episode_id}_full.json
    s3://{bucket}/{slug}/{episode_id}/embeddings/embedding_768d.npy
    s3://{bucket}/{slug}/{episode_id}/meta/meta_{episode_id}_details.json

Destinations:

    transcript_chunks_768d  one doc per segment
        episode_id, chunk_index, text, start_time, end_time,
        embedding_768d, feed_slug

    episode_metadata        the meta JSON stored verbatim (nesting intact)
        plus an added episode_id field set to the top-level `guid`,
        plus duration_seconds / word_count derived from the segments and
        s3_audio_path lifted from raw_entry_original_feed.s3_audio_path_raw.
        Both `guid` and `episode_id` end up present, because
        api/mongodb_vector_search.py joins on `guid` while
        api/improved_hybrid_search.py joins on `episode_id`.

Idempotent: chunks are upserted on (episode_id, chunk_index) and metadata is
replaced on episode_id, so re-running never duplicates. Resumable: an episode
whose chunk count already matches its segment count and whose metadata row
exists is skipped unless --force.

Usage (single episode):

    python scripts/load_episodes_s3_to_mongo.py \
        --slug unchained --episode-id 014ae528-4588-11f0-a760-7b05fa58ca4e

Multi-episode runs are opt-in: pass --episode-id more than once, or
--all-in-slug to walk every episode under a slug prefix.
"""

import argparse
import io
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
import numpy as np
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError, OperationFailure

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUCKET = "pod-insights-stage"
CHUNKS_COLLECTION = "transcript_chunks_768d"
METADATA_COLLECTION = "episode_metadata"
EMBEDDING_DIM = 768
BULK_CHUNK_SIZE = 500


class EpisodeSkipped(Exception):
    """Raised when an episode cannot be loaded; the run continues."""


@dataclass
class EpisodeReport:
    episode_id: str
    slug: str
    status: str = "pending"
    reason: str = ""
    segment_count: int = 0
    embedding_rows: int = 0
    embedding_dtype: str = ""
    chunks_before: int = 0
    chunks_inserted: int = 0
    chunks_modified: int = 0
    chunks_matched: int = 0
    chunks_after: int = 0
    metadata_action: str = ""
    metadata_top_level_keys: int = 0
    duration_seconds: int = 0
    word_count: int = 0
    audio_path_set: bool = False
    elapsed_s: float = 0.0
    notes: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------- S3


def s3_key_prefix(slug: str, episode_id: str) -> str:
    return f"{slug}/{episode_id}"


def get_json(s3, bucket: str, key: str) -> Any:
    try:
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("NoSuchKey", "404", "AccessDenied"):
            raise EpisodeSkipped(f"s3://{bucket}/{key} unreadable ({code})") from exc
        raise
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise EpisodeSkipped(f"s3://{bucket}/{key} is not valid JSON: {exc}") from exc


def get_npy(s3, bucket: str, key: str) -> np.ndarray:
    try:
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("NoSuchKey", "404", "AccessDenied"):
            raise EpisodeSkipped(f"s3://{bucket}/{key} unreadable ({code})") from exc
        raise
    try:
        return np.load(io.BytesIO(body), allow_pickle=False)
    except Exception as exc:  # noqa: BLE001 - surface any malformed .npy as a skip
        raise EpisodeSkipped(f"s3://{bucket}/{key} is not a readable .npy: {exc}") from exc


def list_episode_ids(s3, bucket: str, slug: str) -> List[str]:
    """Every immediate child 'directory' of {slug}/ is an episode id."""
    ids: List[str] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=f"{slug}/", Delimiter="/"):
        for cp in page.get("CommonPrefixes", []):
            ids.append(cp["Prefix"][len(slug) + 1 :].rstrip("/"))
    return sorted(ids)


# ------------------------------------------------------------------- transform


def build_chunk_docs(
    segments: List[Dict[str, Any]],
    vectors: np.ndarray,
    episode_id: str,
    feed_slug: str,
) -> List[Dict[str, Any]]:
    docs = []
    for i, seg in enumerate(segments):
        if "start" not in seg or "end" not in seg:
            raise EpisodeSkipped(f"segment {i} has no start/end keys: {sorted(seg)}")
        docs.append(
            {
                "episode_id": episode_id,
                "chunk_index": i,
                "text": (seg.get("text") or "").strip(),
                "start_time": float(seg["start"]),
                "end_time": float(seg["end"]),
                "embedding_768d": vectors[i].tolist(),
                "feed_slug": feed_slug,
            }
        )
    return docs


# ---------------------------------------------------------------------- loader


def load_episode(
    s3,
    db,
    bucket: str,
    slug: str,
    episode_id: str,
    force: bool = False,
    dry_run: bool = False,
) -> EpisodeReport:
    started = time.time()
    report = EpisodeReport(episode_id=episode_id, slug=slug)
    chunks = db[CHUNKS_COLLECTION]
    metadata = db[METADATA_COLLECTION]
    prefix = s3_key_prefix(slug, episode_id)

    try:
        # ---- segments -----------------------------------------------------
        seg_key = f"{prefix}/segments/{episode_id}_full.json"
        seg_doc = get_json(s3, bucket, seg_key)
        if not isinstance(seg_doc, dict):
            raise EpisodeSkipped(f"{seg_key}: expected an object, got {type(seg_doc).__name__}")

        segments = seg_doc.get("segments")
        if not isinstance(segments, list) or not segments:
            raise EpisodeSkipped(f"{seg_key}: no usable 'segments' list")

        guid = seg_doc.get("guid")
        if not guid:
            raise EpisodeSkipped(f"{seg_key}: no top-level 'guid'")
        if guid != episode_id:
            report.notes.append(f"segments guid {guid!r} != S3 path id {episode_id!r}; using guid")

        feed_slug = seg_doc.get("feed_slug")
        if not feed_slug:
            raise EpisodeSkipped(f"{seg_key}: no top-level 'feed_slug'")
        if feed_slug != slug:
            report.notes.append(f"segments feed_slug {feed_slug!r} != S3 path slug {slug!r}; using feed_slug")

        episode_key = guid
        report.episode_id = episode_key
        report.segment_count = len(segments)

        # ---- embeddings ---------------------------------------------------
        emb_key = f"{prefix}/embeddings/embedding_768d.npy"
        vectors = get_npy(s3, bucket, emb_key)
        report.embedding_dtype = str(vectors.dtype)
        if vectors.ndim != 2:
            raise EpisodeSkipped(f"{emb_key}: expected a 2-D array, got shape {vectors.shape}")
        report.embedding_rows = int(vectors.shape[0])

        # The hard gate: one vector per segment, or we do not touch this episode.
        if vectors.shape[0] != len(segments):
            raise EpisodeSkipped(
                f"row/segment mismatch: embeddings {vectors.shape[0]} vs segments {len(segments)}"
            )
        if vectors.shape[1] != EMBEDDING_DIM:
            raise EpisodeSkipped(f"{emb_key}: expected {EMBEDDING_DIM} dims, got {vectors.shape[1]}")

        # float16 on disk -> float32 so BSON gets sane doubles.
        if vectors.dtype != np.float32:
            vectors = vectors.astype(np.float32)
        if not np.isfinite(vectors).all():
            raise EpisodeSkipped(f"{emb_key}: contains NaN or Inf")

        # ---- resume check -------------------------------------------------
        report.chunks_before = chunks.count_documents({"episode_id": episode_key})
        meta_present = metadata.count_documents({"episode_id": episode_key}, limit=1) > 0
        if not force and report.chunks_before == len(segments) and meta_present:
            report.status = "skipped-already-loaded"
            report.reason = f"{report.chunks_before} chunks + metadata already present"
            report.chunks_after = report.chunks_before
            report.elapsed_s = time.time() - started
            return report

        # ---- metadata (verbatim, nesting intact) --------------------------
        meta_key = f"{prefix}/meta/meta_{episode_id}_details.json"
        meta_doc = get_json(s3, bucket, meta_key)
        if not isinstance(meta_doc, dict):
            raise EpisodeSkipped(f"{meta_key}: expected an object, got {type(meta_doc).__name__}")

        meta_guid = meta_doc.get("guid")
        if not meta_guid:
            raise EpisodeSkipped(f"{meta_key}: no top-level 'guid'")
        if meta_guid != episode_key:
            raise EpisodeSkipped(
                f"{meta_key}: guid {meta_guid!r} != segments guid {episode_key!r}"
            )

        report.metadata_top_level_keys = len(meta_doc)
        # Stored as-is; episode_id is added so `guid` (mongodb_vector_search)
        # and `episode_id` (improved_hybrid_search) both resolve. Nesting untouched.
        meta_out = dict(meta_doc)
        meta_out["episode_id"] = meta_guid

        # Derived from the segments, because the meta JSON carries neither:
        # duration is the last segment end, word_count the sum over segment text.
        duration_seconds = int(round(max(float(s["end"]) for s in segments)))
        word_count = sum(len((s.get("text") or "").split()) for s in segments)
        meta_out["duration_seconds"] = duration_seconds
        meta_out["word_count"] = word_count
        report.duration_seconds = duration_seconds
        report.word_count = word_count

        # Audio lives in the raw bucket; the feed entry is the authoritative source.
        audio_path = (meta_doc.get("raw_entry_original_feed") or {}).get("s3_audio_path_raw")
        if not audio_path:
            audio_path = meta_doc.get("s3_audio_path")
            if audio_path:
                report.notes.append("s3_audio_path_raw missing; fell back to top-level s3_audio_path")
        if audio_path:
            meta_out["s3_audio_path"] = audio_path
        else:
            report.notes.append("no audio path found in meta; s3_audio_path left unset")
        report.audio_path_set = bool(audio_path)

        chunk_docs = build_chunk_docs(segments, vectors, episode_key, feed_slug)

        if dry_run:
            report.status = "dry-run"
            report.chunks_after = report.chunks_before
            report.metadata_action = "would-replace"
            report.elapsed_s = time.time() - started
            return report

        # ---- write chunks -------------------------------------------------
        for start in range(0, len(chunk_docs), BULK_CHUNK_SIZE):
            batch = chunk_docs[start : start + BULK_CHUNK_SIZE]
            ops = [
                UpdateOne(
                    {"episode_id": d["episode_id"], "chunk_index": d["chunk_index"]},
                    {"$set": d},
                    upsert=True,
                )
                for d in batch
            ]
            try:
                res = chunks.bulk_write(ops, ordered=False)
            except BulkWriteError as exc:
                raise EpisodeSkipped(f"chunk bulk_write failed: {exc.details}") from exc
            report.chunks_inserted += res.upserted_count
            report.chunks_modified += res.modified_count
            report.chunks_matched += res.matched_count

        # ---- write metadata -----------------------------------------------
        res = metadata.replace_one({"episode_id": meta_guid}, meta_out, upsert=True)
        report.metadata_action = "inserted" if res.upserted_id is not None else "replaced"

        report.chunks_after = chunks.count_documents({"episode_id": episode_key})
        if report.chunks_after != len(segments):
            report.status = "verify-failed"
            report.reason = (
                f"post-write chunk count {report.chunks_after} != {len(segments)} segments"
            )
        else:
            report.status = "loaded"

    except EpisodeSkipped as exc:
        report.status = "skipped"
        report.reason = str(exc)

    report.elapsed_s = time.time() - started
    return report


# --------------------------------------------------------------------- indexes


def ensure_indexes(db, verbose: bool = True) -> None:
    """Idempotency depends on the unique keys; create them if absent."""
    try:
        db[CHUNKS_COLLECTION].create_index(
            [("episode_id", 1), ("chunk_index", 1)],
            unique=True,
            name="episode_id_1_chunk_index_1",
        )
        db[METADATA_COLLECTION].create_index("episode_id", unique=True, name="episode_id_1")
        db[METADATA_COLLECTION].create_index("guid", unique=True, name="guid_1")
        if verbose:
            print("indexes: ensured unique (episode_id, chunk_index), episode_id, guid")
    except OperationFailure as exc:
        print(f"indexes: WARNING could not create indexes ({exc}); upserts may duplicate")


def report_vector_index(db) -> None:
    """Informational only - the Atlas Search index is not created by this script."""
    try:
        names = [ix.get("name") for ix in db[CHUNKS_COLLECTION].list_search_indexes()]
    except Exception as exc:  # noqa: BLE001 - unsupported on non-Atlas deployments
        print(f"vector index: could not enumerate search indexes ({type(exc).__name__})")
        return
    if "vector_index_768d" in names:
        print("vector index: vector_index_768d present")
    else:
        print(f"vector index: WARNING vector_index_768d NOT found (search indexes: {names or 'none'})")


# ------------------------------------------------------------------------ main


def print_report(r: EpisodeReport) -> None:
    print(f"\n=== {r.slug}/{r.episode_id} -> {r.status} ===")
    if r.reason:
        print(f"  reason              : {r.reason}")
    for note in r.notes:
        print(f"  note                : {note}")
    print(f"  segments            : {r.segment_count}")
    print(f"  embedding rows      : {r.embedding_rows} (dtype {r.embedding_dtype or 'n/a'} -> float32)")
    print(f"  chunks before       : {r.chunks_before}")
    print(f"  chunks inserted     : {r.chunks_inserted}")
    print(f"  chunks modified     : {r.chunks_modified}")
    print(f"  chunks matched      : {r.chunks_matched}")
    print(f"  chunks after        : {r.chunks_after}")
    print(f"  metadata            : {r.metadata_action or 'not written'}"
          + (f" ({r.metadata_top_level_keys} top-level keys, verbatim + episode_id)"
             if r.metadata_top_level_keys else ""))
    print(f"  derived duration    : {r.duration_seconds}s")
    print(f"  derived word_count  : {r.word_count}")
    print(f"  s3_audio_path       : {'set' if r.audio_path_set else 'MISSING'}")
    print(f"  elapsed             : {r.elapsed_s:.2f}s")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--slug", required=True, help="podcast feed slug, e.g. unchained")
    p.add_argument("--episode-id", action="append", default=[], help="episode id (repeatable)")
    p.add_argument("--all-in-slug", action="store_true",
                   help="load every episode under the slug prefix (multi-episode; opt-in)")
    p.add_argument("--bucket", default=DEFAULT_BUCKET)
    p.add_argument("--force", action="store_true", help="reload even if already complete")
    p.add_argument("--dry-run", action="store_true", help="read and validate, write nothing")
    p.add_argument("--no-indexes", action="store_true", help="skip index creation")
    args = p.parse_args()

    if not args.episode_id and not args.all_in_slug:
        p.error("pass --episode-id at least once, or --all-in-slug")

    load_dotenv(REPO_ROOT / ".env")
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        print("MONGODB_URI is not set", file=sys.stderr)
        return 2
    db_name = os.environ.get("MONGODB_DATABASE", "podinsight")

    s3 = boto3.client("s3")
    client = MongoClient(uri, serverSelectionTimeoutMS=20000)
    db = client[db_name]

    print(f"mongo: {db_name} @ {uri.split('@')[-1].split('/')[0]}")
    print(f"s3   : s3://{args.bucket}/{args.slug}/")
    if args.dry_run:
        print("mode : DRY RUN (no writes)")

    if not args.no_indexes and not args.dry_run:
        ensure_indexes(db)
    report_vector_index(db)

    episode_ids = args.episode_id or list_episode_ids(s3, args.bucket, args.slug)
    print(f"episodes to process: {len(episode_ids)}")

    reports = [
        load_episode(s3, db, args.bucket, args.slug, eid,
                     force=args.force, dry_run=args.dry_run)
        for eid in episode_ids
    ]
    for r in reports:
        print_report(r)

    print("\n=== run summary ===")
    by_status: Dict[str, int] = {}
    for r in reports:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    for status, n in sorted(by_status.items()):
        print(f"  {status:24s}: {n}")
    print(f"  chunks inserted total   : {sum(r.chunks_inserted for r in reports)}")
    print(f"  chunks modified total   : {sum(r.chunks_modified for r in reports)}")
    print(f"\ncollection totals: {CHUNKS_COLLECTION}={db[CHUNKS_COLLECTION].count_documents({})} "
          f"{METADATA_COLLECTION}={db[METADATA_COLLECTION].count_documents({})}")

    failed = [r for r in reports if r.status in ("skipped", "verify-failed")]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
