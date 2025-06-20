#!/usr/bin/env python3
"""
Comprehensive analysis of episode title issues and recommendations for entity API fixes
"""

import os
from supabase import create_client
from pymongo import MongoClient
from datetime import datetime
import json

# Get credentials
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY")
mongodb_uri = os.environ.get("MONGODB_URI")

def analyze_episode_titles():
    """Analyze episode title data quality across both databases"""
    
    print("="*80)
    print("EPISODE TITLE DATA QUALITY ANALYSIS")
    print("="*80)
    
    # Check Supabase
    if url and key:
        print("\n1. SUPABASE EPISODES TABLE:")
        print("-" * 40)
        
        supabase = create_client(url, key)
        
        try:
            response = supabase.table("episodes").select("id, guid, podcast_name, episode_title, published_at").limit(10).execute()
            
            if response.data:
                print(f"✅ Found {len(response.data)} sample episodes")
                
                # Count generic vs proper titles
                generic_count = 0
                proper_count = 0
                
                for episode in response.data:
                    title = episode.get('episode_title', '')
                    guid = episode.get('guid', '')
                    guid_prefix = guid.split('-')[0] if guid else ''
                    
                    if title == f"Episode {guid_prefix}":
                        generic_count += 1
                    else:
                        proper_count += 1
                
                print(f"📊 Title Quality Assessment:")
                print(f"   Generic titles (Episode [guid]): {generic_count}")
                print(f"   Proper titles: {proper_count}")
                
                if generic_count > 0:
                    print(f"🚨 ISSUE CONFIRMED: {generic_count}/{len(response.data)} episodes have generic titles")
                
                # Show sample data
                print(f"\n📄 Sample Episodes:")
                for i, episode in enumerate(response.data[:3], 1):
                    print(f"   {i}. {episode.get('podcast_name', 'Unknown')} - {episode.get('episode_title', 'No Title')}")
                    print(f"      Published: {episode.get('published_at', 'Unknown')}")
                    print(f"      GUID: {episode.get('guid', 'Unknown')}")
                
        except Exception as e:
            print(f"❌ Error accessing Supabase: {e}")
    
    # Check MongoDB
    if mongodb_uri:
        print("\n\n2. MONGODB TRANSCRIPTS COLLECTION:")
        print("-" * 40)
        
        try:
            client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            db = client['podinsight']
            
            # Check if titles exist in MongoDB
            sample_docs = list(db.transcripts.find({}, {
                'episode_id': 1, 
                'podcast_name': 1, 
                'episode_title': 1, 
                'published_at': 1, 
                'original_title': 1,
                'metadata': 1
            }).limit(10))
            
            if sample_docs:
                print(f"✅ Found {len(sample_docs)} sample documents")
                
                # Check title quality in MongoDB
                empty_titles = 0
                filled_titles = 0
                
                for doc in sample_docs:
                    title = doc.get('episode_title', '')
                    if not title or title.strip() == '':
                        empty_titles += 1
                    else:
                        filled_titles += 1
                
                print(f"📊 MongoDB Title Quality:")
                print(f"   Empty titles: {empty_titles}")
                print(f"   Filled titles: {filled_titles}")
                
                if empty_titles > 0:
                    print(f"🚨 ISSUE CONFIRMED: {empty_titles}/{len(sample_docs)} documents have empty titles")
                
                # Show sample data
                print(f"\n📄 Sample MongoDB Documents:")
                for i, doc in enumerate(sample_docs[:3], 1):
                    title = doc.get('episode_title', '') or '[EMPTY]'
                    print(f"   {i}. {doc.get('podcast_name', 'Unknown')} - {title}")
                    print(f"      Episode ID: {doc.get('episode_id', 'Unknown')}")
                    print(f"      Published: {doc.get('published_at', 'Unknown')}")
                    
                    # Check for any alternative title fields
                    metadata = doc.get('metadata', {})
                    if metadata:
                        print(f"      Metadata keys: {list(metadata.keys())}")
                
        except Exception as e:
            print(f"❌ Error accessing MongoDB: {e}")
    
    # Generate recommendations
    print("\n\n3. RECOMMENDED SOLUTIONS:")
    print("-" * 40)
    
    print("""
🎯 IMMEDIATE FIXES (for Entity API):

1. IMPROVE DISPLAY FORMAT:
   - Instead of: "Episode fa77104a"
   - Use: "This Week in Startups (Feb 11, 2025)"
   - Format: "{podcast_name} ({formatted_date})"

2. ADD DURATION INFO:
   - Format: "This Week in Startups - 65 min (Feb 11, 2025)"
   - Include episode length for context

3. ENHANCE ENTITY API QUERY:
   - Join episodes table with proper fields
   - Use published_at for meaningful dates
   - Include duration_seconds for length info

🛠️ LONG-TERM SOLUTIONS:

1. EPISODE TITLE RECOVERY:
   - Check RSS feeds for original episode titles
   - Parse S3 metadata files if they exist
   - Implement title extraction from transcripts

2. DATA PIPELINE IMPROVEMENT:
   - Capture original episode titles during ingestion
   - Store RSS feed metadata
   - Implement title validation

3. FALLBACK STRATEGIES:
   - Generate titles from transcript content
   - Use first sentence or topic summary
   - Create semantic titles based on content
""")

