#!/usr/bin/env python3
"""
Check what fields exist in the chunks collection
"""

import os
from pymongo import MongoClient

def check_fields():
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

        print("🔍 Checking chunk fields...")

        # Get a sample document
        sample = collection.find_one({})
        if sample:
            print("\n📋 Available fields in chunks:")
            for field in sample.keys():
                value = sample[field]
                if field in ['created_at', 'published_at', 'episode_date', 'date']:
                    print(f"  - {field}: {value} (type: {type(value).__name__})")
                elif field == 'text':
                    print(f"  - {field}: '{value[:50]}...' (length: {len(value)})")
                elif field == 'embedding_768d':
                    print(f"  - {field}: [vector of {len(value)} floats]")
                else:
                    print(f"  - {field}: {type(value).__name__}")

        # Check for date-related fields
        print("\n📅 Checking date fields...")
        date_fields = ['created_at', 'published_at', 'episode_date', 'date', 'timestamp']
        for field in date_fields:
            count = collection.count_documents({field: {"$exists": True}})
            if count > 0:
                print(f"  ✓ {field}: {count:,} documents")
                # Get a sample date
                doc = collection.find_one({field: {"$exists": True}})
                print(f"    Sample: {doc[field]}")

        client.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_fields()
