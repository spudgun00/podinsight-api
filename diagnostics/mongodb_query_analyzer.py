#!/usr/bin/env python3
"""
MongoDB Query Performance Analyzer for Sentiment API

Analyzes the performance of MongoDB queries used in sentiment analysis
to identify bottlenecks and optimization opportunities.
"""

import os
import time
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
import re

def analyze_mongodb_performance():
    """Analyze MongoDB query performance for sentiment analysis"""

    mongodb_uri = os.getenv('MONGODB_URI')
    if not mongodb_uri:
        print("❌ MONGODB_URI not set!")
        return

    client = MongoClient(mongodb_uri)
    db = client['podinsight']
    collection = db['transcript_chunks_768d']

    print("🔍 MongoDB Query Performance Analysis")
    print("=" * 50)

    # Basic collection stats
    print("\n📊 Collection Statistics:")
    total_docs = collection.estimated_document_count()
    print(f"Total documents: {total_docs:,}")

    # Sample document structure
    print("\n📄 Sample Document Structure:")
    sample = collection.find_one()
    if sample:
        print(f"Fields: {list(sample.keys())}")

        # Check date field format
        if 'published_at' in sample:
            pub_date = sample['published_at']
            print(f"published_at type: {type(pub_date)}")
            print(f"published_at sample: {pub_date}")

        # Check text field
        if 'text' in sample:
            text_len = len(sample['text'])
            print(f"text field length: {text_len} characters")

    # Test date range queries (similar to sentiment API)
    print("\n⏱️  Date Range Query Performance:")
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(weeks=4)

    print(f"Date range: {start_date.date()} to {end_date.date()}")

    # Test basic date query
    start_time = time.time()
    date_query = {
        "published_at": {
            "$gte": start_date,
            "$lt": end_date
        }
    }
    date_count = collection.count_documents(date_query)
    date_time = (time.time() - start_time) * 1000
    print(f"Documents in date range: {date_count:,} ({date_time:.2f}ms)")

    # Test topic regex queries
    print("\n🎯 Topic Query Performance:")
    topics = ["AI", "Crypto", "DePIN", "B2B SaaS"]

    for topic in topics:
        topic_pattern = re.compile(re.escape(topic), re.IGNORECASE)

        # Test regex query performance
        start_time = time.time()
        topic_query = {
            "text": {"$regex": topic_pattern},
            "published_at": {
                "$gte": start_date,
                "$lt": end_date
            }
        }
        topic_count = collection.count_documents(topic_query)
        topic_time = (time.time() - start_time) * 1000
        print(f"{topic}: {topic_count:,} chunks ({topic_time:.2f}ms)")

        # Test sample retrieval
        if topic_count > 0:
            start_time = time.time()
            sample_docs = list(collection.find(topic_query).limit(50))
            sample_time = (time.time() - start_time) * 1000
            print(f"  - Sample retrieval (50 docs): {sample_time:.2f}ms")

    # Test indexing
    print("\n📇 Index Analysis:")
    indexes = list(collection.list_indexes())
    print(f"Total indexes: {len(indexes)}")
    for idx in indexes:
        print(f"  - {idx['name']}: {idx.get('key', 'N/A')}")

    # Estimate full sentiment analysis time
    print("\n⏱️  Sentiment Analysis Time Estimate:")
    weeks = 12
    topics = ["AI Agents", "Capital Efficiency", "DePIN", "B2B SaaS", "Crypto/Web3"]

    total_operations = weeks * len(topics)
    avg_time_per_query = 100  # Conservative estimate in ms
    estimated_time = (total_operations * avg_time_per_query) / 1000

    print(f"Total operations: {total_operations} (weeks × topics)")
    print(f"Estimated time: {estimated_time:.1f} seconds")
    print(f"Vercel timeout: 300 seconds")
    print(f"Status: {'✅ Within limits' if estimated_time < 300 else '❌ Exceeds timeout'}")

    # Optimization recommendations
    print("\n💡 Optimization Recommendations:")

    # Check for text index
    has_text_index = any('text' in str(idx.get('key', '')) for idx in indexes)
    if not has_text_index:
        print("  - ❌ Add text index for faster regex searches")
    else:
        print("  - ✅ Text index found")

    # Check for date index
    has_date_index = any('published_at' in str(idx.get('key', '')) for idx in indexes)
    if not has_date_index:
        print("  - ❌ Add published_at index for faster date queries")
    else:
        print("  - ✅ Date index found")

    # Check collection size
    if total_docs > 100000:
        print("  - ⚠️  Large collection - consider sampling strategy")

    print("  - 💡 Use aggregation pipeline for better performance")
    print("  - 💡 Implement result caching")
    print("  - 💡 Process in batches with pagination")

    client.close()

if __name__ == "__main__":
    analyze_mongodb_performance()
