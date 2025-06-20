#!/usr/bin/env python3
"""
Analyze episode data to understand title patterns and find better title sources
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

print("Analyzing episode data for title patterns...")

try:
    # Get sample episodes 
    response = supabase.table("episodes").select("*").limit(5).execute()
    
    if response.data:
        print(f"\nFound {len(response.data)} episodes")
        print("\n" + "="*80)
        print("DETAILED EPISODE ANALYSIS")
        print("="*80)
        
        for i, episode in enumerate(response.data, 1):
            print(f"\n{i}. Episode Analysis:")
            print(f"   ID: {episode.get('id')}")
            print(f"   GUID: {episode.get('guid')}")
            print(f"   Podcast Name: {episode.get('podcast_name')}")
            print(f"   Episode Title: {episode.get('episode_title')}")
            print(f"   Published: {episode.get('published_at')}")
            print(f"   Duration: {episode.get('duration_seconds')} seconds")
            print(f"   Word Count: {episode.get('word_count')}")
            
            # Check if title is just "Episode" + part of GUID
            title = episode.get('episode_title', '')
            guid = episode.get('guid', '')
            
            # Extract first 8 characters of GUID
            guid_prefix = guid.split('-')[0] if guid else ''
            
            if title == f"Episode {guid_prefix}":
                print(f"   🚨 GENERIC TITLE: '{title}' uses GUID prefix '{guid_prefix}'")
            else:
                print(f"   ✅ PROPER TITLE: '{title}'")
        
        # Now let's check the S3 paths to see if we can find better metadata
        print(f"\n\nS3 PATH ANALYSIS:")
        print("-" * 40)
        
        for i, episode in enumerate(response.data, 1):
            s3_path = episode.get('s3_stage_prefix', '')
            print(f"\n{i}. S3 Path: {s3_path}")
            
            # Parse the S3 path structure
            if s3_path:
                path_parts = s3_path.strip('/').split('/')
                if len(path_parts) >= 3:
                    bucket = path_parts[0]
                    podcast_slug = path_parts[1] if len(path_parts) > 1 else 'unknown'
                    episode_guid = path_parts[2] if len(path_parts) > 2 else 'unknown'
                    
                    print(f"   Bucket: {bucket}")
                    print(f"   Podcast Slug: {podcast_slug}")
                    print(f"   Episode GUID: {episode_guid}")
                    
                    # Compare podcast slug with podcast name
                    podcast_name = episode.get('podcast_name', '')
                    if podcast_name:
                        slug_normalized = podcast_slug.replace('-', ' ').title()
                        print(f"   Podcast Name vs Slug: '{podcast_name}' vs '{slug_normalized}'")
        
        # Check if there are any other tables that might have better episode metadata
        print(f"\n\nCHECKING FOR RELATED METADATA TABLES:")
        print("-" * 50)
        
        # Check if there are any transcripts or other metadata tables
        tables_to_check = ['transcripts', 'episode_metadata', 'podcasts', 'feeds']
        
        for table in tables_to_check:
            try:
                test_response = supabase.table(table).select("*").limit(1).execute()
                if test_response.data:
                    print(f"✅ Found table: {table} (has {len(test_response.data)} records in sample)")
                    # Show structure of first record
                    if test_response.data:
                        sample = test_response.data[0]
                        title_fields = [k for k in sample.keys() if 'title' in k.lower() or 'name' in k.lower()]
                        if title_fields:
                            print(f"   Title-related fields: {title_fields}")
                            for field in title_fields:
                                print(f"     {field}: {sample.get(field)}")
                else:
                    print(f"❌ Table {table} exists but is empty")
            except Exception as e:
                print(f"❌ Table {table} not found or error: {str(e)[:50]}...")
                
    else:
        print("No episodes found")
        
except Exception as e:
    print(f"Error: {e}")

print("\nDone!")