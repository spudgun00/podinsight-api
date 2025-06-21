#!/usr/bin/env python3
"""
Check MongoDB collections for guid fields
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv
import json

load_dotenv()
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.podinsight

print("🔍 CHECKING FOR GUID FIELDS IN MONGODB")
print("=" * 60)

# Check transcripts collection
print("\n1. TRANSCRIPTS COLLECTION:")
transcript = db.transcripts.find_one()

if transcript:
    fields = sorted(list(transcript.keys()))
    print(f"   Fields available: {fields}")
    
    # Check for guid
    if 'guid' in transcript:
        print(f"\n   ✅ GUID FOUND: {transcript['guid']}")
    else:
        print("\n   ❌ No 'guid' field found")
    
    # Check s3_paths which might contain guid
    if 's3_paths' in transcript:
        print("\n   📁 S3 paths structure:")
        for key, path in transcript['s3_paths'].items():
            print(f"      {key}: {path}")
            # Extract potential guid from path
            if '/' in path:
                parts = path.split('/')
                if len(parts) >= 3:
                    potential_guid = parts[-2]  # Usually feed_slug/guid/file
                    print(f"      → Extracted from path: {potential_guid}")
    
    # Show episode_id for comparison
    print(f"\n   episode_id: {transcript.get('episode_id')}")
    print(f"   podcast_name: {transcript.get('podcast_name')}")

# Check transcript_chunks_768d collection
print("\n\n2. TRANSCRIPT_CHUNKS_768D COLLECTION:")
chunk = db.transcript_chunks_768d.find_one()

if chunk:
    fields = sorted([f for f in chunk.keys() if f != 'embedding_768d'])
    print(f"   Fields available: {fields}")
    
    # Check for guid
    if 'guid' in chunk:
        print(f"\n   ✅ GUID FOUND: {chunk['guid']}")
    else:
        print("\n   ❌ No 'guid' field found")
    
    print(f"\n   episode_id: {chunk.get('episode_id')}")
    print(f"   feed_slug: {chunk.get('feed_slug')}")

# Try to find how guids might be stored
print("\n\n3. SEARCHING FOR GUID PATTERNS:")

# Check if any documents have guid field
transcripts_with_guid = db.transcripts.count_documents({'guid': {'$exists': True}})
chunks_with_guid = db.transcript_chunks_768d.count_documents({'guid': {'$exists': True}})

print(f"   Transcripts with 'guid' field: {transcripts_with_guid}")
print(f"   Chunks with 'guid' field: {chunks_with_guid}")

# Sample a few more documents to be sure
print("\n\n4. CHECKING MULTIPLE DOCUMENTS:")
for i, doc in enumerate(db.transcripts.find().limit(3)):
    print(f"\n   Document {i+1}:")
    print(f"   - episode_id: {doc.get('episode_id')}")
    print(f"   - Has guid field: {'guid' in doc}")
    if 's3_paths' in doc and 'transcript' in doc['s3_paths']:
        path = doc['s3_paths']['transcript']
        parts = path.split('/')
        if len(parts) >= 3:
            print(f"   - GUID from S3 path: {parts[-2]}")

client.close()