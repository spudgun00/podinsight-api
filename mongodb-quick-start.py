#!/usr/bin/env python3
"""
Quick MongoDB setup and test for PodInsight transcripts
Run this to verify MongoDB is working before full migration
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Test MongoDB connection
def test_mongodb_connection():
    """Step 1: Verify MongoDB Atlas is set up correctly"""
    
    # Get your MongoDB URI from Atlas dashboard
    # Format: mongodb+srv://username:password@cluster.mongodb.net/podinsight?retryWrites=true&w=majority
    MONGODB_URI = os.getenv('MONGODB_URI')
    
    if not MONGODB_URI:
        print("❌ Please set MONGODB_URI in .env file")
        print("Get this from MongoDB Atlas dashboard > Connect > Python")
        return False
        
    try:
        client = MongoClient(MONGODB_URI)
        db = client['podinsight']
        
        # Test write
        test_doc = {
            'test': True,
            'message': 'MongoDB connected successfully!'
        }
        result = db.test.insert_one(test_doc)
        print(f"✅ MongoDB connected! Test document ID: {result.inserted_id}")
        
        # Clean up
        db.test.delete_one({'_id': result.inserted_id})
        
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False

# Create collections with indexes
def setup_collections():
    """Step 2: Create collections with proper indexes"""
    
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client['podinsight']
    
    # Create transcripts collection
    if 'transcripts' not in db.list_collection_names():
        db.create_collection('transcripts')
        print("✅ Created transcripts collection")
    
    # Create indexes for search
    db.transcripts.create_index([("full_text", "text")])  # Full-text search
    db.transcripts.create_index("episode_id")  # Fast lookups
    db.transcripts.create_index("published_at")  # Date filtering
    
    print("✅ Created search indexes")
    
    # Show collection info
    stats = db.command("collStats", "transcripts")
    print(f"📊 Collection size: {stats.get('size', 0) / 1024 / 1024:.2f} MB")
    print(f"📊 Document count: {stats.get('count', 0)}")

# Test with one transcript
def test_single_transcript():
    """Step 3: Test storing and searching one transcript"""
    
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client['podinsight']
    
    # Sample transcript (you'll get real ones from S3)
    test_transcript = {
        'episode_id': 'test-123',
        'podcast_name': 'Test Podcast',
        'episode_title': 'AI Agents and the Future',
        'published_at': '2025-06-19',
        'full_text': """
        This episode explores how AI agents are transforming software development.
        We discuss autonomous agents, their capabilities, and how venture capital
        is flowing into this space. The conversation covers B2B SaaS applications
        and the future of AI agent deployment in enterprise environments.
        """,
        'topics': ['AI Agents', 'B2B SaaS'],
        'word_count': 50
    }
    
    # Insert
    result = db.transcripts.insert_one(test_transcript)
    print(f"✅ Inserted test transcript: {result.inserted_id}")
    
    # Search test
    search_results = db.transcripts.find(
        {"$text": {"$search": "AI agents venture capital"}},
        {"score": {"$meta": "textScore"}}
    ).sort([("score", {"$meta": "textScore"})]).limit(5)
    
    for doc in search_results:
        print(f"\n🔍 Found: {doc['episode_title']}")
        print(f"   Score: {doc['score']:.2f}")
        print(f"   Text preview: {doc['full_text'][:100]}...")
    
    # Clean up
    db.transcripts.delete_one({'episode_id': 'test-123'})

if __name__ == "__main__":
    print("🚀 MongoDB Quick Start Test\n")
    
    # Step 1: Test connection
    if test_mongodb_connection():
        
        # Step 2: Set up collections
        setup_collections()
        
        # Step 3: Test transcript storage and search
        test_single_transcript()
        
        print("\n✅ MongoDB is ready for transcript migration!")
        print("\nNext steps:")
        print("1. Run the full migration script")
        print("2. Update search API to use MongoDB")
        print("3. Enjoy REAL search results with actual excerpts!")
    else:
        print("\n❌ Fix MongoDB connection first")
        print("1. Sign up at mongodb.com/atlas")
        print("2. Create M10 cluster")
        print("3. Get connection string")
        print("4. Add to .env as MONGODB_URI")