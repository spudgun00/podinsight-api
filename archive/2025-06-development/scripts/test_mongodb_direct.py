#!/usr/bin/env python3
"""
Direct MongoDB test to verify vector search is working
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client["podinsight"]
collection = db["transcript_chunks_768d"]

# Modal endpoint for embeddings
MODAL_URL = "https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run"

def get_embedding(text):
    """Get embedding from Modal endpoint"""
    response = requests.post(
        f"{MODAL_URL}/embed",
        json={"text": text}
    )
    if response.status_code == 200:
        return response.json()["embedding"]
    else:
        raise Exception(f"Modal error: {response.status_code}")

def test_search():
    """Test vector search directly"""

    # Test query
    query = "AI and machine learning"
    print(f"🔍 Testing query: '{query}'")

    # Get embedding
    print("📡 Getting embedding from Modal...")
    try:
        embedding = get_embedding(query)
        print(f"✅ Got embedding (dimensions: {len(embedding)})")
    except Exception as e:
        print(f"❌ Error getting embedding: {e}")
        return

    # Perform vector search
    print("\n🔎 Performing vector search...")
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index_768d",
                "path": "embedding_768d",
                "queryVector": embedding,
                "numCandidates": 100,
                "limit": 5
            }
        },
        {
            "$project": {
                "text": 1,
                "episode_id": 1,
                "feed_slug": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]

    try:
        results = list(collection.aggregate(pipeline))

        if results:
            print(f"✅ SUCCESS! Found {len(results)} results\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. Episode: {result.get('episode_id', 'Unknown')}")
                print(f"   Feed: {result.get('feed_slug', 'Unknown')}")
                print(f"   Score: {result.get('score', 0):.4f}")
                print(f"   Text: {result.get('text', '')[:100]}...")
                print()
        else:
            print("❌ No results found")

    except Exception as e:
        print(f"❌ MongoDB error: {e}")

if __name__ == "__main__":
    print("🚀 Direct MongoDB Vector Search Test")
    print(f"📊 Collection: {collection.name}")
    print(f"📈 Document count: {collection.count_documents({})}")
    print()
    test_search()
    client.close()
