#!/usr/bin/env python3
"""
Check if DEBUG_MODE is enabled in Vercel
"""
import requests

def check_debug_mode():
    """Make a minimal request to check if raw_chunks are included"""
    url = "https://podinsight-api.vercel.app/api/search"
    
    # Very simple query to minimize other factors
    payload = {
        "query": "test",
        "limit": 1  # Just 1 result
    }
    
    print("Checking if DEBUG_MODE is enabled in Vercel...")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if raw_chunks is present in response
            if "raw_chunks" in data and data["raw_chunks"] is not None:
                print("⚠️  WARNING: DEBUG_MODE appears to be ENABLED!")
                print("raw_chunks are included in the response")
                print(f"Number of raw chunks: {len(data['raw_chunks'])}")
                if data['raw_chunks']:
                    first_chunk_size = len(str(data['raw_chunks'][0]))
                    print(f"First chunk size: {first_chunk_size} chars")
            else:
                print("✅ DEBUG_MODE appears to be DISABLED")
                print("No raw_chunks in response")
                
            # Also check response size
            response_size = len(response.content)
            print(f"\nTotal response size: {response_size} bytes ({response_size/1024:.1f} KB)")
            
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_debug_mode()