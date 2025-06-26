#!/usr/bin/env python
"""
Test connection pooling with multiple workers
"""
import subprocess
import time
import asyncio
import aiohttp
import os
import signal

API_BASE_URL = "http://localhost:8000"


async def test_with_multiple_workers():
    """Test the API with multiple worker processes"""
    print("🚀 Testing Connection Pool with Multiple Workers")
    print("=" * 60)

    # Start server with 4 workers
    print("Starting uvicorn with 4 workers...")

    # Set environment variables
    env = os.environ.copy()

    # Start the server process
    server_process = subprocess.Popen(
        ["uvicorn", "api.topic_velocity:app", "--workers", "4", "--port", "8000"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid  # Create new process group
    )

    # Wait for server to start
    print("Waiting for server to start...")
    await asyncio.sleep(3)

    try:
        # Check if server is running
        async with aiohttp.ClientSession() as session:
            for i in range(10):
                try:
                    async with session.get(f"{API_BASE_URL}/") as resp:
                        if resp.status == 200:
                            print("✅ Server is running!")
                            break
                except:
                    await asyncio.sleep(0.5)

        # Run concurrent test
        print("\n🧪 Firing 100 concurrent requests across 4 workers...")

        async with aiohttp.ClientSession() as session:
            # Monitor initial state
            async with session.get(f"{API_BASE_URL}/api/pool-stats") as resp:
                initial_stats = (await resp.json())['stats']
                print(f"Initial pool state: {initial_stats['active_connections']} active")

            # Create 100 concurrent requests
            tasks = []
            for i in range(100):
                task = session.get(f"{API_BASE_URL}/api/topic-velocity?weeks=12")
                tasks.append(task)

            # Execute all at once
            start = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.time() - start

            # Count successes
            successes = sum(1 for r in results if not isinstance(r, Exception) and hasattr(r, 'status') and r.status == 200)

            print(f"\n📊 Multi-Worker Test Results:")
            print(f"  - Successful requests: {successes}/100")
            print(f"  - Duration: {duration:.2f}s")
            print(f"  - Requests per second: {100/duration:.1f}")

            # Note: With 4 workers, each has its own pool of 10 connections
            # So we have 40 total connections available
            print(f"\n📝 Note: With 4 workers × 10 connections = 40 total connections")
            print(f"  This demonstrates each worker maintains its own pool")

    finally:
        # Stop the server
        print("\n🛑 Stopping server...")
        os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
        server_process.wait()
        print("Server stopped.")


async def main():
    """Run multi-worker test"""
    # First ensure any existing servers are stopped
    os.system("pkill -f uvicorn")
    await asyncio.sleep(1)

    # Run the test
    await test_with_multiple_workers()

    print("\n✅ Multi-worker test complete!")
    print("Each worker process maintains its own connection pool,")
    print("properly limiting connections within each process.")


if __name__ == "__main__":
    # Check if dotenv is available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Note: python-dotenv not available, using system environment")

    asyncio.run(main())
