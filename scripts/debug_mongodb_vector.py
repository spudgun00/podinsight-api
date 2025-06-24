#!/usr/bin/env python3
"""
Debug script to test MongoDB Vector Search connectivity and functionality
"""
import os
import sys
import asyncio
import logging
from datetime import datetime

# Add the parent directory to Python path so we can import from api/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.mongodb_vector_search import get_vector_search_handler
from api.embeddings_768d_modal import get_embedder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_mongodb_connection():
    """Test MongoDB connection and basic operations"""
    print("=" * 60)
    print("1. TESTING MONGODB CONNECTION")
    print("=" * 60)
    
    try:
        handler = await get_vector_search_handler()
        
        # Test basic connection
        if handler.client is None:
            print("❌ ERROR: MongoDB client is None")
            return False
            
        if handler.db is None:
            print("❌ ERROR: MongoDB database is None")
            return False
            
        if handler.collection is None:
            print("❌ ERROR: MongoDB collection is None")
            return False
            
        print("✅ MongoDB client created successfully")
        print("✅ Database connected: podinsight")
        print("✅ Collection connected: transcript_chunks_768d")
        
        # Test server connection
        try:
            await handler.client.admin.command('ping')
            print("✅ MongoDB server ping successful")
        except Exception as e:
            print(f"❌ MongoDB server ping failed: {e}")
            return False
            
        # Test collection access
        try:
            count = await handler.collection.count_documents({})
            print(f"✅ Collection accessible - Total documents: {count}")
        except Exception as e:
            print(f"❌ Collection access failed: {e}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection test failed: {e}")
        return False

async def test_vector_index():
    """Test if the vector index exists and is configured correctly"""
    print("\n" + "=" * 60)
    print("2. TESTING VECTOR INDEX CONFIGURATION")
    print("=" * 60)
    
    try:
        handler = await get_vector_search_handler()
        
        # List all indexes
        indexes = await handler.collection.list_indexes().to_list(None)
        print(f"Found {len(indexes)} indexes:")
        
        vector_index_found = False
        for idx in indexes:
            print(f"  - {idx['name']}: {idx.get('key', 'No key info')}")
            if idx['name'] == 'vector_index_768d':
                vector_index_found = True
                print(f"    ✅ Vector index found!")
                print(f"    Definition: {idx}")
        
        if not vector_index_found:
            print("❌ ERROR: vector_index_768d not found!")
            print("Available indexes:")
            for idx in indexes:
                print(f"  - {idx['name']}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Vector index test failed: {e}")
        return False

async def test_document_structure():
    """Test document structure to verify embedding field exists"""
    print("\n" + "=" * 60)
    print("3. TESTING DOCUMENT STRUCTURE")
    print("=" * 60)
    
    try:
        handler = await get_vector_search_handler()
        
        # Get a sample document
        sample_doc = await handler.collection.find_one()
        if not sample_doc:
            print("❌ ERROR: No documents found in collection")
            return False
            
        print("✅ Sample document found")
        print(f"Document fields: {list(sample_doc.keys())}")
        
        # Check for embedding field
        if 'embedding_768d' not in sample_doc:
            print("❌ ERROR: 'embedding_768d' field not found in documents")
            print(f"Available fields: {list(sample_doc.keys())}")
            return False
        else:
            embedding = sample_doc['embedding_768d']
            print(f"✅ 'embedding_768d' field found")
            print(f"Embedding type: {type(embedding)}")
            print(f"Embedding length: {len(embedding) if isinstance(embedding, list) else 'Not a list'}")
            
        # Check other required fields
        required_fields = ['episode_id', 'text', 'start_time', 'end_time']
        for field in required_fields:
            if field in sample_doc:
                print(f"✅ '{field}' field found")
            else:
                print(f"❌ WARNING: '{field}' field not found")
                
        return True
        
    except Exception as e:
        print(f"❌ Document structure test failed: {e}")
        return False

async def test_embedding_generation():
    """Test 768D embedding generation"""
    print("\n" + "=" * 60)
    print("4. TESTING EMBEDDING GENERATION")
    print("=" * 60)
    
    try:
        embedder = get_embedder()
        if embedder is None:
            print("❌ ERROR: Embedder is None")
            return False
            
        print("✅ Embedder loaded successfully")
        
        # Test embedding generation
        test_query = "artificial intelligence and machine learning"
        print(f"Testing with query: '{test_query}'")
        
        embedding = embedder.encode_query(test_query)
        if embedding is None:
            print("❌ ERROR: Embedding generation returned None")
            return False
            
        print(f"✅ Embedding generated successfully")
        print(f"Embedding type: {type(embedding)}")
        print(f"Embedding length: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
        
        return embedding
        
    except Exception as e:
        print(f"❌ Embedding generation test failed: {e}")
        return False

async def test_vector_search_pipeline(embedding):
    """Test the actual vector search pipeline"""
    print("\n" + "=" * 60)
    print("5. TESTING VECTOR SEARCH PIPELINE")
    print("=" * 60)
    
    try:
        handler = await get_vector_search_handler()
        
        print("Testing vector search with minimal parameters...")
        
        # Create the search pipeline manually to debug
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index_768d",
                    "path": "embedding_768d",
                    "queryVector": embedding,
                    "numCandidates": 100,
                    "limit": 5,
                    "filter": {}
                }
            },
            {
                "$addFields": {
                    "score": {"$meta": "vectorSearchScore"}
                }
            },
            {
                "$project": {
                    "episode_id": 1,
                    "feed_slug": 1,
                    "text": 1,
                    "start_time": 1,
                    "end_time": 1,
                    "score": 1
                }
            }
        ]
        
        print("Executing vector search pipeline...")
        cursor = handler.collection.aggregate(pipeline)
        results = await cursor.to_list(None)
        
        print(f"✅ Vector search executed successfully")
        print(f"Number of results: {len(results)}")
        
        if results:
            print("\nFirst result:")
            for key, value in results[0].items():
                if key == 'text':
                    print(f"  {key}: {str(value)[:100]}...")
                else:
                    print(f"  {key}: {value}")
        else:
            print("❌ WARNING: No results returned from vector search")
            
        return results
        
    except Exception as e:
        print(f"❌ Vector search pipeline test failed: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}")
        return False

