#!/usr/bin/env python3
"""
Show detailed Supabase episodes data to understand the issue
"""

import os
from supabase import create_client, Client
from datetime import datetime

def show_episodes_data():
    """Show comprehensive view of episodes data"""

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not all([supabase_url, supabase_key]):
        print("❌ Missing Supabase credentials")
        return

    supabase: Client = create_client(supabase_url, supabase_key)

    print("📊 SUPABASE EPISODES TABLE ANALYSIS")
    print("=" * 80)

    # 1. Get total count
    count_result = supabase.table('episodes').select('*', count='exact').execute()
    total_count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
    print(f"\nTotal episodes in table: {total_count}")

    # 2. Show sample of ALL episodes (not just specific ones)
    print("\n🔍 RANDOM SAMPLE OF 30 EPISODES:")
    print("-" * 80)
    print(f"{'GUID':40} | {'TITLE':30} | {'DATE':12} | {'PODCAST':25}")
    print("-" * 80)

    result = supabase.table('episodes').select('guid, episode_title, published_at, podcast_name').limit(30).execute()

    for ep in result.data:
        guid = ep['guid'][:40]
        title = ep['episode_title'][:30]
        date = ep['published_at'][:10] if ep['published_at'] else 'None'
        podcast = (ep.get('podcast_name') or 'Unknown')[:25]
        print(f"{guid:40} | {title:30} | {date:12} | {podcast:25}")

    # 3. Check for specific patterns
    print("\n📋 EPISODE TITLE PATTERNS:")
    print("-" * 80)

    # Check if all titles follow "Episode {guid_prefix}" pattern
    generic_titles = 0
    real_titles = 0

    for ep in result.data:
        title = ep['episode_title']
        guid = ep['guid']

        # Check if title is generic (starts with "Episode " and contains part of GUID)
        if title.startswith("Episode ") and guid[:8] in title:
            generic_titles += 1
        else:
            real_titles += 1

    print(f"Generic titles (Episode XXX): {generic_titles}")
    print(f"Real titles: {real_titles}")

    # 4. Check date distribution
    print("\n📅 PUBLISHED DATE ANALYSIS:")
    print("-" * 80)

    future_dates = 0
    past_dates = 0
    no_dates = 0
    today = datetime.now()

    for ep in result.data:
        if not ep['published_at']:
            no_dates += 1
        else:
            try:
                pub_date = datetime.fromisoformat(ep['published_at'].replace('Z', '+00:00'))
                if pub_date > today:
                    future_dates += 1
                else:
                    past_dates += 1
            except:
                no_dates += 1

    print(f"Future dates (after today): {future_dates}")
    print(f"Past dates: {past_dates}")
    print(f"No/invalid dates: {no_dates}")

    # 5. Show episodes that MongoDB found
    print("\n🎯 CHECKING EPISODES FROM MONGODB SEARCH RESULTS:")
    print("-" * 80)

    mongodb_episode_ids = [
        'pod-5da4196b2cf22d308b3a41e09',
        'substack:post:156609115',
        '47aa54e7-0c3a-487e-a776-b6c14d90859e'
    ]

    result = supabase.table('episodes').select('*').in_('guid', mongodb_episode_ids).execute()

    for ep in result.data:
        print(f"\nGUID: {ep['guid']}")
        print(f"Title: {ep['episode_title']}")
        print(f"Published: {ep['published_at']}")
        print(f"Podcast: {ep.get('podcast_name', 'Unknown')}")
        print(f"Duration: {ep.get('duration_seconds', 0)} seconds")
        print(f"Word Count: {ep.get('word_count', 0)}")
        print(f"S3 Path: {ep.get('s3_audio_path', 'None')[:50]}...")

    # 6. Check if there's another title field
    print("\n🔍 CHECKING ALL FIELDS IN FIRST EPISODE:")
    print("-" * 80)

    if result.data:
        first_ep = result.data[0]
        for key, value in first_ep.items():
            if value and str(value).strip():
                print(f"{key}: {str(value)[:100]}...")

if __name__ == "__main__":
    show_episodes_data()
