#!/usr/bin/env python3
"""
Test Modal production endpoint performance
"""

import requests
import time
import json

# Production endpoints
HEALTH_URL = "https://podinsighthq--podinsight-embeddings-simple-health-check.modal.run"
EMBEDDING_URL = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"

def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    start = time.time()
    response = requests.get(HEALTH_URL)
    elapsed = time.time() - start
    
    print(f"   Status: {response.status_code}")
    print(f"   Time: {elapsed:.2f}s")
    if response.status_code == 200:
        data = response.json()
        print(f"   GPU: {data.get('gpu_name', 'N/A')}")
        print(f"   PyTorch: {data.get('torch_version', 'N/A')}")
    print()

def test_embedding_performance():
    """Test embedding endpoint performance"""
    print("🧪 Testing embedding endpoint performance...")
    
    # Test 1: First request (potentially cold start)
    print("\n1️⃣ First request (cold start if container was idle):")
    start = time.time()
    response = requests.post(
        EMBEDDING_URL,
        json={"text": "test cold start performance"},
        timeout=60
    )
    elapsed = time.time() - start
    
    print(f"   Status: {response.status_code}")
    print(f"   Total request time: {elapsed:.2f}s")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Model load time: {data.get('model_load_time_ms', 0)}ms")
        print(f"   Inference time: {data.get('inference_time_ms', 0)}ms")
        print(f"   Total processing: {data.get('total_time_ms', 0)}ms")
        print(f"   Embedding dimension: {data.get('dimension', 0)}")
        
        # Check if embedding is valid (not null)
        embedding = data.get('embedding', [])
        if embedding and embedding[0] is not None:
            print(f"   ✅ Valid embedding generated")
        else:
            print(f"   ❌ Invalid embedding (null values)")
    
    # Test 2-5: Warm requests
    print("\n🔥 Warm requests (should be <1s):")
    for i in range(2, 6):
        time.sleep(0.5)  # Small delay between requests
        
        start = time.time()
        response = requests.post(
            EMBEDDING_URL,
            json={"text": f"test warm performance request {i}"},
            timeout=10
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Request {i}: {elapsed:.3f}s total, "
                  f"{data.get('inference_time_ms', 0)}ms inference, "
                  f"{data.get('model_load_time_ms', 0)}ms model load")
        else:
            print(f"   Request {i}: Failed - {response.status_code}")

def test_memory_snapshots():
    """Test if memory snapshots are working"""
    print("\n📸 Testing memory snapshots...")
    print("   Note: If the container was already warm, we can't test cold start.")
    print("   Memory snapshots should reduce cold start from ~10s to ~4s")
    print("   Check Modal dashboard for container startup logs to verify snapshots")

def main():
    print("🚀 Modal Production Endpoint Tests")
    print("=" * 50)
    
    test_health()
    test_embedding_performance()
    test_memory_snapshots()
    
    print("\n✅ Test complete!")
    print("\n📊 Expected Performance:")
    print("   - Cold start: ~4s (with memory snapshots)")
    print("   - Warm requests: <1s (typically 50-200ms)")
    print("   - Model caching: Model load time should be 0ms after first request")

if __name__ == "__main__":
    main()