#!/usr/bin/env python3
"""
Debug script to check what dates have chunks in MongoDB
"""

import os
from pymongo import MongoClient
from datetime import datetime, timezone

def check_chunk_dates():
    mongodb_uri = os.getenv('MONGODB_URI')
    if not mongodb_uri:
        print("❌ MONGODB_URI not set")
        return

    # Add database name if missing
    if '/podinsight?' not in mongodb_uri and mongodb_uri.endswith('mongodb.net/?'):
        mongodb_uri = mongodb_uri.replace('mongodb.net/?', 'mongodb.net/podinsight?')
        print(f"✅ Added database name to URI")

    client = MongoClient(mongodb_uri)
    db = client['podinsight']
    collection = db['transcript_chunks_768d']

    print("🔍 Checking chunk date ranges...")

    # Get date range
    pipeline = [
        {
            "$group": {
                "_id": None,
                "min_date": {"$min": "$created_at"},
                "max_date": {"$max": "$created_at"},
                "total_count": {"$sum": 1}
            }
        }
    ]

    result = list(collection.aggregate(pipeline))

    if result:
        stats = result[0]
        print(f"📊 Total chunks: {stats['total_count']:,}")
        print(f"📅 Date range: {stats['min_date']} to {stats['max_date']}")

        # Check recent chunks
        recent_count = collection.count_documents({
            "created_at": {"$gte": datetime(2025, 6, 1, tzinfo=timezone.utc)}
        })
        print(f"🗓️  June 2025 chunks: {recent_count:,}")

        # Sample a few chunks to check text content
        samples = list(collection.find().limit(3))
        print(f"\n📄 Sample chunks:")
        for i, chunk in enumerate(samples, 1):
            text_preview = chunk.get('text', '')[:100] + "..." if len(chunk.get('text', '')) > 100 else chunk.get('text', '')
            print(f"   {i}. {chunk.get('created_at')} - {text_preview}")

        # Check for topic mentions
        print(f"\n🎯 Topic mentions:")
        topics = ["AI", "crypto", "agents", "SaaS", "efficiency"]
        for topic in topics:
            count = collection.count_documents({"text": {"$regex": topic, "$options": "i"}})
            print(f"   {topic}: {count:,} chunks")

    else:
        print("❌ No chunks found in collection")

    client.close()

if __name__ == "__main__":
    check_chunk_dates()
