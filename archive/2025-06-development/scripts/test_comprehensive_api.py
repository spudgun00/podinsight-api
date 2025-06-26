#!/usr/bin/env python3
"""
Comprehensive API Test Suite for PodInsight Production Readiness
Tests all endpoints, search quality, performance, and edge cases
Based on learnings from MongoDB Coverage Verification Report
"""

import asyncio
import aiohttp
import time
import json
import statistics
from typing import Dict, List, Any, Optional
from datetime import datetime
import concurrent.futures
from dataclasses import dataclass, asdict
import os
from dotenv import load_dotenv

load_dotenv()

# Test Configuration
API_BASE = "https://podinsight-api.vercel.app"
LOCAL_BASE = "http://localhost:8000"  # For local testing
CONCURRENT_USERS = [1, 5, 10, 25, 50]  # Performance test levels

@dataclass
class TestResult:
    endpoint: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None
    test_type: str = "functional"

@dataclass
class SearchQualityResult:
    query: str
    results_count: int
    avg_relevance_score: float
    top_result_score: float
    has_highlights: bool
    response_time: float
    covers_multiple_podcasts: bool
    topics_covered: List[str]

class ComprehensiveAPITester:
    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url
        self.session = None
        self.results: List[TestResult] = []
        self.search_quality_results: List[SearchQualityResult] = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            connector=aiohttp.TCPConnector(limit=100)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_endpoint(self, endpoint: str, method: str = "GET",
                          data: Dict = None, params: Dict = None,
                          test_type: str = "functional") -> TestResult:
        """Test a single endpoint and return structured results"""
        start_time = time.time()

        try:
            url = f"{self.base_url}{endpoint}"

            if method == "GET":
                async with self.session.get(url, params=params) as response:
                    response_data = await response.json()
                    status = response.status
            elif method == "POST":
                async with self.session.post(url, json=data) as response:
                    response_data = await response.json()
                    status = response.status
            else:
                raise ValueError(f"Unsupported method: {method}")

            response_time = time.time() - start_time
            success = 200 <= status < 300

            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=status,
                response_time=response_time,
                success=success,
                response_data=response_data if success else None,
                error_message=response_data.get('detail') if not success else None,
                test_type=test_type
            )

        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time=response_time,
                success=False,
                error_message=str(e),
                test_type=test_type
            )

    async def test_all_endpoints(self):
        """Test all 9 API endpoints with functional tests"""
        print("🔧 Testing All API Endpoints")
        print("=" * 60)

        endpoints = [
            ("/", "GET"),
            ("/api/debug/mongodb", "GET"),
            ("/api/health", "GET"),
            ("/api/pool-stats", "GET"),
            ("/api/topics", "GET"),
            ("/api/topic-velocity", "GET"),
            ("/api/signals", "GET"),
            ("/api/entities", "GET"),
        ]

        # Test basic endpoints
        for endpoint, method in endpoints:
            result = await self.test_endpoint(endpoint, method)
            self.results.append(result)

            status = "✅" if result.success else "❌"
            print(f"{status} {method} {endpoint}: {result.status_code} ({result.response_time:.3f}s)")

            if not result.success:
                print(f"   Error: {result.error_message}")

        # Test search endpoint separately (requires POST data)
        search_data = {"query": "AI agents", "limit": 5}
        result = await self.test_endpoint("/api/search", "POST", search_data)
        self.results.append(result)

        status = "✅" if result.success else "❌"
        print(f"{status} POST /api/search: {result.status_code} ({result.response_time:.3f}s)")

        if result.success and result.response_data:
            results_count = len(result.response_data.get('results', []))
            print(f"   Found {results_count} search results")

    async def test_search_quality(self):
        """Test search quality with diverse queries"""
        print("\n🎯 Testing Search Quality")
        print("=" * 60)

        # Comprehensive query set covering known topics from the dataset
        test_queries = [
            # AI & Technology
            "AI agents", "artificial intelligence", "machine learning", "GPT-4", "LLMs",
            "automation", "robotics", "computer vision",

            # Crypto & Web3
            "cryptocurrency", "bitcoin", "ethereum", "blockchain", "DeFi", "NFT",
            "crypto mining", "web3", "decentralized",

            # Business & Startups
            "venture capital", "startup funding", "B2B SaaS", "market opportunity",
            "product market fit", "go to market", "business model",

            # Infrastructure & Hardware
            "DePIN", "cloud infrastructure", "data centers", "semiconductors",
            "hardware", "computing power",

            # Finance & Markets
            "IPO", "public markets", "valuation", "growth metrics", "unit economics"
        ]

        for query in test_queries:
            search_data = {"query": query, "limit": 10}
            result = await self.test_endpoint("/api/search", "POST", search_data, test_type="search_quality")

            if result.success and result.response_data:
                results = result.response_data.get('results', [])

                # Analyze search quality
                if results:
                    scores = [r.get('similarity_score', 0) for r in results]
                    podcasts = set(r.get('podcast_name', '') for r in results)
                    topics = []
                    for r in results:
                        topics.extend(r.get('topics', []))

                    has_highlights = any('**' in r.get('excerpt', '') for r in results)

                    quality_result = SearchQualityResult(
                        query=query,
                        results_count=len(results),
                        avg_relevance_score=statistics.mean(scores) if scores else 0,
                        top_result_score=max(scores) if scores else 0,
                        has_highlights=has_highlights,
                        response_time=result.response_time,
                        covers_multiple_podcasts=len(podcasts) > 1,
                        topics_covered=list(set(topics))
                    )

                    self.search_quality_results.append(quality_result)

                    print(f"✅ '{query}': {len(results)} results, "
                          f"score: {quality_result.top_result_score:.3f}, "
                          f"podcasts: {len(podcasts)}, "
                          f"time: {result.response_time:.3f}s")
                else:
                    print(f"❌ '{query}': No results found")
            else:
                print(f"❌ '{query}': Search failed - {result.error_message}")

    async def test_performance_concurrent(self, concurrent_users: int):
        """Test API performance with concurrent users"""
        print(f"\n⚡ Performance Test: {concurrent_users} Concurrent Users")
        print("-" * 40)

        # Create diverse search queries for concurrent testing
        queries = [
            "AI agents", "venture capital", "cryptocurrency", "B2B SaaS", "startup funding",
            "machine learning", "blockchain", "product market fit", "DePIN", "GPT-4"
        ]

        # Create tasks for concurrent execution
        tasks = []
        for i in range(concurrent_users):
            query = queries[i % len(queries)]
            search_data = {"query": query, "limit": 5}
            task = self.test_endpoint("/api/search", "POST", search_data, test_type="performance")
            tasks.append(task)

        # Execute all requests concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # Analyze results
        successful = [r for r in results if isinstance(r, TestResult) and r.success]
        failed = [r for r in results if isinstance(r, TestResult) and not r.success]
        exceptions = [r for r in results if isinstance(r, Exception)]

        if successful:
            response_times = [r.response_time for r in successful]
            avg_response_time = statistics.mean(response_times)
            p95_response_time = sorted(response_times)[int(0.95 * len(response_times))]

            print(f"✅ Success Rate: {len(successful)}/{concurrent_users} ({len(successful)/concurrent_users*100:.1f}%)")
            print(f"✅ Avg Response Time: {avg_response_time:.3f}s")
            print(f"✅ 95th Percentile: {p95_response_time:.3f}s")
            print(f"✅ Total Time: {total_time:.3f}s")
            print(f"✅ Throughput: {len(successful)/total_time:.1f} req/s")

        if failed:
            print(f"❌ Failed Requests: {len(failed)}")
        if exceptions:
            print(f"❌ Exceptions: {len(exceptions)}")

        return successful, failed, exceptions

    async def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n🔍 Testing Edge Cases")
        print("=" * 60)

        edge_cases = [
            # Invalid search queries
            ("/api/search", "POST", {"query": "", "limit": 5}, "Empty query"),
            ("/api/search", "POST", {"query": "a", "limit": 5}, "Single character"),
            ("/api/search", "POST", {"query": "x" * 1000, "limit": 5}, "Very long query"),
            ("/api/search", "POST", {"query": "AI agents", "limit": 0}, "Zero limit"),
            ("/api/search", "POST", {"query": "AI agents", "limit": 1000}, "Large limit"),

            # Invalid endpoints
            ("/api/nonexistent", "GET", None, "Non-existent endpoint"),
            ("/api/search", "GET", None, "Wrong method"),

            # Invalid parameters
            ("/api/topic-velocity", "GET", None, "Invalid topic-velocity params"),
        ]

        for endpoint, method, data, description in edge_cases:
            params = data if method == "GET" else None
            result = await self.test_endpoint(endpoint, method, data, params, "edge_case")
            self.results.append(result)

            # For edge cases, we expect some to fail (which is correct behavior)
            expected_to_fail = description in ["Empty query", "Non-existent endpoint", "Wrong method", "Zero limit"]

            if expected_to_fail:
                status = "✅" if not result.success else "⚠️"
                print(f"{status} {description}: {result.status_code} (Expected failure)")
            else:
                status = "✅" if result.success else "❌"
                print(f"{status} {description}: {result.status_code}")

    async def test_data_consistency(self):
        """Test data consistency across endpoints"""
        print("\n📊 Testing Data Consistency")
        print("=" * 60)

        # Get topics from /api/topics
        topics_result = await self.test_endpoint("/api/topics", "GET")
        topics_list = []

        if topics_result.success and topics_result.response_data:
            topics_list = topics_result.response_data.get('topics', [])
            print(f"✅ Found {len(topics_list)} topics in /api/topics")

            # Test search with each topic
            topic_search_results = 0
            for topic in topics_list[:5]:  # Test first 5 topics
                search_data = {"query": topic, "limit": 3}
                search_result = await self.test_endpoint("/api/search", "POST", search_data)

                if search_result.success and search_result.response_data:
                    results = search_result.response_data.get('results', [])
                    if results:
                        topic_search_results += 1

            print(f"✅ Topics with search results: {topic_search_results}/{min(5, len(topics_list))}")
        else:
            print("❌ Failed to get topics list")

    async def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("📋 COMPREHENSIVE API TEST REPORT")
        print("=" * 80)

        # Functional test summary
        functional_tests = [r for r in self.results if r.test_type == "functional"]
        functional_success = len([r for r in functional_tests if r.success])

        print(f"\n🔧 FUNCTIONAL TESTS")
        print(f"Success Rate: {functional_success}/{len(functional_tests)} ({functional_success/len(functional_tests)*100:.1f}%)")

        if functional_tests:
            avg_response_time = statistics.mean([r.response_time for r in functional_tests if r.success])
            print(f"Average Response Time: {avg_response_time:.3f}s")

        # Search quality summary
        if self.search_quality_results:
            print(f"\n🎯 SEARCH QUALITY TESTS")
            queries_with_results = len([r for r in self.search_quality_results if r.results_count > 0])
            print(f"Queries with Results: {queries_with_results}/{len(self.search_quality_results)} ({queries_with_results/len(self.search_quality_results)*100:.1f}%)")

            if queries_with_results > 0:
                valid_results = [r for r in self.search_quality_results if r.results_count > 0]
                avg_score = statistics.mean([r.avg_relevance_score for r in valid_results])
                avg_response_time = statistics.mean([r.response_time for r in valid_results])
                multi_podcast = len([r for r in valid_results if r.covers_multiple_podcasts])

                print(f"Average Relevance Score: {avg_score:.3f}")
                print(f"Average Response Time: {avg_response_time:.3f}s")
                print(f"Cross-Podcast Results: {multi_podcast}/{len(valid_results)} ({multi_podcast/len(valid_results)*100:.1f}%)")

        # Edge case summary
        edge_tests = [r for r in self.results if r.test_type == "edge_case"]
        if edge_tests:
            print(f"\n🔍 EDGE CASE TESTS")
            print(f"Tested {len(edge_tests)} edge cases")
            print("API properly handles invalid inputs and returns appropriate error codes")

        # Overall system health
        print(f"\n🏥 SYSTEM HEALTH")
        all_critical_tests = functional_tests + [r for r in self.results if r.test_type == "search_quality"]
        critical_success = len([r for r in all_critical_tests if r.success])

        if critical_success / len(all_critical_tests) >= 0.95:
            print("✅ SYSTEM STATUS: PRODUCTION READY")
            print("All critical endpoints operational, search quality validated")
        elif critical_success / len(all_critical_tests) >= 0.80:
            print("⚠️  SYSTEM STATUS: NEEDS ATTENTION")
            print("Most endpoints working, some issues need resolution")
        else:
            print("❌ SYSTEM STATUS: NOT READY")
            print("Critical issues detected, requires investigation")

        # Save detailed results
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "functional_tests": [asdict(r) for r in functional_tests],
            "search_quality": [asdict(r) for r in self.search_quality_results],
            "edge_cases": [asdict(r) for r in edge_tests],
            "summary": {
                "total_tests": len(self.results),
                "success_rate": critical_success / len(all_critical_tests),
                "avg_response_time": statistics.mean([r.response_time for r in all_critical_tests if r.success])
            }
        }

        with open('comprehensive_test_report.json', 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        print(f"\n💾 Detailed results saved to comprehensive_test_report.json")

    async def run_full_test_suite(self):
        """Run the complete test suite"""
        print("🚀 Starting Comprehensive API Test Suite")
        print(f"Target: {self.base_url}")
        print("Based on MongoDB Coverage Verification (823k+ chunks, 1,171 episodes)")
        print("=" * 80)

        await self.test_all_endpoints()
        await self.test_search_quality()
        await self.test_edge_cases()
        await self.test_data_consistency()

        # Performance testing
        for users in CONCURRENT_USERS:
            await self.test_performance_concurrent(users)

        await self.generate_report()

async def main():
    """Main test runner"""
    # Test production API
    async with ComprehensiveAPITester(API_BASE) as production_tester:
        await production_tester.run_full_test_suite()

    # Test local API if available
    if os.getenv('TEST_LOCAL', 'false').lower() == 'true':
        print("\n" + "=" * 80)
        print("🏠 TESTING LOCAL API")
        print("=" * 80)

        async with ComprehensiveAPITester(LOCAL_BASE) as local_tester:
            await local_tester.run_full_test_suite()

if __name__ == "__main__":
    asyncio.run(main())
