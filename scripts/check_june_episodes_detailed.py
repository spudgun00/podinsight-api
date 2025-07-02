#!/usr/bin/env python3
"""
Check for June episodes in Supabase with proper column names
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from supabase import create_client

def check_june_episodes():
    # Create Supabase client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        print("❌ Supabase configuration not found in environment")
        return

    client = create_client(url, key)

    print("🔍 Checking for June episodes in Supabase...")

    try:
        # Check June 2025 episodes
        result_june_2025 = client.table("episodes").select("id, guid, podcast_name, episode_title, published_at, duration_seconds").gte("published_at", "2025-06-01").lte("published_at", "2025-06-30").order("published_at", desc=True).execute()

        print(f"\n📅 June 2025 Episodes: {len(result_june_2025.data)}")

        if result_june_2025.data:
            print("\n🎙️ June 2025 Episodes Details:")
            for i, episode in enumerate(result_june_2025.data):
                print(f"\n{i+1}. {episode['podcast_name']}")
                print(f"   Title: {episode['episode_title']}")
                print(f"   Date: {episode['published_at']}")
                print(f"   Duration: {episode['duration_seconds']}s ({episode['duration_seconds']//60} minutes)")
                print(f"   GUID: {episode['guid']}")

        # Check June 2024 episodes
        result_june_2024 = client.table("episodes").select("id, guid, podcast_name, episode_title, published_at").gte("published_at", "2024-06-01").lte("published_at", "2024-06-30").execute()

        print(f"\n📅 June 2024 Episodes: {len(result_june_2024.data)}")

        # Get podcast distribution for June 2025
        if result_june_2025.data:
            podcast_counts = {}
            for ep in result_june_2025.data:
                podcast_name = ep['podcast_name']
                podcast_counts[podcast_name] = podcast_counts.get(podcast_name, 0) + 1

            print("\n📊 June 2025 Podcast Distribution:")
            for podcast, count in sorted(podcast_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {podcast}: {count} episodes")

        # Check latest episodes overall
        latest = client.table("episodes").select("podcast_name, episode_title, published_at").order("published_at", desc=True).limit(5).execute()

        print("\n🆕 Latest Episodes in Database:")
        for ep in latest.data:
            print(f"  - {ep['podcast_name']}: {ep['episode_title']} ({ep['published_at']})")

        # Check total episodes count
        total = client.table("episodes").select("id").execute()
        print(f"\n📊 Total episodes in database: {len(total.data)}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_june_episodes()
