#!/usr/bin/env python3
"""Test concurrent requests to Modal.com embedding endpoint"""

import requests
import json
import time
import concurrent.futures
from typing import Dict, Any, List
import statistics

# Modal endpoint
ENDPOINT = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"

def make_request(request_id: int) -> Dict[str, Any]:
    """Make a single request to the endpoint"""
    query = f"venture capital investment strategy {request_id}"
    start_time = time.time()

    try:
        response = requests.post(
            ENDPOINT,
            json={"text": query},
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        elapsed = time.time() - start_time

        result = {
            "request_id": request_id,
            "status_code": response.status_code,
            "elapsed_time": elapsed,
            "success": False,
            "error": None
        }

        if response.status_code == 200:
            data = response.json()
            if "embedding" in data and len(data["embedding"]) == 768:
                result["success"] = True
        else:
            result["error"] = f"HTTP {response.status_code}"

    except Exception as e:
        elapsed = time.time() - start_time
        result = {
            "request_id": request_id,
            "status_code": None,
            "elapsed_time": elapsed,
            "success": False,
            "error": str(e)
        }

    return result

def main():
    print("=" * 80)
    print("🔥 CONCURRENT REQUESTS TEST")
    print("Testing Modal.com endpoint under parallel load")
    print("=" * 80)

    # Test parameters
    num_concurrent = 20

    print(f"\n📊 Test Configuration:")
    print(f"   - Concurrent requests: {num_concurrent}")
    print(f"   - Endpoint: {ENDPOINT}")
    print(f"   - Timeout: 30s per request")

    print(f"\n🚀 Launching {num_concurrent} parallel requests...")

    # Execute concurrent requests
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        # Submit all requests
        futures = [executor.submit(make_request, i) for i in range(num_concurrent)]

        # Collect results as they complete
        results = []
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)

            # Print progress
            status = "✅" if result["success"] else "❌"
            print(f"   Request #{result['request_id']:02d}: {status} {result['status_code'] or 'ERROR'} ({result['elapsed_time']:.2f}s)")

    total_time = time.time() - start_time

    # Analyze results
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    response_times = [r["elapsed_time"] for r in successful]

    print("\n" + "=" * 80)
    print("📊 TEST RESULTS")
    print("=" * 80)

    print(f"\n✅ Success Rate: {len(successful)}/{num_concurrent} ({len(successful)/num_concurrent*100:.1f}%)")
    print(f"❌ Failures: {len(failed)}")
    print(f"⏱️  Total Test Time: {total_time:.2f}s")

    if response_times:
        print(f"\n📈 Response Time Statistics (successful requests):")
        print(f"   - Min: {min(response_times):.2f}s")
        print(f"   - Max: {max(response_times):.2f}s")
        print(f"   - Average: {statistics.mean(response_times):.2f}s")
        print(f"   - Median: {statistics.median(response_times):.2f}s")
        if len(response_times) > 1:
            print(f"   - Std Dev: {statistics.stdev(response_times):.2f}s")

    if failed:
        print(f"\n❌ Failed Requests:")
        for r in failed:
            print(f"   - Request #{r['request_id']}: {r['error']}")

    # Performance analysis
    print("\n🎯 Performance Analysis:")
    if response_times:
        avg_time = statistics.mean(response_times)
        if avg_time < 2.0:
            print("   ✅ Excellent: Average response time under 2s")
        elif avg_time < 5.0:
            print("   ⚠️  Good: Average response time under 5s")
        else:
            print("   ❌ Poor: Average response time over 5s")

    print("\n💡 Expected Behavior:")
    print("   - All requests should succeed (100% success rate)")
    print("   - Response times should remain consistent")
    print("   - Modal should auto-scale containers as needed")
    print("   - Check Modal dashboard for container scaling metrics")

    # Success criteria
    if len(successful) == num_concurrent and all(t < 10 for t in response_times):
        print("\n✅ TEST PASSED: All requests succeeded with reasonable response times")
    else:
        print("\n❌ TEST FAILED: Some requests failed or took too long")

if __name__ == "__main__":
    main()
