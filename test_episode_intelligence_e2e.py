#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite for Episode Intelligence API
Tests all endpoints, data integrity, performance, and known issues
"""
import httpx
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import os
from collections import defaultdict

# Configuration
BASE_URL = os.getenv("API_BASE_URL", "https://podinsight-api.vercel.app")
MONGODB_URI = os.getenv("MONGODB_URI")

# Performance thresholds (in milliseconds)
PERF_THRESHOLDS = {
    "dashboard": 500,
    "brief": 2000,
    "health": 200,
    "share": 1000,
    "preferences": 500
}

class TestResults:
    """Store and format test results"""
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.performance = {}
        self.data_integrity = {}

    def add_test(self, name: str, status: str, message: str, duration_ms: Optional[float] = None):
        self.tests.append({
            "name": name,
            "status": status,
            "message": message,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        })

        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
        elif status == "WARN":
            self.warnings += 1

    def add_performance(self, endpoint: str, duration_ms: float):
        if endpoint not in self.performance:
            self.performance[endpoint] = []
        self.performance[endpoint].append(duration_ms)

    def add_data_check(self, check_name: str, result: Dict):
        self.data_integrity[check_name] = result

    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        report = []
        report.append("=" * 80)
        report.append("EPISODE INTELLIGENCE E2E TEST REPORT")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("=" * 80)

        # Summary
        report.append("\n## SUMMARY")
        report.append(f"Total Tests: {len(self.tests)}")
        report.append(f"Passed: {self.passed} ✅")
        report.append(f"Failed: {self.failed} ❌")
        report.append(f"Warnings: {self.warnings} ⚠️")
        report.append(f"Success Rate: {(self.passed / len(self.tests) * 100):.1f}%")

        # Performance Summary
        report.append("\n## PERFORMANCE SUMMARY")
        for endpoint, times in self.performance.items():
            avg_time = sum(times) / len(times)
            threshold = PERF_THRESHOLDS.get(endpoint, 1000)
            status = "✅" if avg_time < threshold else "❌"
            report.append(f"{endpoint}: {avg_time:.0f}ms (threshold: {threshold}ms) {status}")

        # Data Integrity Summary
        report.append("\n## DATA INTEGRITY CHECKS")
        for check, result in self.data_integrity.items():
            report.append(f"\n### {check}")
            for key, value in result.items():
                report.append(f"  {key}: {value}")

        # Detailed Test Results
        report.append("\n## DETAILED TEST RESULTS")
        for test in self.tests:
            status_icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(test["status"], "❓")
            report.append(f"\n{status_icon} {test['name']}")
            report.append(f"   Status: {test['status']}")
            report.append(f"   Message: {test['message']}")
            if test.get("duration_ms"):
                report.append(f"   Duration: {test['duration_ms']:.0f}ms")

        return "\n".join(report)

async def test_health_endpoint(client: httpx.AsyncClient, results: TestResults):
    """Test health check endpoint"""
    print("\n🔍 Testing Health Endpoint...")

    start_time = time.time()
    try:
        response = await client.get(f"{BASE_URL}/api/intelligence/health")
        duration_ms = (time.time() - start_time) * 1000
        results.add_performance("health", duration_ms)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy" and data.get("mongodb") == "connected":
                results.add_test(
                    "Health Check",
                    "PASS",
                    f"Service healthy, MongoDB connected to {data.get('database_name')}",
                    duration_ms
                )

                # Check collections
                collections = data.get("collections", [])
                required_collections = ["episode_metadata", "episode_intelligence", "user_preferences"]
                missing = [c for c in required_collections if c not in collections]

                if missing:
                    results.add_test(
                        "Required Collections Check",
                        "FAIL",
                        f"Missing collections: {missing}"
                    )
                else:
                    results.add_test(
                        "Required Collections Check",
                        "PASS",
                        "All required collections present"
                    )

                # Check episode count
                episode_count = data.get("episode_metadata_count", 0)
                if episode_count > 0:
                    results.add_test(
                        "Episode Data Check",
                        "PASS",
                        f"Found {episode_count} episodes in metadata"
                    )
                else:
                    results.add_test(
                        "Episode Data Check",
                        "WARN",
                        "No episodes found in metadata collection"
                    )
            else:
                results.add_test(
                    "Health Check",
                    "FAIL",
                    f"Service unhealthy: {data}",
                    duration_ms
                )
        else:
            results.add_test(
                "Health Check",
                "FAIL",
                f"Health check returned status {response.status_code}",
                duration_ms
            )
    except Exception as e:
        results.add_test(
            "Health Check",
            "FAIL",
            f"Health check failed: {str(e)}"
        )

async def test_dashboard_endpoint(client: httpx.AsyncClient, results: TestResults):
    """Test dashboard endpoint comprehensively"""
    print("\n🔍 Testing Dashboard Endpoint...")

    # Test 1: Basic dashboard request
    start_time = time.time()
    try:
        response = await client.get(f"{BASE_URL}/api/intelligence/dashboard")
        duration_ms = (time.time() - start_time) * 1000
        results.add_performance("dashboard", duration_ms)

        if response.status_code == 200:
            data = response.json()
            episodes = data.get("episodes", [])

            results.add_test(
                "Dashboard Basic Request",
                "PASS" if episodes else "WARN",
                f"Returned {len(episodes)} episodes",
                duration_ms
            )

            # Validate episode structure
            if episodes:
                episode = episodes[0]
                required_fields = ["episode_id", "title", "podcast_name", "signals", "relevance_score"]
                missing_fields = [f for f in required_fields if f not in episode]

                if missing_fields:
                    results.add_test(
                        "Episode Structure Validation",
                        "FAIL",
                        f"Missing fields: {missing_fields}"
                    )
                else:
                    results.add_test(
                        "Episode Structure Validation",
                        "PASS",
                        "All required fields present"
                    )

                # Check signals
                total_signals = sum(len(ep.get("signals", [])) for ep in episodes)
                episodes_with_signals = sum(1 for ep in episodes if ep.get("signals"))

                results.add_test(
                    "Signal Extraction Check",
                    "PASS" if total_signals > 0 else "FAIL",
                    f"{episodes_with_signals}/{len(episodes)} episodes have signals (total: {total_signals})"
                )

                # Check relevance scores
                scores = [ep.get("relevance_score", 0) for ep in episodes]
                if all(scores[i] >= scores[i+1] for i in range(len(scores)-1)):
                    results.add_test(
                        "Relevance Score Ordering",
                        "PASS",
                        "Episodes correctly ordered by relevance score"
                    )
                else:
                    results.add_test(
                        "Relevance Score Ordering",
                        "FAIL",
                        "Episodes not properly ordered by relevance score"
                    )
            else:
                # Test debug endpoint to understand why no episodes
                debug_response = await client.get(f"{BASE_URL}/api/intelligence/dashboard-debug")
                if debug_response.status_code == 200:
                    debug_data = debug_response.json()
                    results.add_test(
                        "Dashboard Debug Analysis",
                        "WARN",
                        f"Debug info: {debug_data.get('debug_logs', ['No debug info'])[-1]}"
                    )
        else:
            results.add_test(
                "Dashboard Basic Request",
                "FAIL",
                f"Dashboard returned status {response.status_code}",
                duration_ms
            )
    except Exception as e:
        results.add_test(
            "Dashboard Basic Request",
            "FAIL",
            f"Dashboard request failed: {str(e)}"
        )

    # Test 2: Dashboard with limit parameter
    try:
        response = await client.get(f"{BASE_URL}/api/intelligence/dashboard?limit=5")
        if response.status_code == 200:
            data = response.json()
            episodes = data.get("episodes", [])
            if len(episodes) <= 5:
                results.add_test(
                    "Dashboard Limit Parameter",
                    "PASS",
                    f"Limit respected: returned {len(episodes)} episodes"
                )
            else:
                results.add_test(
                    "Dashboard Limit Parameter",
                    "FAIL",
                    f"Limit not respected: returned {len(episodes)} episodes (expected <= 5)"
                )
    except Exception as e:
        results.add_test(
            "Dashboard Limit Parameter",
            "FAIL",
            f"Failed to test limit parameter: {str(e)}"
        )

async def test_brief_endpoint(client: httpx.AsyncClient, results: TestResults):
    """Test intelligence brief endpoint"""
    print("\n🔍 Testing Brief Endpoint...")

    # First get an episode ID from dashboard
    episode_id = None
    try:
        response = await client.get(f"{BASE_URL}/api/intelligence/dashboard")
        if response.status_code == 200:
            episodes = response.json().get("episodes", [])
            if episodes:
                episode_id = episodes[0].get("episode_id")
    except:
        pass

    if not episode_id:
        # Try to get from find-episodes endpoint
        try:
            response = await client.get(f"{BASE_URL}/api/intelligence/find-episodes-with-intelligence")
            if response.status_code == 200:
                matches = response.json().get("matches", [])
                if matches:
                    episode_id = matches[0].get("metadata_id")
        except:
            pass

    if episode_id:
        # Test 1: Valid episode brief
        start_time = time.time()
        try:
            response = await client.get(f"{BASE_URL}/api/intelligence/brief/{episode_id}")
            duration_ms = (time.time() - start_time) * 1000
            results.add_performance("brief", duration_ms)

            if response.status_code == 200:
                data = response.json()
                results.add_test(
                    "Brief Valid Episode",
                    "PASS",
                    f"Retrieved brief for episode: {data.get('title', 'Unknown')}",
                    duration_ms
                )

                # Validate brief structure
                required_fields = ["episode_id", "title", "podcast_name", "signals", "key_insights", "summary"]
                missing_fields = [f for f in required_fields if f not in data]

                if missing_fields:
                    results.add_test(
                        "Brief Structure Validation",
                        "FAIL",
                        f"Missing fields: {missing_fields}"
                    )
                else:
                    results.add_test(
                        "Brief Structure Validation",
                        "PASS",
                        "All required fields present"
                    )

                # Check key insights extraction
                insights = data.get("key_insights", [])
                if len(insights) >= 3:
                    results.add_test(
                        "Key Insights Extraction",
                        "PASS",
                        f"Extracted {len(insights)} key insights"
                    )
                else:
                    results.add_test(
                        "Key Insights Extraction",
                        "WARN",
                        f"Only {len(insights)} key insights (expected >= 3)"
                    )
            else:
                results.add_test(
                    "Brief Valid Episode",
                    "FAIL",
                    f"Brief returned status {response.status_code}",
                    duration_ms
                )
        except Exception as e:
            results.add_test(
                "Brief Valid Episode",
                "FAIL",
                f"Brief request failed: {str(e)}"
            )
    else:
        results.add_test(
            "Brief Valid Episode",
            "FAIL",
            "No episode ID available for testing"
        )

    # Test 2: Invalid episode ID
    try:
        response = await client.get(f"{BASE_URL}/api/intelligence/brief/invalid-episode-id")
        if response.status_code == 404:
            results.add_test(
                "Brief Invalid Episode",
                "PASS",
                "Correctly returned 404 for invalid episode"
            )
        else:
            results.add_test(
                "Brief Invalid Episode",
                "FAIL",
                f"Expected 404, got {response.status_code}"
            )
    except Exception as e:
        results.add_test(
            "Brief Invalid Episode",
            "FAIL",
            f"Failed to test invalid episode: {str(e)}"
        )

async def test_share_endpoint(client: httpx.AsyncClient, results: TestResults):
    """Test share intelligence endpoint"""
    print("\n🔍 Testing Share Endpoint...")

    # Get an episode ID for testing
    episode_id = None
    try:
        response = await client.get(f"{BASE_URL}/api/intelligence/dashboard")
        if response.status_code == 200:
            episodes = response.json().get("episodes", [])
            if episodes:
                episode_id = episodes[0].get("episode_id")
    except:
        pass

    if episode_id:
        # Test 1: Email sharing
        start_time = time.time()
        try:
            response = await client.post(
                f"{BASE_URL}/api/intelligence/share",
                json={
                    "episode_id": episode_id,
                    "method": "email",
                    "recipient": "test@example.com",
                    "include_summary": True,
                    "personal_note": "Check out this episode"
                }
            )
            duration_ms = (time.time() - start_time) * 1000
            results.add_performance("share", duration_ms)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    results.add_test(
                        "Share via Email",
                        "PASS",
                        "Email share simulated successfully",
                        duration_ms
                    )
                else:
                    results.add_test(
                        "Share via Email",
                        "FAIL",
                        f"Share failed: {data.get('message')}",
                        duration_ms
                    )
            else:
                results.add_test(
                    "Share via Email",
                    "FAIL",
                    f"Share returned status {response.status_code}",
                    duration_ms
                )
        except Exception as e:
            results.add_test(
                "Share via Email",
                "FAIL",
                f"Email share failed: {str(e)}"
            )

        # Test 2: Slack sharing
        try:
            response = await client.post(
                f"{BASE_URL}/api/intelligence/share",
                json={
                    "episode_id": episode_id,
                    "method": "slack",
                    "recipient": "#general"
                }
            )
            if response.status_code == 200:
                results.add_test(
                    "Share via Slack",
                    "PASS",
                    "Slack share simulated successfully"
                )
            else:
                results.add_test(
                    "Share via Slack",
                    "FAIL",
                    f"Slack share returned status {response.status_code}"
                )
        except Exception as e:
            results.add_test(
                "Share via Slack",
                "FAIL",
                f"Slack share failed: {str(e)}"
            )

    # Test 3: Invalid share method
    try:
        response = await client.post(
            f"{BASE_URL}/api/intelligence/share",
            json={
                "episode_id": "test",
                "method": "invalid",
                "recipient": "test"
            }
        )
        if response.status_code == 400:
            results.add_test(
                "Share Invalid Method",
                "PASS",
                "Correctly rejected invalid share method"
            )
        else:
            results.add_test(
                "Share Invalid Method",
                "FAIL",
                f"Expected 400, got {response.status_code}"
            )
    except Exception as e:
        results.add_test(
            "Share Invalid Method",
            "FAIL",
            f"Failed to test invalid method: {str(e)}"
        )

async def test_preferences_endpoint(client: httpx.AsyncClient, results: TestResults):
    """Test user preferences endpoint"""
    print("\n🔍 Testing Preferences Endpoint...")

    # Test updating preferences
    start_time = time.time()
    try:
        response = await client.put(
            f"{BASE_URL}/api/intelligence/preferences",
            json={
                "portfolio_companies": ["Stripe", "OpenAI", "Anthropic"],
                "interest_topics": ["AI", "FinTech", "Developer Tools"],
                "notification_frequency": "daily",
                "email_notifications": True,
                "slack_notifications": False
            }
        )
        duration_ms = (time.time() - start_time) * 1000
        results.add_performance("preferences", duration_ms)

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                results.add_test(
                    "Update Preferences",
                    "PASS",
                    "Preferences updated successfully",
                    duration_ms
                )

                # Validate returned preferences
                prefs = data.get("preferences", {})
                if len(prefs.get("portfolio_companies", [])) == 3:
                    results.add_test(
                        "Preferences Validation",
                        "PASS",
                        "Preferences correctly stored and returned"
                    )
                else:
                    results.add_test(
                        "Preferences Validation",
                        "FAIL",
                        "Preferences not correctly returned"
                    )
            else:
                results.add_test(
                    "Update Preferences",
                    "FAIL",
                    "Preferences update failed",
                    duration_ms
                )
        else:
            results.add_test(
                "Update Preferences",
                "FAIL",
                f"Preferences returned status {response.status_code}",
                duration_ms
            )
    except Exception as e:
        results.add_test(
            "Update Preferences",
            "FAIL",
            f"Preferences update failed: {str(e)}"
        )

async def test_data_integrity(client: httpx.AsyncClient, results: TestResults):
    """Test data integrity between collections"""
    print("\n🔍 Testing Data Integrity...")

    # Test 1: Check GUID matching
    try:
        response = await client.get(f"{BASE_URL}/api/intelligence/check-guid-matching")
        if response.status_code == 200:
            data = response.json()
            matching_count = data.get("matching_count", 0)
            non_matching_count = data.get("non_matching_count", 0)
            total = data.get("total_intelligence_docs", 0)

            match_rate = (matching_count / total * 100) if total > 0 else 0

            results.add_data_check("GUID Matching", {
                "total_intelligence_docs": total,
                "matching_episodes": matching_count,
                "non_matching_episodes": non_matching_count,
                "match_rate": f"{match_rate:.1f}%"
            })

            if match_rate > 90:
                results.add_test(
                    "GUID Matching Check",
                    "PASS",
                    f"{match_rate:.1f}% of intelligence docs have matching metadata"
                )
            elif match_rate > 50:
                results.add_test(
                    "GUID Matching Check",
                    "WARN",
                    f"Only {match_rate:.1f}% of intelligence docs have matching metadata"
                )
            else:
                results.add_test(
                    "GUID Matching Check",
                    "FAIL",
                    f"Poor match rate: {match_rate:.1f}%"
                )
    except Exception as e:
        results.add_test(
            "GUID Matching Check",
            "FAIL",
            f"Failed to check GUID matching: {str(e)}"
        )

    # Test 2: Audit empty signals
    try:
        response = await client.get(f"{BASE_URL}/api/intelligence/audit-empty-signals")
        if response.status_code == 200:
            data = response.json()
            total_docs = data.get("total_documents", 0)
            with_signals = data.get("documents_with_signals", 0)
            empty_docs = data.get("documents_empty", 0)

            signal_rate = (with_signals / total_docs * 100) if total_docs > 0 else 0

            results.add_data_check("Signal Extraction", {
                "total_episodes": total_docs,
                "episodes_with_signals": with_signals,
                "empty_episodes": empty_docs,
                "success_rate": f"{signal_rate:.1f}%",
                "signal_distribution": data.get("signal_distribution", {})
            })

            if signal_rate > 80:
                results.add_test(
                    "Signal Extraction Rate",
                    "PASS",
                    f"{signal_rate:.1f}% of episodes have extracted signals"
                )
            elif signal_rate > 50:
                results.add_test(
                    "Signal Extraction Rate",
                    "WARN",
                    f"Only {signal_rate:.1f}% of episodes have signals"
                )
            else:
                results.add_test(
                    "Signal Extraction Rate",
                    "FAIL",
                    f"Poor signal extraction: {signal_rate:.1f}%"
                )

            # List some empty episodes for investigation
            empty_episodes = data.get("empty_episodes", [])[:5]
            if empty_episodes:
                results.add_test(
                    "Empty Episodes Sample",
                    "WARN",
                    f"Sample empty episodes: {[ep['episode_id'] for ep in empty_episodes]}"
                )
    except Exception as e:
        results.add_test(
            "Signal Extraction Audit",
            "FAIL",
            f"Failed to audit signals: {str(e)}"
        )

async def test_debug_endpoints(client: httpx.AsyncClient, results: TestResults):
    """Test debug endpoints for additional insights"""
    print("\n🔍 Testing Debug Endpoints...")

    # Test MongoDB debug endpoint
    try:
        response = await client.get(f"{BASE_URL}/api/intelligence/debug")
        if response.status_code == 200:
            data = response.json()

            # Check collections
            collections = data.get("collections", [])
            required = ["episode_metadata", "episode_intelligence", "user_preferences", "podcast_authority"]
            missing = [c for c in required if c not in collections]

            if not missing:
                results.add_test(
                    "MongoDB Collections Check",
                    "PASS",
                    f"All required collections present ({len(collections)} total)"
                )
            else:
                results.add_test(
                    "MongoDB Collections Check",
                    "FAIL",
                    f"Missing collections: {missing}"
                )

            # Check collection counts
            metadata_count = data.get("episode_metadata", {}).get("count", 0)
            intelligence_count = data.get("episode_intelligence", {}).get("count", 0)

            results.add_data_check("Collection Counts", {
                "episode_metadata": metadata_count,
                "episode_intelligence": intelligence_count,
                "podcast_authority": data.get("podcast_authority", {}).get("count", 0),
                "user_intelligence_prefs": data.get("user_intelligence_prefs", {}).get("count", 0)
            })

            # Check sample data structure
            if data.get("episode_intelligence", {}).get("sample"):
                sample = data["episode_intelligence"]["sample"]
                if sample.get("has_signals"):
                    signal_types = sample.get("signal_types", [])
                    results.add_test(
                        "Signal Types Check",
                        "PASS" if signal_types else "WARN",
                        f"Signal types found: {signal_types}"
                    )
    except Exception as e:
        results.add_test(
            "MongoDB Debug Check",
            "FAIL",
            f"Debug endpoint failed: {str(e)}"
        )

async def test_performance_benchmarks(client: httpx.AsyncClient, results: TestResults):
    """Run performance benchmarks"""
    print("\n🔍 Running Performance Benchmarks...")

    # Run multiple requests to get average times
    endpoints = [
        ("GET", "/api/intelligence/health", None, "health"),
        ("GET", "/api/intelligence/dashboard?limit=5", None, "dashboard"),
    ]

    for method, path, body, name in endpoints:
        times = []
        for i in range(3):  # Run 3 times
            start_time = time.time()
            try:
                if method == "GET":
                    response = await client.get(f"{BASE_URL}{path}")
                else:
                    response = await client.post(f"{BASE_URL}{path}", json=body)

                duration_ms = (time.time() - start_time) * 1000
                times.append(duration_ms)

                await asyncio.sleep(0.1)  # Small delay between requests
            except:
                pass

        if times:
            avg_time = sum(times) / len(times)
            threshold = PERF_THRESHOLDS.get(name, 1000)

            if avg_time < threshold:
                results.add_test(
                    f"Performance: {name}",
                    "PASS",
                    f"Average response time: {avg_time:.0f}ms (threshold: {threshold}ms)"
                )
            else:
                results.add_test(
                    f"Performance: {name}",
                    "FAIL",
                    f"Average response time: {avg_time:.0f}ms exceeds threshold: {threshold}ms"
                )

async def run_all_tests():
    """Run all E2E tests"""
    print("\n" + "=" * 80)
    print("EPISODE INTELLIGENCE E2E TEST SUITE")
    print(f"API Base URL: {BASE_URL}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 80)

    results = TestResults()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Run all test suites
        await test_health_endpoint(client, results)
        await test_dashboard_endpoint(client, results)
        await test_brief_endpoint(client, results)
        await test_share_endpoint(client, results)
        await test_preferences_endpoint(client, results)
        await test_data_integrity(client, results)
        await test_debug_endpoints(client, results)
        await test_performance_benchmarks(client, results)

    # Generate and save report
    report = results.generate_report()

    # Save to file
    report_filename = f"episode_intelligence_e2e_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_filename, "w") as f:
        f.write(report)

    # Print summary
    print("\n" + report)
    print(f"\n📄 Full report saved to: {report_filename}")

    return results

if __name__ == "__main__":
    asyncio.run(run_all_tests())
