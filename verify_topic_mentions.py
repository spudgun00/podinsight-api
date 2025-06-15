#!/usr/bin/env python3
"""
Script to verify topic_mentions data by counting distinct week numbers
and comparing with API response data.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Get Supabase credentials
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env file")

# Create Supabase client
supabase: Client = create_client(url, key)

print("Connected to Supabase successfully!")
print(f"URL: {url}")
print("-" * 50)

# First, let's explore the table structure
print("\n0. Exploring table structure...")
try:
    # Get a sample record to see available columns
    response = supabase.table('topic_mentions') \
        .select('*') \
        .limit(1) \
        .execute()
    
    if response.data:
        columns = list(response.data[0].keys())
        print(f"Available columns: {columns}")
        print(f"\nFirst record structure:")
        for key, value in response.data[0].items():
            print(f"  {key}: {value} (type: {type(value).__name__})")
    else:
        print("No data found in table")
        
except Exception as e:
    print(f"Error exploring table structure: {e}")

# Query 1: Count distinct week numbers in topic_mentions
print("\n1. Counting distinct week numbers in topic_mentions table...")
try:
    # Get all records to analyze week data
    response = supabase.table('topic_mentions') \
        .select('*') \
        .execute()
    
    # Find week-related columns and extract unique weeks
    weeks = set()
    week_column = None
    
    if response.data:
        # Check for week-related columns
        first_record = response.data[0]
        for col in first_record.keys():
            if 'week' in col.lower():
                week_column = col
                break
        
        if week_column:
            for record in response.data:
                if record.get(week_column):
                    weeks.add(record[week_column])
            
            distinct_weeks = sorted(list(weeks))
            
            print(f"Week column found: {week_column}")
            print(f"Total distinct weeks: {len(distinct_weeks)}")
            if distinct_weeks:
                print(f"Week range: {distinct_weeks[0]} to {distinct_weeks[-1]}")
                print(f"\nDistinct weeks: {distinct_weeks}")
        else:
            print("No week column found in the table")
    
except Exception as e:
    print(f"Error querying distinct weeks: {e}")

# Query 2: Get total record count
print("\n2. Getting total record count...")
try:
    response = supabase.table('topic_mentions') \
        .select('*', count='exact') \
        .execute()
    
    print(f"Total records in topic_mentions: {response.count}")
    
except Exception as e:
    print(f"Error getting record count: {e}")

# Query 3: Get count by topic
print("\n3. Getting count by topic...")
try:
    response = supabase.table('topic_mentions') \
        .select('*') \
        .execute()
    
    # Find topic-related column
    topic_column = None
    week_column = None
    
    if response.data:
        first_record = response.data[0]
        for col in first_record.keys():
            if 'topic' in col.lower():
                topic_column = col
            if 'week' in col.lower():
                week_column = col
        
        if topic_column:
            # Count by topic
            topic_counts = {}
            topic_weeks = {}
            
            for record in response.data:
                topic = record.get(topic_column)
                week = record.get(week_column) if week_column else None
                
                if topic:
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
                    if topic not in topic_weeks:
                        topic_weeks[topic] = set()
                    if week:
                        topic_weeks[topic].add(week)
            
            print(f"\nTopic column found: {topic_column}")
            print("\nTopic counts:")
            for topic, count in sorted(topic_counts.items()):
                week_count = len(topic_weeks.get(topic, set()))
                print(f"  {topic}: {count} mentions across {week_count} weeks")
        else:
            print("No topic column found in the table")
    
except Exception as e:
    print(f"Error getting topic counts: {e}")

# Query 4: Sample data to verify structure
print("\n4. Sample data (first 5 records)...")
try:
    response = supabase.table('topic_mentions') \
        .select('*') \
        .limit(5) \
        .execute()
    
    print("\nSample records:")
    for i, record in enumerate(response.data, 1):
        print(f"\nRecord {i}:")
        # Print all fields dynamically
        for key, value in record.items():
            if value is not None:
                print(f"  {key}: {value}")
        
except Exception as e:
    print(f"Error getting sample data: {e}")

print("\n" + "-" * 50)
print("Verification complete!")