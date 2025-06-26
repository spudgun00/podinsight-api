#!/usr/bin/env python3
"""
Investigate missing episodes from MongoDB migration
Checks for GUID format issues, S3 path problems, etc.
"""

import os
import boto3
from pymongo import MongoClient
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path
import json
from datetime import datetime

# Load .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

def investigate_missing_episodes():
    """Find episodes in Supabase but not in MongoDB"""

    # Setup connections
    MONGODB_URI = os.getenv('MONGODB_URI')
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    print("🔍 Investigating Missing Episodes\n")

    # Connect to MongoDB
    mongo_client = MongoClient(MONGODB_URI)
    db = mongo_client['podinsight']

    # Connect to Supabase
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Get all episode IDs from MongoDB
    print("📊 Getting MongoDB episode IDs...")
    mongo_episodes = set()
    for doc in db.transcripts.find({}, {'episode_id': 1}):
        mongo_episodes.add(doc['episode_id'])
    print(f"Found {len(mongo_episodes)} episodes in MongoDB")

    # Get all episodes from Supabase (need to handle pagination)
    print("\n📊 Getting Supabase episodes...")
    all_episodes = []

    # First batch (up to 1000)
    response = supabase.table('episodes').select('*').limit(1000).execute()
    all_episodes.extend(response.data)

    # Second batch (remaining episodes)
    response = supabase.table('episodes').select('*').offset(1000).limit(1000).execute()
    all_episodes.extend(response.data)

    supabase_episodes = all_episodes
    print(f"Found {len(supabase_episodes)} episodes in Supabase")

    # Find missing episodes
    missing_episodes = []
    guid_issues = []
    path_issues = []

    for episode in supabase_episodes:
        episode_id = episode['id']

        if episode_id not in mongo_episodes:
            missing_episodes.append(episode)

            # Check for GUID format issues
            if 'guid' in episode and episode['guid']:
                # Check if GUID differs from ID
                if episode['guid'] != episode_id:
                    guid_issues.append({
                        'id': episode_id,
                        'guid': episode['guid'],
                        'podcast': episode.get('feed_slug', 'Unknown'),
                        'title': episode.get('title', 'No title')[:50]
                    })

    print(f"\n❗ Found {len(missing_episodes)} missing episodes")

    # Save detailed report
    report_file = f"missing_episodes_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Analyze missing episodes
    analysis = {
        'total_missing': len(missing_episodes),
        'guid_issues': len(guid_issues),
        'missing_by_podcast': {},
        'missing_by_date': {},
        'sample_missing': [],
        'guid_mismatches': guid_issues[:10]  # First 10 GUID issues
    }

    # Group by podcast
    for episode in missing_episodes:
        podcast = episode.get('feed_slug', 'Unknown')
        if podcast not in analysis['missing_by_podcast']:
            analysis['missing_by_podcast'][podcast] = 0
        analysis['missing_by_podcast'][podcast] += 1

    # Check S3 for a sample of missing episodes
    print("\n🔍 Checking S3 for sample of missing episodes...")
    s3_client = boto3.client('s3')
    bucket_name = 'pod-insights-stage'

    for episode in missing_episodes[:10]:  # Check first 10
        episode_id = episode['id']
        feed_slug = episode.get('feed_slug', 'unknown')
        guid = episode.get('guid', episode_id)

        sample_data = {
            'episode_id': episode_id,
            'guid': guid,
            'feed_slug': feed_slug,
            'title': episode.get('title', 'No title')[:100],
            'published_at': episode.get('published_at', 'Unknown'),
            's3_transcript_path': episode.get('s3_transcript_path', 'Not set'),
            's3_paths_found': []
        }

        # Try to find files in S3
        prefix = f"{feed_slug}/{guid}/"
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=10
            )

            if 'Contents' in response:
                for obj in response['Contents']:
                    sample_data['s3_paths_found'].append(obj['Key'])
            else:
                sample_data['s3_issue'] = 'No files found in S3'

        except Exception as e:
            sample_data['s3_issue'] = str(e)

        # Check if it's using episode_id instead of guid
        if not sample_data['s3_paths_found'] and guid != episode_id:
            alt_prefix = f"{feed_slug}/{episode_id}/"
            try:
                response = s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix=alt_prefix,
                    MaxKeys=10
                )
                if 'Contents' in response:
                    sample_data['alt_path_found'] = True
                    sample_data['alt_paths'] = [obj['Key'] for obj in response['Contents']]
            except:
                pass

        analysis['sample_missing'].append(sample_data)

    # Save report
    with open(report_file, 'w') as f:
        json.dump(analysis, f, indent=2)

    # Print summary
    print("\n📊 MISSING EPISODES ANALYSIS")
    print("="*50)
    print(f"Total missing: {analysis['total_missing']}")
    print(f"GUID mismatches: {analysis['guid_issues']}")

    print("\n📻 Missing by Podcast:")
    for podcast, count in sorted(analysis['missing_by_podcast'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {podcast}: {count}")

    print("\n🔍 Sample S3 Investigation:")
    for sample in analysis['sample_missing'][:5]:
        print(f"\nEpisode: {sample['title']}")
        print(f"  ID: {sample['episode_id']}")
        print(f"  GUID: {sample['guid']}")
        if sample['s3_paths_found']:
            print(f"  ✅ Found in S3: {len(sample['s3_paths_found'])} files")
        elif sample.get('alt_path_found'):
            print(f"  ⚠️  Found using episode_id instead of GUID!")
            print(f"  Alt paths: {sample['alt_paths'][:2]}")
        else:
            print(f"  ❌ Not found in S3")

    print(f"\n📄 Full report saved to: {report_file}")

    # Check if it's primarily a GUID issue
    if analysis['guid_issues'] > 50:
        print("\n⚠️  SIGNIFICANT GUID ISSUE DETECTED!")
        print("Many episodes have different GUIDs than their IDs.")
        print("The migration script may be looking in wrong S3 paths.")

if __name__ == "__main__":
    investigate_missing_episodes()
