#!/usr/bin/env python3
"""
Debug script to check chunks and topics in MongoDB
"""

import os
from pymongo import MongoClient
from datetime import datetime, timezone
import re

def debug_chunks_topics():
    mongodb_uri = os.getenv('MONGODB_URI')
    if not mongodb_uri:
        print("❌ MONGODB_URI not set")
        return

    # Add database name if missing
    if '/podinsight?' not in mongodb_uri and mongodb_uri.endswith('mongodb.net/?'):
        mongodb_uri = mongodb_uri.replace('mongodb.net/?', 'mongodb.net/podinsight?')

    client = MongoClient(mongodb_uri)
    db = client['podinsight']
    collection = db['transcript_chunks_768d']

    print("🔍 Checking chunks and topics...")

    # Check total chunks
    total_count = collection.count_documents({})
    print(f"📊 Total chunks: {total_count:,}")

    # Check date range for 2025
    jan_2025_count = collection.count_documents({
        "created_at": {
            "$gte": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "$lt": datetime(2025, 2, 1, tzinfo=timezone.utc)
        }
    })
    print(f"📅 January 2025 chunks: {jan_2025_count:,}")

    # Check for specific topics
    topics = ["AI Agents", "Capital Efficiency", "DePIN", "B2B SaaS", "Crypto/Web3"]

    print("\n🔍 Checking topics in January 2025:")
    for topic in topics:
        # Try exact match first
        exact_count = collection.count_documents({
            "text": {"$regex": re.escape(topic), "$options": "i"},
            "created_at": {
                "$gte": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "$lt": datetime(2025, 1, 8, tzinfo=timezone.utc)  # First week
            }
        })

        # Try partial match
        words = topic.split()
        if len(words) > 1:
            # Search for individual words
            partial_count = collection.count_documents({
                "text": {"$regex": re.escape(words[0]), "$options": "i"},
                "created_at": {
                    "$gte": datetime(2025, 1, 1, tzinfo=timezone.utc),
                    "$lt": datetime(2025, 1, 8, tzinfo=timezone.utc)
                }
            })
            print(f"  {topic}: exact={exact_count}, partial ('{words[0]}')={partial_count}")
        else:
            print(f"  {topic}: {exact_count}")

    # Sample a few chunks to see content
    print("\n📝 Sample chunk texts (first 200 chars):")
    sample_chunks = collection.find({
        "created_at": {
            "$gte": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "$lt": datetime(2025, 1, 8, tzinfo=timezone.utc)
        }
    }).limit(3)

    for i, chunk in enumerate(sample_chunks):
        text = chunk.get('text', '')[:200]
        date = chunk.get('created_at', 'Unknown')
        print(f"\n  Chunk {i+1} ({date}):")
        print(f"  {text}...")

if __name__ == "__main__":
    debug_chunks_topics()
