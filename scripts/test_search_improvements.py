#!/usr/bin/env python3
"""
Test script for MongoDB search improvements
Tests both local and production APIs
"""

import asyncio
import httpx
import json
import time
from typing import Dict, List, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test queries that were previously failing
TEST_QUERIES = [
    "What are VCs saying about AI valuations?",
    "Series A funding trends",
    "Startup burn rates",
    "Unicorn valuations 2024",
    "AI agents",
    "Capital efficiency metrics",
    "B2B SaaS revenue multiples"
]

# API endpoints
LOCAL_API = "http://localhost:8000/api/search"
PROD_API = "https://podinsight-api.vercel.app/api/search"


async def test_search_endpoint(api_url: str, query: str) -> Dict[str, Any]:
    """Test a single search query against an API endpoint"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        start_time = time.time()

        try:
            response = await client.post(
                api_url,
                json={"query": query, "limit": 10}
            )

            elapsed_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()

                # Check if we got results
                has_results = len(data.get("results", [])) > 0
                has_answer = bool(data.get("answer", {}).get("answer"))

                # Check if results have both vector and text scores
                hybrid_working = False
                if has_results and "results" in data:
                    first_result = data["results"][0]
                    if "hybrid_score" in first_result and "text_score" in first_result:
                        hybrid_working = first_result["text_score"] > 0

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "elapsed_time": elapsed_time,
                    "has_results": has_results,
                    "has_answer": has_answer,
                    "result_count": len(data.get("results", [])),
                    "hybrid_working": hybrid_working,
                    "first_result_score": data["results"][0].get("score", 0) if has_results else 0,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "elapsed_time": elapsed_time,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}"
                }

        except httpx.TimeoutException:
            return {
                "success": False,
                "elapsed_time": time.time() - start_time,
                "error": "Request timeout (>30s)"
            }
        except Exception as e:
            return {
                "success": False,
                "elapsed_time": time.time() - start_time,
                "error": str(e)
            }


async def run_tests(api_url: str, api_name: str):
    """Run all test queries against an API endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing {api_name}: {api_url}")
    print(f"{'='*60}\n")

    results = []

    for query in TEST_QUERIES:
        print(f"Testing: {query}")
        result = await test_search_endpoint(api_url, query)
        results.append({"query": query, **result})

        # Print summary
        if result["success"]:
            status = "✅" if result["has_results"] else "❌"
            hybrid = "✅" if result.get("hybrid_working") else "❌"
            print(f"  Status: {status} | Time: {result['elapsed_time']:.2f}s | "
                  f"Results: {result['result_count']} | Hybrid: {hybrid} | "
                  f"Score: {result['first_result_score']:.3f}")
        else:
            print(f"  Status: ❌ | Error: {result['error']}")

        # Small delay between requests
        await asyncio.sleep(1)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Summary for {api_name}")
    print(f"{'='*60}")

    successful = sum(1 for r in results if r["success"])
    with_results = sum(1 for r in results if r.get("has_results", False))
    hybrid_working = sum(1 for r in results if r.get("hybrid_working", False))
    avg_time = sum(r["elapsed_time"] for r in results if r["success"]) / max(successful, 1)

    print(f"Successful requests: {successful}/{len(TEST_QUERIES)}")
    print(f"Queries with results: {with_results}/{len(TEST_QUERIES)}")
    print(f"Hybrid search working: {hybrid_working}/{len(TEST_QUERIES)}")
    print(f"Average response time: {avg_time:.2f}s")

    return results


async def main():
    """Run tests against both local and production APIs"""
    print("MongoDB Search Improvements Test Suite")
    print("=====================================")

    # Test production first (before deployment)
    print("\n🔍 Testing PRODUCTION API (before deployment)...")
    prod_results_before = await run_tests(PROD_API, "Production (Before)")

    # If running locally, test local API
    if os.getenv("MONGODB_URI"):
        print("\n🔍 Testing LOCAL API (with improvements)...")
        local_results = await run_tests(LOCAL_API, "Local")
    else:
        print("\n⚠️  Skipping local tests - MONGODB_URI not set")

    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)

    # Compare results
    print("\nProduction API (Before):")
    print(f"- Working queries: {sum(1 for r in prod_results_before if r.get('has_results', False))}/{len(TEST_QUERIES)}")
    print(f"- Hybrid search: {sum(1 for r in prod_results_before if r.get('hybrid_working', False))}/{len(TEST_QUERIES)}")
    print(f"- Avg response time: {sum(r['elapsed_time'] for r in prod_results_before if r['success']) / max(sum(1 for r in prod_results_before if r['success']), 1):.2f}s")

    print("\n✅ Implementation complete!")
    print("Next steps:")
    print("1. Review the test results above")
    print("2. Deploy to Vercel if local tests pass")
    print("3. Run this script again after deployment to verify improvements")


if __name__ == "__main__":
    asyncio.run(main())
