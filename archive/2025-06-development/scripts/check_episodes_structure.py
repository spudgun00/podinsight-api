#!/usr/bin/env python3
"""
Check the episodes table structure in Supabase
"""

import os
from supabase import create_client

# Get Supabase credentials from environment
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")
    print("Available env vars:", [k for k in os.environ.keys() if 'SUPABASE' in k])
    exit(1)

print(f"Connecting to Supabase at: {url}")
supabase = create_client(url, key)

print("Checking episodes table structure...\n")

try:
    # Get a few sample episodes to see the structure
    response = supabase.table("episodes").select("*").limit(3).execute()

    if response.data and len(response.data) > 0:
        print(f"Found {len(response.data)} sample episodes")
        print("\n" + "="*60)
        print("EPISODES TABLE STRUCTURE")
        print("="*60)

        # Show the structure of the first episode
        sample = response.data[0]
        print(f"\nSample Episode Record:")
        print("-" * 30)

        for key, value in sample.items():
            value_type = type(value).__name__
            # Truncate long strings for readability
            if isinstance(value, str) and len(value) > 100:
                display_value = f"{value[:100]}..."
            else:
                display_value = value
            print(f"{key:20} | {value_type:10} | {display_value}")

        # Show all unique column names across all samples
        all_columns = set()
        for record in response.data:
            all_columns.update(record.keys())

        print(f"\n\nAll Episode Columns ({len(all_columns)} total):")
        print("-" * 40)
        for col in sorted(all_columns):
            print(f"  - {col}")

        # Look for title-related fields specifically
        title_fields = [col for col in all_columns if 'title' in col.lower() or 'name' in col.lower()]
        if title_fields:
            print(f"\n\nTitle/Name Related Fields:")
            print("-" * 30)
            for field in title_fields:
                for record in response.data:
                    value = record.get(field)
                    if value:
                        print(f"{field:20} | {value}")
                        break

        # Show sample data for key fields
        print(f"\n\nSample Data for Key Fields:")
        print("-" * 40)
        key_fields = ['id', 'episode_id', 'title', 'podcast_title', 'feed_title', 'episode_title', 'episode_number', 'published_at', 'duration']

        for field in key_fields:
            if field in all_columns:
                values = [record.get(field) for record in response.data[:3] if record.get(field)]
                if values:
                    print(f"{field:15} | {values[0]}")

    else:
        print("No episodes found in the table")

except Exception as e:
    print(f"Error querying episodes table: {e}")
    print(f"Error type: {type(e).__name__}")

print("\nDone!")
