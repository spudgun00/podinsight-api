#!/usr/bin/env python
"""
Test to verify connection pooling under true concurrent load
"""
import asyncio
import aiohttp
import time

API_BASE_URL = "http://localhost:8000"


async def slow_query_endpoint():
    """Create an endpoint that takes longer to process"""
    # This will make requests take longer, allowing connections to stack up
    url = f"{API_BASE_URL}/api/topic-velocity?weeks=52"  # More weeks = more data

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return resp.status


async def monitor_connections(duration=10):
    """Monitor connections while test runs"""
    async with aiohttp.ClientSession() as session:
        max_active = 0
        samples = []

        start = time.time()
        while time.time() - start < duration:
            try:
                async with session.get(f"{API_BASE_URL}/api/pool-stats") as resp:
                    stats = (await resp.json())['stats']
                    active = stats['active_connections']
                    max_active = max(max_active, active)
                    samples.append(active)

                    # Print if we see multiple connections
                    if active > 1:
                        print(f"🔥 {active} active connections!")

            except:
                pass
            await asyncio.sleep(0.05)  # Sample every 50ms

        return max_active, samples


async def true_concurrent_test():
    """Test with truly concurrent requests"""
    print("\n🚀 True Concurrent Connection Test")
    print("=" * 60)
    print("Making 50 simultaneous requests to slower endpoint...")

    # Start monitoring
    monitor_task = asyncio.create_task(monitor_connections(15))

    # Wait a moment
    await asyncio.sleep(0.5)

    # Create many tasks that will run concurrently
    async with aiohttp.ClientSession() as session:
        # Create all tasks
        tasks = []
        for i in range(50):
            task = asyncio.create_task(session.get(f"{API_BASE_URL}/api/topic-velocity?weeks=52"))
            tasks.append(task)
            # Don't wait between creating tasks

        print("⚡ All tasks created, executing concurrently...")

        # Execute all at once
        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start

    # Get monitoring results
    max_active, samples = await monitor_task

    # Analyze
    success = sum(1 for r in results if not isinstance(r, Exception) and r.status == 200)
    avg_active = sum(samples) / len(samples) if samples else 0

    print(f"\n📊 Results:")
    print(f"   ✅ Successful: {success}/50")
    print(f"   ⏱️  Total time: {duration:.2f}s")
    print(f"   🔝 Peak concurrent connections: {max_active}/10")
    print(f"   📈 Average active connections: {avg_active:.2f}")
    print(f"   📏 Connection samples taken: {len(samples)}")

    # Check pool stats
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/api/pool-stats") as resp:
            final_stats = (await resp.json())['stats']

    print(f"\n📊 Final Pool Statistics:")
    print(f"   - Peak connections: {final_stats['peak_connections']}/10")
    print(f"   - Total requests: {final_stats['total_requests']}")
    print(f"   - Connection errors: {final_stats['errors']}")

    if max_active > 1:
        print(f"\n✅ SUCCESS: Observed {max_active} concurrent connections!")
    else:
        print("\n⚠️  WARNING: Only 1 connection observed. Server may be single-threaded.")

    return max_active


async def stress_test_connections():
    """Stress test to try to exceed connection limit"""
    print("\n💣 Stress Test: Attempting to exceed connection limit")
    print("=" * 60)

    # Create a huge number of concurrent requests
    async with aiohttp.ClientSession() as session:
        tasks = []

        # Create 100 requests as fast as possible
        for i in range(100):
            task = session.get(f"{API_BASE_URL}/api/topic-velocity?weeks=12")
            tasks.append(task)

        print("🚀 Firing 100 concurrent requests...")

        # Monitor while executing
        monitor_task = asyncio.create_task(monitor_connections(10))

        # Execute all
        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start

        max_active, samples = await monitor_task

        # Count successes and failures
        successes = sum(1 for r in results if not isinstance(r, Exception) and hasattr(r, 'status') and r.status == 200)
        failures = 100 - successes

        print(f"\n📊 Stress Test Results:")
        print(f"   ✅ Successful: {successes}/100")
        print(f"   ❌ Failed: {failures}/100")
        print(f"   ⏱️  Duration: {duration:.2f}s")
        print(f"   🔝 Peak connections: {max_active}/10")

        if max_active <= 10:
            print("   ✅ Connection limit properly enforced!")
        else:
            print(f"   ❌ Connection limit exceeded! ({max_active} > 10)")


async def main():
    """Run all concurrent tests"""
    print("🧪 Advanced Connection Pool Tests")
    print("Testing true concurrency and connection limits...")

    # Test 1: True concurrent connections
    max_concurrent = await true_concurrent_test()

    # Wait for connections to clear
    await asyncio.sleep(2)

    # Test 2: Stress test
    await stress_test_connections()

    print("\n" + "=" * 60)
    print("🏁 All tests complete!")

    if max_concurrent <= 1:
        print("\n⚠️  Note: FastAPI with uvicorn runs in a single thread by default.")
        print("   To test true concurrency, run with: uvicorn api.topic_velocity:app --workers 4")
        print("   Or use gunicorn: gunicorn api.topic_velocity:app -w 4 -k uvicorn.workers.UvicornWorker")


if __name__ == "__main__":
    asyncio.run(main())
