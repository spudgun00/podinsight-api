#!/usr/bin/env python3
"""
Production Test Runner
Executes all comprehensive tests for production readiness validation
"""

import asyncio
import subprocess
import sys
import time
from datetime import datetime
import json
import os

class ProductionTestRunner:
    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()

    def log(self, message: str):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    async def run_test_script(self, script_name: str, description: str) -> dict:
        """Run a test script and capture results"""
        self.log(f"🧪 Starting: {description}")

        start_time = time.time()
        try:
            # Run the test script
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()
            duration = time.time() - start_time

            result = {
                "script": script_name,
                "description": description,
                "success": process.returncode == 0,
                "duration": duration,
                "returncode": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else ""
            }

            if result["success"]:
                self.log(f"✅ Completed: {description} ({duration:.1f}s)")
            else:
                self.log(f"❌ Failed: {description} (code: {process.returncode})")
                if stderr:
                    self.log(f"   Error: {stderr.decode()[:200]}...")

            return result

        except Exception as e:
            duration = time.time() - start_time
            self.log(f"❌ Exception in {description}: {str(e)}")
            return {
                "script": script_name,
                "description": description,
                "success": False,
                "duration": duration,
                "error": str(e)
            }

    def check_prerequisites(self) -> bool:
        """Check if all test scripts exist"""
        required_scripts = [
            "test_comprehensive_api.py",
            "test_vector_search_comprehensive.py",
            "monitoring_health_check.py"
        ]

        missing_scripts = []
        for script in required_scripts:
            if not os.path.exists(script):
                missing_scripts.append(script)

        if missing_scripts:
            self.log(f"❌ Missing required scripts: {missing_scripts}")
            return False

        self.log("✅ All test scripts found")
        return True

    async def run_all_tests(self):
        """Run all production readiness tests"""
        self.log("🚀 Starting Production Readiness Test Suite")
        self.log("=" * 60)

        # Check prerequisites
        if not self.check_prerequisites():
            return False

        # Test suite configuration
        tests = [
            {
                "script": "monitoring_health_check.py",
                "description": "Health Check & Monitoring",
                "priority": "critical"
            },
            {
                "script": "test_comprehensive_api.py",
                "description": "Comprehensive API Testing",
                "priority": "critical"
            },
            {
                "script": "test_vector_search_comprehensive.py",
                "description": "Vector Search Quality Testing",
                "priority": "critical"
            }
        ]

        # Run tests sequentially
        all_results = []
        critical_failures = 0

        for test_config in tests:
            result = await self.run_test_script(
                test_config["script"],
                test_config["description"]
            )

            result["priority"] = test_config["priority"]
            all_results.append(result)

            if not result["success"] and test_config["priority"] == "critical":
                critical_failures += 1

            # Brief pause between tests
            await asyncio.sleep(2)

        # Analyze results
        total_duration = time.time() - self.start_time
        successful_tests = len([r for r in all_results if r["success"]])

        self.log("=" * 60)
        self.log("📋 PRODUCTION TEST SUITE RESULTS")
        self.log("=" * 60)

        # Individual test results
        for result in all_results:
            status = "✅" if result["success"] else "❌"
            priority = result["priority"].upper()
            self.log(f"{status} [{priority}] {result['description']} ({result['duration']:.1f}s)")

            if not result["success"]:
                if "error" in result:
                    self.log(f"   Error: {result['error']}")
                elif result.get("stderr"):
                    self.log(f"   Error: {result['stderr'][:200]}...")

        # Overall assessment
        self.log(f"\n📊 SUMMARY:")
        self.log(f"Total Tests: {len(all_results)}")
        self.log(f"Successful: {successful_tests}/{len(all_results)} ({successful_tests/len(all_results)*100:.1f}%)")
        self.log(f"Critical Failures: {critical_failures}")
        self.log(f"Total Duration: {total_duration:.1f}s")

        # Production readiness decision
        if critical_failures == 0 and successful_tests == len(all_results):
            self.log(f"\n🎉 PRODUCTION READINESS: ✅ GO")
            self.log("All critical tests passed - system ready for production")
            production_ready = True
        elif critical_failures == 0:
            self.log(f"\n⚠️  PRODUCTION READINESS: ⚠️  CONDITIONAL GO")
            self.log("Critical tests passed but some non-critical issues detected")
            production_ready = True
        else:
            self.log(f"\n❌ PRODUCTION READINESS: ❌ NO-GO")
            self.log(f"{critical_failures} critical test(s) failed - requires investigation")
            production_ready = False

        # Save comprehensive results
        test_summary = {
            "timestamp": datetime.now().isoformat(),
            "production_ready": production_ready,
            "total_tests": len(all_results),
            "successful_tests": successful_tests,
            "critical_failures": critical_failures,
            "total_duration": total_duration,
            "test_results": all_results,
            "environment": {
                "python_version": sys.version,
                "platform": sys.platform
            }
        }

        with open('production_test_summary.json', 'w') as f:
            json.dump(test_summary, f, indent=2, default=str)

        self.log(f"\n💾 Detailed results saved to production_test_summary.json")

        # Check for generated report files
        report_files = [
            'comprehensive_test_report.json',
            'vector_search_quality_report.json'
        ]

        found_reports = [f for f in report_files if os.path.exists(f)]
        if found_reports:
            self.log(f"\n📄 Generated Reports:")
            for report in found_reports:
                self.log(f"   - {report}")

        return production_ready

    async def quick_health_check(self):
        """Run just the health check for rapid status assessment"""
        self.log("🏥 Quick Health Check")
        self.log("-" * 30)

        result = await self.run_test_script(
            "monitoring_health_check.py",
            "System Health Check"
        )

        if result["success"]:
            self.log("✅ System appears healthy")
        else:
            self.log("❌ System health issues detected")

        return result["success"]

def main():
    """Main entry point"""
    runner = ProductionTestRunner()

    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Quick health check only
        result = asyncio.run(runner.quick_health_check())
        sys.exit(0 if result else 1)
    else:
        # Full test suite
        result = asyncio.run(runner.run_all_tests())
        sys.exit(0 if result else 1)

if __name__ == "__main__":
    main()
