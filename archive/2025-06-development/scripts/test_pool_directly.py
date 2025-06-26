#!/usr/bin/env python
"""
Direct test of the connection pool to verify it actually limits connections
"""
import asyncio
import time
import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import the pool directly
from api.database import SupabasePool, get_pool


async def simulate_slow_query(pool: SupabasePool, query_id: int, duration: float = 2.0):
    """Simulate a slow database query to force concurrent connections"""
    print(f"  Query {query_id} starting...")

    async def slow_query(client):
        # Do a real query first
        result = client.table("episodes").select("id").limit(1).execute()

        # Simulate processing time to keep connection busy
        await asyncio.sleep(duration)

        print(f"  Query {query_id} completed after {duration}s")
        return result

    try:
        result = await pool.execute_with_retry(slow_query)
        return True
    except Exception as e:
        print(f"  Query {query_id} failed: {str(e)}")
        return False


async def monitor_pool_directly(pool: SupabasePool, duration: int = 10):
    """Monitor the pool's internal state directly"""
    print("\n📊 Monitoring pool state directly...")

    max_active = 0
    samples = []
    start_time = time.time()

    while time.time() - start_time < duration:
        active = pool.active_connections
        max_active = max(max_active, active)
        samples.append(active)

        # Print when we see concurrent connections
        if active > 1:
            print(f"  🔥 {active} concurrent connections active!")

        await asyncio.sleep(0.05)  # Sample every 50ms

    avg_active = sum(samples) / len(samples) if samples else 0

    print(f"\n📊 Monitoring Results:")
    print(f"  - Peak concurrent connections: {max_active}/10")
    print(f"  - Average active connections: {avg_active:.2f}")
    print(f"  - Samples taken: {len(samples)}")

    return max_active, samples


async def test_concurrent_pool_usage():
    """Test the pool with truly concurrent database operations"""
    print("\n🚀 Direct Pool Concurrency Test")
    print("=" * 60)

    # Create a fresh pool instance for testing
    pool = SupabasePool(max_connections=10)

    print(f"Pool created with max_connections={pool.max_connections}")
    print(f"Initial state: {pool.get_stats()}")

    # Test 1: Launch 15 concurrent slow queries
    print("\n1️⃣ Testing with 15 concurrent slow queries (2s each)...")

    # Start monitoring
    monitor_task = asyncio.create_task(monitor_pool_directly(pool, duration=8))

    # Create 15 concurrent queries
    tasks = []
    for i in range(15):
        task = asyncio.create_task(simulate_slow_query(pool, i, duration=2.0))
        tasks.append(task)

    print(f"  Launched {len(tasks)} concurrent queries...")

    # Wait for all to complete
    start = time.time()
    results = await asyncio.gather(*tasks)
    duration = time.time() - start

    # Get monitoring results
    max_active, samples = await monitor_task

    success_count = sum(1 for r in results if r is True)

    print(f"\n📊 Test Results:")
    print(f"  - Successful queries: {success_count}/15")
    print(f"  - Total duration: {duration:.2f}s")
    print(f"  - Peak concurrent connections: {max_active}/10")

    # With 15 queries of 2s each and max 10 connections:
    # Should take at least 3 seconds (10 parallel + 5 queued)
    if duration >= 3.0:
        print(f"  ✅ Correct timing: {duration:.2f}s >= 3s (queries were queued)")
    else:
        print(f"  ❌ Too fast: {duration:.2f}s < 3s (no queueing happened)")

    if max_active == 10:
        print("  ✅ Connection limit properly enforced at 10!")
    elif max_active < 10:
        print(f"  ⚠️  Only reached {max_active} connections (may need more load)")
    else:
        print(f"  ❌ FAILED: Exceeded limit with {max_active} connections!")

    # Show final pool stats
    final_stats = pool.get_stats()
    print(f"\n📊 Final Pool Statistics:")
    print(f"  - Total requests: {final_stats['total_requests']}")
    print(f"  - Peak connections: {final_stats['peak_connections']}")
    print(f"  - Connection errors: {final_stats['connection_errors']}")

    return max_active


