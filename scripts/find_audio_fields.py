#!/usr/bin/env python3
"""Find audio-related fields in episode_metadata"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
mongodb_uri = os.getenv('MONGODB_URI')
client = MongoClient(mongodb_uri)
db = client['podinsight']

# Get a sample episode and check for audio-related fields
sample = db.episode_metadata.find_one()
if sample:
    print("=== All fields in episode_metadata ===")
    for key in sorted(sample.keys()):
        print(f"  - {key}: {type(sample[key]).__name__}")
        if 'audio' in key.lower() or 'duration' in key.lower() or 'length' in key.lower():
            print(f"    VALUE: {sample[key]}")

# Check if we have transcript chunks
print("\n=== Sample transcript_chunks_768d ===")
chunk_sample = db.transcript_chunks_768d.find_one()
if chunk_sample:
    for key in sorted(chunk_sample.keys()):
        print(f"  - {key}: {type(chunk_sample[key]).__name__}")

# Find episodes with audio URLs
print("\n=== Checking for episodes with audio URLs ===")
episodes_with_audio = db.episode_metadata.find(
    {"audio_url_original_feed": {"$exists": True, "$ne": None}},
    {"_id": 1, "guid": 1, "episode_title": 1, "audio_url_original_feed": 1, "audio_length_bytes_original_feed": 1}
).limit(5)

for ep in episodes_with_audio:
    print(f"\nEpisode: {ep['episode_title'][:50]}...")
    print(f"  ID: {ep['_id']}")
    print(f"  GUID: {ep['guid']}")
    print(f"  Audio bytes: {ep.get('audio_length_bytes_original_feed', 'N/A')}")

client.close()
