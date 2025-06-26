#!/usr/bin/env python3
"""
Simple test for 768D vector search - focuses on the critical path
"""

import os
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_modal_direct():
    """Test Modal endpoint directly with requests"""
    print("\n🧪 Testing Modal Endpoint Directly...")

    url = "https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run"

    # Test health
    resp = requests.get(f"{url}/health")
    print(f"✅ Health: {resp.json()}")

    # Test embedding
    query = "AI venture capital trends"
    start = time.time()
    resp = requests.post(f"{url}/embed", json={"text": query})
    elapsed = time.time() - start

    if resp.status_code == 200:
        embedding = resp.json()["embedding"]
        print(f"✅ Embedding: {len(embedding)}D in {elapsed:.2f}s")
        print(f"   First 5 values: {embedding[:5]}")
        return embedding
    else:
        print(f"❌ Error: {resp.status_code} - {resp.text}")
        return None


def test_embeddings_module():
    """Test the embeddings module directly"""
    print("\n🧪 Testing Embeddings Module...")

    from api.embeddings_768d_modal import get_embedder

    embedder = get_embedder()

    queries = [
        "What did Sequoia say about AI valuations?",
        "confidence with humility"
    ]

    for query in queries:
        try:
            start = time.time()
            embedding = embedder.encode_query(query)
            elapsed = time.time() - start

            if embedding:
                print(f"✅ '{query}' → {len(embedding)}D in {elapsed:.2f}s")
            else:
                print(f"❌ '{query}' → Failed")
        except Exception as e:
            print(f"❌ '{query}' → Error: {e}")


def test_api_search():
    """Test the API search endpoint locally"""
    print("\n🧪 Testing API Search Endpoint...")

    # Test via local FastAPI
    url = "http://localhost:8000/api/search"

    queries = [
        "AI agents and automation",
        "venture capital returns"
    ]

    for query in queries:
        try:
            start = time.time()
            resp = requests.post(url, json={
                "query": query,
                "limit": 3
            })
            elapsed = time.time() - start

            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ '{query}':")
                print(f"   Method: {data.get('search_method', 'unknown')}")
                print(f"   Results: {data.get('total_results', 0)}")
                print(f"   Time: {elapsed:.2f}s")

                if data.get('results'):
                    top = data['results'][0]
                    print(f"   Top match: {top.get('podcast_name', 'N/A')} (score: {top.get('similarity_score', 0):.3f})")
            else:
                print(f"❌ '{query}' → {resp.status_code}")
        except Exception as e:
            print(f"❌ '{query}' → Connection error: {e}")
            print("   (Is the API running locally on port 8000?)")


def main():
    print("🚀 Simple 768D Vector Search Test")
    print("=" * 50)

    # Test 1: Modal endpoint
    embedding = test_modal_direct()

    # Test 2: Embeddings module
    test_embeddings_module()

    # Test 3: API search (only if running locally)
    print("\n" + "=" * 50)
    print("To test the API, run: uvicorn api.main:app --reload")
    print("Then run this test again.")
    # test_api_search()


if __name__ == "__main__":
    main()
