#!/usr/bin/env python
"""
Test script to verify performance improvement after disabling expand_chunk_context
Expected: Response time should drop from ~21s to ~3s
"""
import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict

API_URL = "https://podinsight-api.vercel.app/api/search"
LOCAL_URL = "http://localhost:8000/api/search"

async def test_search(session: aiohttp.ClientSession, url: str, query: str, limit: int = 10) -> Dict:
    """Test a single search request and measure timing"""
    start_time = time.time()

    try:
        async with session.post(
            url,
            json={"query": query, "limit": limit},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            end_time = time.time()
            response_time = end_time - start_time

            data = await response.json()

            return {
                "success": response.status == 200,
                "status": response.status,
                "response_time": response_time,
                "has_answer": data.get("answer") is not None if response.status == 200 else False,
                "num_results": len(data.get("results", [])) if response.status == 200 else 0,
                "error": data.get("detail") if response.status != 200 else None
            }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "status": 0,
            "response_time": time.time() - start_time,
            "has_answer": False,
            "num_results": 0,
            "error": "Timeout"
        }
    except Exception as e:
        return {
            "success": False,
            "status": 0,
            "response_time": time.time() - start_time,
            "has_answer": False,
            "num_results": 0,
            "error": str(e)
        }

async def run_performance_tests():
    """Run multiple tests to measure performance"""
    test_queries = [
        ("AI valuations", 10),
        ("machine learning", 5),
        ("startup funding", 8),
        ("AI", 1),  # Simple query with 1 result
        ("artificial intelligence trends", 10)  # Complex query
    ]

    async with aiohttp.ClientSession() as session:
        print("🚀 Testing PodInsight API Performance")
        print("=" * 60)
        print(f"Target: {API_URL}")
        print("=" * 60)

        all_times = []

        for query, limit in test_queries:
            print(f"\n📊 Testing: '{query}' (limit={limit})")

            # Run 3 tests for each query
            times = []
            for i in range(3):
                result = await test_search(session, API_URL, query, limit)
                times.append(result["response_time"])

                status_emoji = "✅" if result["success"] else "❌"
                answer_emoji = "💡" if result["has_answer"] else "❓"

                print(f"  Test {i+1}: {status_emoji} {result['response_time']:.2f}s "
                      f"({result['num_results']} results) {answer_emoji}")

                if not result["success"]:
                    print(f"    Error: {result['error']}")

                # Small delay between requests
                await asyncio.sleep(1)

            avg_time = statistics.mean(times)
            all_times.extend(times)
            print(f"  Average: {avg_time:.2f}s")

        print("\n" + "=" * 60)
        print("📈 Overall Statistics:")
        print(f"  Total tests: {len(all_times)}")
        print(f"  Average response time: {statistics.mean(all_times):.2f}s")
        print(f"  Median response time: {statistics.median(all_times):.2f}s")
        print(f"  Min response time: {min(all_times):.2f}s")
        print(f"  Max response time: {max(all_times):.2f}s")

        # Performance verdict
        avg_response = statistics.mean(all_times)
        print("\n🎯 Performance Verdict:")
        if avg_response < 5:
            print("  ✅ EXCELLENT: Response times are production-ready!")
        elif avg_response < 10:
            print("  ⚠️  GOOD: Response times are acceptable but could be better")
        else:
            print("  ❌ POOR: Response times are too slow for production")

        print(f"\n💡 Expected improvement: From ~21s to ~3s")
        print(f"   Actual average: {avg_response:.2f}s")

if __name__ == "__main__":
    asyncio.run(run_performance_tests())
