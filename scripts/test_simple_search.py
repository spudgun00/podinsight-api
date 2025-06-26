#!/usr/bin/env python3
"""
Simple test to see if we can find any chunks with topics
"""

import os
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

def test_simple_search():
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

        print("🔍 Testing simple searches...")

        # Test connection
        count = collection.count_documents({})
        print(f"✅ Connected! Total chunks: {count:,}")

        # Get a sample chunk
        sample = collection.find_one({})
        if sample:
            print(f"\n📝 Sample chunk text (first 200 chars):")
            print(f"{sample.get('text', '')[:200]}...")
            print(f"Created at: {sample.get('created_at')}")

        # Test simple searches without date filters
        print("\n🔍 Testing topic searches (no date filter):")

        searches = [
            ("ai", "\\bai\\b"),
            ("crypto", "\\bcrypto\\b"),
            ("saas", "\\bsaas\\b"),
            ("agent", "\\bagent\\b"),
            ("blockchain", "\\bblockchain\\b"),
            ("efficiency", "\\befficiency\\b")
        ]

        for name, pattern in searches:
            count = collection.count_documents({
                "text": {"$regex": pattern, "$options": "i"}
            }, maxTimeMS=5000)
            print(f"  '{name}': {count:,} chunks")

        # Now test with date filter for recent week
        print("\n🔍 Testing with date filter (last 7 days):")
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        recent_count = collection.count_documents({
            "created_at": {"$gte": week_ago}
        })
        print(f"  Chunks in last 7 days: {recent_count:,}")

        if recent_count > 0:
            for name, pattern in searches[:3]:  # Test first 3
                count = collection.count_documents({
                    "text": {"$regex": pattern, "$options": "i"},
                    "created_at": {"$gte": week_ago}
                })
                print(f"  '{name}' in last 7 days: {count:,} chunks")

        client.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_simple_search()
