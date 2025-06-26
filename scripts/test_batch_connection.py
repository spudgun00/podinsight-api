#!/usr/bin/env python3
"""
Minimal test to check batch processor connection and data
"""

import os
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

def test_connection():
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
        collection = db['transcript_chunks_768d']

        # Test 1: Basic connection
        count = collection.count_documents({})
        print(f"✅ Total chunks in database: {count:,}")

        # Test 2: Check date range (12 weeks ago to now)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(weeks=12)

        count_in_range = collection.count_documents({
            "created_at": {
                "$gte": start_date,
                "$lt": end_date
            }
        })
        print(f"✅ Chunks in last 12 weeks ({start_date.date()} to {end_date.date()}): {count_in_range:,}")

        # Test 3: Search for simple word "ai"
        ai_count = collection.count_documents({
            "text": {"$regex": "\\bai\\b", "$options": "i"}
        })
        print(f"✅ Chunks containing 'ai': {ai_count:,}")

        # Test 4: Search for "ai" in the date range
        ai_in_range = collection.count_documents({
            "text": {"$regex": "\\bai\\b", "$options": "i"},
            "created_at": {
                "$gte": start_date,
                "$lt": end_date
            }
        })
        print(f"✅ Chunks containing 'ai' in last 12 weeks: {ai_in_range:,}")

        # Test 5: Get actual date range of data
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "min_date": {"$min": "$created_at"},
                    "max_date": {"$max": "$created_at"}
                }
            }
        ]
        result = list(collection.aggregate(pipeline))
        if result:
            stats = result[0]
            print(f"\n📅 Actual data date range:")
            print(f"   Earliest: {stats['min_date']}")
            print(f"   Latest: {stats['max_date']}")

        client.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_connection()
