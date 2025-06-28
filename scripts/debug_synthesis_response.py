#!/usr/bin/env python3
"""
Debug script to understand the actual API response structure
"""
import requests
import json
from pprint import pprint

def debug_api_response(query: str = "AI", limit: int = 1):
    """Call the API and print the raw response structure"""
    url = "https://podinsight-api.vercel.app/api/search"

    print(f"🔍 Testing query: '{query}' (limit={limit})")
    print("=" * 80)

    try:
        response = requests.post(
            url,
            json={"query": query, "limit": limit},
            timeout=30
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print("\n" + "=" * 80 + "\n")

        if response.status_code == 200:
            data = response.json()

            # Print the full structure
            print("FULL RESPONSE STRUCTURE:")
            print(json.dumps(data, indent=2))

            # Specifically check the answer structure
            if "answer" in data and data["answer"]:
                print("\n" + "=" * 80 + "\n")
                print("ANSWER OBJECT STRUCTURE:")
                print(f"Type: {type(data['answer'])}")
                print("Keys:", list(data['answer'].keys()) if isinstance(data['answer'], dict) else "Not a dict")

                if "citations" in data["answer"]:
                    print("\nCITATION STRUCTURE:")
                    citations = data["answer"]["citations"]
                    print(f"Number of citations: {len(citations)}")
                    if citations:
                        print("First citation type:", type(citations[0]))
                        print("First citation keys:", list(citations[0].keys()) if isinstance(citations[0], dict) else "Not a dict")
                        print("\nFirst citation content:")
                        pprint(citations[0])

        else:
            print(f"Error Response: {response.text}")

    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    debug_api_response()
