#!/usr/bin/env python3
"""Find suitable test episodes for audio clip testing - Version 2"""

import os
from pymongo import MongoClient
from bson import ObjectId
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

mongodb_uri = os.getenv('MONGODB_URI')
if not mongodb_uri:
    print("Error: MONGODB_URI not found in .env file")
    exit(1)

# Connect to MongoDB
client = MongoClient(mongodb_uri)
db = client['podinsight']

print("=== Finding Test Episodes for Audio Clip Testing ===\n")

# 1. Find episodes with S3 audio paths
print("1. Finding episodes with S3 audio paths:")
episodes_with_audio = list(db.episode_metadata.find(
    {
        "s3_audio_path": {"$exists": True, "$ne": None},
        "guid": {"$exists": True, "$ne": None}
    },
    {
        "_id": 1,
        "guid": 1,
        "episode_title": 1,
        "podcast_title": 1,
        "s3_audio_path": 1
    }
).limit(10))

print(f"Found {len(episodes_with_audio)} episodes with S3 audio paths")

# 2. Check which episodes have transcript chunks
print("\n2. Checking which episodes have transcript chunks:")
episodes_with_transcripts = []
episodes_without_transcripts = []

for ep in episodes_with_audio:
    # Check if this episode has transcript chunks
    chunk_count = db.transcript_chunks_768d.count_documents(
        {"episode_id": ep["guid"]}
    )

    if chunk_count > 0:
        # Get feed_slug and timing info from first chunk
        first_chunk = db.transcript_chunks_768d.find_one(
            {"episode_id": ep["guid"]},
            {"feed_slug": 1, "start_time": 1, "end_time": 1}
        )

        # Get the total duration by finding the last chunk
        last_chunk = db.transcript_chunks_768d.find_one(
            {"episode_id": ep["guid"]},
            {"end_time": 1},
            sort=[("end_time", -1)]
        )

        ep_data = {
            "episode_id": str(ep["_id"]),
            "guid": ep["guid"],
            "title": ep.get("episode_title", "Untitled") or "Untitled",
            "podcast": ep.get("podcast_title", "Unknown"),
            "s3_audio_path": ep["s3_audio_path"],
            "chunk_count": chunk_count,
            "feed_slug": first_chunk.get("feed_slug", "unknown"),
            "duration_sec": last_chunk["end_time"] if last_chunk else 0
        }
        episodes_with_transcripts.append(ep_data)
        print(f"  ✓ {ep_data['title'][:40]}... ({chunk_count} chunks, ~{ep_data['duration_sec']:.0f}s)")
    else:
        ep_data = {
            "episode_id": str(ep["_id"]),
            "guid": ep["guid"],
            "title": ep.get("episode_title", "Untitled") or "Untitled",
            "s3_audio_path": ep["s3_audio_path"]
        }
        episodes_without_transcripts.append(ep_data)
        print(f"  ✗ {ep_data['title'][:40]}... (NO transcript chunks)")

print(f"\n{len(episodes_with_transcripts)} episodes have transcript data")
print(f"{len(episodes_without_transcripts)} episodes have NO transcript data")

# 3. Create test data
print("\n3. Creating test data...")

# Select best test episodes (prefer longer ones)
valid_episodes = sorted(episodes_with_transcripts,
                       key=lambda x: x.get('duration_sec', 0),
                       reverse=True)[:3]

test_data = {
    "generated_at": datetime.now().isoformat(),
    "mongodb_info": {
        "database": "podinsight",
        "collections": {
            "episode_metadata": "Contains episode info with _id as episode_id",
            "transcript_chunks_768d": "Contains chunks with episode_id = guid"
        }
    },
    "test_episodes": {
        "valid_episodes": valid_episodes,
        "episode_without_transcript": episodes_without_transcripts[0]["episode_id"] if episodes_without_transcripts else None,
        "invalid_episode_id": "ffffffffffffffffffffffff"
    },
    "api_endpoint": "https://podinsight-api.vercel.app/api/v1/audio_clips",
    "lambda_url": "https://zxhnx2lugw3pprozjzvn3275ee0ypqpw.lambda-url.eu-west-2.on.aws/",
    "test_parameters": {
        "standard_start_time_ms": 30000,
        "custom_duration_ms": 15000,
        "max_duration_ms": 60000
    }
}

# Save to file
output_file = "/Users/jamesgill/PodInsights/podinsight-api/test_episodes_v2.json"
with open(output_file, 'w') as f:
    json.dump(test_data, f, indent=2)

print(f"\nTest data saved to: {output_file}")

# 4. Generate test commands
if valid_episodes:
    test_ep = valid_episodes[0]
    print("\n=== Ready-to-use Test Commands ===")
    print(f"\n# Test Episode: {test_ep['title'][:60]}...")
    print(f"# Episode ID: {test_ep['episode_id']}")
    print(f"# Duration: ~{test_ep['duration_sec']:.0f} seconds")
    print(f"# Feed: {test_ep['feed_slug']}")

    print(f"\n# 1. Standard 30-second clip test:")
    print(f'curl -X GET "https://podinsight-api.vercel.app/api/v1/audio_clips/{test_ep["episode_id"]}?start_time_ms=30000" \\')
    print(f'  -H "Accept: application/json" | jq')

    print(f"\n# 2. Custom 15-second clip test:")
    print(f'curl -X GET "https://podinsight-api.vercel.app/api/v1/audio_clips/{test_ep["episode_id"]}?start_time_ms=60000&duration_ms=15000" \\')
    print(f'  -H "Accept: application/json" | jq')

    print(f"\n# 3. Error test - episode without transcript:")
    if episodes_without_transcripts:
        print(f'curl -X GET "https://podinsight-api.vercel.app/api/v1/audio_clips/{episodes_without_transcripts[0]["episode_id"]}?start_time_ms=30000" \\')
        print(f'  -H "Accept: application/json" | jq')

    print(f"\n# 4. Error test - invalid episode ID:")
    print(f'curl -X GET "https://podinsight-api.vercel.app/api/v1/audio_clips/invalid-id?start_time_ms=30000" \\')
    print(f'  -H "Accept: application/json" | jq')

client.close()
