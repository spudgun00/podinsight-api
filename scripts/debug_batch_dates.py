#!/usr/bin/env python3
"""
Debug script to check date ranges for batch processing
"""

import os
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
import re

def debug_batch_dates():
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

    print("🔍 Debug batch processing date ranges...")

    # Calculate week ranges like batch processor does
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(weeks=12)

    print(f"\n📅 Processing 12 weeks from {start_date.date()} to {end_date.date()}")

    # Check first few weeks
    for week_offset in range(3):
        week_start = start_date + timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=7)

        print(f"\n📅 Week {week_offset + 1}: {week_start.date()} to {week_end.date()}")

        # Count chunks in this week
        week_count = collection.count_documents({
            "created_at": {
                "$gte": week_start,
                "$lt": week_end
            }
        })
        print(f"  Total chunks: {week_count:,}")

        # Test our regex patterns
        if week_count > 0:
            # Test AI pattern
            ai_pattern = "(?=.*\\b(ai|artificial intelligence)\\b)(?=.*\\b(agent|agents)\\b)"
            try:
                ai_count = collection.count_documents({
                    "text": {"$regex": ai_pattern, "$options": "i"},
                    "created_at": {"$gte": week_start, "$lt": week_end}
                })
                print(f"  AI Agents (complex regex): {ai_count}")
            except Exception as e:
                print(f"  AI Agents regex failed: {e}")

            # Try simpler patterns
            simple_ai_count = collection.count_documents({
                "text": {"$regex": "\\bai\\b", "$options": "i"},
                "created_at": {"$gte": week_start, "$lt": week_end}
            })
            print(f"  Simple 'AI' search: {simple_ai_count}")

            crypto_count = collection.count_documents({
                "text": {"$regex": "\\b(crypto|blockchain|web3)\\b", "$options": "i"},
                "created_at": {"$gte": week_start, "$lt": week_end}
            })
            print(f"  Crypto/Web3: {crypto_count}")

            saas_count = collection.count_documents({
                "text": {"$regex": "\\b(saas|software.as.a.service)\\b", "$options": "i"},
                "created_at": {"$gte": week_start, "$lt": week_end}
            })
            print(f"  SaaS: {saas_count}")

    # Check what's actually in the database
    print("\n📊 Database content summary:")
    total = collection.count_documents({})
    print(f"Total chunks: {total:,}")

    # Get date range
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
        print(f"Date range: {stats['min_date']} to {stats['max_date']}")

    client.close()

if __name__ == "__main__":
    debug_batch_dates()
