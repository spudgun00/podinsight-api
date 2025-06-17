#!/usr/bin/env python
"""Test direct database query performance"""
import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Create Supabase client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
supabase = create_client(url, key)

print("🔍 Direct Database Query Performance Test")
print("=" * 60)

# Test 1: Simple count query
print("\n1️⃣ Simple count query (episodes):")
start = time.time()
response = supabase.table("episodes").select("id", count="exact").execute()
elapsed = (time.time() - start) * 1000
print(f"   Time: {elapsed:.2f}ms")
print(f"   Count: {response.count if hasattr(response, 'count') else len(response.data)}")

# Test 2: Topic mentions query (same as API)
print("\n2️⃣ Topic mentions query (12 weeks, all topics):")
end_date = datetime.now()
start_date = end_date - timedelta(weeks=12)
topics = ["AI Agents", "Capital Efficiency", "DePIN", "B2B SaaS", "Crypto/Web3"]

start_time = time.time()
response = supabase.table("topic_mentions") \
    .select("*, episodes!inner(published_at)") \
    .gte("mention_date", start_date.date().isoformat()) \
    .lte("mention_date", end_date.date().isoformat()) \
    .in_("topic_name", topics) \
    .execute()
elapsed = (time.time() - start_time) * 1000
print(f"   Time: {elapsed:.2f}ms")
print(f"   Rows returned: {len(response.data)}")

# Test 3: Without join
print("\n3️⃣ Topic mentions without join:")
start_time = time.time()
response = supabase.table("topic_mentions") \
    .select("*") \
    .gte("mention_date", start_date.date().isoformat()) \
    .lte("mention_date", end_date.date().isoformat()) \
    .in_("topic_name", topics) \
    .execute()
elapsed = (time.time() - start_time) * 1000
print(f"   Time: {elapsed:.2f}ms")
print(f"   Rows returned: {len(response.data)}")

# Test 4: Single topic
print("\n4️⃣ Single topic query:")
start_time = time.time()
response = supabase.table("topic_mentions") \
    .select("*, episodes!inner(published_at)") \
    .gte("mention_date", start_date.date().isoformat()) \
    .lte("mention_date", end_date.date().isoformat()) \
    .eq("topic_name", "AI Agents") \
    .execute()
elapsed = (time.time() - start_time) * 1000
print(f"   Time: {elapsed:.2f}ms")
print(f"   Rows returned: {len(response.data)}")

# Test 5: Test connection pool overhead
print("\n5️⃣ Multiple sequential queries (connection reuse):")
times = []
for i in range(5):
    start_time = time.time()
    response = supabase.table("episodes").select("id").limit(1).execute()
    elapsed = (time.time() - start_time) * 1000
    times.append(elapsed)
    print(f"   Query {i+1}: {elapsed:.2f}ms")
print(f"   Average: {sum(times)/len(times):.2f}ms")

print("\n" + "=" * 60)
print("📊 Summary:")
print("The direct database queries show the baseline performance.")
print("Compare these times with the API endpoint to identify overhead.")