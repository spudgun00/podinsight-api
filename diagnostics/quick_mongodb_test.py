#!/usr/bin/env python3
"""
Quick MongoDB Test for Sentiment API Debugging

Fast diagnostic script to check basic MongoDB connectivity and data structure
without full performance testing.
"""

import os
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import re

def quick_test():
    """Quick test of MongoDB connection and data"""

    mongodb_uri = os.getenv('MONGODB_URI')
    if not mongodb_uri:
        print("❌ MONGODB_URI not set!")
        return False

    try:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        db = client['podinsight']
        collection = db['transcript_chunks_768d']

        print("🔍 Quick MongoDB Test")
        print("=" * 30)

        # Test connection
        total_docs = collection.estimated_document_count()
        print(f"✅ Connected - {total_docs:,} documents")

        # Check sample document
        sample = collection.find_one()
        if not sample:
            print("❌ No documents found!")
            return False

        print(f"✅ Sample document fields: {list(sample.keys())}")

        # Check published_at field
        if 'published_at' in sample:
            pub_date = sample['published_at']
            print(f"✅ published_at: {type(pub_date)} = {pub_date}")
        else:
            print("❌ No published_at field!")
            return False

        # Test simple date query
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)

        date_query = {
            "published_at": {
                "$gte": start_date,
                "$lt": end_date
            }
        }

        recent_count = collection.count_documents(date_query)
        print(f"✅ Recent documents (7 days): {recent_count:,}")

        # Test topic search
        topic_pattern = re.compile(re.escape("AI"), re.IGNORECASE)
        topic_query = {
            "text": {"$regex": topic_pattern},
            "published_at": {
                "$gte": start_date,
                "$lt": end_date
            }
        }

        ai_count = collection.count_documents(topic_query)
        print(f"✅ AI mentions (7 days): {ai_count:,}")

        # Get sample AI chunk
        if ai_count > 0:
            ai_sample = collection.find_one(topic_query, {"text": 1, "episode_id": 1})
            if ai_sample:
                text_preview = ai_sample['text'][:100] + "..." if len(ai_sample['text']) > 100 else ai_sample['text']
                print(f"✅ Sample AI text: {text_preview}")

        # Test indexes
        indexes = list(collection.list_indexes())
        print(f"✅ Indexes: {len(indexes)}")
        for idx in indexes:
            print(f"   - {idx['name']}")

        client.close()
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = quick_test()
    exit(0 if success else 1)
