#!/usr/bin/env python3
"""
PodInsight System Health Monitor

Monitors all critical components and alerts on failures.
Run this regularly (e.g., via cron) to catch issues early.
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Configuration
MODAL_URL = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"
API_URL = "https://podinsight-api.vercel.app/api/search"
HEALTH_URL = "https://podinsight-api.vercel.app/api/health"

# Critical test queries that should always return results
CRITICAL_QUERIES = [
    "openai",
    "venture capital",
    "artificial intelligence",
    "podcast",
    "sam altman"
]

class HealthMonitor:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "components": {},
            "critical_queries": {},
            "overall_status": "UNKNOWN"
        }

    def test_modal_endpoint(self) -> bool:
        """Test Modal embedding endpoint"""
        print("🔍 Testing Modal Endpoint...")

        try:
            response = requests.post(
                MODAL_URL,
                json={"text": "test health check"},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("dimension") == 768:
                    self.results["components"]["modal"] = {
                        "status": "HEALTHY",
                        "message": f"768D embeddings, GPU: {data.get('gpu_available', False)}",
                        "response_time_ms": data.get("total_time_ms", 0)
                    }
                    print("  ✅ Modal endpoint healthy")
                    return True

            self.results["components"]["modal"] = {
                "status": "UNHEALTHY",
                "message": f"HTTP {response.status_code}",
                "response_time_ms": 0
            }
            print(f"  ❌ Modal endpoint unhealthy: HTTP {response.status_code}")
            return False

        except Exception as e:
            self.results["components"]["modal"] = {
                "status": "UNHEALTHY",
                "message": str(e),
                "response_time_ms": 0
            }
            print(f"  ❌ Modal endpoint error: {e}")
            return False

    def test_api_health(self) -> bool:
        """Test API health endpoint"""
        print("🏥 Testing API Health...")

        try:
            start = time.time()
            response = requests.get(HEALTH_URL, timeout=5)
            elapsed = (time.time() - start) * 1000

            if response.status_code == 200:
                self.results["components"]["api_health"] = {
                    "status": "HEALTHY",
                    "message": "Health check passed",
                    "response_time_ms": elapsed
                }
                print(f"  ✅ API health check passed ({elapsed:.0f}ms)")
                return True

            self.results["components"]["api_health"] = {
                "status": "UNHEALTHY",
                "message": f"HTTP {response.status_code}",
                "response_time_ms": elapsed
            }
            print(f"  ❌ API health check failed: HTTP {response.status_code}")
            return False

        except Exception as e:
            self.results["components"]["api_health"] = {
                "status": "UNHEALTHY",
                "message": str(e),
                "response_time_ms": 0
            }
            print(f"  ❌ API health check error: {e}")
            return False

    def test_search_queries(self) -> Tuple[int, int]:
        """Test critical search queries"""
        print("🔎 Testing Critical Queries...")

        passed = 0
        total = len(CRITICAL_QUERIES)

        for query in CRITICAL_QUERIES:
            try:
                # Use offset=0 parameter which seems to work better
                start = time.time()
                response = requests.post(
                    API_URL,
                    json={"query": query, "offset": 0},
                    timeout=15
                )
                elapsed = (time.time() - start) * 1000

                if response.status_code == 200:
                    data = response.json()
                    num_results = len(data.get("results", []))

                    if num_results > 0:
                        self.results["critical_queries"][query] = {
                            "status": "PASS",
                            "results": num_results,
                            "method": data.get("search_method", "unknown"),
                            "response_time_ms": elapsed
                        }
                        print(f"  ✅ '{query}': {num_results} results ({elapsed:.0f}ms)")
                        passed += 1
                    else:
                        self.results["critical_queries"][query] = {
                            "status": "FAIL",
                            "results": 0,
                            "method": data.get("search_method", "unknown"),
                            "response_time_ms": elapsed
                        }
                        print(f"  ❌ '{query}': 0 results ({elapsed:.0f}ms)")
                else:
                    self.results["critical_queries"][query] = {
                        "status": "ERROR",
                        "error": f"HTTP {response.status_code}",
                        "response_time_ms": elapsed
                    }
                    print(f"  ❌ '{query}': HTTP {response.status_code}")

            except Exception as e:
                self.results["critical_queries"][query] = {
                    "status": "ERROR",
                    "error": str(e),
                    "response_time_ms": 0
                }
                print(f"  ❌ '{query}': {e}")

        return passed, total

    def determine_overall_status(self, modal_ok: bool, api_ok: bool, queries_passed: int, queries_total: int):
        """Determine overall system status"""

        # Calculate query pass rate
        query_pass_rate = queries_passed / queries_total if queries_total > 0 else 0

        if modal_ok and api_ok and query_pass_rate >= 0.8:
            self.results["overall_status"] = "HEALTHY"
            self.results["summary"] = "All systems operational"
        elif modal_ok and api_ok and query_pass_rate >= 0.5:
            self.results["overall_status"] = "DEGRADED"
            self.results["summary"] = f"Search performance degraded ({queries_passed}/{queries_total} queries passing)"
        else:
            self.results["overall_status"] = "UNHEALTHY"
            issues = []
            if not modal_ok:
                issues.append("Modal endpoint down")
            if not api_ok:
                issues.append("API health check failing")
            if query_pass_rate < 0.5:
                issues.append(f"Search failing ({queries_passed}/{queries_total} queries passing)")
            self.results["summary"] = "; ".join(issues)

    def save_results(self, filename: str = "health_check_results.json"):
        """Save results to file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Results saved to {filename}")

    def run(self) -> bool:
        """Run all health checks"""
        print("\n" + "=" * 60)
        print("🏥 PodInsight System Health Monitor")
        print(f"Started: {self.results['timestamp']}")
        print("=" * 60)

        # Run tests
        modal_ok = self.test_modal_endpoint()
        api_ok = self.test_api_health()
        queries_passed, queries_total = self.test_search_queries()

        # Determine overall status
        self.determine_overall_status(modal_ok, api_ok, queries_passed, queries_total)

        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        status_emoji = {
            "HEALTHY": "✅",
            "DEGRADED": "⚠️",
            "UNHEALTHY": "❌"
        }

        print(f"\nOverall Status: {status_emoji.get(self.results['overall_status'], '❓')} {self.results['overall_status']}")
        print(f"Summary: {self.results['summary']}")

        # Component status
        print("\nComponent Status:")
        for component, status in self.results["components"].items():
            emoji = "✅" if status["status"] == "HEALTHY" else "❌"
            print(f"  {emoji} {component}: {status['status']} - {status['message']}")

        # Query results
        print(f"\nQuery Results: {queries_passed}/{queries_total} passed")

        # Save results
        self.save_results()

        # Return success if healthy or degraded
        return self.results["overall_status"] in ["HEALTHY", "DEGRADED"]

def main():
    """Main entry point"""
    monitor = HealthMonitor()
    success = monitor.run()

    # Exit with appropriate code
    if success:
        print("\n✅ Health check completed successfully")
        sys.exit(0)
    else:
        print("\n❌ Health check detected issues")
        sys.exit(1)

if __name__ == "__main__":
    main()
