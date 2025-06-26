#!/usr/bin/env python3
"""
Test the correct MongoDB query structure for sentiment analysis
"""

import os
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import re

def test_corrected_query():
    """Test the corrected query approach"""

    mongodb_uri = os.getenv('MONGODB_URI')
    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client['podinsight']
    chunks_collection = db['transcript_chunks_768d']
    episodes_collection = db['episodes']

    print("🔧 Testing Corrected Sentiment Query")
    print("=" * 40)

    # Check episode collection structure
    episode_sample = episodes_collection.find_one()
    print(f"Episode fields: {list(episode_sample.keys())}")

    # Find the published date field
    published_field = None
    for field in episode_sample.keys():
        if 'published' in field.lower():
            published_field = field
            print(f"Found published field: {field} = {episode_sample[field]}")
            break

    if not published_field:
        print("❌ No published field found in episodes!")
        return

    # Test date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(weeks=4)

    print(f"\nTesting date range: {start_date.date()} to {end_date.date()}")

    # Method 1: Use aggregation with $lookup (JOIN)
    print("\n🔍 Method 1: Aggregation with $lookup")

    topic = "AI"
    topic_pattern = re.compile(re.escape(topic), re.IGNORECASE)

    pipeline = [
        # Stage 1: Match chunks with topic
        {
            "$match": {
                "text": {"$regex": topic_pattern}
            }
        },
        # Stage 2: Join with episodes collection
        {
            "$lookup": {
                "from": "episodes",
                "localField": "episode_id",
                "foreignField": "_id" if "_id" in episode_sample else "id",
                "as": "episode"
            }
        },
        # Stage 3: Unwind episode array
        {
            "$unwind": "$episode"
        },
        # Stage 4: Match date range
        {
            "$match": {
                f"episode.{published_field}": {
                    "$gte": start_date,
                    "$lt": end_date
                }
            }
        },
        # Stage 5: Project needed fields
        {
            "$project": {
                "text": 1,
                "episode_id": 1,
                f"published_at": f"$episode.{published_field}"
            }
        },
        # Stage 6: Limit for testing
        {
            "$limit": 100
        }
    ]

    try:
        import time
        start_time = time.time()
        results = list(chunks_collection.aggregate(pipeline))
        elapsed = time.time() - start_time

        print(f"✅ Found {len(results)} chunks in {elapsed:.2f}s")
        if results:
            print(f"Sample: episode_id={results[0]['episode_id']}, published={results[0]['published_at']}")
            print(f"Text preview: {results[0]['text'][:100]}...")

    except Exception as e:
        print(f"❌ Aggregation failed: {e}")

    # Method 2: Use created_at as proxy (simpler but less accurate)
    print("\n🔍 Method 2: Use created_at as date proxy")

    simple_query = {
        "text": {"$regex": topic_pattern},
        "created_at": {
            "$gte": start_date,
            "$lt": end_date
        }
    }

    try:
        start_time = time.time()
        simple_count = chunks_collection.count_documents(simple_query)
        elapsed = time.time() - start_time

        print(f"✅ Found {simple_count} chunks in {elapsed:.2f}s")

        if simple_count > 0:
            sample = chunks_collection.find_one(simple_query, {"text": 1, "created_at": 1})
            print(f"Sample: created_at={sample['created_at']}")
            print(f"Text preview: {sample['text'][:100]}...")

    except Exception as e:
        print(f"❌ Simple query failed: {e}")

    # Method 3: Pre-fetch episode IDs in date range (hybrid approach)
    print("\n🔍 Method 3: Pre-fetch episode IDs")

    try:
        # First, get episode IDs in date range
        start_time = time.time()
        episode_query = {
            published_field: {
                "$gte": start_date,
                "$lt": end_date
            }
        }

        episode_ids = [ep["_id"] if "_id" in ep else ep["id"]
                      for ep in episodes_collection.find(episode_query, {"_id": 1, "id": 1})]

        print(f"Found {len(episode_ids)} episodes in date range")

        if episode_ids:
            # Then query chunks for those episodes
            chunk_query = {
                "text": {"$regex": topic_pattern},
                "episode_id": {"$in": episode_ids}
            }

            chunk_count = chunks_collection.count_documents(chunk_query)
            elapsed = time.time() - start_time

            print(f"✅ Found {chunk_count} chunks in {elapsed:.2f}s")

    except Exception as e:
        print(f"❌ Hybrid query failed: {e}")

    client.close()

if __name__ == "__main__":
    test_corrected_query()
