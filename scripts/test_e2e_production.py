#!/usr/bin/env python3
"""
End-to-End Production Test Suite for PodInsight API
Tests the LIVE production endpoints on Vercel and Modal
"""

import requests
import time
import json
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Any
import statistics
import sys

# Production endpoints
VERCEL_BASE = "https://podinsight-api.vercel.app"
MODAL_ENDPOINT = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"

# Test results storage
test_results = []
start_time = datetime.now()

def log_result(test_name: str, status: str, details: Dict[str, Any]):
    """Log test result with timestamp"""
    result = {
        "timestamp": datetime.now().isoformat(),
        "test": test_name,
        "status": status,
        "details": details
    }
    test_results.append(result)
    
    # Print to console
    icon = "✅" if status == "PASS" else "❌"
    print(f"{icon} {test_name}: {status}")
    if details.get("latency_ms"):
        print(f"   Latency: {details['latency_ms']}ms")
    if details.get("error"):
        print(f"   Error: {details['error']}")
    print()

def test_health_endpoint():
    """1. Smoke test - Health endpoint"""
    print("=" * 60)
    print("1. SMOKE TEST - Health Endpoint")
    print("=" * 60)
    
    try:
        start = time.time()
        response = requests.get(f"{VERCEL_BASE}/api/health", timeout=10)
        latency = int((time.time() - start) * 1000)
        
        if response.status_code == 200:
            log_result("Health Endpoint", "PASS", {
                "status_code": response.status_code,
                "latency_ms": latency,
                "response": response.json()
            })
        else:
            log_result("Health Endpoint", "FAIL", {
                "status_code": response.status_code,
                "latency_ms": latency,
                "error": response.text
            })
    except Exception as e:
        log_result("Health Endpoint", "FAIL", {"error": str(e)})

def test_cold_start():
    """2. Cold start test - Wait 8 minutes then test"""
    print("=" * 60)
    print("2. COLD START TEST")
    print("=" * 60)
    
    print("Waiting 8 minutes for containers to scale to zero...")
    print("(You can skip this with Ctrl+C if containers are already cold)")
    
    try:
        for i in range(480, 0, -30):
            print(f"   {i} seconds remaining...")
            time.sleep(30)
    except KeyboardInterrupt:
        print("   Skipped waiting period")
    
    try:
        start = time.time()
        response = requests.post(
            f"{VERCEL_BASE}/api/search",
            json={"query": "cold start ping", "limit": 1},
            timeout=30
        )
        latency = int((time.time() - start) * 1000)
        
        if response.status_code == 200:
            data = response.json()
            log_result("Cold Start", "PASS", {
                "status_code": response.status_code,
                "latency_ms": latency,
                "results_count": len(data.get("results", [])),
                "total_results": data.get("total_results", 0)
            })
            
            if latency > 20000:
                print("⚠️  WARNING: Cold start took >20s, possible regression")
        else:
            log_result("Cold Start", "FAIL", {
                "status_code": response.status_code,
                "latency_ms": latency,
                "error": response.text[:200]
            })
    except Exception as e:
        log_result("Cold Start", "FAIL", {"error": str(e)})

