#!/usr/bin/env python3
"""Test bad input handling for Modal.com embedding endpoint"""

import requests
import json
import time
from typing import Dict, Any

# Modal endpoint
ENDPOINT = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"

def test_bad_input(test_name: str, query: Any) -> Dict[str, Any]:
    """Test a single bad input case"""
    print(f"\n🧪 Testing: {test_name}")
    print(f"   Input type: {type(query).__name__}")
    if isinstance(query, str):
        print(f"   Input length: {len(query)} chars")
    
    start_time = time.time()
    
    try:
        # Prepare payload
        payload = {"text": query} if query is not None else {}
        
        # Make request
        response = requests.post(
            ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        elapsed = time.time() - start_time
        
        result = {
            "test_name": test_name,
            "status_code": response.status_code,
            "elapsed_time": elapsed,
            "success": False,
            "error": None,
            "embedding_dim": None
        }
        
        if response.status_code == 200:
            data = response.json()
            if "embedding" in data and isinstance(data["embedding"], list):
                result["embedding_dim"] = len(data["embedding"])
                result["success"] = result["embedding_dim"] == 768
                print(f"   ✅ Status: {response.status_code}")
                print(f"   ✅ Embedding dimension: {result['embedding_dim']}")
            else:
                result["error"] = "Invalid response format"
                print(f"   ❌ Invalid response format")
        else:
            result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
            print(f"   ❌ Status: {response.status_code}")
            print(f"   ❌ Error: {response.text[:200]}")
            
        print(f"   ⏱️  Time: {elapsed:.2f}s")
        
    except Exception as e:
        elapsed = time.time() - start_time
        result = {
            "test_name": test_name,
            "status_code": None,
            "elapsed_time": elapsed,
            "success": False,
            "error": str(e),
            "embedding_dim": None
        }
        print(f"   ❌ Exception: {str(e)}")
        print(f"   ⏱️  Time: {elapsed:.2f}s")
    
    return result

def main():
    print("=" * 80)
    print("🔥 BAD INPUT HANDLING TEST")
    print("Testing Modal.com embedding endpoint with edge cases")
    print("=" * 80)
    
    # Generate a very long string (2000+ chars)
    long_text = "venture capital " * 150  # ~2100 chars
    
    # Test cases
    test_cases = [
        ("Empty string", ""),
        ("Single character", "a"),
        ("Single space", " "),
        ("Multiple spaces", "   "),
        ("Newlines only", "\n\n\n"),
        ("Special characters", "!@#$%^&*()_+-=[]{}|;':\",./<>?"),
        ("2000+ character paragraph", long_text),
        ("None/null value", None),
        ("Numeric input", "12345"),
        ("Boolean string", "true"),
        ("JSON injection", '{"query": "test", "extra": "field"}'),
        ("SQL injection attempt", "'; DROP TABLE chunks; --"),
        ("HTML tags", "<script>alert('test')</script>"),
        ("Zero-width characters", "test\u200b\u200c\u200d"),
        ("Control characters", "test\x00\x01\x02"),
        ("Mixed whitespace", "\t\n\r test \t\n\r"),
        ("Repeated punctuation", "???!!!..."),
        ("URL", "https://example.com/test?param=value"),
        ("Email", "test@example.com"),
        ("Emoji only", "🤖")
    ]
    
    results = []
    passed = 0
    failed = 0
    
    print("\n📊 Running edge case tests...")
    
    for test_name, query in test_cases:
        result = test_bad_input(test_name, query)
        results.append(result)
        
        if result["success"] or (result["status_code"] in [400, 422] and result["error"]):
            # Either got valid embedding or proper error response
            passed += 1
        else:
            failed += 1
        
        time.sleep(0.5)  # Small delay between requests
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    print(f"\n✅ Passed: {passed}/{len(test_cases)}")
    print(f"❌ Failed: {failed}/{len(test_cases)}")
    
    print("\n📈 Detailed Results:")
    print("-" * 80)
    print(f"{'Test Name':<30} {'Status':<10} {'Time':<8} {'Embedding':<10} {'Result':<10}")
    print("-" * 80)
    
    for r in results:
        status = r['status_code'] or 'ERROR'
        time_str = f"{r['elapsed_time']:.2f}s"
        embed_str = f"{r['embedding_dim']}D" if r['embedding_dim'] else "N/A"
        result_str = "✅ PASS" if (r['success'] or (r['status_code'] in [400, 422])) else "❌ FAIL"
        
        print(f"{r['test_name']:<30} {status:<10} {time_str:<8} {embed_str:<10} {result_str:<10}")
    
    print("\n🎯 Expected Behavior:")
    print("- Valid inputs → 768D embeddings")
    print("- Invalid inputs → 400/422 errors with clear messages")
    print("- No crashes or 500 errors")
    print("- All requests complete within timeout")
    
    # Check for critical failures
    critical_failures = [r for r in results if r['status_code'] == 500 or r['status_code'] is None]
    if critical_failures:
        print("\n⚠️  CRITICAL FAILURES DETECTED:")
        for r in critical_failures:
            print(f"  - {r['test_name']}: {r['error']}")
    else:
        print("\n✅ No critical failures (500 errors or timeouts)")

if __name__ == "__main__":
    main()