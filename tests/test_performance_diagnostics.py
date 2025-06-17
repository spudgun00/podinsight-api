#!/usr/bin/env python
"""
Performance diagnostics to understand API slowdown
"""
import asyncio
import time
import aiohttp
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

API_BASE_URL = "http://localhost:8000"


async def run_diagnostic_tests():
    """Run various diagnostic tests to identify performance bottlenecks"""
    print("🔍 Performance Diagnostics")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Health endpoint (no database)
        print("\n1️⃣ Health Endpoint (baseline - no data queries):")
        times = []
        for i in range(5):
            start = time.time()
            async with session.get(f"{API_BASE_URL}/") as resp:
                await resp.json()
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
        avg_health = sum(times) / len(times)
        print(f"   Average: {avg_health:.2f}ms (min: {min(times):.2f}ms, max: {max(times):.2f}ms)")
        
        # Test 2: Varying week ranges
        print("\n2️⃣ Testing Different Week Ranges:")
        for weeks in [1, 4, 8, 12, 26, 52]:
            start = time.time()
            async with session.get(f"{API_BASE_URL}/api/topic-velocity?weeks={weeks}") as resp:
                data = await resp.json()
            elapsed = (time.time() - start) * 1000
            
            # Count data points
            total_points = sum(len(topic_data) for topic_data in data['data'].values())
            print(f"   {weeks:2d} weeks: {elapsed:6.2f}ms ({total_points} data points)")
        
        # Test 3: Single topic vs multiple topics
        print("\n3️⃣ Testing Topic Count Impact:")
        topics_tests = [
            ("AI Agents", "Single topic"),
            ("AI Agents,DePIN", "Two topics"),
            ("AI Agents,Capital Efficiency,DePIN,B2B SaaS,Crypto/Web3", "All 5 topics")
        ]
        
        for topics, desc in topics_tests:
            times = []
            for _ in range(3):
                start = time.time()
                async with session.get(f"{API_BASE_URL}/api/topic-velocity?weeks=4&topics={topics}") as resp:
                    await resp.json()
                times.append((time.time() - start) * 1000)
            avg = sum(times) / len(times)
            print(f"   {desc}: {avg:.2f}ms")
        
        # Test 4: Pool stats endpoint (minimal processing)
        print("\n4️⃣ Pool Stats Endpoint (connection pool overhead check):")
        times = []
        for _ in range(5):
            start = time.time()
            async with session.get(f"{API_BASE_URL}/api/pool-stats") as resp:
                await resp.json()
            times.append((time.time() - start) * 1000)
        avg_pool = sum(times) / len(times)
        print(f"   Average: {avg_pool:.2f}ms")
        
        # Test 5: Compare first call vs subsequent calls
        print("\n5️⃣ Cold Start vs Warm Calls:")
        # Cold start
        start = time.time()
        async with session.get(f"{API_BASE_URL}/api/topic-velocity?weeks=12") as resp:
            await resp.json()
        cold_time = (time.time() - start) * 1000
        
        # Warm calls
        warm_times = []
        for _ in range(5):
            start = time.time()
            async with session.get(f"{API_BASE_URL}/api/topic-velocity?weeks=12") as resp:
                await resp.json()
            warm_times.append((time.time() - start) * 1000)
        
        avg_warm = sum(warm_times) / len(warm_times)
        print(f"   Cold start: {cold_time:.2f}ms")
        print(f"   Warm average: {avg_warm:.2f}ms")
        print(f"   Difference: {cold_time - avg_warm:.2f}ms")
        
        # Test 6: Topics endpoint (simple query)
        print("\n6️⃣ Topics Endpoint (simple list query):")
        times = []
        for _ in range(5):
            start = time.time()
            async with session.get(f"{API_BASE_URL}/api/topics") as resp:
                await resp.json()
            times.append((time.time() - start) * 1000)
        avg_topics = sum(times) / len(times)
        print(f"   Average: {avg_topics:.2f}ms")


async def test_with_timing_logs():
    """Add detailed timing to understand which part is slow"""
    print("\n\n🔬 Detailed Timing Analysis")
    print("=" * 60)
    
    # We'll need to check server logs for this
    print("\nMaking request with timing logs enabled...")
    print("Check server console for detailed timing breakdown")
    
    async with aiohttp.ClientSession() as session:
        start = time.time()
        async with session.get(f"{API_BASE_URL}/api/topic-velocity?weeks=12") as resp:
            data = await resp.json()
        total = (time.time() - start) * 1000
        
        print(f"\nTotal request time: {total:.2f}ms")
        print(f"Topics returned: {list(data['data'].keys())}")
        
        # Check connection pool usage
        async with session.get(f"{API_BASE_URL}/api/pool-stats") as resp:
            pool_stats = await resp.json()
            stats = pool_stats['stats']
            print(f"\nConnection Pool Stats:")
            print(f"  Active: {stats['active_connections']}")
            print(f"  Peak: {stats['peak_connections']}")
            print(f"  Total requests: {stats['total_requests']}")
            print(f"  Errors: {stats['errors']}")


if __name__ == "__main__":
    # Start server reminder
    print("⚠️  Make sure the server is running with: uvicorn api.topic_velocity:app --reload")
    print("")
    
    asyncio.run(run_diagnostic_tests())
    asyncio.run(test_with_timing_logs())