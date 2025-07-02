#!/usr/bin/env python3
"""
Test script to verify Topic Velocity API returns correct number of weeks
"""
import asyncio
import aiohttp
import json
from datetime import datetime

# API endpoint
API_BASE = "http://localhost:8000"  # For local testing
# API_BASE = "https://podinsight-api.vercel.app"

async def test_week_counts():
    """Test that API returns the correct number of weeks"""
    print("🔍 Testing Topic Velocity Week Count Fix\n")

    test_cases = [
        {"weeks": 4, "name": "1 Month"},
        {"weeks": 12, "name": "3 Months"},
        {"weeks": 24, "name": "6 Months"},
        {"weeks": 52, "name": "1 Year"}
    ]

    all_passed = True

    async with aiohttp.ClientSession() as session:
        for test in test_cases:
            weeks_requested = test["weeks"]
            url = f"{API_BASE}/api/topic-velocity"
            params = {
                "weeks": weeks_requested,
                "topics": "AI Agents,DePIN"
            }

            try:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        print(f"❌ {test['name']}: API returned {response.status}")
                        all_passed = False
                        continue

                    data = await response.json()

                    # Count unique weeks returned
                    unique_weeks = set()
                    for topic, topic_data in data["data"].items():
                        for item in topic_data:
                            unique_weeks.add(item["week"])

                    weeks_returned = len(unique_weeks)

                    if weeks_returned == weeks_requested:
                        print(f"✅ {test['name']}: Requested {weeks_requested} weeks, got {weeks_returned} weeks")
                        # Show the week range
                        if unique_weeks:
                            sorted_weeks = sorted(unique_weeks)
                            print(f"   Range: {sorted_weeks[0]} to {sorted_weeks[-1]}")
                    else:
                        print(f"❌ {test['name']}: Requested {weeks_requested} weeks, got {weeks_returned} weeks")
                        print(f"   Weeks returned: {sorted(unique_weeks)}")
                        all_passed = False

            except Exception as e:
                print(f"❌ {test['name']}: Error - {str(e)}")
                all_passed = False

    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)

    if all_passed:
        print("✅ SUCCESS: All tests passed! API returns correct number of weeks.")
    else:
        print("❌ FAILURE: Some tests failed. API is not returning correct week counts.")

    # Show current date context
    print(f"\nCurrent date: {datetime.now().strftime('%Y-%m-%d')}")
    iso_year, iso_week, _ = datetime.now().isocalendar()
    print(f"Current week: {iso_year}-W{str(iso_week).zfill(2)}")

if __name__ == "__main__":
    asyncio.run(test_week_counts())
