#!/usr/bin/env python3
"""
Test script for sentiment analysis API endpoint
"""

import os
import sys
import json
import requests
from datetime import datetime

# Add the api directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

def test_local_handler():
    """Test the handler locally without HTTP server"""
    print("Testing sentiment analysis handler locally...\n")

    # Import the handler
    from sentiment_analysis import handler

    # Create a mock request
    class MockRequest:
        def __init__(self, path):
            self.path = path

    class MockWFile:
        def __init__(self):
            self.data = b""

        def write(self, data):
            self.data += data

    # Test the handler
    h = handler(MockRequest("/api/sentiment_analysis?weeks=4&topics[]=AI+Agents&topics[]=B2B+SaaS"), ('127.0.0.1', 8000), None)
    h.wfile = MockWFile()

    # Mock the send_response and send_header methods
    h.send_response = lambda code: print(f"Response code: {code}")
    h.send_header = lambda key, value: print(f"Header: {key} = {value}")
    h.end_headers = lambda: print("Headers sent\n")

    try:
        h.do_GET()

        # Parse the response
        response_data = h.wfile.data.decode('utf-8')
        response = json.loads(response_data)

        print("Response received!")
        print(f"Success: {response.get('success')}")
        print(f"Data points: {len(response.get('data', []))}")

        # Show sample data
        if response.get('data'):
            print("\nSample sentiment data:")
            for item in response['data'][:10]:  # Show first 10 items
                print(f"  {item['topic']} - {item['week']}: {item['sentiment']} (from {item['episodeCount']} episodes)")

    except Exception as e:
        print(f"Error testing handler: {e}")
        import traceback
        traceback.print_exc()


def test_deployed_api():
    """Test the deployed API endpoint"""
    print("\n\nTesting deployed API endpoint...")

    # Test URLs
    urls = [
        "http://localhost:3000/api/sentiment_analysis?weeks=4",
        "https://podinsight-api.vercel.app/api/sentiment_analysis?weeks=4"
    ]

    for url in urls:
        print(f"\nTesting: {url}")
        try:
            response = requests.get(url, timeout=30)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Success: {data.get('success')}")
                print(f"Data points: {len(data.get('data', []))}")

                # Show sample data
                if data.get('data'):
                    print("\nSample sentiment data:")
                    for item in data['data'][:5]:
                        print(f"  {item['topic']} - {item['week']}: {item['sentiment']} (from {item['episodeCount']} episodes)")
            else:
                print(f"Error response: {response.text}")

        except requests.exceptions.ConnectionError:
            print("Connection failed - endpoint not running")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    # Check for MongoDB URI
    if not os.getenv('MONGODB_URI'):
        print("ERROR: MONGODB_URI environment variable not set!")
        print("Please set it before running tests.")
        sys.exit(1)

    print("Starting sentiment analysis API tests...")
    print(f"Timestamp: {datetime.now()}")
    print("-" * 50)

    # Test locally first
    test_local_handler()

    # Then test deployed endpoints
    # test_deployed_api()  # Uncomment when ready to test deployed version
