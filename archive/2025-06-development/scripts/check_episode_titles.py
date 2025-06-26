#!/usr/bin/env python3
"""
Check episode titles to understand the data quality issue
"""

import os
from supabase import create_client

# Get Supabase credentials from environment
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")
    exit(1)

supabase = create_client(url, key)

print("Analyzing episode titles in Supabase...")

try:
    # Get 10 sample episodes to see title patterns
    response = supabase.table("episodes").select("id, guid, podcast_name, episode_title, published_at").limit(10).execute()

    if response.data:
        print(f"\nFound {len(response.data)} episodes. Analyzing titles...")
        print("\n" + "="*80)
        print("EPISODE TITLE ANALYSIS")
        print("="*80)

        for i, episode in enumerate(response.data, 1):
            print(f"\n{i}. Episode ID: {episode.get('id', 'N/A')}")
            print(f"   GUID: {episode.get('guid', 'N/A')}")
            print(f"   Podcast: {episode.get('podcast_name', 'N/A')}")
            print(f"   Title: {episode.get('episode_title', 'N/A')}")
            print(f"   Published: {episode.get('published_at', 'N/A')}")

        # Check if all titles follow the "Episode [guid]" pattern
        print(f"\n\nTITLE PATTERN ANALYSIS:")
        print("-" * 40)

        generic_titles = 0
        for episode in response.data:
            title = episode.get('episode_title', '')
            guid = episode.get('guid', '')
            if title.startswith('Episode ') and guid in title:
                generic_titles += 1

        print(f"Episodes with generic 'Episode [guid]' titles: {generic_titles}/{len(response.data)}")

        if generic_titles == len(response.data):
            print("🚨 ALL EPISODES have generic titles - this is the data quality issue!")
        elif generic_titles > len(response.data) * 0.8:
            print("⚠️  Most episodes have generic titles - significant data quality issue")
        else:
            print("✅ Mixed title quality - some episodes have proper titles")

        # Check podcasts
        unique_podcasts = set(episode.get('podcast_name') for episode in response.data)
        print(f"\nUnique podcasts in sample: {len(unique_podcasts)}")
        for podcast in sorted(unique_podcasts):
            print(f"  - {podcast}")

    else:
        print("No episodes found")

except Exception as e:
    print(f"Error: {e}")

print("\nDone!")