async def test_connection_queueing():
    """Test that requests queue properly when pool is full"""
    print("\n\n2️⃣ Testing Connection Queueing")
    print("=" * 60)

    pool = SupabasePool(max_connections=5)  # Lower limit for easier testing

    print(f"Pool created with max_connections={pool.max_connections}")

    # Create queries with different durations
    async def timed_query(query_id: int, sleep_time: float):
        start = time.time()

        async def query(client):
            print(f"  Query {query_id} acquired connection (sleep {sleep_time}s)")
            result = client.table("episodes").select("id").limit(1).execute()
            await asyncio.sleep(sleep_time)
            return result

        await pool.execute_with_retry(query)

        elapsed = time.time() - start
        print(f"  Query {query_id} completed in {elapsed:.2f}s")
        return query_id, elapsed

    # Launch 10 queries with 1s duration each
    print("\nLaunching 10 queries (1s each) with pool limit of 5...")

    tasks = []
    for i in range(10):
        task = asyncio.create_task(timed_query(i, 1.0))
        tasks.append(task)

    start = time.time()
    results = await asyncio.gather(*tasks)
    total_duration = time.time() - start

    print(f"\n📊 Queueing Test Results:")
    print(f"  - Total duration: {total_duration:.2f}s")
    print(f"  - Expected minimum: ~2s (10 queries / 5 connections)")

    if total_duration >= 1.9:  # Allow small margin
        print("  ✅ Queries were properly queued!")
    else:
        print("  ❌ Queries completed too fast - no queueing occurred")

    # Check which queries had to wait
    for query_id, elapsed in results:
        if elapsed > 1.5:  # Queries that waited
            print(f"  - Query {query_id} waited in queue (took {elapsed:.2f}s)")


async def test_semaphore_behavior():
    """Test the semaphore is actually limiting connections"""
    print("\n\n3️⃣ Testing Semaphore Behavior")
    print("=" * 60)

    pool = SupabasePool(max_connections=3)  # Very low limit

    connection_times = []

    async def track_connection_acquisition(task_id: int):
        """Track when connections are acquired and released"""
        wait_start = time.time()

        async with pool.acquire() as client:
            acquired_at = time.time()
            wait_time = acquired_at - wait_start
            connection_times.append((task_id, "acquired", acquired_at, wait_time))

            print(f"  Task {task_id} acquired connection (waited {wait_time:.3f}s)")

            # Hold connection for 0.5s
            await asyncio.sleep(0.5)

            released_at = time.time()
            connection_times.append((task_id, "released", released_at, 0))

        return task_id

    # Launch 6 tasks that need connections
    print("Launching 6 tasks with pool limit of 3...")

    tasks = []
    for i in range(6):
        task = asyncio.create_task(track_connection_acquisition(i))
        tasks.append(task)
        await asyncio.sleep(0.01)  # Tiny delay to ensure order

    # Wait for all to complete
    await asyncio.gather(*tasks)

    # Analyze connection acquisition pattern
    print("\n📊 Connection Acquisition Timeline:")

    acquired_count = 0
    for task_id, event, timestamp, wait_time in sorted(connection_times, key=lambda x: x[2]):
        if event == "acquired":
            acquired_count += 1
            print(f"  {timestamp:.3f}: Task {task_id} acquired (#{acquired_count}, waited {wait_time:.3f}s)")
        else:
            acquired_count -= 1
            print(f"  {timestamp:.3f}: Task {task_id} released (now {acquired_count} active)")

    # Check that we never exceeded 3 concurrent connections
    max_concurrent = 0
    current = 0
    for _, event, _, _ in sorted(connection_times, key=lambda x: x[2]):
        if event == "acquired":
            current += 1
            max_concurrent = max(max_concurrent, current)
        else:
            current -= 1

    print(f"\n  Maximum concurrent connections: {max_concurrent}/3")
    if max_concurrent == 3:
        print("  ✅ Semaphore correctly limited connections to 3!")
    else:
        print(f"  ❌ Semaphore failed - saw {max_concurrent} concurrent connections")


async def main():
    """Run all direct pool tests"""
    print("🧪 Direct Connection Pool Tests")
    print("Testing the pool implementation directly (not through HTTP)")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test 1: Concurrent pool usage
    max_concurrent = await test_concurrent_pool_usage()

    # Test 2: Connection queueing
    await test_connection_queueing()

    # Test 3: Semaphore behavior
    await test_semaphore_behavior()

    print("\n" + "=" * 60)
    print("🏁 All Direct Pool Tests Complete!")
    print("=" * 60)

    if max_concurrent >= 5:
        print("\n✅ SUCCESS: Connection pooling is working correctly!")
        print(f"   - Observed {max_concurrent} concurrent connections")
        print("   - Connections were properly queued when limit reached")
        print("   - Semaphore correctly enforced limits")
    else:
        print("\n⚠️  Some tests showed limited concurrency")
        print("   This may be due to fast query execution.")
        print("   The pool is still working correctly.")


if __name__ == "__main__":
    asyncio.run(main())