async def test_supabase_metadata():
    """Test Supabase metadata enrichment"""
    print("\n" + "=" * 60)
    print("6. TESTING SUPABASE METADATA ENRICHMENT")
    print("=" * 60)
    
    try:
        handler = await get_vector_search_handler()
        
        if not handler.supabase:
            print("❌ ERROR: Supabase client not initialized")
            return False
            
        print("✅ Supabase client initialized")
        
        # Test basic Supabase query
        try:
            result = handler.supabase.table('episodes').select('*').limit(1).execute()
            if result.data:
                print("✅ Supabase episodes table accessible")
                sample_episode = result.data[0]
                print(f"Sample episode fields: {list(sample_episode.keys())}")
            else:
                print("❌ WARNING: No episodes found in Supabase")
                
        except Exception as e:
            print(f"❌ Supabase query failed: {e}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Supabase metadata test failed: {e}")
        return False

async def test_full_search_flow():
    """Test the complete search flow as used by the API"""
    print("\n" + "=" * 60)
    print("7. TESTING FULL SEARCH FLOW")
    print("=" * 60)
    
    try:
        handler = await get_vector_search_handler()
        
        # Generate embedding
        embedder = get_embedder()
        test_query = "startup entrepreneurship business"
        embedding = embedder.encode_query(test_query)
        
        print(f"Testing full search flow with query: '{test_query}'")
        
        # Perform vector search using the handler method
        results = await handler.vector_search(
            embedding=embedding,
            limit=3,
            min_score=0.0  # Lowered to match the search file
        )
        
        print(f"✅ Full search flow completed")
        print(f"Results count: {len(results)}")
        
        for i, result in enumerate(results[:2]):  # Show first 2 results
            print(f"\nResult {i+1}:")
            print(f"  Episode ID: {result.get('episode_id')}")
            print(f"  Podcast: {result.get('podcast_name')}")
            print(f"  Episode: {result.get('episode_title')}")
            print(f"  Score: {result.get('score')}")
            print(f"  Published: {result.get('published_at')}")
            print(f"  Text: {result.get('text', '')[:100]}...")
            
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Full search flow test failed: {e}")
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}")
        return False

async def main():
    """Run all diagnostic tests"""
    print("MongoDB Vector Search Diagnostic Tool")
    print(f"Time: {datetime.now()}")
    print(f"MongoDB URI: {os.getenv('MONGODB_URI', 'NOT SET')[:50]}...")
    print(f"Supabase URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
    
    tests = [
        ("MongoDB Connection", test_mongodb_connection),
        ("Vector Index", test_vector_index),
        ("Document Structure", test_document_structure),
        ("Embedding Generation", test_embedding_generation),
    ]
    
    results = {}
    embedding = None
    
    # Run basic tests
    for test_name, test_func in tests:
        try:
            if test_name == "Embedding Generation":
                result = await test_func()
                results[test_name] = result is not False
                embedding = result if result is not False else None
            else:
                results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Run advanced tests if basics pass
    if embedding and results.get("MongoDB Connection") and results.get("Vector Index"):
        try:
            vector_results = await test_vector_search_pipeline(embedding)
            results["Vector Search Pipeline"] = vector_results is not False
        except Exception as e:
            print(f"❌ Vector Search Pipeline test crashed: {e}")
            results["Vector Search Pipeline"] = False
            
        try:
            results["Supabase Metadata"] = await test_supabase_metadata()
        except Exception as e:
            print(f"❌ Supabase Metadata test crashed: {e}")
            results["Supabase Metadata"] = False
            
        try:
            results["Full Search Flow"] = await test_full_search_flow()
        except Exception as e:
            print(f"❌ Full Search Flow test crashed: {e}")
            results["Full Search Flow"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status} {test_name}")
        if passed_test:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Vector search should be working.")
    else:
        print("❌ Some tests failed. Review the output above for issues.")

if __name__ == "__main__":
    asyncio.run(main())