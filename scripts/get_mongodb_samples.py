#!/usr/bin/env python3
"""Get sample documents from MongoDB collections"""

import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

mongodb_uri = os.getenv('MONGODB_URI')
if not mongodb_uri:
    print("Error: MONGODB_URI not found in .env file")
    exit(1)

# Connect to MongoDB
client = MongoClient(mongodb_uri)
db = client['podinsight']

print("=== MongoDB Sample Documents ===\n")

# Get sample from episode_metadata
print("1. EPISODE_METADATA Collection Sample:")
print("-" * 50)
metadata_sample = db.episode_metadata.find_one()
if metadata_sample:
    # Convert ObjectId to string for JSON serialization
    metadata_sample['_id'] = str(metadata_sample['_id'])
    print(json.dumps(metadata_sample, indent=2, default=str)[:2000] + "...")

# Get sample from episode_transcripts
print("\n\n2. EPISODE_TRANSCRIPTS Collection Sample:")
print("-" * 50)
transcript_sample = db.episode_transcripts.find_one()
if transcript_sample:
    transcript_sample['_id'] = str(transcript_sample['_id'])
    # Truncate the full_text and segments for display
    if 'full_text' in transcript_sample:
        transcript_sample['full_text'] = transcript_sample['full_text'][:500] + "..."
    if 'segments' in transcript_sample and len(transcript_sample['segments']) > 2:
        transcript_sample['segments'] = transcript_sample['segments'][:2] + ["... more segments ..."]
    print(json.dumps(transcript_sample, indent=2, default=str)[:2000] + "...")

# Get sample from transcript_chunks_768d
print("\n\n3. TRANSCRIPT_CHUNKS_768D Collection Sample:")
print("-" * 50)
chunk_sample = db.transcript_chunks_768d.find_one()
if chunk_sample:
    chunk_sample['_id'] = str(chunk_sample['_id'])
    # Truncate embedding for display
    if 'embedding_768d' in chunk_sample:
        chunk_sample['embedding_768d'] = chunk_sample['embedding_768d'][:5] + ["... 763 more values ..."]
    print(json.dumps(chunk_sample, indent=2, default=str))

# Get indexes
print("\n\n4. MongoDB Indexes:")
print("-" * 50)
for collection_name in ['episode_metadata', 'episode_transcripts', 'transcript_chunks_768d']:
    print(f"\n{collection_name} indexes:")
    indexes = db[collection_name].list_indexes()
    for idx in indexes:
        print(f"  - {idx['name']}: {idx.get('key', {})}")

client.close()