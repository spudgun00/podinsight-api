#!/usr/bin/env python3
"""
Test script to verify Topic Velocity API consistency fix
Tests that the same week returns identical data regardless of time window
"""
import asyncio
import aiohttp
import json
from typing import Dict, List

# API endpoint (adjust as needed)
API_BASE = "https://podinsight-api.vercel.app"
# API_BASE = "http://localhost:8000"  # For local testing

async def fetch_topic_velocity(weeks: int, topics: str = "DePIN") -> Dict:
    """Fetch topic velocity data for given weeks"""
    url = f"{API_BASE}/api/topic-velocity"
    params = {
        "weeks": weeks,
        "topics": topics
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"API returned {response.status}")
            return await response.json()

async def compare_results():
    """Compare results from different time windows"""
    print("🔍 Testing Topic Velocity API Consistency\n")

    # Test multiple time windows
    time_windows = [4, 12, 24, 52]
    results = {}

    # Fetch data for each time window
    print("Fetching data for different time windows...")
    for weeks in time_windows:
        try:
            data = await fetch_topic_velocity(weeks)
            results[weeks] = data
            print(f"✅ Fetched {weeks} weeks of data")
        except Exception as e:
            print(f"❌ Failed to fetch {weeks} weeks: {e}")
            return

    # Find common weeks across all results
    print("\n📊 Analyzing consistency across time windows...")

    # Extract DePIN data from each result
    depin_data = {}
    for weeks, result in results.items():
        if "data" in result and "DePIN" in result["data"]:
            depin_data[weeks] = {
                item["week"]: item["mentions"]
                for item in result["data"]["DePIN"]
            }

    # Find weeks that appear in multiple results
    all_weeks = set()
    for data in depin_data.values():
        all_weeks.update(data.keys())

    # Check consistency for each week
    inconsistencies = []
    consistent_count = 0

    print("\nWeek-by-week comparison:")
    print("-" * 60)

    for week in sorted(all_weeks):
        # Get mention counts for this week from each time window
        counts = {}
        for window, data in depin_data.items():
            if week in data:
                counts[window] = data[week]

        # Check if all counts are the same
        if len(counts) > 1:
            unique_values = set(counts.values())
            if len(unique_values) == 1:
                consistent_count += 1
                print(f"✅ {week}: Consistent across all windows (mentions: {list(unique_values)[0]})")
            else:
                inconsistencies.append({
                    "week": week,
                    "counts": counts
                })
                print(f"❌ {week}: INCONSISTENT - {counts}")

    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)

    total_comparable = consistent_count + len(inconsistencies)
    if total_comparable > 0:
        consistency_rate = (consistent_count / total_comparable) * 100
        print(f"Total comparable weeks: {total_comparable}")
        print(f"Consistent weeks: {consistent_count}")
        print(f"Inconsistent weeks: {len(inconsistencies)}")
        print(f"Consistency rate: {consistency_rate:.1f}%")

        if len(inconsistencies) == 0:
            print("\n✅ SUCCESS: All weeks show consistent data across different time windows!")
        else:
            print(f"\n❌ FAILURE: Found {len(inconsistencies)} inconsistent weeks")
            print("\nInconsistent weeks details:")
            for inc in inconsistencies[:5]:  # Show first 5
                print(f"  - {inc['week']}: {inc['counts']}")
    else:
        print("❌ No comparable weeks found")

if __name__ == "__main__":
    asyncio.run(compare_results())
