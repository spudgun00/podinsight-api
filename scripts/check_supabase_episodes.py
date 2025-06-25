#!/usr/bin/env python3
"""
Check if the episode IDs from MongoDB exist in Supabase
"""

import os
from supabase import create_client, Client

# Episode IDs from MongoDB vector search
episode_ids = [
    'pod-5da4196b2cf22d308b3a41e09',
    'substack:post:156609115', 
    '47aa54e7-0c3a-487e-a776-b6c14d90859e'
]

def check_episodes():
    """Check if episodes exist in Supabase"""
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not all([supabase_url, supabase_key]):
        print("❌ Missing Supabase credentials")
        return
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print("🔍 Checking episode IDs in Supabase...")
    print("=" * 60)
    
    # Method 1: Check using IN query (same as the API)
    print("\n1. Using IN query (API method):")
    result = supabase.table('episodes').select('guid, episode_title').in_('guid', episode_ids).execute()
    print(f"   Found {len(result.data)} episodes")
    for ep in result.data:
        print(f"   - {ep['guid']}: {ep['episode_title'][:50]}...")
    
    # Method 2: Check each ID individually
    print("\n2. Checking each ID individually:")
    for episode_id in episode_ids:
        result = supabase.table('episodes').select('guid, episode_title').eq('guid', episode_id).execute()
        if result.data:
            print(f"   ✅ {episode_id}: Found")
        else:
            print(f"   ❌ {episode_id}: NOT FOUND")
    
    # Method 3: Get some sample episodes to see format
    print("\n3. Sample episodes from Supabase:")
    result = supabase.table('episodes').select('guid, episode_title').limit(10).execute()
    for ep in result.data[:5]:
        print(f"   - {ep['guid']}: {ep['episode_title'][:30]}...")
    
    # Method 4: Search for partial matches
    print("\n4. Searching for partial matches:")
    for episode_id in episode_ids:
        # Try searching for parts of the ID
        if 'pod-' in episode_id:
            search_term = episode_id.split('pod-')[1][:8]
        elif 'substack:' in episode_id:
            search_term = episode_id.split(':')[1][:8]
        else:
            search_term = episode_id[:8]
            
        result = supabase.table('episodes').select('guid, episode_title').like('guid', f'%{search_term}%').limit(3).execute()
        if result.data:
            print(f"\n   Partial match for '{episode_id}':")
            for ep in result.data:
                print(f"     - {ep['guid']}")
        else:
            print(f"\n   No partial matches for '{episode_id}'")

if __name__ == "__main__":
    check_episodes()