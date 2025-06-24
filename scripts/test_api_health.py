#!/usr/bin/env python3
"""
Test API health and available endpoints
"""

import requests
import json

# Test different possible endpoints
endpoints = [
    {
        "name": "Vercel API - Health",
        "url": "https://podinsight-api.vercel.app/api/health",
        "method": "GET"
    },
    {
        "name": "Vercel API - Root",
        "url": "https://podinsight-api.vercel.app/",
        "method": "GET"
    },
    {
        "name": "Vercel API - API Root",
        "url": "https://podinsight-api.vercel.app/api",
        "method": "GET"
    },
    {
        "name": "Vercel API - Search (GET)",
        "url": "https://podinsight-api.vercel.app/api/search",
        "method": "GET"
    },
    {
        "name": "Vercel API - Search (POST)",
        "url": "https://podinsight-api.vercel.app/api/search",
        "method": "POST",
        "json": {"query": "test"}
    },
    {
        "name": "Modal Embeddings - Health",
        "url": "https://jamesgill--podinsight-embeddings-simple-health-check.modal.run",
        "method": "GET"
    },
    {
        "name": "Modal Embeddings - Generate",
        "url": "https://jamesgill--podinsight-embeddings-simple-generate-embedding.modal.run",
        "method": "POST",
        "json": {"text": "test"}
    }
]

print("Testing API Endpoints...")
print("=" * 60)

for endpoint in endpoints:
    print(f"\nTesting: {endpoint['name']}")
    print(f"URL: {endpoint['url']}")
    print(f"Method: {endpoint['method']}")
    
    try:
        if endpoint['method'] == 'GET':
            response = requests.get(endpoint['url'], timeout=10)
        else:
            headers = {"Content-Type": "application/json"} if 'json' in endpoint else {}
            data = endpoint.get('json', {})
            response = requests.post(endpoint['url'], json=data, headers=headers, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        # Try to parse JSON response
        try:
            json_response = response.json()
            print(f"Response: {json.dumps(json_response, indent=2)[:200]}...")
        except:
            print(f"Response (text): {response.text[:200]}...")
            
    except Exception as e:
        print(f"Error: {e}")
    
    print("-" * 60)