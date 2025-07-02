#!/usr/bin/env python3
"""
Check Supabase schema and June episodes
"""
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from supabase import create_client

def check_supabase_schema():
    # Create Supabase client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        print("❌ Supabase configuration not found in environment")
        return

    client = create_client(url, key)

    print("🔍 Checking Supabase episodes table...")

    try:
        # First, get a single episode to see the schema
        sample = client.table("episodes").select("*").limit(1).execute()

        if sample.data:
            print("\n📋 Episodes table columns:")
            for key in sample.data[0].keys():
                print(f"  - {key}: {type(sample.data[0][key]).__name__}")

            print(f"\n📝 Sample episode data:")
            for key, value in sample.data[0].items():
                if isinstance(value, str) and len(str(value)) > 50:
                    print(f"  - {key}: {str(value)[:50]}...")
                else:
                    print(f"  - {key}: {value}")

        # Now check for June episodes using the correct columns
        print("\n🔍 Checking for June episodes...")

        # Check what date columns exist
        if sample.data and 'air_date' in sample.data[0]:
            date_column = 'air_date'
        elif sample.data and 'date' in sample.data[0]:
            date_column = 'date'
        elif sample.data and 'published_at' in sample.data[0]:
            date_column = 'published_at'
        else:
            print("❌ No date column found in episodes table")
            return

        print(f"Using date column: {date_column}")

        # Query for June 2024 episodes
        result_2024 = client.table("episodes").select("*").gte(date_column, "2024-06-01").lte(date_column, "2024-06-30").limit(5).execute()
        print(f"\n📅 June 2024 Episodes: Found {len(result_2024.data)}")

        # Query for June 2025 episodes
        result_2025 = client.table("episodes").select("*").gte(date_column, "2025-06-01").lte(date_column, "2025-06-30").limit(5).execute()
        print(f"📅 June 2025 Episodes: Found {len(result_2025.data)}")

        # Query for June 2023 episodes
        result_2023 = client.table("episodes").select("*").gte(date_column, "2023-06-01").lte(date_column, "2023-06-30").limit(5).execute()
        print(f"📅 June 2023 Episodes: Found {len(result_2023.data)}")

        # Get count of all episodes with dates
        all_with_dates = client.table("episodes").select("id").not_.is_(date_column, "null").execute()
        print(f"\n📊 Total episodes with {date_column}: {len(all_with_dates.data)}")

        # Get latest episodes
        latest = client.table("episodes").select("*").order(date_column, desc=True).limit(3).execute()
        print(f"\n🆕 Latest episodes by {date_column}:")
        for episode in latest.data:
            # Find title-like field
            title = episode.get('name') or episode.get('title') or episode.get('episode_name') or 'No title'
            date = episode.get(date_column)
            print(f"  - {title[:60]}... ({date})")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_supabase_schema()
