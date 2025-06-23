#!/usr/bin/env python3
"""
Verify MongoDB 768D embeddings collection and test data
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI')
if not MONGODB_URI:
    print("❌ MONGODB_URI not set in .env file")
    exit(1)

print("🔄 Connecting to MongoDB Atlas...")
client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)

try:
    # Test connection
    client.admin.command('ping')
    print("✅ Connected to MongoDB Atlas")
    
    # Get database and collection
    db = client['podinsight']
    
    # Check for transcript_chunks_768d collection
    collections = db.list_collection_names()
    print(f"\n📦 Available collections: {collections}")
    
    if 'transcript_chunks_768d' in collections:
        print("\n✅ Found transcript_chunks_768d collection")
        
        # Get collection info
        chunks_collection = db['transcript_chunks_768d']
        
        # Count documents
        total_docs = chunks_collection.count_documents({})
        print(f"📊 Total documents: {total_docs}")
        
        # Get unique episodes
        unique_episodes = chunks_collection.distinct('episode_id')
        print(f"📼 Unique episodes: {len(unique_episodes)}")
        
        # Show test episodes mentioned in playbook
        test_episodes = [
            "1216c2e7-42b8-42ca-92d7-bad784f80af2",
            "24fed311-54ac-4dab-805a-ea90cd455b3b", 
            "46dc5446-2e3b-46d6-b4af-24e7c0e8beff",
            "4c2fe9c7-ce0c-4ee2-a93e-993327035281",
            "4df073b5-c70b-4516-af04-7302c5e6d635"
        ]
        
        print("\n🧪 Test episodes status:")
        for episode_id in test_episodes:
            count = chunks_collection.count_documents({'episode_id': episode_id})
            feed_slug = chunks_collection.find_one({'episode_id': episode_id}, {'feed_slug': 1})
            if feed_slug:
                print(f"  - {feed_slug.get('feed_slug', 'unknown')}/{episode_id}: {count} chunks")
            else:
                print(f"  - {episode_id}: Not found")
        
        # Sample a document to see structure
        sample_doc = chunks_collection.find_one()
        if sample_doc:
            print("\n📄 Sample document structure:")
            # Remove embedding data for display
            if 'embedding_768d' in sample_doc:
                sample_doc['embedding_768d'] = f"[{len(sample_doc['embedding_768d'])} float values]"
            print(json.dumps(sample_doc, indent=2, default=str))
            
        # Check for vector search index
        indexes = chunks_collection.list_indexes()
        print("\n🔍 Collection indexes:")
        for index in indexes:
            print(f"  - {index['name']}: {index.get('key', 'N/A')}")
            
    else:
        print("\n⚠️  transcript_chunks_768d collection not found")
        print("The migration might still be in progress...")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
finally:
    client.close()
    print("\n👋 Connection closed")