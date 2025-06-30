#!/usr/bin/env python3
"""Find suitable test episodes for audio clip testing"""

import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from bson import ObjectId
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get MongoDB URI from environment
mongodb_uri = os.getenv('MONGODB_URI')
if not mongodb_uri:
    print("Error: MONGODB_URI not found in .env file")
    print("Please ensure your .env file contains: MONGODB_URI='mongodb://...'")
    exit(1)

# Connect to MongoDB
try:
    client = MongoClient(mongodb_uri)
    # Verify connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except ConnectionFailure as e:
    print(f"MongoDB connection failed: {e}")
    print("Please check your MONGODB_URI and network connectivity.")
    exit(1)
except Exception as e:
    print(f"An unexpected error occurred during MongoDB connection: {e}")
    exit(1)

db = client['podinsight']

print("=== Finding Test Episodes for Audio Clip Testing ===\n")

# First, let's check what episodes exist
print("0. Checking total episodes in database:")
total_count = db.episode_metadata.count_documents({})
print(f"   Total episodes: {total_count}")

# Check some sample episodes
sample_episodes = db.episode_metadata.find({}, {"audio_duration_sec": 1}).limit(10)
durations = [ep.get("audio_duration_sec", 0) for ep in sample_episodes]
print(f"   Sample durations: {durations}")

# 1. Find episodes with long duration
print("\n1. Finding episodes with duration > 120 seconds:")
episodes_with_duration = db.episode_metadata.find(
    {"audio_duration_sec": {"$gt": 120}},
    {"_id": 1, "guid": 1, "episode_title": 1, "audio_duration_sec": 1, "podcast_title": 1}
).limit(5)

test_episodes = []
for ep in episodes_with_duration:
    test_episodes.append({
        "episode_id": str(ep["_id"]),
        "guid": ep["guid"],
        "title": ep["episode_title"],
        "podcast": ep.get("podcast_title", "Unknown"),
        "duration_sec": ep["audio_duration_sec"]
    })
    print(f"  - {ep['episode_title'][:50]}... (ID: {ep['_id']}, Duration: {ep['audio_duration_sec']}s)")

print(f"\nFound {len(test_episodes)} episodes with sufficient duration")

# 2. Check which episodes have transcripts
print("\n2. Checking which episodes have transcript chunks:")
episodes_with_transcripts = []

for ep in test_episodes:
    chunk_count = db.transcript_chunks_768d.count_documents(
        {"episode_id": ep["guid"]}
    )
    if chunk_count > 0:
        # Get feed_slug from first chunk
        first_chunk = db.transcript_chunks_768d.find_one(
            {"episode_id": ep["guid"]},
            {"feed_slug": 1}
        )
        ep["chunk_count"] = chunk_count
        ep["feed_slug"] = first_chunk.get("feed_slug", "unknown")
        episodes_with_transcripts.append(ep)
        print(f"  ✓ {ep['title'][:40]}... has {chunk_count} chunks (feed: {ep['feed_slug']})")
    else:
        print(f"  ✗ {ep['title'][:40]}... has NO chunks")

print(f"\n{len(episodes_with_transcripts)} episodes have transcript data")

# 3. Find episodes without transcripts (for error testing)
print("\n3. Finding episodes WITHOUT transcripts (for error testing):")
pipeline = [
    {"$lookup": {
        "from": "transcript_chunks_768d",
        "localField": "guid",
        "foreignField": "episode_id",
        "as": "chunks"
    }},
    {"$match": {"chunks": {"$size": 0}}},
    {"$limit": 2},
    {"$project": {"_id": 1, "guid": 1, "episode_title": 1}}
]

episodes_without_transcripts = list(db.episode_metadata.aggregate(pipeline))
for ep in episodes_without_transcripts:
    print(f"  - {ep['episode_title'][:50]}... (ID: {ep['_id']})")

# 4. Save test data to file
print("\n4. Saving test data to file...")
test_data = {
    "generated_at": datetime.now().isoformat(),
    "test_episodes": {
        "valid_episodes": episodes_with_transcripts[:3] if episodes_with_transcripts else [],
        "episode_without_transcript": str(episodes_without_transcripts[0]["_id"]) if episodes_without_transcripts else None,
        "invalid_episode_id": "ffffffffffffffffffffffff"
    },
    "api_endpoint": "https://podinsight-api.vercel.app/api/v1/audio_clips",
    "test_parameters": {
        "standard_start_time_ms": 30000,
        "custom_duration_ms": 15000,
        "long_duration_ms": 60000
    }
}

output_file = "/Users/jamesgill/PodInsights/podinsight-api/test_episodes.json"
with open(output_file, 'w') as f:
    json.dump(test_data, f, indent=2)

print(f"Test data saved to: {output_file}")

# 5. Print ready-to-use test commands
if episodes_with_transcripts:
    test_ep = episodes_with_transcripts[0]
    print("\n=== Ready-to-use Test Commands ===")
    print(f"\n# Test Episode: {test_ep['title'][:60]}...")
    print(f"# Episode ID: {test_ep['episode_id']}")
    print(f"# Duration: {test_ep['duration_sec']} seconds")
    print(f"\n# Standard 30-second clip test:")
    print(f'curl -X GET "https://podinsight-api.vercel.app/api/v1/audio_clips/{test_ep["episode_id"]}?start_time_ms=30000" -H "Accept: application/json"')
    print(f"\n# Custom 15-second clip test:")
    print(f'curl -X GET "https://podinsight-api.vercel.app/api/v1/audio_clips/{test_ep["episode_id"]}?start_time_ms=60000&duration_ms=15000" -H "Accept: application/json"')

client.close()
