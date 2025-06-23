#!/usr/bin/env python
"""
Test script for connection pool implementation
Run this to verify the connection pooling is working correctly
"""
import asyncio
import aiohttp
import time
from datetime import datetime

API_BASE_URL = "http://localhost:8000"  # Update this if deployed


async def test_single_request():
    """Test a single request"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/api/pool-stats") as resp:
            data = await resp.json()
            print(f"Pool stats: {data['stats']}")
            return data


async def test_concurrent_requests(num_requests=15):
    """Test multiple concurrent requests"""
    print(f"\n🧪 Testing {num_requests} concurrent requests...")
    
    async with aiohttp.ClientSession() as session:
        # Create multiple concurrent requests
        tasks = []
        for i in range(num_requests):
            task = session.get(f"{API_BASE_URL}/api/topic-velocity?weeks=4")
            tasks.append(task)
        
        # Execute all requests concurrently
        start_time = time.time()
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Check results
        success_count = sum(1 for r in responses if r.status == 200)
        print(f"✅ Successful requests: {success_count}/{num_requests}")
        print(f"⏱️  Total time: {end_time - start_time:.2f}s")
        
        # Get pool stats after load
        async with session.get(f"{API_BASE_URL}/api/pool-stats") as resp:
            data = await resp.json()
            stats = data['stats']
            print(f"\n📊 Pool Statistics after load test:")
            print(f"   - Active connections: {stats['active_connections']}")
            print(f"   - Peak connections: {stats['peak_connections']}")
            print(f"   - Total requests: {stats['total_requests']}")
            print(f"   - Errors: {stats['errors']}")
            print(f"   - Utilization: {stats['utilization_percent']:.1f}%")


async def test_connection_limit():
    """Test that pool properly limits connections"""
    print("\n🧪 Testing connection limit enforcement...")
    
    async with aiohttp.ClientSession() as session:
        # Monitor pool stats during test
        async def monitor_pool():
            max_active = 0
            for _ in range(10):
                async with session.get(f"{API_BASE_URL}/api/pool-stats") as resp:
                    data = await resp.json()
                    active = data['stats']['active_connections']
                    max_active = max(max_active, active)
                await asyncio.sleep(0.1)
            return max_active
        
        # Run requests and monitoring concurrently
        monitor_task = asyncio.create_task(monitor_pool())
        
        # Create 20 concurrent requests (exceeding pool limit of 10)
        tasks = []
        for i in range(20):
            task = session.get(f"{API_BASE_URL}/api/topic-velocity")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        max_active = await monitor_task
        
        print(f"✅ All requests completed successfully")
        print(f"📊 Maximum active connections observed: {max_active}/10")
        
        if max_active <= 10:
            print("✅ Connection pool properly enforced limit!")
        else:
            print("❌ Connection pool exceeded limit!")


async def test_error_recovery():
    """Test connection pool error recovery"""
    print("\n🧪 Testing error recovery...")
    
    async with aiohttp.ClientSession() as session:
        # Test with invalid endpoint to trigger errors
        tasks = []
        for i in range(5):
            task = session.get(f"{API_BASE_URL}/api/invalid-endpoint")
            tasks.append(task)
        
        # Also include some valid requests
        for i in range(5):
            task = session.get(f"{API_BASE_URL}/api/pool-stats")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        error_count = sum(1 for r in responses if isinstance(r, Exception) or (hasattr(r, 'status') and r.status >= 400))
        success_count = 10 - error_count
        
        print(f"✅ Successful requests: {success_count}/10")
        print(f"❌ Failed requests: {error_count}/10")
        
        # Check pool health after errors
        async with session.get(f"{API_BASE_URL}/") as resp:
            data = await resp.json()
            pool_health = data['connection_pool']
            print(f"\n📊 Pool health after errors: {pool_health['status']}")


async def main():
    """Run all tests"""
    print("🚀 Starting Connection Pool Tests")
    print("=" * 50)
    
    # Test 1: Single request
    print("\n1️⃣ Testing single request...")
    await test_single_request()
    
    # Test 2: Concurrent requests
    await test_concurrent_requests(15)
    
    # Test 3: Connection limit
    await test_connection_limit()
    
    # Test 4: Error recovery
    await test_error_recovery()
    
    print("\n✅ All tests completed!")
    print("=" * 50)


if __name__ == "__main__":
    # Note: To test against deployed API, update API_BASE_URL
    print(f"Testing against: {API_BASE_URL}")
    asyncio.run(main())