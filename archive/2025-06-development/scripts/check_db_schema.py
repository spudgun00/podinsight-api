#!/usr/bin/env python3
"""
Quick script to check the actual database schema and sample data
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY")

if not url or not key:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_ANON_KEY")
    exit(1)

supabase = create_client(url, key)

print("Checking database schema and data...\n")

# 1. Check topic_mentions table structure by getting a sample
print("1. Checking topic_mentions table:")
print("-" * 50)

try:
    # Get a few sample records
    response = supabase.table("topic_mentions").select("*").limit(5).execute()

    if response.data and len(response.data) > 0:
        print(f"Found {len(response.data)} sample records")
        print("\nSample record structure:")
        sample = response.data[0]
        for key, value in sample.items():
            print(f"  {key}: {type(value).__name__} = {value}")

        # Show all unique column names
        all_columns = set()
        for record in response.data:
            all_columns.update(record.keys())
        print(f"\nAll columns found: {sorted(all_columns)}")
    else:
        print("No records found in topic_mentions table")

except Exception as e:
    print(f"Error querying topic_mentions: {e}")

# 2. Check episodes table structure
print("\n\n2. Checking episodes table:")
print("-" * 50)

try:
    response = supabase.table("episodes").select("*").limit(1).execute()

    if response.data and len(response.data) > 0:
        print("Sample episode record structure:")
        sample = response.data[0]
        for key, value in sample.items():
            print(f"  {key}: {type(value).__name__} = {value[:50] if isinstance(value, str) and len(value) > 50 else value}")
    else:
        print("No records found in episodes table")

except Exception as e:
    print(f"Error querying episodes: {e}")

# 3. Check unique topics
print("\n\n3. Unique topics in database:")
print("-" * 50)

try:
    # Get all topic mentions to extract unique topics
    response = supabase.table("topic_mentions").select("topic_name").execute()

    if response.data:
        unique_topics = set(record.get("topic_name") for record in response.data if record.get("topic_name"))
        print(f"Found {len(unique_topics)} unique topics:")
        for topic in sorted(unique_topics):
            print(f"  - {topic}")
    else:
        print("No topic mentions found")

except Exception as e:
    print(f"Error getting unique topics: {e}")

# 4. Check date fields
print("\n\n4. Date field analysis:")
print("-" * 50)

try:
    response = supabase.table("topic_mentions").select("*").limit(10).execute()

    if response.data:
        # Check what date-related fields exist
        date_fields = {}
        for record in response.data:
            for key, value in record.items():
                if 'date' in key.lower() or 'week' in key.lower() or 'time' in key.lower():
                    if key not in date_fields:
                        date_fields[key] = []
                    date_fields[key].append(value)

        print("Date-related fields found:")
        for field, values in date_fields.items():
            print(f"  {field}: {values[0]} (sample)")

except Exception as e:
    print(f"Error analyzing date fields: {e}")

print("\n\nAnalysis complete!")
