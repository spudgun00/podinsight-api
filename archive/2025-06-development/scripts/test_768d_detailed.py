#!/usr/bin/env python3
"""
Detailed test to verify 768D Modal.com system and diagnose search issues
"""

import requests
import json
import time

# Configuration
API_BASE_URL = "https://podinsight-api.vercel.app"
MODAL_ENDPOINT = "https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run"

def test_modal_embedding():
    """Test Modal.com embedding generation"""
    print("\n1. TESTING MODAL.COM EMBEDDING GENERATION")
    print("="*50)

    test_query = "artificial intelligence and machine learning"

    try:
        response = requests.post(
            f"{MODAL_ENDPOINT}/embed",
            json={"text": test_query},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            embedding = data.get("embedding", [])

            print(f"✅ Modal endpoint working")
            print(f"✅ Response status: {response.status_code}")
            print(f"✅ Embedding dimensions: {len(embedding)}")
            print(f"✅ First 5 values: {embedding[:5] if embedding else 'N/A'}")

            # Check if it's exactly 768D
            if len(embedding) == 768:
                print("✅ CONFIRMED: Exactly 768 dimensions")
            else:
                print(f"⚠️  WARNING: Expected 768 dimensions, got {len(embedding)}")

            return True, embedding
        else:
            print(f"❌ Modal request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False, None

    except Exception as e:
        print(f"❌ Modal error: {str(e)}")
        return False, None

def test_search_with_lower_threshold():
    """Test search with different score thresholds"""
    print("\n2. TESTING SEARCH WITH DIFFERENT THRESHOLDS")
    print("="*50)

    queries = [
        "artificial intelligence",
        "venture capital",
        "startup funding",
        "podcast"  # Very generic term that should match many documents
    ]

    for query in queries:
        print(f"\nTesting query: '{query}'")

        try:
            response = requests.post(
                f"{API_BASE_URL}/api/search",
                json={"query": query, "limit": 5},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                num_results = len(data.get("results", []))
                search_method = data.get("search_method", "unknown")

                print(f"  Search method: {search_method}")
                print(f"  Results: {num_results}")

                if num_results > 0:
                    # Show score distribution
                    scores = [r.get("similarity_score", 0) for r in data["results"]]
                    print(f"  Score range: {min(scores):.4f} - {max(scores):.4f}")
                    print(f"  First result:")
                    first = data["results"][0]
                    print(f"    - Title: {first.get('episode_title', 'N/A')[:50]}...")
                    print(f"    - Score: {first.get('similarity_score', 0):.4f}")
                    print(f"    - Excerpt: {first.get('excerpt', 'N/A')[:100]}...")
            else:
                print(f"  ❌ Search failed: {response.status_code}")

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")

def test_direct_mongodb_connection():
    """Test if we can get any info about the MongoDB state"""
    print("\n3. CHECKING MONGODB CONNECTION VIA API")
    print("="*50)

    # Try the health endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ API health endpoint working")
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")

def test_search_endpoint_details():
    """Get detailed info about search endpoint behavior"""
    print("\n4. TESTING SEARCH ENDPOINT DETAILS")
    print("="*50)

    # Test with a very simple query
    simple_query = "AI"

    print(f"Testing simple query: '{simple_query}'")

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/search",
            json={"query": simple_query, "limit": 10},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()

            print(f"\nSearch Response Details:")
            print(f"  - Total results: {data.get('total_results', 0)}")
            print(f"  - Search method: {data.get('search_method', 'unknown')}")
            print(f"  - Cache hit: {data.get('cache_hit', False)}")
            print(f"  - Query: {data.get('query', 'N/A')}")
            print(f"  - Limit: {data.get('limit', 'N/A')}")
            print(f"  - Offset: {data.get('offset', 'N/A')}")

            # If we got results, show them
            if data.get('results'):
                print(f"\nResults found! Showing first 3:")
                for i, result in enumerate(data['results'][:3]):
                    print(f"\n  Result {i+1}:")
                    print(f"    - Podcast: {result.get('podcast_name', 'N/A')}")
                    print(f"    - Episode: {result.get('episode_title', 'N/A')[:50]}...")
                    print(f"    - Score: {result.get('similarity_score', 0):.4f}")
                    print(f"    - Has excerpt: {'Yes' if result.get('excerpt') else 'No'}")
                    print(f"    - Has timestamp: {'Yes' if result.get('timestamp') else 'No'}")
            else:
                print("\n⚠️  No results returned - vector index may need configuration")

        else:
            print(f"❌ Search request failed: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Search error: {str(e)}")

def test_768d_specific_endpoint():
    """Test the 768D specific endpoint if available"""
    print("\n5. TESTING 768D SPECIFIC ENDPOINT")
    print("="*50)

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/search_lightweight_768d",
            json={"query": "machine learning", "limit": 3},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 768D endpoint available")
            print(f"Results: {len(data.get('results', []))}")
        elif response.status_code == 404:
            print("⚠️  768D endpoint not found (might be using main search endpoint)")
        else:
            print(f"❌ 768D endpoint error: {response.status_code}")

    except Exception as e:
        print(f"❌ 768D endpoint error: {str(e)}")

def main():
    print("\n" + "="*60)
    print("🚀 DETAILED 768D MODAL.COM SYSTEM VERIFICATION")
    print("="*60)

    # Run all tests
    modal_ok, embedding = test_modal_embedding()
    test_search_with_lower_threshold()
    test_direct_mongodb_connection()
    test_search_endpoint_details()
    test_768d_specific_endpoint()

    # Summary
    print("\n" + "="*60)
    print("📊 DIAGNOSIS SUMMARY")
    print("="*60)

    if modal_ok:
        print("✅ Modal.com integration is working correctly")
        print("✅ 768D embeddings are being generated")
    else:
        print("❌ Modal.com integration has issues")

    print("\n🔍 LIKELY ISSUES:")
    print("1. MongoDB vector index may need lower similarity threshold")
    print("2. Vector index might not be fully built/synced")
    print("3. Embedding field name mismatch (embedding_768d)")
    print("4. Documents might not have 768D embeddings stored")

    print("\n💡 RECOMMENDATIONS:")
    print("1. Check MongoDB Atlas console for index status")
    print("2. Verify documents have 'embedding_768d' field")
    print("3. Consider lowering min_score threshold in search")
    print("4. Check if documents were re-embedded with 768D")

if __name__ == "__main__":
    main()
