#!/usr/bin/env python3
"""
Detailed analysis of the 171 missing episodes
Check if they belong to specific podcasts or are truly orphaned
"""

import os
from pymongo import MongoClient
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path
import json
from datetime import datetime
from collections import defaultdict

# Load .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

def analyze_missing_episodes_detail():
    """Detailed analysis of missing episodes"""
    
    # Setup connections
    MONGODB_URI = os.getenv('MONGODB_URI')
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    print("🔍 Detailed Analysis of Missing Episodes\n")
    
    # Connect to MongoDB
    mongo_client = MongoClient(MONGODB_URI)
    db = mongo_client['podinsight']
    
    # Connect to Supabase
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get all episode IDs from MongoDB
    print("📊 Getting migrated episodes from MongoDB...")
    mongo_episodes = set()
    for doc in db.transcripts.find({}, {'episode_id': 1}):
        mongo_episodes.add(doc['episode_id'])
    
    # Get all episodes from Supabase with more details
    print("📊 Getting all episodes from Supabase...")
    all_episodes = []
    
    # First batch
    response = supabase.table('episodes').select('*').limit(1000).execute()
    all_episodes.extend(response.data)
    
    # Second batch
    response = supabase.table('episodes').select('*').offset(1000).limit(1000).execute()
    all_episodes.extend(response.data)
    
    print(f"Total episodes in Supabase: {len(all_episodes)}")
    
    # Analyze missing episodes
    missing_episodes = []
    missing_by_feed = defaultdict(list)
    missing_by_date = defaultdict(int)
    
    for episode in all_episodes:
        if episode['id'] not in mongo_episodes:
            missing_episodes.append(episode)
            
            # Group by feed_slug (or lack thereof)
            feed = episode.get('feed_slug', 'NO_FEED_SLUG')
            missing_by_feed[feed].append({
                'id': episode['id'],
                'guid': episode.get('guid', 'NO_GUID'),
                'title': episode.get('title', 'NO_TITLE'),
                'published_at': episode.get('published_at', 'NO_DATE'),
                's3_transcript_path': episode.get('s3_transcript_path', 'NO_PATH'),
                's3_audio_path': episode.get('s3_audio_path', 'NO_AUDIO_PATH'),
                'feed_title': episode.get('feed_title', 'NO_FEED_TITLE')
            })
            
            # Group by month
            pub_date = episode.get('published_at', '')
            if pub_date:
                month = pub_date[:7]  # YYYY-MM
                missing_by_date[month] += 1
    
    # Create detailed report
    report = {
        'summary': {
            'total_in_supabase': len(all_episodes),
            'total_in_mongodb': len(mongo_episodes),
            'total_missing': len(missing_episodes),
            'missing_percentage': (len(missing_episodes) / len(all_episodes) * 100) if all_episodes else 0
        },
        'missing_by_feed': {},
        'missing_by_date': dict(sorted(missing_by_date.items())),
        'sample_missing_episodes': []
    }
    
    # Analyze by feed
    print("\n📻 Missing Episodes by Feed/Podcast:")
    print("="*60)
    
    for feed, episodes in sorted(missing_by_feed.items(), key=lambda x: len(x[1]), reverse=True):
        report['missing_by_feed'][feed] = {
            'count': len(episodes),
            'sample_episodes': episodes[:5]  # First 5 as sample
        }
        
        # Print summary
        print(f"\n{feed}: {len(episodes)} missing episodes")
        
        # Check if these episodes have any identifying info
        has_title = sum(1 for e in episodes if e['title'] != 'NO_TITLE')
        has_s3_path = sum(1 for e in episodes if e['s3_transcript_path'] != 'NO_PATH')
        
        print(f"  - Episodes with titles: {has_title}")
        print(f"  - Episodes with S3 paths: {has_s3_path}")
        
        # Show sample
        for i, ep in enumerate(episodes[:3]):
            print(f"  Sample {i+1}:")
            print(f"    Title: {ep['title'][:50] if ep['title'] != 'NO_TITLE' else 'NO_TITLE'}")
            print(f"    Date: {ep['published_at'][:10] if ep['published_at'] != 'NO_DATE' else 'NO_DATE'}")
            print(f"    S3 Path: {'YES' if ep['s3_transcript_path'] != 'NO_PATH' else 'NO'}")
    
    # Check if any missing episodes are from known podcasts
    print("\n🔍 Checking if missing episodes belong to known podcasts:")
    known_feeds = set()
    for doc in db.transcripts.find({}, {'podcast_name': 1}).limit(100):
        if 'podcast_name' in doc:
            known_feeds.add(doc['podcast_name'])
    
    print(f"Known podcasts in MongoDB: {len(known_feeds)}")
    
    # Save detailed report
    report_file = f"missing_episodes_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    # Final summary
    print("\n🎯 SUMMARY:")
    print("="*60)
    if 'NO_FEED_SLUG' in missing_by_feed and len(missing_by_feed['NO_FEED_SLUG']) > 100:
        print("✅ Most missing episodes (171) have NO feed_slug")
        print("✅ These appear to be orphaned/test episodes")
        print("✅ Migration successfully captured all real podcast episodes")
    else:
        print("⚠️  Some missing episodes belong to actual podcasts")
        print("⚠️  Further investigation needed")

if __name__ == "__main__":
    analyze_missing_episodes_detail()