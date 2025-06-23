#!/usr/bin/env python3
"""
Direct test of MongoDB Atlas Vector Search
"""

import os
import time
from dotenv import load_dotenv
from pymongo import MongoClient
import requests

load_dotenv()

# Get embedding from Modal
print("🔄 Getting embedding from Modal...")
query = "AI venture capital investments"
resp = requests.post(
    "https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run/embed",
    json={"text": query}
)
embedding = resp.json()["embedding"]
print(f"✅ Got {len(embedding)}D embedding")

# Connect to MongoDB
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.podinsight
collection = db.transcript_chunks_768d

# Test with different min_scores
print(f"\n🔍 Testing vector search for: '{query}'")
for min_score in [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]:
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index_768d",
                "path": "embedding_768d",
                "queryVector": embedding,
                "numCandidates": 100,
                "limit": 10
            }
        },
        {
            "$addFields": {
                "score": {"$meta": "vectorSearchScore"}
            }
        },
        {
            "$match": {
                "score": {"$gte": min_score}
            }
        },
        {
            "$limit": 5
        },
        {
            "$project": {
                "text": 1,
                "score": 1,
                "feed_slug": 1,
                "_id": 0
            }
        }
    ]
    
    start = time.time()
    results = list(collection.aggregate(pipeline))
    elapsed = time.time() - start
    
    print(f"\nmin_score={min_score}: {len(results)} results in {elapsed:.2f}s")
    
    if results:
        for i, result in enumerate(results[:3]):
            print(f"  {i+1}. Score: {result['score']:.3f}")
            print(f"     Feed: {result['feed_slug']}")
            text = result.get('text', '')
            print(f"     Text length: {len(text)}")
            print(f"     Text: {text.strip()[:200]}...")
        break
    else:
        print(f"  No results above {min_score}")

# Also test without any score filter
print("\n🔍 Testing without score filter (top 5):")
pipeline_no_filter = [
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
        "$addFields": {
            "score": {"$meta": "vectorSearchScore"}
        }
    },
    {
        "$project": {
            "text": 1,
            "score": 1,
            "feed_slug": 1,
            "_id": 0
        }
    }
]

results = list(collection.aggregate(pipeline_no_filter))
print(f"Found {len(results)} results")
for i, result in enumerate(results):
    print(f"  {i+1}. Score: {result['score']:.3f}")
    print(f"     Feed: {result['feed_slug']}")
    print(f"     Text: {result['text'][:100]}...")

client.close()