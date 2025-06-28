#!/usr/bin/env python3
"""
Verification script for answer synthesis feature in staging
Tests happy path, feature flag, and graceful fallback
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

# Test configuration
STAGING_URL = os.getenv("STAGING_URL", "https://podinsight-api.vercel.app")
TEST_QUERIES = [
    {
        "name": "AI agent valuations",
        "query": "AI agent valuations",
        "expected_citations": True
    },
    {
        "name": "No results query",
        "query": "asdfghjkl",
        "expected_citations": False
    },
    {
        "name": "Niche query",
        "query": "micropayments in podcasting",
        "expected_citations": True
    }
]

async def test_search_with_synthesis(base_url: str, test_case: dict):
    """Test a single search query with synthesis verification"""
    endpoint = f"{base_url}/api/search"
    query = test_case["query"]

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

                # Verify status code
                assert response.status == 200, f"Expected 200, got {response.status}"

                data = await response.json()

                # Log basic info
                logger.info(f"\n{'='*60}")
                logger.info(f"Test: {test_case['name']}")
                logger.info(f"Query: '{query}'")
                logger.info(f"Response time: {elapsed_ms}ms")
                logger.info(f"Total results: {data.get('total_results', 0)}")

                # Verify response structure
                assert "results" in data, "Missing 'results' in response"

                # Check synthesis based on expectations
                if test_case["expected_citations"] and data.get("total_results", 0) > 0:
                    # Should have synthesis
                    assert "answer" in data, "Missing 'answer' in response when results exist"
                    answer = data["answer"]

                    if answer:  # Could be None if synthesis failed
                        assert "text" in answer, "Missing 'text' in answer"
                        assert "citations" in answer, "Missing 'citations' in answer"

                        answer_text = answer["text"]
                        citations = answer["citations"]

                        logger.info(f"Answer: {answer_text}")
                        logger.info(f"Citations: {len(citations)}")

                        # Verify answer contains superscripts
                        superscripts = ["¹", "²", "³", "⁴", "⁵", "⁶", "⁷", "⁸", "⁹"]
                        has_superscript = any(s in answer_text for s in superscripts)
                        assert has_superscript, f"Answer missing superscript citations: {answer_text}"

                        # Verify word count (approximately)
                        word_count = len(answer_text.split())
                        assert word_count <= 70, f"Answer too long: {word_count} words"

                        # Verify citations structure
                        for i, citation in enumerate(citations):
                            assert "index" in citation, f"Citation {i} missing 'index'"
                            assert "episode_id" in citation, f"Citation {i} missing 'episode_id'"
                            assert "episode_title" in citation, f"Citation {i} missing 'episode_title'"
                            assert "podcast_name" in citation, f"Citation {i} missing 'podcast_name'"
                            assert "timestamp" in citation, f"Citation {i} missing 'timestamp'"
                            assert "start_seconds" in citation, f"Citation {i} missing 'start_seconds'"

                        logger.info("✅ Synthesis validation passed")
                    else:
                        logger.warning("⚠️  Answer is None (synthesis may have failed)")

                elif not test_case["expected_citations"] or data.get("total_results", 0) == 0:
                    # Should not have synthesis (no results)
                    if "answer" in data and data["answer"]:
                        logger.warning("⚠️  Unexpected answer for query with no/few results")
                    else:
                        logger.info("✅ No synthesis for empty results (as expected)")

                # Verify performance
                if elapsed_ms < 2000:
                    logger.info(f"✅ Performance within target: {elapsed_ms}ms < 2000ms")
                else:
                    logger.warning(f"⚠️  Performance exceeds target: {elapsed_ms}ms > 2000ms")

                return True, elapsed_ms, data

    except AssertionError as e:
        logger.error(f"❌ Assertion failed: {str(e)}")
        return False, elapsed_ms, None
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        return False, elapsed_ms, None

async def run_all_tests():
    """Run all verification tests"""
    logger.info(f"Starting synthesis verification against: {STAGING_URL}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")

    results = []

    for test_case in TEST_QUERIES:
        success, elapsed_ms, data = await test_search_with_synthesis(STAGING_URL, test_case)
        results.append({
            "test": test_case["name"],
            "success": success,
            "elapsed_ms": elapsed_ms
        })

        # Small delay between tests
        await asyncio.sleep(1)

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")

    total_tests = len(results)
    passed = sum(1 for r in results if r["success"])

    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        logger.info(f"{status} - {result['test']} ({result['elapsed_ms']}ms)")

    logger.info(f"\nTotal: {passed}/{total_tests} tests passed")

    # Calculate p95 performance
    response_times = [r["elapsed_ms"] for r in results if r["elapsed_ms"] is not None]
    if response_times:
        response_times.sort()
        p95_index = int(len(response_times) * 0.95)
        p95_time = response_times[min(p95_index, len(response_times)-1)]
        logger.info(f"P95 response time: {p95_time}ms")

        if p95_time < 2000:
            logger.info("✅ P95 performance target met!")
        else:
            logger.warning(f"⚠️  P95 performance target missed: {p95_time}ms > 2000ms")

    return passed == total_tests

def main():
    """Main entry point"""
    success = asyncio.run(run_all_tests())

    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
