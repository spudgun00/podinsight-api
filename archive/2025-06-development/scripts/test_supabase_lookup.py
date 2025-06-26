#!/usr/bin/env python3
"""
Test Supabase episode lookup to see if GUIDs match
"""

import os
import asyncio
from supabase import create_client, Client
from motor.motor_asyncio import AsyncIOMotorClient

async def test_supabase_lookup():
    """Test if episode GUIDs from MongoDB exist in Supabase"""

    # Get environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    mongodb_uri = os.getenv("MONGODB_URI")

    if not all([supabase_url, supabase_key, mongodb_uri]):
        print("❌ Missing environment variables")
        return

    # Connect to Supabase
    print("🔗 Connecting to Supabase...")
    supabase: Client = create_client(supabase_url, supabase_key)

    # Connect to MongoDB
    print("🔗 Connecting to MongoDB...")
    client = AsyncIOMotorClient(mongodb_uri)
    db = client.podinsight
    collection = db.transcript_chunks_768d

    try:
        # Get sample episode IDs from MongoDB
        print("\n📊 Getting sample episode IDs from MongoDB...")
        cursor = collection.find({}, {"episode_id": 1}).limit(10)
        chunks = await cursor.to_list(None)

        episode_ids = list(set(chunk['episode_id'] for chunk in chunks))
        print(f"Found {len(episode_ids)} unique episode IDs:")
        for eid in episode_ids[:5]:
            print(f"  - {eid}")

        # Test Supabase lookups
        print("\n🔍 Testing Supabase lookups...")
        for episode_id in episode_ids[:5]:
            print(f"\nLooking up: {episode_id}")

            # Try different lookup strategies
            # 1. Look up by guid
            result = supabase.table('episodes').select('id, guid, episode_title').eq('guid', episode_id).execute()
            if result.data:
                print(f"  ✅ Found by guid: {result.data[0]['episode_title'][:50]}...")
            else:
                # 2. Try looking up by id
                result = supabase.table('episodes').select('id, guid, episode_title').eq('id', episode_id).execute()
                if result.data:
                    print(f"  ⚠️  Found by id (not guid): {result.data[0]['episode_title'][:50]}...")
                    print(f"     Actual guid: {result.data[0]['guid']}")
                else:
                    # 3. Try pattern matching
                    result = supabase.table('episodes').select('id, guid, episode_title').like('guid', f'%{episode_id[-8:]}%').limit(5).execute()
                    if result.data:
                        print(f"  ⚠️  Found {len(result.data)} partial matches:")
                        for ep in result.data[:2]:
                            print(f"     - guid: {ep['guid']}, title: {ep['episode_title'][:30]}...")
                    else:
                        print(f"  ❌ Not found in Supabase")

        # Get some actual GUIDs from Supabase
        print("\n📊 Sample GUIDs from Supabase:")
        result = supabase.table('episodes').select('guid, episode_title').limit(5).execute()
        for ep in result.data:
            print(f"  - {ep['guid']} : {ep['episode_title'][:50]}...")

    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_supabase_lookup())
