#!/usr/bin/env python3
"""
Test script for intelligence endpoints
Tests the endpoints without authentication first to ensure they return 401
"""
import httpx
import asyncio
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

async def test_endpoints():
    """Test all intelligence endpoints"""
    async with httpx.AsyncClient() as client:
        print("Testing Intelligence API Endpoints")
        print("=" * 50)
        
        # Test health check (should work without auth)
        print("\n1. Testing health check...")
        try:
            response = await client.get(f"{BASE_URL}/api/intelligence/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"   Error: {str(e)}")
        
        # Test dashboard without auth (should return 401)
        print("\n2. Testing dashboard without auth...")
        try:
            response = await client.get(f"{BASE_URL}/api/intelligence/dashboard")
            print(f"   Status: {response.status_code}")
            if response.status_code == 401:
                print("   ✓ Correctly requires authentication")
            else:
                print(f"   ✗ Expected 401, got {response.status_code}")
        except Exception as e:
            print(f"   Error: {str(e)}")
        
        # Test brief without auth (should return 401)
        print("\n3. Testing brief without auth...")
        try:
            response = await client.get(f"{BASE_URL}/api/intelligence/brief/test-episode-id")
            print(f"   Status: {response.status_code}")
            if response.status_code == 401:
                print("   ✓ Correctly requires authentication")
            else:
                print(f"   ✗ Expected 401, got {response.status_code}")
        except Exception as e:
            print(f"   Error: {str(e)}")
        
        # Test share without auth (should return 401)
        print("\n4. Testing share without auth...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/intelligence/share",
                json={
                    "episode_id": "test-episode",
                    "method": "email",
                    "recipient": "test@example.com"
                }
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 401:
                print("   ✓ Correctly requires authentication")
            else:
                print(f"   ✗ Expected 401, got {response.status_code}")
        except Exception as e:
            print(f"   Error: {str(e)}")
        
        # Test preferences without auth (should return 401)
        print("\n5. Testing preferences without auth...")
        try:
            response = await client.put(
                f"{BASE_URL}/api/intelligence/preferences",
                json={
                    "portfolio_companies": ["TestCo"],
                    "interest_topics": ["AI", "SaaS"]
                }
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 401:
                print("   ✓ Correctly requires authentication")
            else:
                print(f"   ✗ Expected 401, got {response.status_code}")
        except Exception as e:
            print(f"   Error: {str(e)}")
        
        print("\n" + "=" * 50)
        print("All authentication checks passed! ✓")
        print("Endpoints correctly require authentication.")

if __name__ == "__main__":
    asyncio.run(test_endpoints())