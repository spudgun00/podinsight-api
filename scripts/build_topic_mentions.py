#!/usr/bin/env python3
"""
Build topic mention counts from transcript text.

Scans transcript_chunks_768d for the five tracked topics (TOPICS_TO_TRACK) and
counts regex occurrences per episode, joined to published_at and podcast_name
from episode_metadata. The result is stored so the API never has to scan the
transcripts on request.

Counting is on the transcript text itself, NOT the cleaned_entities NER files -
those are deduplicated per episode and carry no occurrence counts.

Destination:

    topic_mentions   one doc per (episode_id, topic), zeros included so that
                     "scanned but never mentioned" is distinguishable from
                     "episode not scanned"

        episode_id, topic, mention_count, published_at, podcast_name,
        chunks_scanned, terms, terms_version

Idempotent: the collection is rebuilt from scratch on every run.

Usage:
    python scripts/build_topic_mentions.py
    python scripts/build_topic_mentions.py --dry-run
"""

import argparse
import os
import re
import sys
from collections import Counter, defaultdict

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

COLLECTION = "topic_mentions"
TERMS_VERSION = 1

# One pattern set per tracked topic. Deliberately narrow: these match the topic
# being named, not every loosely related word. Widening them changes what the
# numbers mean, so the set is versioned via TERMS_VERSION.
TOPIC_TERMS = {
    "AI Agents":          [r"ai agents?", r"agentic", r"autonomous agents?"],
    "Capital Efficiency": [r"capital efficien\w*", r"burn multiple", r"default alive"],
    "DePIN":              [r"depin", r"decentrali[sz]ed physical infrastructure"],
    "B2B SaaS":           [r"b2b saas", r"b2b software"],
    "Crypto/Web3":        [r"crypto\w*", r"web ?3(?:\.0)?"],
}

PATTERNS = {
    topic: re.compile("|".join(f"(?:{term})" for term in terms), re.IGNORECASE)
    for topic, terms in TOPIC_TERMS.items()
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="scan and report, write nothing")
    args = parser.parse_args()

    mongo_uri = os.environ.get("MONGODB_URI")
    if not mongo_uri:
        sys.exit("MONGODB_URI not set")

    db = MongoClient(mongo_uri)["podinsight"]

    episodes = {}
    for doc in db["episode_metadata"].find({}, {
        "episode_id": 1,
        "podcast_title": 1,
        "raw_entry_original_feed.published_date_iso": 1,
    }):
        raw_entry = doc.get("raw_entry_original_feed") or {}
        episodes[doc["episode_id"]] = {
            "published_at": raw_entry.get("published_date_iso"),
            "podcast_name": doc.get("podcast_title"),
        }
    print(f"episodes in episode_metadata: {len(episodes)}")

    counts = defaultdict(Counter)
    chunks_scanned = Counter()

    cursor = db["transcript_chunks_768d"].find({}, {"episode_id": 1, "text": 1})
    total_chunks = 0
    for chunk in cursor:
        episode_id = chunk.get("episode_id")
        text = chunk.get("text") or ""
        if not episode_id:
            continue
        total_chunks += 1
        chunks_scanned[episode_id] += 1
        for topic, pattern in PATTERNS.items():
            hits = len(pattern.findall(text))
            if hits:
                counts[episode_id][topic] += hits

    print(f"chunks scanned: {total_chunks} across {len(chunks_scanned)} episodes")

    documents = []
    for episode_id, chunk_total in chunks_scanned.items():
        meta = episodes.get(episode_id, {})
        for topic in TOPIC_TERMS:
            documents.append({
                "episode_id": episode_id,
                "topic": topic,
                "mention_count": counts[episode_id].get(topic, 0),
                "published_at": meta.get("published_at"),
                "podcast_name": meta.get("podcast_name"),
                "chunks_scanned": chunk_total,
                "terms": TOPIC_TERMS[topic],
                "terms_version": TERMS_VERSION,
            })

    totals = Counter()
    episodes_with = Counter()
    for doc in documents:
        totals[doc["topic"]] += doc["mention_count"]
        if doc["mention_count"]:
            episodes_with[doc["topic"]] += 1

    print(f"\ndocuments: {len(documents)}")
    for topic in TOPIC_TERMS:
        print(f"  {topic:20} {totals[topic]:6} mentions across {episodes_with[topic]:2}/{len(chunks_scanned)} episodes")

    missing_dates = sum(1 for d in documents if not d["published_at"])
    if missing_dates:
        print(f"  WARNING: {missing_dates} rows have no published_at")

    if args.dry_run:
        print("\ndry run, nothing written")
        return

    db[COLLECTION].delete_many({})
    db[COLLECTION].insert_many(documents)
    db[COLLECTION].create_index([("topic", ASCENDING), ("published_at", ASCENDING)])
    db[COLLECTION].create_index([("episode_id", ASCENDING)])
    print(f"\nstored: {db[COLLECTION].count_documents({})} docs in {COLLECTION}")


if __name__ == "__main__":
    main()
