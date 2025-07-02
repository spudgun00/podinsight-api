#!/usr/bin/env python3
"""
Check Supabase for June podcasts
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

def check_june_podcasts():
    # Create Supabase client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        print("❌ Supabase configuration not found in environment")
        return

    client = create_client(url, key)

    # Check episodes table for June dates
    print("🔍 Checking for June podcasts in Supabase...")

    try:
        # Query for June 2024 episodes
        result_2024 = client.table("episodes").select("id, title, air_date, podcast_id").gte("air_date", "2024-06-01").lte("air_date", "2024-06-30").execute()

        print(f"\n📅 June 2024 Episodes: {len(result_2024.data)}")
        if result_2024.data:
            for i, episode in enumerate(result_2024.data[:5]):  # Show first 5
                print(f"  - {episode['title'][:60]}... (Date: {episode['air_date']})")
            if len(result_2024.data) > 5:
                print(f"  ... and {len(result_2024.data) - 5} more")

        # Query for June 2025 episodes
        result_2025 = client.table("episodes").select("id, title, air_date, podcast_id").gte("air_date", "2025-06-01").lte("air_date", "2025-06-30").execute()

        print(f"\n📅 June 2025 Episodes: {len(result_2025.data)}")
        if result_2025.data:
            for i, episode in enumerate(result_2025.data[:5]):  # Show first 5
                print(f"  - {episode['title'][:60]}... (Date: {episode['air_date']})")
            if len(result_2025.data) > 5:
                print(f"  ... and {len(result_2025.data) - 5} more")

        # Get total episode count
        total_result = client.table("episodes").select("id", count="exact").execute()
        print(f"\n📊 Total episodes in database: {total_result.count if hasattr(total_result, 'count') else len(total_result.data)}")

        # Check latest episodes
        latest = client.table("episodes").select("id, title, air_date").order("air_date", desc=True).limit(5).execute()
        print(f"\n🆕 Latest episodes by air_date:")
        for episode in latest.data:
            print(f"  - {episode['title'][:60]}... (Date: {episode['air_date']})")

        # Check for any 2023 June episodes
        result_2023 = client.table("episodes").select("id").gte("air_date", "2023-06-01").lte("air_date", "2023-06-30").limit(1).execute()
        if result_2023.data:
            print(f"\n📅 June 2023 Episodes: Found (checking count...)")
            count_2023 = client.table("episodes").select("id").gte("air_date", "2023-06-01").lte("air_date", "2023-06-30").execute()
            print(f"   Total: {len(count_2023.data)} episodes")

    except Exception as e:
        print(f"❌ Error querying Supabase: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_june_podcasts()
