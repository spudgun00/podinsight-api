#!/usr/bin/env python3
"""
Production Monitoring and Health Check System
Continuous monitoring for PodInsight API production readiness
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import statistics
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class HealthCheckResult:
    timestamp: str
    endpoint: str
    status: str  # "healthy", "degraded", "unhealthy"
    response_time: float
    status_code: int
    error_message: Optional[str] = None
    details: Optional[Dict] = None

@dataclass
class SearchQualityMetric:
    timestamp: str
    query: str
    results_found: int
    avg_relevance: float
    response_time: float
    success: bool

class ProductionMonitor:
    def __init__(self, api_base: str = "https://podinsight-api.vercel.app"):
        self.api_base = api_base
        self.session = None
        self.health_results: List[HealthCheckResult] = []
        self.search_metrics: List[SearchQualityMetric] = []

        # Health check thresholds
        self.response_time_threshold = 2.0  # seconds
        self.search_quality_threshold = 0.5  # minimum relevance score

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=20)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def check_endpoint_health(self, endpoint: str, method: str = "GET",
                                   data: Dict = None) -> HealthCheckResult:
        """Check health of a specific endpoint"""
        start_time = time.time()
        timestamp = datetime.now().isoformat()

        try:
            url = f"{self.api_base}{endpoint}"

            if method == "GET":
                async with self.session.get(url) as response:
                    response_data = await response.json()
                    status_code = response.status
            elif method == "POST":
                async with self.session.post(url, json=data) as response:
                    response_data = await response.json()
                    status_code = response.status
            else:
                raise ValueError(f"Unsupported method: {method}")

            response_time = time.time() - start_time

            # Determine health status
            if 200 <= status_code < 300:
                if response_time <= self.response_time_threshold:
                    status = "healthy"
                else:
                    status = "degraded"
            else:
                status = "unhealthy"

            return HealthCheckResult(
                timestamp=timestamp,
                endpoint=endpoint,
                status=status,
                response_time=response_time,
                status_code=status_code,
                details=response_data
            )

        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                timestamp=timestamp,
                endpoint=endpoint,
                status="unhealthy",
                response_time=response_time,
                status_code=0,
                error_message=str(e)
            )

    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check on all endpoints"""
        logger.info("Starting comprehensive health check")

        # Core endpoints to monitor
        endpoints = [
            ("/api/health", "GET"),
            ("/api/debug/mongodb", "GET"),
            ("/api/topics", "GET"),
            ("/api/pool-stats", "GET"),
        ]

        # Search endpoint (requires POST data)
        search_data = {"query": "AI agents", "limit": 3}
        endpoints.append(("/api/search", "POST", search_data))

        results = []
        for endpoint_config in endpoints:
            if len(endpoint_config) == 2:
                endpoint, method = endpoint_config
                result = await self.check_endpoint_health(endpoint, method)
            else:
                endpoint, method, data = endpoint_config
                result = await self.check_endpoint_health(endpoint, method, data)

            results.append(result)
            self.health_results.append(result)

        # Calculate overall health
        healthy_count = len([r for r in results if r.status == "healthy"])
        degraded_count = len([r for r in results if r.status == "degraded"])
        unhealthy_count = len([r for r in results if r.status == "unhealthy"])

        overall_status = "healthy"
        if unhealthy_count > 0:
            overall_status = "unhealthy"
        elif degraded_count > 0:
            overall_status = "degraded"

        avg_response_time = statistics.mean([r.response_time for r in results])

        health_summary = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "healthy_endpoints": healthy_count,
            "degraded_endpoints": degraded_count,
            "unhealthy_endpoints": unhealthy_count,
            "total_endpoints": len(results),
            "avg_response_time": avg_response_time,
            "individual_results": [asdict(r) for r in results]
        }

        logger.info(f"Health check complete: {overall_status} "
                   f"({healthy_count}/{len(results)} healthy, "
                   f"avg response: {avg_response_time:.3f}s)")

        return health_summary

    async def test_search_quality(self) -> SearchQualityMetric:
        """Test search quality with a sample query"""
        test_queries = [
            "artificial intelligence",
            "venture capital",
            "blockchain technology",
            "startup funding",
            "machine learning"
        ]

        # Rotate through queries to test different aspects
        query = test_queries[int(time.time()) % len(test_queries)]
        timestamp = datetime.now().isoformat()

        try:
            start_time = time.time()
            search_data = {"query": query, "limit": 5}

            async with self.session.post(f"{self.api_base}/api/search", json=search_data) as response:
                response_data = await response.json()
                response_time = time.time() - start_time

                if response.status == 200:
                    results = response_data.get('results', [])

                    if results:
                        relevance_scores = [r.get('similarity_score', 0) for r in results]
                        avg_relevance = statistics.mean(relevance_scores)
                        success = avg_relevance >= self.search_quality_threshold
                    else:
                        avg_relevance = 0
                        success = False

                    metric = SearchQualityMetric(
                        timestamp=timestamp,
                        query=query,
                        results_found=len(results),
                        avg_relevance=avg_relevance,
                        response_time=response_time,
                        success=success
                    )

                    self.search_metrics.append(metric)
                    logger.info(f"Search quality test: '{query}' -> "
                               f"{len(results)} results, "
                               f"relevance: {avg_relevance:.3f}, "
                               f"time: {response_time:.3f}s")

                    return metric
                else:
                    logger.error(f"Search quality test failed: HTTP {response.status}")

        except Exception as e:
            logger.error(f"Search quality test error: {e}")

        # Return failed metric
        return SearchQualityMetric(
            timestamp=timestamp,
            query=query,
            results_found=0,
            avg_relevance=0,
            response_time=999,
            success=False
        )

    async def check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            async with self.session.get(f"{self.api_base}/api/debug/mongodb") as response:
                if response.status == 200:
                    debug_data = await response.json()

                    connectivity = {
                        "timestamp": datetime.now().isoformat(),
                        "mongodb_connected": debug_data.get("connection") == "connected",
                        "mongodb_uri_set": debug_data.get("mongodb_uri_set", False),
                        "test_searches": debug_data.get("test_searches", {}),
                        "database_name": debug_data.get("database_name"),
                        "collection_name": debug_data.get("collection_name")
                    }

                    # Check if test searches are working
                    test_searches = debug_data.get("test_searches", {})
                    working_searches = len([s for s in test_searches.values()
                                          if isinstance(s, dict) and s.get("count", 0) > 0])

                    connectivity["working_search_queries"] = working_searches
                    connectivity["total_test_queries"] = len(test_searches)

                    logger.info(f"Database connectivity: "
                               f"MongoDB {'connected' if connectivity['mongodb_connected'] else 'disconnected'}, "
                               f"{working_searches}/{len(test_searches)} test queries working")

                    return connectivity
                else:
                    logger.error(f"Database connectivity check failed: HTTP {response.status}")

        except Exception as e:
            logger.error(f"Database connectivity check error: {e}")

        return {
            "timestamp": datetime.now().isoformat(),
            "mongodb_connected": False,
            "error": "Failed to check database connectivity"
        }

    async def performance_benchmark(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """Run performance benchmark for specified duration"""
        logger.info(f"Starting {duration_minutes}-minute performance benchmark")

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        response_times = []
        success_count = 0
        error_count = 0

        # Test queries for performance testing
        test_queries = [
            "AI agents", "venture capital", "cryptocurrency", "startup funding",
            "machine learning", "blockchain", "B2B SaaS", "product market fit"
        ]

        while time.time() < end_time:
            query = test_queries[int(time.time()) % len(test_queries)]

            try:
                request_start = time.time()
                search_data = {"query": query, "limit": 5}

                async with self.session.post(f"{self.api_base}/api/search", json=search_data) as response:
                    await response.json()  # Consume response
                    request_time = time.time() - request_start

                    if response.status == 200:
                        success_count += 1
                        response_times.append(request_time)
                    else:
                        error_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"Benchmark request failed: {e}")

            # Wait before next request to avoid overwhelming the server
            await asyncio.sleep(0.5)

        # Calculate performance metrics
        total_requests = success_count + error_count
        success_rate = success_count / total_requests if total_requests > 0 else 0

        benchmark_results = {
            "timestamp": datetime.now().isoformat(),
            "duration_minutes": duration_minutes,
            "total_requests": total_requests,
            "successful_requests": success_count,
            "failed_requests": error_count,
            "success_rate": success_rate,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "p95_response_time": sorted(response_times)[int(0.95 * len(response_times))] if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "requests_per_minute": total_requests / duration_minutes
        }

        logger.info(f"Performance benchmark complete: "
                   f"{success_count}/{total_requests} successful "
                   f"({success_rate*100:.1f}%), "
                   f"avg response: {benchmark_results['avg_response_time']:.3f}s")

        return benchmark_results

    async def generate_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""

        # Get current system status
        health_check = await self.comprehensive_health_check()
        search_quality = await self.test_search_quality()
        db_connectivity = await self.check_database_connectivity()

        # Analyze recent history if available
        recent_health = self.health_results[-10:] if len(self.health_results) >= 10 else self.health_results
        recent_search = self.search_metrics[-10:] if len(self.search_metrics) >= 10 else self.search_metrics

        # Calculate trends
        health_trend = "stable"
        if len(recent_health) >= 5:
            recent_healthy = len([r for r in recent_health[-5:] if r.status == "healthy"])
            older_healthy = len([r for r in recent_health[:5] if r.status == "healthy"])

            if recent_healthy > older_healthy:
                health_trend = "improving"
            elif recent_healthy < older_healthy:
                health_trend = "degrading"

        search_trend = "stable"
        if len(recent_search) >= 5:
            recent_quality = statistics.mean([s.avg_relevance for s in recent_search[-5:]])
            older_quality = statistics.mean([s.avg_relevance for s in recent_search[:5]])

            if recent_quality > older_quality + 0.1:
                search_trend = "improving"
            elif recent_quality < older_quality - 0.1:
                search_trend = "degrading"

        report = {
            "timestamp": datetime.now().isoformat(),
            "system_status": health_check["overall_status"],
            "current_health": health_check,
            "current_search_quality": asdict(search_quality),
            "database_connectivity": db_connectivity,
            "trends": {
                "health_trend": health_trend,
                "search_quality_trend": search_trend
            },
            "recent_performance": {
                "avg_response_time": statistics.mean([r.response_time for r in recent_health]) if recent_health else 0,
                "search_success_rate": len([s for s in recent_search if s.success]) / len(recent_search) if recent_search else 0,
                "total_health_checks": len(self.health_results),
                "total_search_tests": len(self.search_metrics)
            }
        }

        # Save report
        with open(f'monitoring_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Monitoring report generated: {report['system_status']} status")

        return report

    async def continuous_monitoring(self, check_interval_minutes: int = 5,
                                  total_duration_hours: int = 24):
        """Run continuous monitoring for specified duration"""
        logger.info(f"Starting continuous monitoring: "
                   f"{check_interval_minutes}min intervals for {total_duration_hours}h")

        start_time = time.time()
        end_time = start_time + (total_duration_hours * 3600)
        check_interval = check_interval_minutes * 60

        while time.time() < end_time:
            try:
                # Run monitoring cycle
                health_check = await self.comprehensive_health_check()
                search_quality = await self.test_search_quality()

                # Check for alerts
                if health_check["overall_status"] == "unhealthy":
                    logger.error("🚨 ALERT: System unhealthy - immediate attention required")
                elif health_check["overall_status"] == "degraded":
                    logger.warning("⚠️  WARNING: System degraded - monitor closely")

                if not search_quality.success:
                    logger.warning("⚠️  WARNING: Search quality below threshold")

                # Wait for next check
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"Monitoring cycle error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

        # Generate final report
        final_report = await self.generate_monitoring_report()
        logger.info("Continuous monitoring completed")
        return final_report

async def main():
    """Main monitoring entry point"""
    async with ProductionMonitor() as monitor:
        # Quick health check
        print("🏥 Quick Health Check:")
        health = await monitor.comprehensive_health_check()
        print(f"System Status: {health['overall_status']}")
        print(f"Healthy Endpoints: {health['healthy_endpoints']}/{health['total_endpoints']}")
        print(f"Avg Response Time: {health['avg_response_time']:.3f}s")

        # Search quality test
        print("\n🎯 Search Quality Test:")
        search = await monitor.test_search_quality()
        print(f"Query: '{search.query}'")
        print(f"Results: {search.results_found}")
        print(f"Relevance: {search.avg_relevance:.3f}")
        print(f"Success: {search.success}")

        # Database connectivity
        print("\n💾 Database Connectivity:")
        db = await monitor.check_database_connectivity()
        print(f"MongoDB Connected: {db.get('mongodb_connected', False)}")
        print(f"Working Queries: {db.get('working_search_queries', 0)}/{db.get('total_test_queries', 0)}")

        # Performance benchmark (optional)
        print("\n⚡ Performance Benchmark (2 minutes):")
        perf = await monitor.performance_benchmark(duration_minutes=2)
        print(f"Success Rate: {perf['success_rate']*100:.1f}%")
        print(f"Avg Response: {perf['avg_response_time']:.3f}s")
        print(f"Requests/min: {perf['requests_per_minute']:.1f}")

        # Generate comprehensive report
        print("\n📋 Generating Monitoring Report:")
        report = await monitor.generate_monitoring_report()
        print(f"Report Status: {report['system_status']}")
        print("Report saved to monitoring_report_*.json")

if __name__ == "__main__":
    asyncio.run(main())
