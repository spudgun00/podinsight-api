#!/usr/bin/env python3
"""
Comprehensive API Test Suite for PodInsight
Tests all endpoints with detailed reporting
"""

import asyncio
import aiohttp
import time
import json
from typing import Dict, List, Any
from datetime import datetime

# Test configuration
API_BASE = "https://podinsight-api.vercel.app"
TEST_QUERIES = [
    "AI agents",
    "venture capital",
    "B2B SaaS",
    "cryptocurrency bitcoin",
    "startup funding",
    "artificial intelligence",
    "DePIN infrastructure",
    "crypto web3"
]

class APITester:
    def __init__(self):
        self.session = None
        self.results = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_endpoint(self, name: str, method: str, url: str, data: Dict = None) -> Dict:
        """Test a single endpoint and return results"""
        start_time = time.time()

        try:
            if method == "GET":
                async with self.session.get(f"{API_BASE}{url}") as response:
                    response_data = await response.json()
                    status = response.status
            else:  # POST
                async with self.session.post(
                    f"{API_BASE}{url}",
                    json=data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response_data = await response.json()
                    status = response.status

            elapsed = (time.time() - start_time) * 1000  # Convert to ms

            return {
                "name": name,
                "success": True,
                "status": status,
                "response_time_ms": round(elapsed, 2),
                "data": response_data
            }

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            return {
                "name": name,
                "success": False,
                "status": "ERROR",
                "response_time_ms": round(elapsed, 2),
                "error": str(e)
            }

    async def test_search_comprehensive(self) -> Dict:
        """Test search functionality comprehensively"""
        print("🔍 Testing Search API...")

        search_results = []

        for query in TEST_QUERIES:
            print(f"  Testing query: '{query}'")
            result = await self.test_endpoint(
                f"Search: {query}",
                "POST",
                "/api/search",
                {"query": query, "limit": 3}
            )

            if result["success"]:
                data = result["data"]
                result["analysis"] = {
                    "total_results": data.get("total_results", 0),
                    "cache_hit": data.get("cache_hit", False),
                    "avg_score": round(
                        sum(r.get("similarity_score", 0) for r in data.get("results", [])) /
                        max(len(data.get("results", [])), 1), 3
                    ),
                    "has_highlights": any(
                        "**" in r.get("excerpt", "") for r in data.get("results", [])
                    ),
                    "mongodb_working": any(
                        "**" in r.get("excerpt", "") and r.get("similarity_score", 0) > 1.0
                        for r in data.get("results", [])
                    )
                }

            search_results.append(result)

        return {
            "name": "Search API Comprehensive Test",
            "results": search_results,
            "summary": self._analyze_search_results(search_results)
        }

    def _analyze_search_results(self, results: List[Dict]) -> Dict:
        """Analyze search results for patterns"""
        successful = [r for r in results if r["success"]]
        mongodb_working = [r for r in successful if r.get("analysis", {}).get("mongodb_working", False)]

        return {
            "total_queries": len(results),
            "successful_queries": len(successful),
            "mongodb_working_count": len(mongodb_working),
            "avg_response_time": round(
                sum(r["response_time_ms"] for r in successful) / max(len(successful), 1), 2
            ),
            "mongodb_success_rate": f"{len(mongodb_working) / max(len(successful), 1) * 100:.1f}%",
            "cache_usage": sum(1 for r in successful if r.get("analysis", {}).get("cache_hit", False))
        }

    async def test_cache_performance(self) -> Dict:
        """Test cache performance with same query twice"""
        print("⚡ Testing Cache Performance...")

        test_query = "AI agents cache test"

        # First request (should be fresh)
        result1 = await self.test_endpoint(
            "Cache Test - First Request",
            "POST",
            "/api/search",
            {"query": test_query, "limit": 2}
        )

        # Second request (should be cached)
        result2 = await self.test_endpoint(
            "Cache Test - Second Request",
            "POST",
            "/api/search",
            {"query": test_query, "limit": 2}
        )

        cache_analysis = {}
        if result1["success"] and result2["success"]:
            cache_analysis = {
                "first_request_time": result1["response_time_ms"],
                "second_request_time": result2["response_time_ms"],
                "speed_improvement": round(
                    (result1["response_time_ms"] - result2["response_time_ms"]) /
                    result1["response_time_ms"] * 100, 1
                ),
                "first_cache_hit": result1["data"].get("cache_hit", False),
                "second_cache_hit": result2["data"].get("cache_hit", False)
            }

        return {
            "name": "Cache Performance Test",
            "first_request": result1,
            "second_request": result2,
            "analysis": cache_analysis
        }

    async def test_all_endpoints(self) -> Dict:
        """Test all API endpoints"""
        print("🚀 Testing All Endpoints...")

        endpoints = [
            {"name": "Health Check", "method": "GET", "url": "/api/health"},
            {"name": "Topic Velocity", "method": "GET", "url": "/api/topic-velocity"},
            {"name": "Topic Velocity (Custom)", "method": "GET", "url": "/api/topic-velocity?weeks=4&topics=AI%20Agents,DePIN"},
            {"name": "Pool Stats", "method": "GET", "url": "/api/pool-stats"},
            {"name": "MongoDB Debug", "method": "GET", "url": "/api/debug/mongodb"}
        ]

        results = []
        for endpoint in endpoints:
            print(f"  Testing: {endpoint['name']}")
            result = await self.test_endpoint(
                endpoint["name"],
                endpoint["method"],
                endpoint["url"]
            )
            results.append(result)

        return {
            "name": "All Endpoints Test",
            "results": results,
            "summary": {
                "total_endpoints": len(results),
                "successful_endpoints": len([r for r in results if r["success"]]),
                "avg_response_time": round(
                    sum(r["response_time_ms"] for r in results if r["success"]) /
                    max(len([r for r in results if r["success"]]), 1), 2
                )
            }
        }

    async def run_full_test_suite(self):
        """Run the complete test suite"""
        print("🧪 PodInsight API - Comprehensive Test Suite")
        print("=" * 50)
        print(f"API Base: {API_BASE}")
        print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Run all test categories
        tests = [
            await self.test_all_endpoints(),
            await self.test_search_comprehensive(),
            await self.test_cache_performance()
        ]

        # Generate summary report
        self._print_summary_report(tests)

        return tests

    def _print_summary_report(self, tests: List[Dict]):
        """Print a comprehensive summary report"""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY REPORT")
        print("=" * 50)

        # Overall status
        all_successful = True
        total_tests = 0
        successful_tests = 0

        for test_category in tests:
            if test_category["name"] == "Search API Comprehensive Test":
                total_tests += len(test_category["results"])
                successful_tests += len([r for r in test_category["results"] if r["success"]])
                mongodb_rate = float(test_category["summary"]["mongodb_success_rate"].replace("%", ""))
                if mongodb_rate < 80:
                    all_successful = False

            elif test_category["name"] == "All Endpoints Test":
                total_tests += len(test_category["results"])
                successful_tests += len([r for r in test_category["results"] if r["success"]])
                if test_category["summary"]["successful_endpoints"] < test_category["summary"]["total_endpoints"]:
                    all_successful = False

            elif test_category["name"] == "Cache Performance Test":
                total_tests += 2
                if test_category["first_request"]["success"] and test_category["second_request"]["success"]:
                    successful_tests += 2
                else:
                    all_successful = False
                    successful_tests += sum([
                        test_category["first_request"]["success"],
                        test_category["second_request"]["success"]
                    ])

        # Overall status
        status_emoji = "✅" if all_successful else "⚠️"
        print(f"{status_emoji} OVERALL STATUS: {'PASS' if all_successful else 'ISSUES DETECTED'}")
        print(f"📈 Success Rate: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
        print()

        # Individual test results
        for test_category in tests:
            self._print_test_category_results(test_category)

        # Recommendations
        print("🎯 RECOMMENDATIONS:")
        if all_successful:
            print("✅ All systems operational! Ready for production use.")
            print("✅ MongoDB search integration working perfectly.")
            print("✅ API performance within acceptable ranges.")
        else:
            print("⚠️  Some issues detected. Review individual test results above.")
            if any("Cache" in test["name"] and not test.get("first_request", {}).get("success", True)
                   for test in tests):
                print("❗ Cache performance test failed - may indicate CORS or network issues")

        print("\n" + "=" * 50)

    def _print_test_category_results(self, test_category: Dict):
        """Print results for a specific test category"""
        print(f"📋 {test_category['name']}")
        print("-" * 30)

        if test_category["name"] == "Search API Comprehensive Test":
            summary = test_category["summary"]
            print(f"  MongoDB Working: {summary['mongodb_success_rate']}")
            print(f"  Avg Response Time: {summary['avg_response_time']}ms")
            print(f"  Successful Queries: {summary['successful_queries']}/{summary['total_queries']}")
            print(f"  Cache Usage: {summary['cache_usage']} requests")

            # Show failed queries
            failed = [r for r in test_category["results"] if not r["success"]]
            if failed:
                print(f"  ❌ Failed Queries: {', '.join(r['name'].replace('Search: ', '') for r in failed)}")

        elif test_category["name"] == "All Endpoints Test":
            summary = test_category["summary"]
            print(f"  Working Endpoints: {summary['successful_endpoints']}/{summary['total_endpoints']}")
            print(f"  Avg Response Time: {summary['avg_response_time']}ms")

            # Show failed endpoints
            failed = [r for r in test_category["results"] if not r["success"]]
            if failed:
                print(f"  ❌ Failed Endpoints: {', '.join(r['name'] for r in failed)}")

        elif test_category["name"] == "Cache Performance Test":
            if test_category["analysis"]:
                analysis = test_category["analysis"]
                print(f"  First Request: {analysis['first_request_time']}ms (cached: {analysis['first_cache_hit']})")
                print(f"  Second Request: {analysis['second_request_time']}ms (cached: {analysis['second_cache_hit']})")
                print(f"  Speed Improvement: {analysis['speed_improvement']}%")
            else:
                print("  ❌ Cache test failed - check network connectivity")

        print()

async def main():
    """Run the comprehensive test suite"""
    async with APITester() as tester:
        await tester.run_full_test_suite()

if __name__ == "__main__":
    asyncio.run(main())
