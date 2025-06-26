#!/usr/bin/env python3
"""Simple test to verify Modal endpoint is working correctly"""

import requests
import json

def test_modal_endpoint():
    """Test the Modal embedding endpoint directly"""
    MODAL_URL = "https://bvjgck--instructor-xl-embeddings-generate-embeddings-web.modal.run/"

    test_queries = [
        "openai",
        "venture capital",
        "artificial intelligence",
        "sequoia capital",
        "founder burnout"
    ]

    print("Testing Modal Embedding Endpoint")
    print("=" * 50)

    for query in test_queries:
        try:
            response = requests.post(
                MODAL_URL,
                json={"texts": [query]},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                embedding = data["embeddings"][0]
                dim = len(embedding)
                first_5 = embedding[:5]
                print(f"✅ '{query}' -> {dim}D embedding [{first_5[0]:.4f}, {first_5[1]:.4f}, ...]")
            else:
                print(f"❌ '{query}' -> Error {response.status_code}")

        except Exception as e:
            print(f"❌ '{query}' -> Exception: {e}")

    print("=" * 50)

if __name__ == "__main__":
    test_modal_endpoint()
