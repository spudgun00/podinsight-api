#!/usr/bin/env python3
"""
Test Supabase episodes data for the 5 test podcasts
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import json

load_dotenv()

# Test episode GUIDs (mentioned in your documentation)
TEST_EPISODES = [
    "1216c2e7-42b8-42ca-92d7-bad784f80af2",  # a16z-podcast
    "24fed311-54ac-4dab-805a-ea90cd455b3b",
    "46dc5446-2e3b-46d6-b4af-24e7c0e8beff", 
    "4c2fe9c7-ce0c-4ee2-a93e-993327035281",
    "4df073b5-c70b-4516-af04-7302c5e6d635"
]

def test_supabase_episodes():
    """Test Supabase episodes data"""
    print("="*60)
    print("SUPABASE EPISODES TEST")
    print("="*60)
    
    # Connect to Supabase
    try:
        supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        print("✅ Supabase connected")
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return
    
    results = {
        "total_episodes": 0,
        "test_episodes_found": {},
        "sample_episodes": [],
        "topic_mentions": {}
    }
    
    # Get total episode count
    try:
        count_response = supabase.table('episodes').select('count', count='exact').execute()
        results["total_episodes"] = count_response.count
        print(f"\n📊 Total episodes in Supabase: {results['total_episodes']}")
    except Exception as e:
        print(f"❌ Error getting episode count: {e}")
        
    # Get sample episodes
    try:
        sample_response = supabase.table('episodes').select('*').limit(10).execute()
        results["sample_episodes"] = sample_response.data
        print(f"\n📋 Sample episodes (showing first 5):")
        for i, ep in enumerate(sample_response.data[:5]):
            print(f"  {i+1}. {ep['id'][:8]}... - {ep.get('podcast_name', 'unknown')} - {ep.get('title', 'No title')[:50]}...")
    except Exception as e:
        print(f"❌ Error getting sample episodes: {e}")
        
    # Check for test episodes
    print(f"\n🧪 Checking {len(TEST_EPISODES)} test episodes:")
    for test_guid in TEST_EPISODES:
        try:
            response = supabase.table('episodes').select('*').eq('id', test_guid).execute()
            if response.data:
                ep = response.data[0]
                results["test_episodes_found"][test_guid] = ep
                print(f"\n✅ Found {test_guid}:")
                print(f"   Podcast: {ep.get('podcast_name', 'N/A')}")
                print(f"   Title: {ep.get('title', 'N/A')[:60]}...")
                print(f"   Published: {ep.get('published_at', 'N/A')}")
                print(f"   Duration: {ep.get('duration_seconds', 0)} seconds")
                print(f"   S3 Stage: {ep.get('s3_stage_prefix', 'N/A')}")
                
                # Check topic mentions for this episode
                try:
                    topics_response = supabase.table('topic_mentions').select('*').eq('episode_id', test_guid).execute()
                    topics = [t['topic_name'] for t in topics_response.data]
                    results["topic_mentions"][test_guid] = topics
                    print(f"   Topics ({len(topics)}): {', '.join(topics) if topics else 'None'}")
                except Exception as e:
                    print(f"   ❌ Error getting topics: {e}")
                    
            else:
                print(f"\n❌ Test episode {test_guid} NOT FOUND in Supabase")
                results["test_episodes_found"][test_guid] = None
                
        except Exception as e:
            print(f"\n❌ Error checking {test_guid}: {e}")
            
    # Summary
    print(f"\n" + "="*60)
    print("SUPABASE TEST SUMMARY")
    print("="*60)
    
    found_count = len([v for v in results["test_episodes_found"].values() if v is not None])
    print(f"Test episodes found: {found_count}/{len(TEST_EPISODES)}")
    print(f"Total episodes in database: {results['total_episodes']}")
    
    # Check if we have the data needed for MongoDB alignment
    if found_count > 0:
        print(f"\n✅ Found {found_count} test episodes with:")
        print("- Episode metadata (title, podcast_name, published_at)")
        print("- S3 paths for transcript data")
        print("- Topic mentions data")
        print("\nReady for MongoDB alignment testing once MongoDB is accessible")
    else:
        print("\n❌ No test episodes found - need to investigate data setup")
    
    # Save results
    with open('supabase_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Detailed results saved to supabase_test_results.json")

if __name__ == "__main__":
    test_supabase_episodes()