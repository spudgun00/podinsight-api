#!/usr/bin/env python3
import asyncio
import aiohttp
import json

async def test_connection():
    with open('mcp_asana_config.json', 'r') as f:
        config = json.load(f)
    
    headers = {
        'Authorization': f"Bearer {config['auth']['pat_token']}",
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    }
    
    print(f"Testing connection to: {config['server_url']}")
    print(f"Using PAT token: {config['auth']['pat_token'][:20]}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(config['server_url'], headers=headers) as response:
                print(f"Response status: {response.status}")
                print(f"Response headers: {dict(response.headers)}")
                if response.status != 200:
                    error = await response.text()
                    print(f"Error response: {error}")
                else:
                    print("Connection successful!")
                    # Read first few bytes to confirm it's working
                    data = await response.content.read(100)
                    print(f"First 100 bytes: {data}")
    except Exception as e:
        print(f"Connection error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())