def create_improved_query_example():
    """Create example of improved entity API query"""
    
    print("\n\n4. IMPROVED ENTITY API QUERY EXAMPLE:")
    print("-" * 50)
    
    print("""
CURRENT PROBLEMATIC QUERY:
SELECT episode_title, ... FROM episodes WHERE ...
RESULT: "Episode fa77104a"

IMPROVED QUERY:
SELECT 
    CONCAT(podcast_name, ' (', DATE_FORMAT(published_at, '%b %d, %Y'), ')') as display_title,
    podcast_name,
    episode_title,
    published_at,
    ROUND(duration_seconds / 60) as duration_minutes,
    id,
    guid
FROM episodes 
WHERE ...

RESULT: "This Week in Startups (Feb 11, 2025)"

EVEN BETTER WITH DURATION:
SELECT 
    CASE 
        WHEN duration_seconds > 0 THEN 
            CONCAT(podcast_name, ' - ', ROUND(duration_seconds / 60), ' min (', DATE_FORMAT(published_at, '%b %d, %Y'), ')')
        ELSE 
            CONCAT(podcast_name, ' (', DATE_FORMAT(published_at, '%b %d, %Y'), ')')
    END as display_title,
    ...
FROM episodes

RESULT: "This Week in Startups - 65 min (Feb 11, 2025)"
""")

def generate_test_data():
    """Generate test data showing the improvement"""
    
    print("\n\n5. BEFORE/AFTER COMPARISON:")
    print("-" * 40)
    
    if url and key:
        try:
            supabase = create_client(url, key)
            response = supabase.table("episodes").select("podcast_name, episode_title, published_at, duration_seconds").limit(5).execute()
            
            if response.data:
                print("BEFORE (Current):")
                for episode in response.data:
                    print(f"  ❌ {episode.get('episode_title', 'No Title')}")
                
                print("\nAFTER (Improved):")
                for episode in response.data:
                    podcast = episode.get('podcast_name', 'Unknown Podcast')
                    duration = episode.get('duration_seconds', 0)
                    published = episode.get('published_at', '')
                    
                    # Format date
                    if published:
                        try:
                            from datetime import datetime
                            date_obj = datetime.fromisoformat(published.replace('Z', '+00:00'))
                            formatted_date = date_obj.strftime('%b %d, %Y')
                        except:
                            formatted_date = 'Unknown Date'
                    else:
                        formatted_date = 'Unknown Date'
                    
                    # Create improved title
                    if duration > 0:
                        duration_min = round(duration / 60)
                        improved_title = f"{podcast} - {duration_min} min ({formatted_date})"
                    else:
                        improved_title = f"{podcast} ({formatted_date})"
                    
                    print(f"  ✅ {improved_title}")
                    
        except Exception as e:
            print(f"Error generating test data: {e}")

if __name__ == "__main__":
    analyze_episode_titles()
    create_improved_query_example()
    generate_test_data()
    
    print(f"\n\n6. NEXT STEPS:")
    print("-" * 20)
    print("""
1. Update the entity API to use the improved query format
2. Test the new display format with sample data
3. Deploy the fix to improve user experience
4. Plan longer-term solution for title recovery

This will immediately fix the "Episode fa77104a" issue by showing
meaningful podcast names and dates instead of generic GUIDs.
""")