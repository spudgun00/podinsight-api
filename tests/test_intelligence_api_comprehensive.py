"""
Comprehensive Test Suite for Episode Intelligence API
Tests all endpoints with real data, validates responses, and measures performance
"""
import asyncio
import json
import os
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
import jwt
from termcolor import colored

# Test configuration
API_BASE_URL = os.getenv("API_URL", "https://podinsight-api.vercel.app")
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "test@podinsight.com")

class SignalType(Enum):
    INVESTABLE = "investable"
    COMPETITIVE = "competitive"
    PORTFOLIO = "portfolio"
    SOUND_BITE = "sound_bite"

@dataclass
class TestResult:
    test_name: str
    status: str  # PASS, FAIL, ERROR
    duration_ms: float
    details: Dict
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

class IntelligenceAPITestSuite:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.results: List[TestResult] = []
        self.client = httpx.AsyncClient(timeout=30.0)
        self.headers = {}

    def print_header(self):
        """Print test suite header"""
        print("\n" + "="*60)
        print(colored("🧪 Episode Intelligence API Test Suite", "cyan", attrs=["bold"]))
        print("="*60)
        print(f"📍 Target: {self.base_url}")
        print(f"🕐 Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("="*60 + "\n")

    def print_test_result(self, result: TestResult):
        """Print individual test result with color coding"""
        icons = {
            "PASS": "✅",
            "FAIL": "❌",
            "ERROR": "⚠️"
        }

        colors = {
            "PASS": "green",
            "FAIL": "red",
            "ERROR": "yellow"
        }

        status_text = colored(f"{icons[result.status]} {result.status}", colors[result.status])
        test_name = colored(result.test_name, "white", attrs=["bold"])
        duration = colored(f"[{result.duration_ms:>6.2f}ms]", "blue")

        print(f"{test_name:<50} {status_text:<15} {duration}")

        if result.status != "PASS" and result.details.get("error"):
            print(f"   └─ {colored(result.details['error'], 'red')}")

    async def get_auth_token(self) -> Optional[str]:
        """Generate JWT token for testing"""
        if not JWT_SECRET:
            print(colored("❌ SUPABASE_JWT_SECRET not set", "red"))
            return None

        try:
            payload = {
                "sub": "test-user-123",
                "email": TEST_USER_EMAIL,
                "role": "authenticated",
                "exp": datetime.utcnow() + timedelta(hours=1)
            }

            token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
            return token
        except Exception as e:
            print(colored(f"❌ Failed to generate JWT: {str(e)}", "red"))
            return None

    async def test_endpoint(self, method: str, endpoint: str,
                          expected_status: int = 200,
                          data: Optional[Dict] = None,
                          test_name: Optional[str] = None) -> TestResult:
        """Generic endpoint test helper"""
        if not test_name:
            test_name = f"{method} {endpoint}"

        start_time = time.time()

        try:
            if method == "GET":
                response = await self.client.get(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers
                )
            elif method == "POST":
                response = await self.client.post(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    json=data or {}
                )
            elif method == "PUT":
                response = await self.client.put(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    json=data or {}
                )
            else:
                raise ValueError(f"Unsupported method: {method}")

            duration_ms = (time.time() - start_time) * 1000

            if response.status_code == expected_status:
                result = TestResult(
                    test_name=test_name,
                    status="PASS",
                    duration_ms=duration_ms,
                    details={
                        "status_code": response.status_code,
                        "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                    }
                )
            else:
                result = TestResult(
                    test_name=test_name,
                    status="FAIL",
                    duration_ms=duration_ms,
                    details={
                        "error": f"Expected {expected_status}, got {response.status_code}",
                        "response": response.text
                    }
                )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = TestResult(
                test_name=test_name,
                status="ERROR",
                duration_ms=duration_ms,
                details={"error": str(e)}
            )

        self.results.append(result)
        self.print_test_result(result)
        return result

    async def test_authentication(self):
        """Test authentication scenarios"""
        print(colored("\n🔐 Testing Authentication", "cyan", attrs=["bold"]))
        print("-" * 60)

        # Test without token
        await self.test_endpoint(
            "GET", "/api/intelligence/dashboard", 401,
            test_name="Dashboard without auth token"
        )

        # Test with invalid token
        self.headers = {"Authorization": "Bearer invalid_token_12345"}
        await self.test_endpoint(
            "GET", "/api/intelligence/dashboard", 401,
            test_name="Dashboard with invalid token"
        )

        # Test with valid token
        token = await self.get_auth_token()
        if token:
            self.headers = {"Authorization": f"Bearer {token}"}
            await self.test_endpoint(
                "GET", "/api/intelligence/dashboard", 200,
                test_name="Dashboard with valid token"
            )

    async def test_dashboard_endpoint(self):
        """Test dashboard endpoint functionality"""
        print(colored("\n📊 Testing Dashboard Endpoint", "cyan", attrs=["bold"]))
        print("-" * 60)

        result = await self.test_endpoint(
            "GET", "/api/intelligence/dashboard", 200,
            test_name="Get dashboard episodes"
        )

        if result.status == "PASS":
            data = result.details["response"]

            # Validate response structure
            tests = [
                ("episodes" in data, "Response contains episodes array"),
                ("total_episodes" in data, "Response contains total_episodes"),
                ("generated_at" in data, "Response contains generated_at"),
                (isinstance(data["episodes"], list), "Episodes is an array"),
                (len(data["episodes"]) <= 8, "Returns maximum 8 episodes"),
                (len(data["episodes"]) >= 1, "Returns at least 1 episode")
            ]

            for condition, test_name in tests:
                test_result = TestResult(
                    test_name=f"Dashboard: {test_name}",
                    status="PASS" if condition else "FAIL",
                    duration_ms=0,
                    details={"validated": condition}
                )
                self.results.append(test_result)
                self.print_test_result(test_result)

            # Validate episode structure
            if data["episodes"]:
                episode = data["episodes"][0]
                await self.validate_episode_structure(episode)

    async def validate_episode_structure(self, episode: Dict):
        """Validate episode data structure"""
        required_fields = [
            "episode_id", "title", "podcast_name", "published_at",
            "duration_seconds", "relevance_score", "signals",
            "summary", "key_insights"
        ]

        for field in required_fields:
            test_result = TestResult(
                test_name=f"Episode field: {field}",
                status="PASS" if field in episode else "FAIL",
                duration_ms=0,
                details={"field": field, "present": field in episode}
            )
            self.results.append(test_result)
            self.print_test_result(test_result)

        # Validate signals
        if "signals" in episode and isinstance(episode["signals"], list):
            for i, signal in enumerate(episode["signals"][:3]):  # Check first 3
                await self.validate_signal_structure(signal, i)

    async def validate_signal_structure(self, signal: Dict, index: int):
        """Validate signal data structure"""
        valid_types = ["investable", "competitive", "portfolio", "sound_bite"]

        tests = [
            ("type" in signal, f"Signal {index}: has type field"),
            ("content" in signal, f"Signal {index}: has content field"),
            ("confidence" in signal, f"Signal {index}: has confidence field"),
            (signal.get("type") in valid_types, f"Signal {index}: valid type"),
            (0 <= signal.get("confidence", 0) <= 1, f"Signal {index}: confidence in range")
        ]

        for condition, test_name in tests:
            test_result = TestResult(
                test_name=test_name,
                status="PASS" if condition else "FAIL",
                duration_ms=0,
                details={"signal": signal}
            )
            self.results.append(test_result)
            self.print_test_result(test_result)

    async def test_episode_brief_endpoint(self):
        """Test episode brief endpoint"""
        print(colored("\n📋 Testing Episode Brief Endpoint", "cyan", attrs=["bold"]))
        print("-" * 60)

        # First get an episode ID from dashboard
        dashboard_result = await self.test_endpoint(
            "GET", "/api/intelligence/dashboard", 200,
            test_name="Get episode for brief test"
        )

        if dashboard_result.status == "PASS":
            episodes = dashboard_result.details["response"]["episodes"]
            if episodes:
                episode_id = episodes[0]["episode_id"]

                # Test valid episode brief
                await self.test_endpoint(
                    "GET", f"/api/intelligence/brief/{episode_id}", 200,
                    test_name=f"Get brief for episode {episode_id[:8]}..."
                )

                # Test invalid episode ID
                await self.test_endpoint(
                    "GET", "/api/intelligence/brief/invalid_id_12345", 404,
                    test_name="Get brief with invalid ID"
                )

    async def test_share_functionality(self):
        """Test share endpoint"""
        print(colored("\n📤 Testing Share Functionality", "cyan", attrs=["bold"]))
        print("-" * 60)

        # Get episode ID
        dashboard_result = await self.test_endpoint(
            "GET", "/api/intelligence/dashboard", 200,
            test_name="Get episode for share test"
        )

        if dashboard_result.status == "PASS":
            episodes = dashboard_result.details["response"]["episodes"]
            if episodes:
                episode_id = episodes[0]["episode_id"]

                # Test email share
                share_data = {
                    "episode_id": episode_id,
                    "method": "email",
                    "recipient": "test@example.com",
                    "include_summary": True,
                    "personal_note": "Check this out!"
                }

                await self.test_endpoint(
                    "POST", "/api/intelligence/share", 200,
                    data=share_data,
                    test_name="Share episode via email"
                )

                # Test invalid share
                invalid_data = {
                    "episode_id": "invalid_id",
                    "method": "telepathy",
                    "recipient": ""
                }

                await self.test_endpoint(
                    "POST", "/api/intelligence/share", 400,
                    data=invalid_data,
                    test_name="Share with invalid data"
                )

    async def test_performance_benchmarks(self):
        """Run performance benchmarks"""
        print(colored("\n⚡ Testing Performance", "cyan", attrs=["bold"]))
        print("-" * 60)

        # Dashboard performance
        dashboard_times = []
        for i in range(5):
            result = await self.test_endpoint(
                "GET", "/api/intelligence/dashboard", 200,
                test_name=f"Dashboard performance test {i+1}"
            )
            if result.status == "PASS":
                dashboard_times.append(result.duration_ms)

        if dashboard_times:
            avg_time = statistics.mean(dashboard_times)
            p95_time = statistics.quantiles(dashboard_times, n=20)[18] if len(dashboard_times) > 1 else dashboard_times[0]

            perf_result = TestResult(
                test_name="Dashboard avg response time < 200ms",
                status="PASS" if avg_time < 200 else "FAIL",
                duration_ms=avg_time,
                details={
                    "average_ms": avg_time,
                    "p95_ms": p95_time,
                    "all_times": dashboard_times
                }
            )
            self.results.append(perf_result)
            self.print_test_result(perf_result)

    async def test_error_handling(self):
        """Test error handling scenarios"""
        print(colored("\n⚠️  Testing Error Handling", "cyan", attrs=["bold"]))
        print("-" * 60)

        # Test various error scenarios
        error_tests = [
            ("/api/intelligence/nonexistent", 404, "Nonexistent endpoint"),
            ("/api/intelligence/brief/", 404, "Empty episode ID"),
        ]

        for endpoint, expected_status, test_name in error_tests:
            await self.test_endpoint("GET", endpoint, expected_status, test_name=test_name)

    async def test_user_journey(self):
        """Test complete user journey"""
        print(colored("\n🚶 Testing User Journey", "cyan", attrs=["bold"]))
        print("-" * 60)

        # 1. Load dashboard
        dashboard = await self.test_endpoint(
            "GET", "/api/intelligence/dashboard", 200,
            test_name="User journey: Load dashboard"
        )

        if dashboard.status == "PASS" and dashboard.details["response"]["episodes"]:
            episode_id = dashboard.details["response"]["episodes"][0]["episode_id"]

            # 2. View episode brief
            brief = await self.test_endpoint(
                "GET", f"/api/intelligence/brief/{episode_id}", 200,
                test_name="User journey: View episode brief"
            )

            # 3. Share episode
            if brief.status == "PASS":
                share_data = {
                    "episode_id": episode_id,
                    "method": "email",
                    "recipient": "team@example.com",
                    "include_summary": True
                }

                await self.test_endpoint(
                    "POST", "/api/intelligence/share", 200,
                    data=share_data,
                    test_name="User journey: Share episode"
                )

    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"])
        errors = len([r for r in self.results if r.status == "ERROR"])
        total = len(self.results)

        # Calculate performance metrics
        perf_results = [r for r in self.results if r.duration_ms > 0]
        avg_response_time = statistics.mean([r.duration_ms for r in perf_results]) if perf_results else 0

        return {
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "success_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%",
                "average_response_time_ms": f"{avg_response_time:.2f}",
                "timestamp": datetime.utcnow().isoformat()
            },
            "failed_tests": [
                {
                    "name": r.test_name,
                    "error": r.details.get("error", "Unknown"),
                    "details": r.details
                } for r in self.results if r.status in ["FAIL", "ERROR"]
            ],
            "performance": {
                "dashboard_tests": [r for r in self.results if "dashboard" in r.test_name.lower() and r.duration_ms > 0],
                "brief_tests": [r for r in self.results if "brief" in r.test_name.lower() and r.duration_ms > 0],
            }
        }

    async def run_all_tests(self):
        """Execute complete test suite"""
        self.print_header()

        # Get auth token first
        token = await self.get_auth_token()
        if not token:
            print(colored("❌ Cannot proceed without authentication", "red"))
            return

        self.headers = {"Authorization": f"Bearer {token}"}

        # Run test categories
        await self.test_authentication()
        await self.test_dashboard_endpoint()
        await self.test_episode_brief_endpoint()
        await self.test_share_functionality()
        await self.test_performance_benchmarks()
        await self.test_error_handling()
        await self.test_user_journey()

        # Generate and display report
        report = self.generate_report()

        print("\n" + "="*60)
        print(colored("📊 TEST RESULTS SUMMARY", "cyan", attrs=["bold"]))
        print("="*60)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Passed: {colored(str(report['summary']['passed']), 'green')} ✅")
        print(f"Failed: {colored(str(report['summary']['failed']), 'red')} ❌")
        print(f"Errors: {colored(str(report['summary']['errors']), 'yellow')} ⚠️")
        print(f"Success Rate: {report['summary']['success_rate']}")
        print(f"Avg Response Time: {report['summary']['average_response_time_ms']}ms")
        print("="*60)

        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"test_results_{timestamp}.json"
        with open(filename, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n💾 Full report saved to: {filename}")

        await self.client.aclose()

async def main():
    """Main test execution"""
    tester = IntelligenceAPITestSuite()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
