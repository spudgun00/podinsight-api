#!/usr/bin/env python3
"""
Debug why vector search returns 0 results
"""

import os
from pymongo import MongoClient
import requests
# import numpy as np  # Not available in this environment

# MongoDB connection
uri = os.environ.get('MONGODB_URI', '')
if not uri:
    print('Set MONGODB_URI environment variable')
    exit(1)

client = MongoClient(uri)
db = client.podinsight

print("🔍 Debugging Vector Search...")
print("=" * 60)

# 1. Check if chunks have embeddings
print("\n1. Checking if chunks have embeddings:")
sample_chunk = db.transcript_chunks_768d.find_one()
if sample_chunk and 'embedding_768d' in sample_chunk:
    embedding = sample_chunk.get('embedding_768d', [])
    print(f"  ✅ Chunks have embeddings (length: {len(embedding)})")
    
    # Check embedding values
    if embedding:
        print(f"  First 10 values: {embedding[:10]}")
        print(f"  Min: {min(embedding)}, Max: {max(embedding)}")
        mean = sum(embedding) / len(embedding)
        print(f"  Mean: {mean:.4f}")
        norm = sum(x**2 for x in embedding) ** 0.5
        print(f"  Norm: {norm:.4f}")
else:
    print("  ❌ No embeddings found in chunks!")

# 2. Test with Modal embedding
print("\n2. Generating test embedding from Modal:")
modal_url = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"
response = requests.post(modal_url, json={"text": "openai"})
if response.status_code == 200:
    query_embedding = response.json()["embedding"]
    print(f"  ✅ Got embedding (length: {len(query_embedding)})")
    print(f"  First 10 values: {query_embedding[:10]}")
    norm = sum(x**2 for x in query_embedding) ** 0.5
    print(f"  Norm: {norm:.4f}")
else:
    print(f"  ❌ Modal error: {response.status_code}")
    exit(1)

# 3. Check if any chunks contain "openai" text
print("\n3. Checking if any chunks contain 'openai' text:")
text_matches = db.transcript_chunks_768d.count_documents(
    {"text": {"$regex": "openai", "$options": "i"}}
)
print(f"  Found {text_matches} chunks containing 'openai'")

if text_matches > 0:
    # Get a sample
    sample = db.transcript_chunks_768d.find_one(
        {"text": {"$regex": "openai", "$options": "i"}}
    )
    print(f"  Sample episode_id: {sample.get('episode_id')}")
    print(f"  Sample text: {sample.get('text', '')[:200]}...")
    
    # Check if this chunk has an embedding
    if 'embedding_768d' in sample:
        sample_embedding = sample['embedding_768d']
        print(f"  ✅ This chunk has embedding (length: {len(sample_embedding)})")
        
        # Calculate similarity manually
        # Normalize vectors
        q_norm = sum(x**2 for x in query_embedding) ** 0.5
        s_norm = sum(x**2 for x in sample_embedding) ** 0.5
        
        # Dot product
        dot_product = sum(q * s for q, s in zip(query_embedding, sample_embedding))
        similarity = dot_product / (q_norm * s_norm)
        print(f"  Manual similarity score: {similarity:.4f}")
    else:
        print("  ❌ This chunk has NO embedding!")

# 4. Check vector index
print("\n4. Checking MongoDB vector index:")
indexes = list(db.transcript_chunks_768d.list_indexes())
for idx in indexes:
    print(f"  Index: {idx['name']}")
    if 'vector' in idx['name'].lower():
        print(f"    ✅ Vector index found")

# 5. Try a manual vector search
print("\n5. Attempting manual vector search:")
pipeline = [
    {
        "$vectorSearch": {
            "index": "vector_index_768d",
            "path": "embedding_768d",
            "queryVector": query_embedding,
            "numCandidates": 100,
            "limit": 5
        }
    },
    {
        "$project": {
            "text": 1,
            "score": {"$meta": "vectorSearchScore"}
        }
    }
]

try:
    results = list(db.transcript_chunks_768d.aggregate(pipeline))
    print(f"  Found {len(results)} results")
    for i, result in enumerate(results[:3]):
        print(f"  {i+1}. Score: {result.get('score', 0):.4f}")
        print(f"     Text: {result.get('text', '')[:100]}...")
except Exception as e:
    print(f"  ❌ Error: {e}")

client.close()