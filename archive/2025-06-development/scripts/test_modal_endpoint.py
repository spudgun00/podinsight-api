#!/usr/bin/env python3
"""
Test script for Modal endpoint performance validation
Run this after deploying the Modal endpoint to verify performance improvements
"""

import requests
import time
import json
from typing import Dict, List

# Update this with your Modal endpoint URL after deployment
MODAL_ENDPOINT_URL = "https://your-modal-app-name--generate-embedding.modal.run"

def test_cold_start():
    """Test cold start performance (should be ~4s with memory snapshots)"""
    print("\n🧪 Testing Cold Start Performance...")
    print("(First request after container scale-down)")

    start = time.time()
    response = requests.post(
        MODAL_ENDPOINT_URL,
        json={"text": "test cold start performance"},
        timeout=30
    )
    end = time.time()

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Cold start successful in {end-start:.2f}s")
        print(f"   - Model load time: {data.get('model_load_time_ms', 0)/1000:.2f}s")
        print(f"   - Inference time: {data.get('inference_time_ms', 0)/1000:.2f}s")
        print(f"   - GPU available: {data.get('gpu_available', False)}")
        return True
    else:
        print(f"❌ Cold start failed: {response.status_code}")
        return False

def test_warm_performance(num_requests: int = 5):
    """Test warm container performance (should be <1s)"""
    print(f"\n🧪 Testing Warm Performance ({num_requests} requests)...")

    times = []
    for i in range(num_requests):
        start = time.time()
        response = requests.post(
            MODAL_ENDPOINT_URL,
            json={"text": f"test warm performance request {i}"},
            timeout=10
        )
        end = time.time()

        if response.status_code == 200:
            data = response.json()
            request_time = end - start
            times.append(request_time)
            print(f"   Request {i+1}: {request_time:.3f}s (inference: {data.get('inference_time_ms', 0)}ms)")
        else:
            print(f"   Request {i+1}: Failed with status {response.status_code}")

    if times:
        avg_time = sum(times) / len(times)
        print(f"\n✅ Average warm request time: {avg_time:.3f}s")
        return avg_time < 1.0  # Should be under 1 second
    return False

def test_concurrent_requests(num_concurrent: int = 5):
    """Test concurrent request handling"""
    print(f"\n🧪 Testing Concurrent Requests ({num_concurrent} simultaneous)...")

    import concurrent.futures

    def make_request(idx):
        start = time.time()
        try:
            response = requests.post(
                MODAL_ENDPOINT_URL,
                json={"text": f"concurrent request {idx}"},
                timeout=30
            )
            end = time.time()
            return {
                "idx": idx,
                "success": response.status_code == 200,
                "time": end - start,
                "data": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            return {
                "idx": idx,
                "success": False,
                "time": time.time() - start,
                "error": str(e)
            }

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(make_request, i) for i in range(num_concurrent)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    successful = sum(1 for r in results if r["success"])
    avg_time = sum(r["time"] for r in results) / len(results)

    print(f"\n✅ Concurrent test results:")
    print(f"   - Successful: {successful}/{num_concurrent}")
    print(f"   - Average time: {avg_time:.2f}s")

    for r in results:
        status = "✅" if r["success"] else "❌"
        print(f"   {status} Request {r['idx']}: {r['time']:.2f}s")

    return successful == num_concurrent

def test_model_caching():
    """Verify model caching works (model_load_time should be 0ms for warm requests)"""
    print("\n🧪 Testing Model Caching...")

    # First request (might load model)
    response1 = requests.post(
        MODAL_ENDPOINT_URL,
        json={"text": "first request to load model"},
        timeout=30
    )

    if response1.status_code != 200:
        print("❌ First request failed")
        return False

    data1 = response1.json()
    load_time1 = data1.get('model_load_time_ms', 0)

    # Second request (should use cached model)
    time.sleep(1)  # Brief pause
    response2 = requests.post(
        MODAL_ENDPOINT_URL,
        json={"text": "second request should use cache"},
        timeout=10
    )

    if response2.status_code != 200:
        print("❌ Second request failed")
        return False

    data2 = response2.json()
    load_time2 = data2.get('model_load_time_ms', 0)

    print(f"✅ Model caching test:")
    print(f"   - First request model load: {load_time1}ms")
    print(f"   - Second request model load: {load_time2}ms")

    if load_time2 < load_time1 / 10:  # Should be near 0
        print("   ✅ Model caching is working!")
        return True
    else:
        print("   ❌ Model appears to be reloading")
        return False

def main():
    """Run all tests"""
    print("🚀 Modal Endpoint Performance Test Suite")
    print("=" * 50)

    # Check if URL is configured
    if "your-modal-app-name" in MODAL_ENDPOINT_URL:
        print("\n❌ Please update MODAL_ENDPOINT_URL with your actual Modal endpoint URL")
        print("   You can find this in the Modal dashboard after deployment")
        return

    tests_passed = 0
    total_tests = 4

    # Run tests
    if test_cold_start():
        tests_passed += 1

    if test_warm_performance():
        tests_passed += 1

    if test_model_caching():
        tests_passed += 1

    if test_concurrent_requests():
        tests_passed += 1

    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Summary: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print("✅ All tests passed! Modal endpoint is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()
