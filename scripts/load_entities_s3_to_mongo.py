#!/usr/bin/env python3
"""
Load cleaned entities from S3 into MongoDB.

Source layout (bucket defaults to pod-insights-stage):

    s3://{bucket}/{slug}/{episode_id}/cleaned_entities/{episode_id}_clean.json

Each file is a flat JSON array of spaCy NER spans:

    [{"text": "Jeff Park", "label": "PERSON", "start_char": 190, "end_char": 199}, ...]

Note: the arrays are already deduplicated - one row per distinct
(text, label) pair per episode, carrying the offsets of a single occurrence.
There is no per-episode mention count in the source data.

Destination:

    episode_entities   one small doc per (episode_id, text, label)
        episode_id, feed_slug, podcast_name, published_at,
        text, normalized, label, start_char, end_char

Only episodes already present in transcript_chunks_768d are loaded.

Idempotent: an episode's rows are deleted before its new rows are inserted, so
re-running never duplicates.

Usage:
    python scripts/load_entities_s3_to_mongo.py
    python scripts/load_entities_s3_to_mongo.py --dry-run
    python scripts/load_entities_s3_to_mongo.py --episode-id <uuid>
"""

import argparse
import json
import os
import sys
from collections import Counter
from urllib.parse import urlparse

import boto3
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

COLLECTION = "episode_entities"


def parse_s3_uri(uri: str):
    parsed = urlparse(uri)
    return parsed.netloc, parsed.path.lstrip("/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="read S3 and report, write nothing")
    parser.add_argument("--episode-id", help="load a single episode")
    args = parser.parse_args()

    mongo_uri = os.environ.get("MONGODB_URI")
    if not mongo_uri:
        sys.exit("MONGODB_URI not set")

    db = MongoClient(mongo_uri)["podinsight"]
    s3 = boto3.client("s3")

    # Only episodes that actually have transcript chunks loaded
    chunked_ids = set(db["transcript_chunks_768d"].distinct("episode_id"))
    print(f"episodes in transcript_chunks_768d: {len(chunked_ids)}")

    query = {"episode_id": {"$in": list(chunked_ids)}}
    if args.episode_id:
        query = {"episode_id": args.episode_id}

    episodes = list(db["episode_metadata"].find(query, {
        "episode_id": 1,
        "podcast_title": 1,
        "cleaned_entities_path": 1,
        "raw_entry_original_feed.podcast_slug": 1,
        "raw_entry_original_feed.published_date_iso": 1,
    }))
    print(f"episodes to process: {len(episodes)}")

    label_totals = Counter()
    loaded = skipped = 0
    total_rows = 0

    for episode in episodes:
        episode_id = episode["episode_id"]
        path = episode.get("cleaned_entities_path")
        if not path:
            print(f"  SKIP {episode_id}: no cleaned_entities_path")
            skipped += 1
            continue

        bucket, key = parse_s3_uri(path)
        try:
            body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            spans = json.loads(body)
        except Exception as e:
            print(f"  SKIP {episode_id}: {type(e).__name__} {e}")
            skipped += 1
            continue

        if not isinstance(spans, list):
            print(f"  SKIP {episode_id}: expected a JSON array, got {type(spans).__name__}")
            skipped += 1
            continue

        raw_entry = episode.get("raw_entry_original_feed") or {}
        documents = []
        for span in spans:
            text = (span.get("text") or "").strip()
            label = span.get("label")
            if not text or not label:
                continue
            documents.append({
                "episode_id": episode_id,
                "feed_slug": raw_entry.get("podcast_slug"),
                "podcast_name": episode.get("podcast_title"),
                "published_at": raw_entry.get("published_date_iso"),
                "text": text,
                "normalized": text.lower(),
                "label": label,
                "start_char": span.get("start_char"),
                "end_char": span.get("end_char"),
            })
            label_totals[label] += 1

        total_rows += len(documents)
        loaded += 1
        print(f"  {episode_id} {episode.get('podcast_title', '')[:30]:30} {len(documents):5} entities")

        if not args.dry_run and documents:
            db[COLLECTION].delete_many({"episode_id": episode_id})
            db[COLLECTION].insert_many(documents)

    if not args.dry_run:
        db[COLLECTION].create_index([("normalized", ASCENDING), ("label", ASCENDING)])
        db[COLLECTION].create_index([("episode_id", ASCENDING)])
        db[COLLECTION].create_index([("label", ASCENDING)])

    print(f"\nepisodes loaded: {loaded}  skipped: {skipped}  entity rows: {total_rows}")
    print("label totals:", label_totals.most_common())
    if not args.dry_run:
        print("collection count:", db[COLLECTION].count_documents({}))


if __name__ == "__main__":
    main()
