#!/usr/bin/env python3
"""
Test synthesis with debugging logs to identify timeout cause
"""
import requests
import time
import json

def test_synthesis_debug():
    """Test synthesis endpoint and monitor for timeout"""
    url = "https://podinsight-api.vercel.app/api/search"
    
    # Test query that should trigger synthesis
    payload = {
        "query": "AI valuations",
        "limit": 10  # Request 10 results to test larger payload
    }
    
    print(f"Testing synthesis with query: '{payload['query']}'")
    print(f"Requesting {payload['limit']} results to test payload size...")
    print("-" * 50)
    
    start_time = time.time()
    
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=35  # Set timeout slightly above Vercel's 30s
        )
        
        elapsed = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            response_size = len(response.content)
            print(f"Response Size: {response_size} bytes ({response_size/1024:.1f} KB)")
            
            if "answer" in data and data["answer"]:
                print(f"\nSynthesis Result: SUCCESS")
                print(f"Answer: {data['answer']['text'][:100]}...")
                print(f"Citations: {len(data['answer']['citations'])}")
            else:
                print(f"\nSynthesis Result: NO ANSWER")
                
            # Pretty print for debugging
            print("\nFull Response Structure:")
            print(json.dumps(data, indent=2)[:500] + "...")
        else:
            print(f"Error Response: {response.text}")
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"REQUEST TIMEOUT after {elapsed:.2f} seconds!")
        print("This confirms the timeout issue is still occurring.")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

    print("\n" + "="*50)
    print("NEXT STEPS:")
    print("1. Check Vercel logs for our new timing information:")
    print("   - 'Response object created, starting serialization...'")
    print("   - 'Manual serialization successful in X seconds'")
    print("   - 'Serialized response size: X bytes'")
    print("2. Look for any warnings about large payload size")
    print("3. Check if it reaches 'Handing response to framework...'")

if __name__ == "__main__":
    # Wait a moment for deployment to complete
    print("Waiting 30 seconds for Vercel deployment to complete...")
    time.sleep(30)
    
    test_synthesis_debug()