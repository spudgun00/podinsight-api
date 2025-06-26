#!/usr/bin/env python3
"""
Check MongoDB migration status - verify what actually got migrated
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
import json
from pathlib import Path

# Load .env file from the current directory
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

def check_migration_status():
    """Check actual MongoDB document count and content"""

    MONGODB_URI = os.getenv('MONGODB_URI')

    if not MONGODB_URI:
        print("❌ MONGODB_URI not found in environment")
        return

    try:
        print("🔍 Connecting to MongoDB...")
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client['podinsight']

        # Force connection to verify it works
        client.server_info()
        print("✅ Connected to MongoDB successfully")

        # Check collections
        collections = db.list_collection_names()
        print(f"\n📦 Collections found: {collections}")

        # Check transcripts collection
        if 'transcripts' in collections:
            count = db.transcripts.count_documents({})
            print(f"\n📊 Documents in transcripts collection: {count}")

            if count > 0:
                print("\n📄 Sample documents:")
                # Get first few documents
                for i, doc in enumerate(db.transcripts.find().limit(3)):
                    print(f"\n--- Document {i+1} ---")
                    print(f"Episode ID: {doc.get('episode_id', 'N/A')}")
                    print(f"Podcast: {doc.get('podcast_name', 'N/A')}")
                    print(f"Title: {doc.get('episode_title', 'N/A')}")
                    print(f"Word count: {doc.get('word_count', 'N/A')}")
                    print(f"Topics: {doc.get('topics', [])}")

                    # Check if full_text exists and has content
                    full_text = doc.get('full_text', '')
                    if full_text:
                        print(f"Full text length: {len(full_text)} characters")
                        print(f"Text preview: {full_text[:200]}...")
                    else:
                        print("⚠️  No full_text found!")

                    # Check segments
                    segments = doc.get('segments', [])
                    print(f"Segments: {len(segments)} found")
                    if segments and len(segments) > 0:
                        print(f"First segment: {segments[0].get('text', '')[:100]}...")

                # Get migration stats
                print("\n📈 Migration Statistics:")
                # Count documents with full_text
                with_text = db.transcripts.count_documents({'full_text': {'$exists': True, '$ne': ''}})
                print(f"Documents with full_text: {with_text}")

                # Count by podcast
                pipeline = [
                    {'$group': {'_id': '$podcast_name', 'count': {'$sum': 1}}},
                    {'$sort': {'count': -1}}
                ]
                podcasts = list(db.transcripts.aggregate(pipeline))
                print("\nDocuments by podcast:")
                for p in podcasts:
                    print(f"  {p['_id']}: {p['count']}")

                # Check indexes
                indexes = db.transcripts.list_indexes()
                print("\n🔍 Indexes:")
                for idx in indexes:
                    print(f"  {idx['name']}: {idx.get('key', {})}")

            else:
                print("\n⚠️  No documents found in transcripts collection!")
                print("The migration may not have completed successfully.")

        else:
            print("\n❌ No 'transcripts' collection found!")
            print("The migration has not been run or failed to create the collection.")

        # Check for test collection
        if 'test' in collections:
            test_count = db.test.count_documents({})
            print(f"\n🧪 Test collection has {test_count} documents")

    except Exception as e:
        print(f"\n❌ Error checking MongoDB: {e}")
        print("\nPossible issues:")
        print("1. MongoDB URI is incorrect")
        print("2. Network/firewall blocking connection")
        print("3. MongoDB cluster is paused or deleted")

if __name__ == "__main__":
    print("🔍 MongoDB Migration Status Check\n")
    check_migration_status()
