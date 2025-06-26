#!/usr/bin/env python3
"""Test rate limiting on search endpoint"""
import asyncio
import aiohttp
import time

async def test_rate_limit():
    """Send 25 requests to test rate limit of 20/minute"""
    url = "http://localhost:8000/api/search"
    headers = {"Content-Type": "application/json"}
    data = {"query": "test rate limit", "limit": 1}

    async with aiohttp.ClientSession() as session:
        results = []
        start_time = time.time()

        for i in range(25):
            try:
                async with session.post(url, json=data, headers=headers) as resp:
                    status = resp.status
                    if status == 429:
                        retry_after = resp.headers.get('Retry-After', 'N/A')
                        results.append(f"Request {i+1}: RATE LIMITED (retry after: {retry_after}s)")
                    else:
                        results.append(f"Request {i+1}: SUCCESS ({status})")
            except Exception as e:
                results.append(f"Request {i+1}: ERROR - {str(e)}")

            # Small delay between requests
            await asyncio.sleep(0.1)

        elapsed = time.time() - start_time

        print("Rate Limit Test Results")
        print("=" * 40)
        for result in results:
            print(result)
        print(f"\nTotal time: {elapsed:.1f}s")
        print(f"Expected: 20 successful, 5 rate limited")

if __name__ == "__main__":
    asyncio.run(test_rate_limit())
