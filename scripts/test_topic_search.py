#!/usr/bin/env python3
"""
Test script to check if topics are found in chunks
"""

import os
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
import re

def test_topic_search():
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

    print("🔍 Testing topic search in chunks...")

    # Define topics
    topics = ["AI Agents", "Capital Efficiency", "DePIN", "B2B SaaS", "Crypto/Web3"]

    # Test for recent week (W1 would be 12 weeks ago from now)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(weeks=12)
    week1_start = start_date
    week1_end = week1_start + timedelta(days=7)

    print(f"\n📅 Week 1 date range: {week1_start.date()} to {week1_end.date()}")

    # Check total chunks in this week
    week_total = collection.count_documents({
        "created_at": {
            "$gte": week1_start,
            "$lt": week1_end
        }
    })
    print(f"📊 Total chunks in week 1: {week_total:,}")

    print("\n🎯 Topic search results for week 1:")
    for topic in topics:
        topic_pattern = re.compile(re.escape(topic), re.IGNORECASE)

        # Count chunks with this topic
        count = collection.count_documents({
            "text": {"$regex": topic_pattern},
            "created_at": {
                "$gte": week1_start,
                "$lt": week1_end
            }
        })

        # Try looser search
        words = topic.lower().split()
        loose_count = 0
        if len(words) > 1:
            # Search for just the main word
            main_word = words[0] if words[0] != "ai" else words[1]
            loose_count = collection.count_documents({
                "text": {"$regex": main_word, "$options": "i"},
                "created_at": {
                    "$gte": week1_start,
                    "$lt": week1_end
                }
            })

        print(f"  {topic}: exact={count}, loose='{words[0] if len(words) > 1 else topic}'={loose_count}")

    # Sample some chunks to see what's actually in the text
    print("\n📝 Sample chunks from week 1:")
    samples = collection.find({
        "created_at": {
            "$gte": week1_start,
            "$lt": week1_end
        }
    }).limit(5)

    for i, chunk in enumerate(samples, 1):
        text = chunk.get('text', '')[:300]
        print(f"\n  Chunk {i}:")
        print(f"  {text}...")

    # Try searching for more general tech terms
    print("\n🔍 General tech term search in week 1:")
    general_terms = ["AI", "crypto", "SaaS", "web3", "blockchain", "startup", "agent", "efficiency"]
    for term in general_terms:
        count = collection.count_documents({
            "text": {"$regex": term, "$options": "i"},
            "created_at": {
                "$gte": week1_start,
                "$lt": week1_end
            }
        })
        print(f"  '{term}': {count:,} chunks")

    client.close()

if __name__ == "__main__":
    test_topic_search()
