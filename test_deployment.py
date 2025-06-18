#!/usr/bin/env python3
"""Test the deployed search API on Vercel"""

import requests
import json
import time
from typing import Optional

def test_health_endpoint():
    """Test the health check endpoint"""
    url = "https://podinsight-api.vercel.app/api/health"
    try:
        response = requests.get(url)
        print(f"✓ Health check: {response.status_code}")
        if response.status_code == 200:
            print(f"  Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_search_endpoint():
    """Test the search endpoint with a simple query"""
    url = "https://podinsight-api.vercel.app/api/search"
    data = {"query": "AI agents", "limit": 3}
    
    print(f"\nTesting search endpoint...")
    print(f"  URL: {url}")
    print(f"  Query: {data['query']}")
    
    try:
        response = requests.post(url, json=data)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Search successful!")
            print(f"  Results found: {len(result.get('results', []))}")
            print(f"  Cache hit: {result.get('cache_hit', False)}")
            print(f"  Search ID: {result.get('search_id', 'N/A')}")
            
            # Show first result if available
            if result.get('results'):
                first = result['results'][0]
                print(f"\n  First result:")
                print(f"    Title: {first.get('title', 'N/A')}")
                print(f"    Podcast: {first.get('podcast_name', 'N/A')}")
                print(f"    Score: {first.get('score', 'N/A')}")
                excerpt = first.get('excerpt', '')
                if excerpt:
                    print(f"    Excerpt: {excerpt[:100]}...")
            
            return True
        else:
            print(f"✗ Search failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Search request failed: {e}")
        return False

def test_topic_velocity():
    """Test the topic velocity endpoint"""
    url = "https://podinsight-api.vercel.app/api/topic-velocity"
    
    print(f"\nTesting topic velocity endpoint...")
    
    try:
        response = requests.get(url)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Topic velocity successful!")
            
            # Check for data
            if 'weeklyData' in result:
                print(f"  Weeks of data: {len(result['weeklyData'])}")
                # Check topics
                topics = set()
                for week in result['weeklyData']:
                    topics.update(week.keys())
                topics.discard('week')
                print(f"  Topics found: {', '.join(sorted(topics))}")
            
            return True
        else:
            print(f"✗ Topic velocity failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Topic velocity request failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Testing PodInsight API Deployment on Vercel")
    print("=" * 60)
    
    # Test all endpoints
    health_ok = test_health_endpoint()
    
    if health_ok:
        # Give the API a moment to warm up
        time.sleep(1)
        
        search_ok = test_search_endpoint()
        velocity_ok = test_topic_velocity()
        
        print("\n" + "=" * 60)
        print("Summary:")
        print(f"  Health Check: {'✓ PASS' if health_ok else '✗ FAIL'}")
        print(f"  Search API: {'✓ PASS' if search_ok else '✗ FAIL'}")
        print(f"  Topic Velocity: {'✓ PASS' if velocity_ok else '✗ FAIL'}")
        print("=" * 60)
        
        if all([health_ok, search_ok, velocity_ok]):
            print("\n🎉 All tests passed! Your deployment is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Check the Vercel logs:")
            print("https://vercel.com/james-projects-eede2cf2/podinsight-api/functions")
    else:
        print("\n❌ Health check failed. The deployment might still be in progress.")
        print("Wait a minute and try again, or check Vercel logs.")

if __name__ == "__main__":
    main()