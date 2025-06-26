#!/usr/bin/env python3
"""
Script to verify alignment between topic_mentions data and API response format.
Compares database counts with what the API would return.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timedelta
from collections import defaultdict
import json

# Load environment variables
load_dotenv()

# Get Supabase credentials
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env file")

# Create Supabase client
supabase: Client = create_client(url, key)

print("=" * 80)
print("TOPIC MENTIONS DATABASE vs API ALIGNMENT VERIFICATION")
print("=" * 80)

# Default topics from API
default_topics = [
    "AI Agents",
    "Capital Efficiency",
    "DePIN",
    "B2B SaaS"
]

# 1. Database Analysis
print("\n1. DATABASE ANALYSIS")
print("-" * 40)

# Get all topic mentions
response = supabase.table('topic_mentions') \
    .select('*') \
    .execute()

# Analyze by week number
week_analysis = defaultdict(lambda: defaultdict(int))
total_by_topic = defaultdict(int)
weeks_by_topic = defaultdict(set)

for record in response.data:
    topic = record['topic_name']
    week_num = record['week_number']

    week_analysis[week_num][topic] += 1
    total_by_topic[topic] += 1
    weeks_by_topic[topic].add(week_num)

# Print summary
print(f"\nTotal records: {len(response.data)}")
print(f"\nDistinct week numbers: {sorted(set(record['week_number'] for record in response.data))}")
print(f"Total distinct weeks: {len(set(record['week_number'] for record in response.data))}")

print("\nMentions by topic:")
for topic in sorted(total_by_topic.keys()):
    print(f"  {topic}: {total_by_topic[topic]} mentions across {len(weeks_by_topic[topic])} weeks")

# 2. Simulate API Response
print("\n\n2. SIMULATED API RESPONSE (12 weeks)")
print("-" * 40)

# Calculate date range for API simulation (12 weeks back)
end_date = datetime.now()
start_date = end_date - timedelta(weeks=12)

# Query with date filter (similar to API)
api_response = supabase.table("topic_mentions") \
    .select("*, episodes!inner(published_at)") \
    .gte("mention_date", start_date.date().isoformat()) \
    .lte("mention_date", end_date.date().isoformat()) \
    .in_("topic_name", default_topics) \
    .execute()

print(f"\nRecords within 12-week window: {len(api_response.data)}")

# Process data similar to API
api_weekly_data = {}

for mention in api_response.data:
    topic = mention["topic_name"]
    week_num = mention["week_number"]

    # Parse the episode's published_at date to get year
    published_at_str = mention["episodes"]["published_at"]
    # Remove microseconds if present (handle both formats)
    if '.' in published_at_str:
        published_at_str = published_at_str.split('.')[0] + '+00:00'
    published_at = datetime.fromisoformat(published_at_str.replace('+00:00', ''))
    year = published_at.year

    # Convert week number to ISO week format
    week_key = f"{year}-W{week_num.zfill(2)}"

    if week_key not in api_weekly_data:
        api_weekly_data[week_key] = {topic: 0 for topic in default_topics}

    if topic in api_weekly_data[week_key]:
        api_weekly_data[week_key][topic] += 1

# Sort weeks chronologically
sorted_api_weeks = sorted(api_weekly_data.keys())

print(f"\nWeeks in API response: {sorted_api_weeks}")
print(f"Total weeks in API response: {len(sorted_api_weeks)}")

# Build API-style data structure
data_by_topic = {topic: [] for topic in default_topics}

for week in sorted_api_weeks:
    for topic in default_topics:
        mentions = api_weekly_data[week].get(topic, 0)
        data_by_topic[topic].append({
            "week": week,
            "mentions": mentions
        })

print("\nAPI Response Summary:")
for topic in default_topics:
    total_mentions = sum(point["mentions"] for point in data_by_topic[topic])
    weeks_with_data = sum(1 for point in data_by_topic[topic] if point["mentions"] > 0)
    print(f"  {topic}: {total_mentions} mentions across {weeks_with_data} weeks")

# 3. Week Number Analysis
print("\n\n3. WEEK NUMBER ANALYSIS")
print("-" * 40)

# Check for any issues with week numbering
print("\nWeek number distribution:")
week_counts = defaultdict(int)
for record in response.data:
    week_counts[record['week_number']] += 1

for week in sorted(week_counts.keys(), key=lambda x: int(x)):
    print(f"  Week {week}: {week_counts[week]} mentions")

# 4. Date Consistency Check
print("\n\n4. DATE CONSISTENCY CHECK")
print("-" * 40)

# Sample some records to verify week numbers match dates
print("\nSample date-to-week mapping:")
sample_records = response.data[:10]  # First 10 records

for record in sample_records:
    mention_date = datetime.fromisoformat(record['mention_date'])
    week_num = mention_date.isocalendar()[1]
    stored_week = int(record['week_number'])

    match = "✓" if week_num == stored_week else "✗"
    print(f"  {record['mention_date']} -> Week {week_num} (stored: {stored_week}) {match}")

# 5. Crypto/Web3 Analysis (not in default topics)
print("\n\n5. NON-DEFAULT TOPIC ANALYSIS")
print("-" * 40)

crypto_mentions = [r for r in response.data if r['topic_name'] == 'Crypto/Web3']
print(f"\nCrypto/Web3 mentions: {len(crypto_mentions)}")
print("Note: Crypto/Web3 is tracked but not in the API's default topics")

# Get all weeks and print summary
all_response = supabase.table("topic_mentions") \
    .select("*, episodes!inner(published_at)") \
    .execute()

crypto_weekly = defaultdict(int)
for mention in all_response.data:
    if mention["topic_name"] == "Crypto/Web3":
        # Handle datetime parsing with microseconds
        published_at_str = mention["episodes"]["published_at"]
        # Remove microseconds if present (handle both formats)
        if '.' in published_at_str:
            published_at_str = published_at_str.split('.')[0] + '+00:00'
        published_at = datetime.fromisoformat(published_at_str.replace('+00:00', ''))
        year = published_at.year
        week_key = f"{year}-W{mention['week_number'].zfill(2)}"
        crypto_weekly[week_key] += 1

print(f"Crypto/Web3 appears in {len(crypto_weekly)} weeks")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
