#!/usr/bin/env python3
"""
Test script for the fixed Modal endpoint with memory snapshots
"""

import requests
import time
import json

# Fixed endpoint URLs (from deployment output)
HEALTH_URL = "https://podinsighthq--podinsight-embeddings-fixed-embeddingmodel-b78a32.modal.run"
EMBEDDING_URL = "https://podinsighthq--podinsight-embeddings-fixed-embeddingmodel-d791bf.modal.run"

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

def test_cold_start():
    """Test cold start performance"""
    print("🧪 Testing embedding endpoint (first request - cold start)...")
    print("   This should trigger memory snapshot creation on first deploy")
    print("   Or use existing snapshot on subsequent deploys")

    start = time.time()
    response = requests.post(
        EMBEDDING_URL,
        json={"text": "test cold start with memory snapshots"},
        timeout=60
    )
    elapsed = time.time() - start

    print(f"\n   Status: {response.status_code}")
    print(f"   Total request time: {elapsed:.2f}s")

    if response.status_code == 200:
        data = response.json()
        print(f"   Model load time: {data.get('model_load_time_ms', 0)}ms")
        print(f"   Inference time: {data.get('inference_time_ms', 0)}ms")
        print(f"   Total processing: {data.get('total_time_ms', 0)}ms")
        print(f"   Cold start: {data.get('is_cold_start', 'unknown')}")
        print(f"   Embedding dimension: {data.get('dimension', 0)}")

        # Check if embedding is valid
        embedding = data.get('embedding', [])
        if embedding and embedding[0] is not None:
            print(f"   ✅ Valid embedding generated")
        else:
            print(f"   ❌ Invalid embedding (null values)")

    return elapsed

def test_warm_performance():
    """Test warm requests"""
    print("\n🔥 Testing warm requests (should be <1s):")

    times = []
    for i in range(1, 4):
        time.sleep(0.5)

        start = time.time()
        response = requests.post(
            EMBEDDING_URL,
            json={"text": f"test warm performance request {i}"},
            timeout=10
        )
        elapsed = time.time() - start

        if response.status_code == 200:
            data = response.json()
            times.append(elapsed)
            print(f"   Request {i}: {elapsed:.3f}s total, "
                  f"{data.get('inference_time_ms', 0)}ms inference")
        else:
            print(f"   Request {i}: Failed - {response.status_code}")

    if times:
        avg_time = sum(times) / len(times)
        print(f"\n   Average warm request time: {avg_time:.3f}s")

def main():
    print("🚀 Testing Fixed Modal Endpoint with Memory Snapshots")
    print("=" * 60)

    # Test health check
    test_health()

    # Test cold start
    cold_start_time = test_cold_start()

    # Test warm performance
    test_warm_performance()

    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"   Cold start time: {cold_start_time:.2f}s")

    if cold_start_time < 7:
        print("   ✅ Memory snapshots appear to be working!")
        print("   (Cold start under 7s indicates snapshot restoration)")
    elif cold_start_time < 15:
        print("   ⚠️  Partial improvement - snapshots may be partially working")
    else:
        print("   ❌ Memory snapshots don't appear to be working yet")
        print("   Check Modal logs for 'Creating/Using memory snapshot' messages")

    print("\n💡 Next steps:")
    print("   1. If this was first run, wait 10+ minutes for container to scale down")
    print("   2. Run this test again to see true cold start with snapshots")
    print("   3. Check Modal dashboard logs for snapshot messages")

if __name__ == "__main__":
    main()
