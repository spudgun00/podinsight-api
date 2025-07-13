#!/usr/bin/env python3
"""
Test Supabase connection and table access
Run this locally to diagnose the topic-velocity issue
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def test_supabase_connection():
    """Test basic Supabase connection and table access"""

    # Check environment variables
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

    print("=== Environment Check ===")
    print(f"SUPABASE_URL present: {bool(url)}")
    print(f"SUPABASE_KEY present: {bool(key)}")

    if not url or not key:
        print("ERROR: Missing Supabase configuration")
        return

    print(f"URL: {url}")
    print(f"Key (first 20 chars): {key[:20]}...")

    # Create client
    try:
        client = create_client(url, key)
        print("\n✅ Supabase client created successfully")
    except Exception as e:
        print(f"\n❌ Failed to create client: {e}")
        return

    # Test 1: Check if topic_mentions table exists
    print("\n=== Testing Tables ===")
    try:
        result = client.table("topic_mentions").select("*").limit(1).execute()
        print(f"✅ topic_mentions table: {len(result.data)} rows (limited to 1)")
    except Exception as e:
        print(f"❌ topic_mentions table error: {e}")

    # Test 2: Check if episodes table exists
    try:
        result = client.table("episodes").select("*").limit(1).execute()
        print(f"✅ episodes table: {len(result.data)} rows (limited to 1)")
    except Exception as e:
        print(f"❌ episodes table error: {e}")

    # Test 3: Check if topic_signals table exists
    try:
        result = client.table("topic_signals").select("*").limit(1).execute()
        print(f"✅ topic_signals table: {len(result.data)} rows (limited to 1)")
    except Exception as e:
        print(f"❌ topic_signals table error: {e}")

    # Test 4: Test the specific join used in topic-velocity
    print("\n=== Testing Join Query ===")
    try:
        result = client.table("topic_mentions") \
            .select("*, episodes!inner(published_at)") \
            .limit(5) \
            .execute()
        print(f"✅ Join query successful: {len(result.data)} rows")
        if result.data:
            print(f"   Sample data: {result.data[0]}")
    except Exception as e:
        print(f"❌ Join query error: {e}")
        print("   This is likely the cause of the 500 error!")

    # Test 5: Test with specific topics (as used in the endpoint)
    print("\n=== Testing Topic Query ===")
    topics = ["AI Agents", "Capital Efficiency", "DePIN", "B2B SaaS", "Crypto/Web3"]
    try:
        result = client.table("topic_mentions") \
            .select("*, episodes!inner(published_at)") \
            .in_("topic_name", topics) \
            .limit(5) \
            .execute()
        print(f"✅ Topic query successful: {len(result.data)} rows")
    except Exception as e:
        print(f"❌ Topic query error: {e}")
        print("   This is likely the cause of the 500 error!")

    # Test 6: Check RLS status (this might fail if RLS blocks it)
    print("\n=== RLS Check ===")
    print("If queries above failed with 'permission denied', RLS is blocking access")
    print("Check Supabase Dashboard → Authentication → Policies")

if __name__ == "__main__":
    test_supabase_connection()
