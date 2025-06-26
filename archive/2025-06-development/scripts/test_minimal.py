import requests
import json

# Test the search endpoint
url = "https://podinsight-api.vercel.app/api/search"
data = {"query": "AI agents", "limit": 3}

print("Testing search endpoint...")
print(f"URL: {url}")
print(f"Data: {json.dumps(data)}")

response = requests.post(url, json=data)
print(f"\nStatus Code: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
print(f"Response Text: {response.text}")

if response.status_code == 500:
    print("\n❌ Server error - check Vercel logs at:")
    print("https://vercel.com/james-projects-eede2cf2/podinsight-api/functions")
