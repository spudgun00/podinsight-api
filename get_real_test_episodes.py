#!/usr/bin/env python3
"""
Get real episode GUIDs from Supabase to use for testing
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import json

load_dotenv()

def get_test_episodes():
    """Get diverse test episodes from Supabase"""
    print("="*60)
    print("GETTING REAL TEST EPISODES FROM SUPABASE")
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
    
    test_episodes = []
    
    # Get episodes from different podcasts
    podcasts_to_test = [
        "a16z Podcast",
        "This Week in Startups", 
        "Acquired",
        "All-In with Chamath, Jason, Sacks & Friedberg",
        "The Tim Ferriss Show"
    ]
    
    print(f"\n🎯 Looking for episodes from {len(podcasts_to_test)} different podcasts...")
    
    for podcast in podcasts_to_test:
        try:
            response = supabase.table('episodes').select('*').eq('podcast_name', podcast).limit(2).execute()
            
            if response.data:
                print(f"\n✅ {podcast}: Found {len(response.data)} episodes")
                for ep in response.data:
                    episode_info = {
                        'id': ep['id'],
                        'podcast_name': ep.get('podcast_name'),
                        'title': ep.get('title', 'No title'),
                        'published_at': ep.get('published_at'),
                        's3_stage_prefix': ep.get('s3_stage_prefix'),
                        'duration_seconds': ep.get('duration_seconds', 0)
                    }
                    test_episodes.append(episode_info)
                    print(f"  - {ep['id']}: {ep.get('title', 'No title')[:50]}...")
            else:
                print(f"\n❌ {podcast}: No episodes found")
                
        except Exception as e:
            print(f"\n❌ Error getting episodes for {podcast}: {e}")
    
    # Also get some random episodes to ensure diversity
    try:
        print(f"\n🎲 Getting 3 random episodes...")
        random_response = supabase.table('episodes').select('*').limit(3).execute()
        
        for ep in random_response.data:
            episode_info = {
                'id': ep['id'],
                'podcast_name': ep.get('podcast_name'),
                'title': ep.get('title', 'No title'),
                'published_at': ep.get('published_at'),
                's3_stage_prefix': ep.get('s3_stage_prefix'),
                'duration_seconds': ep.get('duration_seconds', 0)
            }
            test_episodes.append(episode_info)
            print(f"  - {ep['id']}: {ep.get('podcast_name')} - {ep.get('title', 'No title')[:40]}...")
            
    except Exception as e:
        print(f"❌ Error getting random episodes: {e}")
    
    # Remove duplicates
    unique_episodes = []
    seen_ids = set()
    for ep in test_episodes:
        if ep['id'] not in seen_ids:
            unique_episodes.append(ep)
            seen_ids.add(ep['id'])
    
    print(f"\n📊 Found {len(unique_episodes)} unique test episodes")
    
    # Check topics for each episode
    print(f"\n🏷️  Checking topic mentions...")
    for ep in unique_episodes:
        try:
            topics_response = supabase.table('topic_mentions').select('*').eq('episode_id', ep['id']).execute()
            ep['topics'] = [t['topic_name'] for t in topics_response.data]
            print(f"  {ep['id'][:8]}...: {len(ep['topics'])} topics")
        except Exception as e:
            print(f"  {ep['id'][:8]}...: Error getting topics - {e}")
            ep['topics'] = []
    
    # Save the test episodes
    with open('real_test_episodes.json', 'w') as f:
        json.dump(unique_episodes, f, indent=2, default=str)
    
    # Create a simple list for easy copy-paste
    guid_list = [ep['id'] for ep in unique_episodes[:5]]  # Take first 5
    
    print(f"\n" + "="*60)
    print("TEST EPISODES READY")
    print("="*60)
    
    print(f"\n✅ Selected {len(guid_list)} test episodes:")
    for i, ep in enumerate(unique_episodes[:5]):
        print(f"  {i+1}. {ep['id']}")
        print(f"     Podcast: {ep['podcast_name']}")
        print(f"     Title: {ep['title'][:60]}...")
        print(f"     Topics: {len(ep['topics'])}")
        print()
    
    print("Python list for testing:")
    print("TEST_EPISODES = [")
    for guid in guid_list:
        print(f'    "{guid}",')
    print("]")
    
    print(f"\n💾 Full details saved to real_test_episodes.json")
    
    return unique_episodes

if __name__ == "__main__":
    get_test_episodes()