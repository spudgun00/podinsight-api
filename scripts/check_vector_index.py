#!/usr/bin/env python3
"""
Check MongoDB Atlas Vector Search Index
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient
import json

load_dotenv()

client = MongoClient(os.getenv('MONGODB_URI'))
db = client.podinsight
collection = db.transcript_chunks_768d

print("🔍 Checking transcript_chunks_768d collection...")

# Collection stats
stats = db.command("collStats", "transcript_chunks_768d")
print(f"\n📊 Collection Stats:")
print(f"   Documents: {stats['count']:,}")
print(f"   Size: {stats['size'] / 1024 / 1024:.2f} MB")

# Check sample document
print(f"\n📄 Sample Document:")
sample = collection.find_one()
if sample:
    print(f"   Fields: {list(sample.keys())}")
    if 'embedding_768d' in sample:
        embedding = sample['embedding_768d']
        print(f"   embedding_768d: {len(embedding)}D vector")
        print(f"   First 3 values: {embedding[:3]}")

# List regular indexes
print(f"\n📋 Regular Indexes:")
for index in collection.list_indexes():
    print(f"   - {index['name']}: {list(index.get('key', {}).keys())}")

# Check Atlas Search indexes
print(f"\n🔍 Atlas Search Indexes:")
try:
    search_indexes = list(collection.list_search_indexes())
    if search_indexes:
        for idx in search_indexes:
            print(f"\n   Index: {idx['name']}")
            print(f"   Status: {idx.get('status')}")
            print(f"   Type: {idx.get('type')}")
            
            # Pretty print the definition
            if 'latestDefinition' in idx:
                print("   Definition:")
                print(json.dumps(idx['latestDefinition'], indent=4))
    else:
        print("   ❌ No Atlas Search indexes found!")
        print("\n   To create a vector search index:")
        print("   1. Go to MongoDB Atlas Console")
        print("   2. Navigate to your cluster > Atlas Search")
        print("   3. Create a new index with this JSON:")
        print(json.dumps({
            "fields": [{
                "type": "vector",
                "path": "embedding_768d",
                "numDimensions": 768,
                "similarity": "cosine"
            }]
        }, indent=4))
except Exception as e:
    print(f"   ⚠️  Error checking search indexes: {e}")

client.close()