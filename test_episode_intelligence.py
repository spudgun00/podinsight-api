#!/usr/bin/env python3
"""Test the new Episode Intelligence endpoints"""

import requests
import json
from datetime import datetime

# API base URL
BASE_URL = "https://podinsight-api.vercel.app"

def test_market_signals():
    """Test the market signals endpoint"""
    print("\n=== Testing Market Signals Endpoint ===")

    url = f"{BASE_URL}/api/intelligence/market-signals"
    params = {
        "limit": 5,
        "offset": 0
    }

    try:
        response = requests.get(url, params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")

            # Validate response structure
            assert "data" in data
            assert "items" in data["data"]
            assert "totalCount" in data["data"]
            assert "lastUpdated" in data["data"]

            print("\n✅ Market Signals endpoint working correctly!")
        else:
            print(f"❌ Error: {response.text}")

    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

def test_deals():
    """Test the deals endpoint"""
    print("\n=== Testing Deals Endpoint ===")

    url = f"{BASE_URL}/api/intelligence/deals"
    params = {
        "limit": 5,
        "urgency": "high"
    }

    try:
        response = requests.get(url, params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")

            # Validate response structure
            assert "data" in data
            assert "items" in data["data"]

            print("\n✅ Deals endpoint working correctly!")
        else:
            print(f"❌ Error: {response.text}")

    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

def test_portfolio():
    """Test the portfolio mentions endpoint"""
    print("\n=== Testing Portfolio Endpoint ===")

    url = f"{BASE_URL}/api/intelligence/portfolio"
    params = {
        "limit": 5,
        "portfolio_ids": "OpenAI,Anthropic,Stripe"
    }

    try:
        response = requests.get(url, params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")

            # Validate response structure
            assert "data" in data
            assert "items" in data["data"]

            print("\n✅ Portfolio endpoint working correctly!")
        else:
            print(f"❌ Error: {response.text}")

    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

def test_executive_brief():
    """Test the executive brief endpoint"""
    print("\n=== Testing Executive Brief Endpoint ===")

    url = f"{BASE_URL}/api/intelligence/executive-brief"
    params = {
        "limit": 3
    }

    try:
        response = requests.get(url, params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")

            # Validate response structure
            assert "data" in data
            assert "items" in data["data"]

            print("\n✅ Executive Brief endpoint working correctly!")
        else:
            print(f"❌ Error: {response.text}")

    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

def main():
    """Run all tests"""
    print("=== Episode Intelligence API Tests ===")
    print(f"Testing against: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Test all endpoints
    test_market_signals()
    test_deals()
    test_portfolio()
    test_executive_brief()

    print("\n=== All Tests Completed ===")

if __name__ == "__main__":
    main()
