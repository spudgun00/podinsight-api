#!/usr/bin/env python3
"""Comprehensive Audio API Testing Script"""

import os
import json
import time
import requests
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audio_api_test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = "https://podinsight-api.vercel.app"
API_ENDPOINT = "/api/v1/audio_clips"

# Test data from our MongoDB discovery
TEST_DATA = {
    "valid_episode": {
        "id": "685ba776e4f9ec2f0756267a",  # pragma: allowlist secret
        "guid": "022f8502-14c3-11f0-9b7c-bf77561f0071",  # pragma: allowlist secret
        "duration_sec": 4387,
        "feed_slug": "unchained"
    },
    "episode_without_transcript": {
        "id": "685ba747e4f9ec2f07562424"  # pragma: allowlist secret
    },
    "invalid_episode_id": "ffffffffffffffffffffffff",
    "malformed_episode_id": "invalid-id"
}

class AudioAPITester:
    def __init__(self):
        self.results = {
            "test_run_id": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "performance_metrics": {}
            }
        }
        self.temp_dir = Path("./test_audio_clips")
        self.temp_dir.mkdir(exist_ok=True)

    def run_test(self, test_name: str, test_func, *args, **kwargs) -> bool:
        """Run a single test and log results"""
        logger.info(f"Running test: {test_name}")
        start_time = time.time()

        try:
            result = test_func(*args, **kwargs)
            duration = time.time() - start_time

            self.results["tests"].append({
                "name": test_name,
                "status": "passed" if result["success"] else "failed",
                "duration": duration,
                "details": result
            })

            if result["success"]:
                self.results["summary"]["passed"] += 1
                logger.info(f"✅ {test_name} PASSED ({duration:.2f}s)")
            else:
                self.results["summary"]["failed"] += 1
                logger.error(f"❌ {test_name} FAILED: {result.get('error', 'Unknown error')}")

            self.results["summary"]["total"] += 1
            return result["success"]

        except Exception as e:
            duration = time.time() - start_time
            self.results["tests"].append({
                "name": test_name,
                "status": "error",
                "duration": duration,
                "error": str(e)
            })
            self.results["summary"]["failed"] += 1
            self.results["summary"]["total"] += 1
            logger.error(f"💥 {test_name} ERROR: {e}")
            return False

    def make_api_request(self, episode_id: str, params: Optional[Dict] = None) -> Tuple[Optional[requests.Response], float]:
        """Make API request and return response with timing"""
        url = f"{API_BASE_URL}{API_ENDPOINT}/{episode_id}"
        headers = {"Accept": "application/json"}

        start_time = time.time()
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            request_time = time.time() - start_time
            return response, request_time
        except requests.exceptions.Timeout:
            request_time = time.time() - start_time
            raise Exception(f"Request timed out after {request_time:.2f}s")
        except Exception as e:
            request_time = time.time() - start_time
            raise Exception(f"Request failed after {request_time:.2f}s: {e}")

    # Test Case 1: Standard Request (Happy Path)
    def test_standard_request(self) -> Dict:
        """Test standard 30-second clip generation"""
        episode_id = TEST_DATA["valid_episode"]["id"]
        params = {"start_time_ms": 30000}

        try:
            response, request_time = self.make_api_request(episode_id, params)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Expected 200, got {response.status_code}",
                    "response_body": response.text,
                    "request_time": request_time
                }

            data = response.json()

            # Validate response structure
            required_fields = ["clip_url", "expires_at", "cache_hit", "episode_id",
                             "start_time_ms", "duration_ms", "generation_time_ms"]
            missing_fields = [f for f in required_fields if f not in data]

            if missing_fields:
                return {
                    "success": False,
                    "error": f"Missing required fields: {missing_fields}",
                    "response_data": data
                }

            # Download and verify audio clip
            audio_verification = self.verify_audio_clip(data["clip_url"], "standard_30s.mp3")

            return {
                "success": True,
                "request_time": request_time,
                "generation_time": data["generation_time_ms"],
                "cache_hit": data["cache_hit"],
                "audio_verification": audio_verification,
                "response_data": data
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # Test Case 2: Custom Duration Request
    def test_custom_duration(self) -> Dict:
        """Test custom 15-second clip generation"""
        episode_id = TEST_DATA["valid_episode"]["id"]
        params = {"start_time_ms": 60000, "duration_ms": 15000}

        try:
            response, request_time = self.make_api_request(episode_id, params)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Expected 200, got {response.status_code}",
                    "response_body": response.text
                }

            data = response.json()

            # Verify duration matches request
            if data["duration_ms"] != 15000:
                return {
                    "success": False,
                    "error": f"Expected duration 15000ms, got {data['duration_ms']}ms"
                }

            # Download and verify audio clip
            audio_verification = self.verify_audio_clip(data["clip_url"], "custom_15s.mp3", expected_duration=15)

            return {
                "success": True,
                "request_time": request_time,
                "audio_verification": audio_verification,
                "response_data": data
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # Test Case 3: Cache Hit Performance
    def test_cache_hit(self) -> Dict:
        """Test cache hit performance"""
        episode_id = TEST_DATA["valid_episode"]["id"]
        params = {"start_time_ms": 30000}

        try:
            # First request (cache miss)
            response1, time1 = self.make_api_request(episode_id, params)
            data1 = response1.json()

            # Wait a moment
            time.sleep(1)

            # Second request (should be cache hit)
            response2, time2 = self.make_api_request(episode_id, params)
            data2 = response2.json()

            if not data2.get("cache_hit", False):
                return {
                    "success": False,
                    "error": "Expected cache hit on second request"
                }

            # Cache hit should be much faster
            if data2["generation_time_ms"] > 200:
                return {
                    "success": False,
                    "error": f"Cache hit too slow: {data2['generation_time_ms']}ms (expected <200ms)"
                }

            return {
                "success": True,
                "first_request": {
                    "time": time1,
                    "generation_time": data1["generation_time_ms"],
                    "cache_hit": data1["cache_hit"]
                },
                "second_request": {
                    "time": time2,
                    "generation_time": data2["generation_time_ms"],
                    "cache_hit": data2["cache_hit"]
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # Error Handling Tests
    def test_invalid_episode_id(self) -> Dict:
        """Test invalid episode ID format"""
        episode_id = TEST_DATA["malformed_episode_id"]
        params = {"start_time_ms": 30000}

        try:
            response, _ = self.make_api_request(episode_id, params)

            if response.status_code != 400:
                return {
                    "success": False,
                    "error": f"Expected 400, got {response.status_code}",
                    "response_body": response.text
                }

            data = response.json()
            if "Invalid episode ID format" not in str(data):
                return {
                    "success": False,
                    "error": "Expected 'Invalid episode ID format' error message",
                    "actual_message": data
                }

            return {"success": True, "response": data}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_nonexistent_episode(self) -> Dict:
        """Test non-existent episode"""
        episode_id = TEST_DATA["invalid_episode_id"]
        params = {"start_time_ms": 30000}

        try:
            response, _ = self.make_api_request(episode_id, params)

            if response.status_code != 404:
                return {
                    "success": False,
                    "error": f"Expected 404, got {response.status_code}",
                    "response_body": response.text
                }

            return {"success": True, "response": response.json()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_episode_without_transcript(self) -> Dict:
        """Test episode without transcript data"""
        episode_id = TEST_DATA["episode_without_transcript"]["id"]
        params = {"start_time_ms": 30000}

        try:
            response, _ = self.make_api_request(episode_id, params)

            if response.status_code != 422:
                return {
                    "success": False,
                    "error": f"Expected 422, got {response.status_code}",
                    "response_body": response.text
                }

            return {"success": True, "response": response.json()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_invalid_parameters(self) -> Dict:
        """Test various invalid parameter combinations"""
        episode_id = TEST_DATA["valid_episode"]["id"]

        test_cases = [
            {"params": {"start_time_ms": -1000}, "expected_status": 400, "name": "negative_start_time"},
            {"params": {"start_time_ms": 0, "duration_ms": 70000}, "expected_status": 400, "name": "duration_too_long"},
            {"params": {"start_time_ms": 0, "duration_ms": 0}, "expected_status": 400, "name": "zero_duration"},
        ]

        results = []
        for test in test_cases:
            try:
                response, _ = self.make_api_request(episode_id, test["params"])

                if response.status_code != test["expected_status"]:
                    results.append({
                        "test": test["name"],
                        "success": False,
                        "error": f"Expected {test['expected_status']}, got {response.status_code}"
                    })
                else:
                    results.append({
                        "test": test["name"],
                        "success": True,
                        "response": response.json()
                    })
            except Exception as e:
                results.append({
                    "test": test["name"],
                    "success": False,
                    "error": str(e)
                })

        # All sub-tests must pass
        all_passed = all(r["success"] for r in results)
        return {"success": all_passed, "results": results}

    def verify_audio_clip(self, clip_url: str, filename: str, expected_duration: Optional[int] = 30) -> Dict:
        """Download and verify audio clip"""
        try:
            # Download clip
            response = requests.get(clip_url, timeout=30)
            if response.status_code != 200:
                return {"success": False, "error": f"Failed to download clip: {response.status_code}"}

            # Save to file
            filepath = self.temp_dir / filename
            with open(filepath, 'wb') as f:
                f.write(response.content)

            # Verify with ffprobe
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(filepath)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return {"success": False, "error": "ffprobe failed", "stderr": result.stderr}

            actual_duration = float(result.stdout.strip())
            tolerance = 1.0  # Allow 1 second tolerance

            if abs(actual_duration - expected_duration) > tolerance:
                return {
                    "success": False,
                    "error": f"Duration mismatch: expected ~{expected_duration}s, got {actual_duration}s"
                }

            return {
                "success": True,
                "file_size": len(response.content),
                "duration": actual_duration,
                "filepath": str(filepath)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_performance_metrics(self) -> Dict:
        """Test performance with concurrent requests"""
        episode_id = TEST_DATA["valid_episode"]["id"]

        # Different test scenarios
        test_scenarios = [
            {"start_time_ms": 30000},
            {"start_time_ms": 60000},
            {"start_time_ms": 90000},
            {"start_time_ms": 120000},
            {"start_time_ms": 150000}
        ]

        results = []

        # Test concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_params = {
                executor.submit(self.make_api_request, episode_id, params): params
                for params in test_scenarios
            }

            for future in as_completed(future_to_params):
                params = future_to_params[future]
                try:
                    response, request_time = future.result()
                    data = response.json() if response.status_code == 200 else None
                    results.append({
                        "params": params,
                        "request_time": request_time,
                        "generation_time": data.get("generation_time_ms") if data else None,
                        "cache_hit": data.get("cache_hit") if data else None,
                        "status_code": response.status_code
                    })
                except Exception as e:
                    results.append({
                        "params": params,
                        "error": str(e)
                    })

        # Calculate metrics
        successful_requests = [r for r in results if "error" not in r and r["status_code"] == 200]
        if successful_requests:
            avg_request_time = sum(r["request_time"] for r in successful_requests) / len(successful_requests)
            cache_hits = [r for r in successful_requests if r.get("cache_hit", False)]
            cache_hit_rate = len(cache_hits) / len(successful_requests) * 100

            return {
                "success": True,
                "metrics": {
                    "total_requests": len(results),
                    "successful_requests": len(successful_requests),
                    "average_request_time": avg_request_time,
                    "cache_hit_rate": cache_hit_rate,
                    "results": results
                }
            }
        else:
            return {"success": False, "error": "No successful requests", "results": results}

    def run_all_tests(self):
        """Run all tests in sequence"""
        logger.info("=== Starting Comprehensive Audio API Testing ===\n")

        # Functional Tests
        self.run_test("Standard 30-second Clip", self.test_standard_request)
        self.run_test("Custom 15-second Clip", self.test_custom_duration)
        self.run_test("Cache Hit Performance", self.test_cache_hit)

        # Error Handling Tests
        self.run_test("Invalid Episode ID Format", self.test_invalid_episode_id)
        self.run_test("Non-existent Episode", self.test_nonexistent_episode)
        self.run_test("Episode Without Transcript", self.test_episode_without_transcript)
        self.run_test("Invalid Parameters", self.test_invalid_parameters)

        # Performance Tests
        self.run_test("Concurrent Performance Metrics", self.test_performance_metrics)

        # Save results
        self.save_results()
        self.print_summary()

    def save_results(self):
        """Save test results to JSON file"""
        results_file = f"audio_api_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"\nResults saved to: {results_file}")

    def print_summary(self):
        """Print test summary"""
        summary = self.results["summary"]
        logger.info("\n" + "="*50)
        logger.info("TEST SUMMARY")
        logger.info("="*50)
        logger.info(f"Total Tests: {summary['total']}")
        logger.info(f"Passed: {summary['passed']} ✅")
        logger.info(f"Failed: {summary['failed']} ❌")
        logger.info(f"Success Rate: {(summary['passed']/summary['total']*100):.1f}%")
        logger.info("="*50)

        # Performance summary
        perf_tests = [t for t in self.results["tests"] if "performance" in t["name"].lower()]
        if perf_tests and perf_tests[0]["status"] == "passed":
            metrics = perf_tests[0]["details"]["metrics"]
            logger.info("\nPERFORMANCE METRICS:")
            logger.info(f"  Average Request Time: {metrics['average_request_time']:.2f}s")
            logger.info(f"  Cache Hit Rate: {metrics['cache_hit_rate']:.1f}%")


if __name__ == "__main__":
    # Check if ffprobe is available
    try:
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
    except:
        logger.warning("ffprobe not found. Audio duration verification will be skipped.")
        logger.warning("Install ffmpeg to enable audio verification: brew install ffmpeg")

    tester = AudioAPITester()
    tester.run_all_tests()
