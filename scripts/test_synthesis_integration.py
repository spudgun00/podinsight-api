#!/usr/bin/env python3
"""
Integration test for the answer synthesis feature
Tests the full flow from search to synthesized answer
"""
import asyncio
import os
import sys
import json
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test queries based on the playbook
TEST_QUERIES = [
    "AI agent valuations",
    "seed stage pricing",
    "founder market fit",
    "B2B SaaS metrics",
    "venture capital trends",
    "crypto and web3 investments"
]

async def test_search_endpoint(base_url: str, query: str):
    """Test a single search query"""
    endpoint = f"{base_url}/api/search"

    payload = {
        "query": query,
        "limit": 6,
        "offset": 0
    }

    start_time = time.time()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload) as response:
                elapsed_ms = int((time.time() - start_time) * 1000)

                if response.status == 200:
                    data = await response.json()

                    # Check if answer synthesis worked
                    has_answer = data.get("answer") is not None
                    answer_text = data.get("answer", {}).get("text", "No answer generated")
                    citations_count = len(data.get("answer", {}).get("citations", []))
                    results_count = len(data.get("results", []))

                    # Extract processing time
                    processing_time = data.get("processing_time_ms", elapsed_ms)

                    # Check for superscripts in answer
                    has_superscripts = any(char in answer_text for char in "¹²³⁴⁵⁶⁷⁸⁹")

                    return {
                        "query": query,
                        "success": True,
                        "has_answer": has_answer,
                        "answer_text": answer_text,
                        "citations_count": citations_count,
                        "results_count": results_count,
                        "has_superscripts": has_superscripts,
                        "processing_time_ms": processing_time,
                        "response_time_ms": elapsed_ms,
                        "search_method": data.get("search_method", "unknown")
                    }
                else:
                    error_text = await response.text()
                    return {
                        "query": query,
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}",
                        "response_time_ms": elapsed_ms
                    }

    except Exception as e:
        return {
            "query": query,
            "success": False,
            "error": str(e),
            "response_time_ms": int((time.time() - start_time) * 1000)
        }

async def run_tests(base_url: str):
    """Run all test queries"""
    print(f"\n🧪 Testing Answer Synthesis at {base_url}")
    print("=" * 80)

    # Check if OpenAI key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  WARNING: OPENAI_API_KEY not set - synthesis may fail")

    results = []

    for query in TEST_QUERIES:
        print(f"\n📍 Testing: '{query}'")
        result = await test_search_endpoint(base_url, query)
        results.append(result)

        if result["success"]:
            if result["has_answer"]:
                print(f"✅ Answer generated with {result['citations_count']} citations")
                print(f"   Answer: {result['answer_text'][:100]}...")
                print(f"   Superscripts: {'Yes' if result['has_superscripts'] else 'No'}")
                print(f"   Processing time: {result['processing_time_ms']}ms")
            else:
                print(f"⚠️  No answer generated (search returned {result['results_count']} results)")
                print(f"   Response time: {result['response_time_ms']}ms")
        else:
            print(f"❌ Error: {result['error']}")

        # Small delay between requests
        await asyncio.sleep(0.5)

    # Summary statistics
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)

    successful = [r for r in results if r["success"]]
    with_answers = [r for r in successful if r["has_answer"]]

    print(f"Total queries: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"With answers: {len(with_answers)}")

    if with_answers:
        avg_time = sum(r["processing_time_ms"] for r in with_answers) / len(with_answers)
        max_time = max(r["processing_time_ms"] for r in with_answers)
        print(f"\nAnswer synthesis performance:")
        print(f"  Average: {avg_time:.0f}ms")
        print(f"  Max: {max_time}ms")
        print(f"  Target: <2000ms (p95)")
        print(f"  Status: {'✅ PASS' if max_time < 2000 else '❌ FAIL'}")

        # Check citation quality
        avg_citations = sum(r["citations_count"] for r in with_answers) / len(with_answers)
        print(f"\nCitation statistics:")
        print(f"  Average citations per answer: {avg_citations:.1f}")
        print(f"  Answers with superscripts: {sum(1 for r in with_answers if r['has_superscripts'])}/{len(with_answers)}")

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"synthesis_test_results_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "base_url": base_url,
            "results": results,
            "summary": {
                "total": len(results),
                "successful": len(successful),
                "with_answers": len(with_answers),
                "avg_processing_ms": avg_time if with_answers else None,
                "max_processing_ms": max_time if with_answers else None
            }
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: {filename}")

async def main():
    """Main entry point"""
    # Default to local development
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    await run_tests(base_url)

if __name__ == "__main__":
    asyncio.run(main())