def test_warm_path():
    """3. Warm path latency - 10 requests"""
    print("=" * 60)
    print("3. WARM PATH LATENCY TEST")
    print("=" * 60)
    
    latencies = []
    
    for i in range(10):
        try:
            start = time.time()
            response = requests.post(
                f"{VERCEL_BASE}/api/search",
                json={"query": f"warm test {i}", "limit": 1},
                timeout=10
            )
            latency = int((time.time() - start) * 1000)
            latencies.append(latency)
            
            print(f"   Request {i+1}: {latency}ms - Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"   Error: {response.text[:100]}")
            
            time.sleep(0.5)
        except Exception as e:
            print(f"   Request {i+1}: ERROR - {str(e)}")
    
    if latencies:
        median = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        
        log_result("Warm Path Latency", "PASS" if median < 1000 else "FAIL", {
            "requests": len(latencies),
            "median_ms": median,
            "p95_ms": p95,
            "max_ms": max(latencies),
            "all_latencies": latencies
        })

def test_bad_inputs():
    """4. Bad input resilience"""
    print("=" * 60)
    print("4. BAD INPUT RESILIENCE TEST")
    print("=" * 60)
    
    test_cases = [
        ("Empty string", ""),
        ("Single letter", "a"),
        ("2KB text", "venture capital " * 150),
        ("HTML injection", "<script>alert(1)</script>"),
        ("Special chars", "!@#$%^&*()"),
        ("Null body", None)
    ]
    
    for test_name, query in test_cases:
        try:
            payload = {"query": query, "limit": 1} if query is not None else None
            
            start = time.time()
            response = requests.post(
                f"{VERCEL_BASE}/api/search",
                json=payload,
                timeout=10
            )
            latency = int((time.time() - start) * 1000)
            
            # For null body, we expect 422/400
            # For strings, we expect 200
            expected = [422, 400] if query is None else [200]
            
            if response.status_code in expected:
                log_result(f"Bad Input - {test_name}", "PASS", {
                    "status_code": response.status_code,
                    "latency_ms": latency
                })
            else:
                log_result(f"Bad Input - {test_name}", "FAIL", {
                    "status_code": response.status_code,
                    "expected": expected,
                    "latency_ms": latency,
                    "error": response.text[:200]
                })
                
        except Exception as e:
            log_result(f"Bad Input - {test_name}", "FAIL", {"error": str(e)})

def test_unicode_emoji():
    """5. Unicode & emoji sanity"""
    print("=" * 60)
    print("5. UNICODE & EMOJI TEST")
    print("=" * 60)
    
    test_cases = [
        ("Emoji", "🦄 startup"),
        ("Chinese", "人工智能"),
        ("Arabic", "مرحبا"),
        ("Russian", "Привет мир"),
        ("Mixed", "AI 🤖 startup 创业")
    ]
    
    for test_name, query in test_cases:
        try:
            start = time.time()
            response = requests.post(
                f"{VERCEL_BASE}/api/search",
                json={"query": query, "limit": 1},
                timeout=10
            )
            latency = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                # Check for mojibake in response
                response_text = json.dumps(data)
                has_mojibake = '\\u' in response_text or '?' in response_text
                
                log_result(f"Unicode - {test_name}", "PASS" if not has_mojibake else "FAIL", {
                    "status_code": response.status_code,
                    "latency_ms": latency,
                    "mojibake": has_mojibake
                })
            else:
                log_result(f"Unicode - {test_name}", "FAIL", {
                    "status_code": response.status_code,
                    "latency_ms": latency,
                    "error": response.text[:200]
                })
                
        except Exception as e:
            log_result(f"Unicode - {test_name}", "FAIL", {"error": str(e)})

def test_concurrent_requests():
    """6. Concurrency burst - 20 parallel requests"""
    print("=" * 60)
    print("6. CONCURRENT REQUESTS TEST")
    print("=" * 60)
    
    def make_request(i):
        try:
            start = time.time()
            response = requests.post(
                f"{VERCEL_BASE}/api/search",
                json={"query": f"concurrent test {i}", "limit": 1},
                timeout=30
            )
            latency = int((time.time() - start) * 1000)
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "latency_ms": latency
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    print("Firing 20 parallel requests...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(make_request, i) for i in range(20)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    successful = sum(1 for r in results if r.get("success"))
    latencies = [r["latency_ms"] for r in results if "latency_ms" in r]
    
    log_result("Concurrent Requests", "PASS" if successful >= 18 else "FAIL", {
        "total": 20,
        "successful": successful,
        "failed": 20 - successful,
        "max_latency_ms": max(latencies) if latencies else None,
        "median_latency_ms": statistics.median(latencies) if latencies else None
    })

def test_snapshot_cold_start():
    """7. Cold start after snapshot"""
    print("=" * 60)
    print("7. SNAPSHOT COLD START TEST")
    print("=" * 60)
    
    print("Waiting 10 minutes for containers to scale to zero...")
    print("(You can skip this with Ctrl+C)")
    
    try:
        for i in range(600, 0, -60):
            print(f"   {i} seconds remaining...")
            time.sleep(60)
    except KeyboardInterrupt:
        print("   Skipped waiting period")
    
    try:
        start = time.time()
        response = requests.post(
            f"{VERCEL_BASE}/api/search",
            json={"query": "snapshot cold start test", "limit": 1},
            timeout=30
        )
        latency = int((time.time() - start) * 1000)
        
        if response.status_code == 200:
            # Snapshot should make it ~6s instead of ~14s
            is_snapshot = latency < 8000
            log_result("Snapshot Cold Start", "PASS", {
                "status_code": response.status_code,
                "latency_ms": latency,
                "likely_snapshot": is_snapshot
            })
            
            if not is_snapshot:
                print("⚠️  WARNING: Cold start took >8s, snapshot may not be working")
        else:
            log_result("Snapshot Cold Start", "FAIL", {
                "status_code": response.status_code,
                "latency_ms": latency,
                "error": response.text[:200]
            })
    except Exception as e:
        log_result("Snapshot Cold Start", "FAIL", {"error": str(e)})

def generate_report():
    """Generate final test report"""
    print("\n" + "=" * 60)
    print("FINAL TEST REPORT")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed = sum(1 for r in test_results if r["status"] == "PASS")
    failed = total_tests - passed
    
    print(f"\nTest Summary:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Success Rate: {(passed/total_tests*100):.1f}%")
    print(f"  Duration: {datetime.now() - start_time}")
    
    # Save detailed report
    report = {
        "test_run": {
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration": str(datetime.now() - start_time),
            "endpoints": {
                "vercel": VERCEL_BASE,
                "modal": MODAL_ENDPOINT
            }
        },
        "summary": {
            "total": total_tests,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{(passed/total_tests*100):.1f}%"
        },
        "results": test_results
    }
    
    # Save JSON report
    report_file = f"e2e-test-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    # Show failures
    if failed > 0:
        print("\nFailed Tests:")
        for r in test_results:
            if r["status"] == "FAIL":
                print(f"  - {r['test']}: {r['details'].get('error', 'Unknown error')}")
    
    return passed == total_tests

def main():
    """Run all tests"""
    print("\n🚀 PodInsight End-to-End Production Test Suite")
    print(f"Testing endpoints:")
    print(f"  Vercel: {VERCEL_BASE}")
    print(f"  Modal: {MODAL_ENDPOINT}")
    print(f"Started at: {start_time}\n")
    
    # Run tests in sequence
    test_health_endpoint()
    test_cold_start()
    test_warm_path()
    test_bad_inputs()
    test_unicode_emoji()
    test_concurrent_requests()
    test_snapshot_cold_start()
    
    # Generate report
    all_passed = generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()