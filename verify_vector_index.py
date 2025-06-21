#!/usr/bin/env python3
"""
Verify MongoDB vector index and test vector search
"""

import asyncio
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import json

# Load environment variables
load_dotenv()

async def verify_index():
    """Check MongoDB indexes and data"""
    print("🔍 Verifying MongoDB Vector Index...")
    
    # Connect to MongoDB
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client.podinsight
    collection = db.podcast_chunks
    
    # Get collection stats
    stats = db.command("collStats", "podcast_chunks")
    print(f"\n📊 Collection Stats:")
    print(f"   Documents: {stats['count']:,}")
    print(f"   Size: {stats['size'] / 1024 / 1024:.2f} MB")
    
    # List indexes
    print(f"\n📋 Indexes:")
    for index in collection.list_indexes():
        print(f"   - {index['name']}")
        if index['name'] == 'vector_index':
            print(f"     Type: {index.get('type', 'standard')}")
    
    # Check for vector search indexes via listSearchIndexes
    print(f"\n🔍 Checking Atlas Search Indexes...")
    try:
        # Try to get search indexes
        search_indexes = list(collection.list_search_indexes())
        if search_indexes:
            print(f"   Found {len(search_indexes)} search indexes:")
            for idx in search_indexes:
                print(f"   - {idx['name']}")
                print(f"     Status: {idx.get('status', 'unknown')}")
                if 'latestDefinition' in idx:
                    fields = idx['latestDefinition'].get('fields', [])
                    for field in fields:
                        if field.get('type') == 'vector':
                            print(f"     Vector field: {field.get('path')}")
                            print(f"     Dimensions: {field.get('dimensions')}")
                            print(f"     Similarity: {field.get('similarity')}")
        else:
            print("   ❌ No Atlas Search indexes found")
    except Exception as e:
        print(f"   ⚠️  Could not list search indexes: {e}")
    
    # Sample a document to check structure
    print(f"\n📄 Sample Document Structure:")
    sample = collection.find_one({"embedding_768d": {"$exists": True}})
    if sample:
        print(f"   _id: {sample['_id']}")
        print(f"   podcast_name: {sample.get('podcast_name', 'N/A')}")
        print(f"   episode_title: {sample.get('episode_title', 'N/A')}")
        print(f"   text length: {len(sample.get('text', ''))}")
        if 'embedding_768d' in sample:
            embedding = sample['embedding_768d']
            if isinstance(embedding, list):
                print(f"   embedding_768d: {len(embedding)}D vector")
                print(f"   embedding sample: {embedding[:3]}")
            else:
                print(f"   embedding_768d type: {type(embedding)}")
    else:
        print("   ❌ No documents with embedding_768d found")
    
    # Count documents with 768D embeddings
    count_768d = collection.count_documents({"embedding_768d": {"$exists": True}})
    count_total = collection.count_documents({})
    print(f"\n📊 Embedding Coverage:")
    print(f"   Total documents: {count_total:,}")
    print(f"   With 768D embeddings: {count_768d:,}")
    print(f"   Coverage: {count_768d/count_total*100:.1f}%")
    
    client.close()


async def test_vector_search():
    """Test vector search directly"""
    print("\n\n🧪 Testing Vector Search...")
    
    from api.embeddings_768d_modal import get_embedder
    from api.mongodb_vector_search import get_vector_search_handler
    
    embedder = get_embedder()
    vector_handler = await get_vector_search_handler()
    
    # Test query
    query = "AI venture capital"
    print(f"\n🔍 Testing query: '{query}'")
    
    # Generate embedding
    embedding = embedder.encode_query(query)
    if embedding:
        print(f"✅ Generated {len(embedding)}D embedding")
        
        # Try vector search with different min_scores
        for min_score in [0.9, 0.8, 0.7, 0.6, 0.5]:
            results = await vector_handler.vector_search(
                embedding,
                limit=3,
                min_score=min_score
            )
            
            if results:
                print(f"\n📊 Results with min_score={min_score}: {len(results)} found")
                top = results[0]
                print(f"   Top match (score={top['score']:.3f}):")
                print(f"   {top['podcast_name']} - {top['episode_title']}")
                print(f"   Text: {top['text'][:100]}...")
                break
            else:
                print(f"   No results with min_score={min_score}")
    else:
        print("❌ Failed to generate embedding")
    
    await vector_handler.close()


async def main():
    await verify_index()
    await test_vector_search()


if __name__ == "__main__":
    asyncio.run(main())