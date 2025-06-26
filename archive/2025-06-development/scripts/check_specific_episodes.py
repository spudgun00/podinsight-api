#!/usr/bin/env python3
"""
Check if specific episode IDs exist in MongoDB metadata
"""

import os
from pymongo import MongoClient

# MongoDB connection
uri = os.environ.get('MONGODB_URI', '')
if not uri:
    print('Set MONGODB_URI environment variable')
    exit(1)

client = MongoClient(uri)
db = client.podinsight

# Episode IDs from the search results
test_ids = [
    "e405359e-ea57-11ef-b8c4-ff74e39a637e",
    "flightcast:qoefujdsy5huurb987mnjpw2"
]

print("🔍 Checking specific episode IDs in MongoDB...")
print("=" * 60)

for episode_id in test_ids:
    print(f"\n📋 Checking: {episode_id}")

    # Check in metadata
    metadata = db.episode_metadata.find_one({"guid": episode_id})
    if metadata:
        print("  ✅ Found in episode_metadata!")
        raw = metadata.get('raw_entry_original_feed', {})
        print(f"  - Title: {raw.get('episode_title', 'No title in raw_entry')}")
        print(f"  - Podcast: {raw.get('podcast_title', 'No podcast in raw_entry')}")
    else:
        print("  ❌ NOT found in episode_metadata")

    # Check in chunks to verify it exists
    chunk = db.transcript_chunks_768d.find_one({"episode_id": episode_id})
    if chunk:
        print("  ✅ Found in transcript_chunks_768d")
        print(f"  - Feed slug: {chunk.get('feed_slug')}")
    else:
        print("  ❌ NOT found in transcript_chunks_768d")

# Let's also check what a working episode looks like
print("\n\n📋 Sample working episode from metadata:")
sample = db.episode_metadata.find_one({"raw_entry_original_feed.podcast_title": "a16z Podcast"})
if sample:
    print(f"  GUID: {sample.get('guid')}")
    raw = sample.get('raw_entry_original_feed', {})
    print(f"  Title: {raw.get('episode_title')}")

    # Check if this GUID exists in chunks
    chunk_check = db.transcript_chunks_768d.find_one({"episode_id": sample.get('guid')})
    if chunk_check:
        print("  ✅ This episode HAS chunks")
    else:
        print("  ❌ This episode has NO chunks")

client.close()
