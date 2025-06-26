#!/usr/bin/env python3
"""
Test episode date relationships
"""

import os
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

def test_episode_dates():
    mongodb_uri = os.getenv('MONGODB_URI')
    if not mongodb_uri:
        print("❌ MONGODB_URI not set")
        return

    # Add database name if missing
    if '/podinsight?' not in mongodb_uri and mongodb_uri.endswith('mongodb.net/?'):
        mongodb_uri = mongodb_uri.replace('mongodb.net/?', 'mongodb.net/podinsight?')

    try:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        db = client['podinsight']
        chunks_collection = db['transcript_chunks_768d']
        episodes_collection = db['episode_metadata']

        print("🔍 Testing episode date relationships...")

        # Get a sample chunk
        sample_chunk = chunks_collection.find_one({})
        if sample_chunk:
            print(f"\n📋 Sample chunk:")
            print(f"  - _id: {sample_chunk['_id']}")
            print(f"  - episode_id: {sample_chunk.get('episode_id', 'NOT FOUND')}")
            print(f"  - created_at: {sample_chunk.get('created_at', 'NOT FOUND')}")

            # Try to find the episode
            if 'episode_id' in sample_chunk:
                episode = episodes_collection.find_one({"guid": sample_chunk['episode_id']})
                if episode:
                    print(f"\n📅 Corresponding episode:")
                    print(f"  - guid: {episode['guid']}")
                    print(f"  - published_date_iso: {episode.get('published_date_iso', 'NOT FOUND')}")
                    print(f"  - episode_title: {episode.get('episode_title', 'Unknown')}")
                else:
                    print(f"\n❌ No episode found with guid: {sample_chunk['episode_id']}")

        # Test date search using aggregation
        print("\n🔍 Testing date-based search with episode dates...")

        # Get chunks from last 30 days based on episode publish date
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)

        # Convert dates to ISO string format for comparison
        start_date_iso = start_date.strftime("%Y-%m-%d")
        end_date_iso = end_date.strftime("%Y-%m-%d")

        pipeline = [
            # Lookup episode metadata
            {
                "$lookup": {
                    "from": "episode_metadata",
                    "localField": "episode_id",
                    "foreignField": "guid",
                    "as": "episode"
                }
            },
            # Unwind the episode array
            {"$unwind": "$episode"},
            # Match date range
            {
                "$match": {
                    "episode.published_date_iso": {
                        "$gte": start_date_iso,
                        "$lt": end_date_iso
                    }
                }
            },
            # Count
            {"$count": "total"}
        ]

        result = list(chunks_collection.aggregate(pipeline, maxTimeMS=10000))
        if result:
            print(f"  Chunks from episodes in last 30 days: {result[0]['total']:,}")
        else:
            print(f"  No chunks found from episodes in last 30 days")

        # Test with AI keyword
        pipeline_with_ai = [
            {"$match": {"text": {"$regex": "\\bai\\b", "$options": "i"}}},
            {
                "$lookup": {
                    "from": "episode_metadata",
                    "localField": "episode_id",
                    "foreignField": "guid",
                    "as": "episode"
                }
            },
            {"$unwind": "$episode"},
            {
                "$match": {
                    "episode.published_date_iso": {
                        "$gte": start_date_iso,
                        "$lt": end_date_iso
                    }
                }
            },
            {"$count": "total"}
        ]

        result_ai = list(chunks_collection.aggregate(pipeline_with_ai, maxTimeMS=10000))
        if result_ai:
            print(f"  Chunks with 'ai' from episodes in last 30 days: {result_ai[0]['total']:,}")

        client.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_episode_dates()
