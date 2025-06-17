#!/usr/bin/env python
"""
Load test for connection pooling - makes rapid requests to verify pooling
"""
import asyncio
import aiohttp
import time
from datetime import datetime
import json

API_BASE_URL = "http://localhost:8000"


async def rapid_fire_test(num_requests=20, delay=0):
    """Fire requests rapidly to test connection pooling"""
    print(f"\n🚀 Rapid Fire Test: {num_requests} requests with {delay}s delay")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Track stats before test
        async with session.get(f"{API_BASE_URL}/api/pool-stats") as resp:
            before_stats = await resp.json()
            print(f"📊 Before test: {before_stats['stats']['active_connections']} active connections")
        
        # Create all tasks at once
        tasks = []
        start_time = time.time()
        
        for i in range(num_requests):
            task = asyncio.create_task(
                make_request(session, i, f"{API_BASE_URL}/api/topic-velocity?weeks=4")
            )
            tasks.append(task)
            if delay > 0:
                await asyncio.sleep(delay)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyze results
        success_count = sum(1 for r in results if r is True)
        error_count = len(results) - success_count
        total_time = end_time - start_time
        avg_time = total_time / len(results)
        
        print(f"\n📈 Results:")
        print(f"   ✅ Successful: {success_count}/{num_requests}")
        print(f"   ❌ Failed: {error_count}/{num_requests}")
        print(f"   ⏱️  Total time: {total_time:.2f}s")
        print(f"   ⚡ Avg response: {avg_time:.3f}s")
        
        # Check final stats
        async with session.get(f"{API_BASE_URL}/api/pool-stats") as resp:
            after_stats = await resp.json()
            stats = after_stats['stats']
            print(f"\n📊 After test:")
            print(f"   - Active connections: {stats['active_connections']}")
            print(f"   - Peak connections: {stats['peak_connections']}")
            print(f"   - Total requests: {stats['total_requests']}")
            print(f"   - Errors: {stats['errors']}")
            print(f"   - Utilization: {stats['utilization_percent']:.1f}%")
        
        return stats['peak_connections']


async def make_request(session, request_id, url):
    """Make a single request and track timing"""
    start = time.time()
    try:
        async with session.get(url) as resp:
            await resp.json()  # Ensure we read the response
            duration = time.time() - start
            if request_id % 5 == 0:  # Log every 5th request
                print(f"   Request {request_id}: {resp.status} in {duration:.3f}s")
            return True
    except Exception as e:
        print(f"   Request {request_id} failed: {str(e)}")
        return False


async def continuous_monitoring(duration=10):
    """Monitor pool stats continuously during load test"""
    print(f"\n📊 Monitoring pool for {duration} seconds...")
    
    max_active = 0
    readings = []
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                async with session.get(f"{API_BASE_URL}/api/pool-stats") as resp:
                    data = await resp.json()
                    stats = data['stats']
                    active = stats['active_connections']
                    max_active = max(max_active, active)
                    
                    readings.append({
                        'time': time.time() - start_time,
                        'active': active,
                        'total': stats['total_requests']
                    })
                    
                    # Print if high usage
                    if active > 8:
                        print(f"   ⚠️  High usage at {time.time() - start_time:.1f}s: {active}/10 connections")
                    
            except Exception as e:
                print(f"   Monitoring error: {str(e)}")
            
            await asyncio.sleep(0.1)
    
    print(f"\n📊 Monitoring Summary:")
    print(f"   - Maximum active connections: {max_active}/10")
    print(f"   - Total readings: {len(readings)}")
    print(f"   - Limit exceeded: {'❌ YES' if max_active > 10 else '✅ NO'}")
    
    return max_active, readings


async def burst_test():
    """Test sudden burst of requests"""
    print("\n💥 Burst Test: 30 simultaneous requests")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Create monitoring task
        monitor_task = asyncio.create_task(continuous_monitoring(5))
        
        # Wait a moment for monitoring to start
        await asyncio.sleep(0.5)
        
        # Fire all requests at once
        tasks = []
        for i in range(30):
            task = session.get(f"{API_BASE_URL}/api/topic-velocity?weeks=2")
            tasks.append(task)
        
        # Execute burst
        print("   🚀 Firing burst...")
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Wait for monitoring to complete
        max_active, readings = await monitor_task
        
        # Analyze responses
        success = sum(1 for r in responses if not isinstance(r, Exception) and r.status == 200)
        print(f"\n   ✅ Successful requests: {success}/30")
        
        if max_active <= 10:
            print("   ✅ Connection pool properly enforced limit!")
        else:
            print(f"   ❌ Connection pool exceeded limit: {max_active}/10")


async def sustained_load_test():
    """Test sustained load over time"""
    print("\n🏃 Sustained Load Test: 100 requests over 20 seconds")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        request_times = []
        errors = []
        
        for i in range(100):
            start = time.time()
            try:
                async with session.get(f"{API_BASE_URL}/api/topic-velocity?weeks=1") as resp:
                    await resp.json()
                    request_times.append(time.time() - start)
            except Exception as e:
                errors.append(str(e))
            
            # Small delay to spread load
            await asyncio.sleep(0.2)
            
            # Progress update
            if (i + 1) % 20 == 0:
                avg_time = sum(request_times) / len(request_times) if request_times else 0
                print(f"   Progress: {i+1}/100 - Avg response: {avg_time:.3f}s")
        
        # Final stats
        async with session.get(f"{API_BASE_URL}/api/pool-stats") as resp:
            stats = (await resp.json())['stats']
        
        print(f"\n📊 Sustained Load Results:")
        print(f"   - Successful requests: {len(request_times)}/100")
        print(f"   - Failed requests: {len(errors)}")
        print(f"   - Average response time: {sum(request_times)/len(request_times):.3f}s")
        print(f"   - Peak connections used: {stats['peak_connections']}/10")
        print(f"   - Total errors in pool: {stats['errors']}")


async def main():
    """Run all load tests"""
    print("🧪 Connection Pool Load Tests")
    print("=" * 60)
    print(f"Testing API at: {API_BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if API is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/") as resp:
                if resp.status != 200:
                    print("❌ API is not responding! Please start the server first.")
                    return
    except Exception as e:
        print(f"❌ Cannot connect to API: {str(e)}")
        print("Please start the server with: uvicorn api.topic_velocity:app --reload")
        return
    
    # Run tests
    print("\n✅ API is running. Starting tests...\n")
    
    # Test 1: Rapid fire with no delay
    peak1 = await rapid_fire_test(20, delay=0)
    await asyncio.sleep(2)  # Let connections clear
    
    # Test 2: Burst test with monitoring
    await burst_test()
    await asyncio.sleep(2)
    
    # Test 3: Sustained load
    await sustained_load_test()
    
    # Final summary
    print("\n" + "=" * 60)
    print("🏁 Load Test Complete!")
    print("=" * 60)
    
    # Get final stats
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/api/pool-stats") as resp:
            final_stats = (await resp.json())['stats']
            
    print(f"\n📊 Final Pool Statistics:")
    print(f"   - Peak connections reached: {final_stats['peak_connections']}/10")
    print(f"   - Total requests handled: {final_stats['total_requests']}")
    print(f"   - Total errors: {final_stats['errors']}")
    print(f"   - Pool created at: {final_stats['created_at']}")
    
    if final_stats['peak_connections'] <= 10:
        print("\n✅ SUCCESS: Connection pool properly enforced limits!")
    else:
        print("\n❌ FAILURE: Connection pool exceeded limits!")


if __name__ == "__main__":
    asyncio.run(main())