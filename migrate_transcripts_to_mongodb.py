#!/usr/bin/env python3
"""
MongoDB Transcript Migration Script for PodInsightHQ
Migrates transcripts from S3 to MongoDB for real search functionality
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, List, Optional
import argparse
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from supabase import create_client, Client
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
# Reduce noisy AWS and HTTP debug logs
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class TranscriptMigrator:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            'total': 0,
            'migrated': 0,
            'skipped': 0,
            'errors': 0,
            'missing_transcripts': 0
        }
        
        # Initialize connections
        self._init_mongodb()
        self._init_supabase()
        self._init_s3()
        
    def _init_mongodb(self):
        """Initialize MongoDB connection"""
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not found in environment variables")
            
        try:
            self.mongo_client = MongoClient(
                mongodb_uri,
                maxPoolSize=10,
                serverSelectionTimeoutMS=5000
            )
            # Test connection
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client['podinsight']
            self.transcripts_collection = self.db['transcripts']
            logger.info("✅ MongoDB connection established")
        except PyMongoError as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
            
    def _init_supabase(self):
        """Initialize Supabase connection"""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
            
        try:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            # Test connection with a simple query
            self.supabase.table('episodes').select('count', count='exact').limit(1).execute()
            logger.info("✅ Supabase connection established")
        except Exception as e:
            logger.error(f"❌ Supabase connection failed: {e}")
            raise
            
    def _init_s3(self):
        """Initialize S3 connection"""
        try:
            self.s3_client = boto3.client('s3')
            # Test connection
            self.s3_client.list_buckets()
            self.stage_bucket = os.getenv('S3_BUCKET_STAGE', 'pod-insights-stage')
            logger.info("✅ S3 connection established")
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"❌ S3 connection failed: {e}")
            raise
            
    def get_episodes_from_supabase(self, limit: Optional[int] = None) -> List[Dict]:
        """Fetch all episodes from Supabase"""
        try:
            query = self.supabase.table('episodes').select('*')
            if limit:
                query = query.limit(limit)
                
            response = query.execute()
            episodes = response.data
            logger.info(f"📊 Retrieved {len(episodes)} episodes from Supabase")
            return episodes
        except Exception as e:
            logger.error(f"❌ Failed to fetch episodes from Supabase: {e}")
            raise
            
    def get_episode_topics(self, episode_id: str) -> List[str]:
        """Get topics for an episode from topic_mentions table"""
        try:
            response = self.supabase.table('topic_mentions').select('topic_name').eq('episode_id', episode_id).execute()
            topics = [mention['topic_name'] for mention in response.data]
            return topics
        except Exception as e:
            logger.warning(f"Failed to fetch topics for episode {episode_id}: {e}")
            return []
            
    def discover_transcript_file(self, s3_stage_prefix: str) -> Optional[str]:
        """Discover the actual transcript file using production naming patterns"""
        try:
            # Clean up the prefix - remove S3 URL prefix if present
            clean_prefix = s3_stage_prefix.rstrip('/')
            
            # Remove s3://bucket-name/ prefix if it exists
            if clean_prefix.startswith(f's3://{self.stage_bucket}/'):
                clean_prefix = clean_prefix.replace(f's3://{self.stage_bucket}/', '')
            elif clean_prefix.startswith('s3://'):
                # Handle other S3 URL formats
                clean_prefix = '/'.join(clean_prefix.split('/')[3:])
            
            transcripts_prefix = f"{clean_prefix}/transcripts/"
            
            logger.debug(f"Looking for transcripts in: {transcripts_prefix}")
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.stage_bucket,
                Prefix=transcripts_prefix
            )
            
            files_found = response.get('Contents', [])
            logger.debug(f"Found {len(files_found)} files in {transcripts_prefix}")
            
            for obj in files_found:
                key = obj['Key']
                filename = key.split('/')[-1]
                logger.debug(f"  Checking file: {filename}")
                
                # Look for transcript files with production naming pattern
                if filename.endswith('.json') and ('transcript' in filename.lower() or 'raw' in filename.lower()):
                    logger.debug(f"  ✅ Found transcript: {key}")
                    return key
            
            # If no transcript files found, let's also check what files ARE there
            if not files_found:
                logger.warning(f"No files found at all in {transcripts_prefix}")
            else:
                logger.warning(f"Found {len(files_found)} files but none match transcript pattern:")
                for obj in files_found[:5]:  # Show first 5 files
                    logger.warning(f"  - {obj['Key']}")
                    
            return None
        except Exception as e:
            logger.error(f"Error discovering transcript files in {s3_stage_prefix}: {e}")
            return None

    def download_transcript_from_s3(self, s3_stage_prefix: str) -> Optional[Dict]:
        """Download transcript JSON from S3 using adaptive file discovery"""
        # First try to discover the actual transcript file
        transcript_key = self.discover_transcript_file(s3_stage_prefix)
        
        if not transcript_key:
            logger.warning(f"No transcript file found in {s3_stage_prefix}/transcripts/")
            self.stats['missing_transcripts'] += 1
            return None
        
        try:
            response = self.s3_client.get_object(Bucket=self.stage_bucket, Key=transcript_key)
            transcript_data = json.loads(response['Body'].read().decode('utf-8'))
            logger.debug(f"Successfully downloaded transcript: {transcript_key}")
            return transcript_data
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.warning(f"Transcript not found: {transcript_key}")
                self.stats['missing_transcripts'] += 1
            else:
                logger.error(f"S3 error downloading {transcript_key}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {transcript_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {transcript_key}: {e}")
            return None
            
    def extract_full_text(self, transcript_data: Dict) -> str:
        """Extract full text from transcript segments"""
        segments = transcript_data.get('segments', [])
        if not segments:
            return ""
            
        # Combine all segment text
        full_text_parts = []
        for segment in segments:
            text = segment.get('text', '').strip()
            if text:
                full_text_parts.append(text)
                
        return ' '.join(full_text_parts)
        
    def calculate_word_count(self, text: str) -> int:
        """Calculate approximate word count"""
        return len(text.split()) if text else 0
        
    def is_already_migrated(self, episode_id: str) -> bool:
        """Check if episode is already migrated to MongoDB"""
        try:
            existing = self.transcripts_collection.find_one({'episode_id': episode_id})
            return existing is not None
        except PyMongoError as e:
            logger.error(f"Error checking if episode {episode_id} exists: {e}")
            return False
            
    def create_mongodb_document(self, episode: Dict, transcript_data: Dict, topics: List[str]) -> Dict:
        """Create MongoDB document from episode and transcript data"""
        full_text = self.extract_full_text(transcript_data)
        word_count = self.calculate_word_count(full_text)
        
        # Convert published_at to datetime if it's a string
        published_at = episode.get('published_at')
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            except ValueError:
                published_at = datetime.now()
                
        document = {
            'episode_id': episode['id'],
            'podcast_name': episode.get('podcast_name', ''),
            'episode_title': episode.get('title', ''),
            'published_at': published_at,
            'full_text': full_text,
            'segments': transcript_data.get('segments', []),
            'topics': topics,
            's3_paths': {
                'stage_prefix': episode.get('s3_stage_prefix', ''),
                'raw_prefix': episode.get('s3_raw_prefix', '')
            },
            'word_count': word_count,
            'duration_seconds': episode.get('duration_seconds', 0),
            'migrated_at': datetime.now(timezone.utc)
        }
        
        return document
        
    def migrate_single_episode(self, episode: Dict) -> bool:
        """Migrate a single episode to MongoDB"""
        episode_id = episode['id']
        s3_stage_prefix = episode.get('s3_stage_prefix')
        
        if not s3_stage_prefix:
            logger.warning(f"No S3 stage prefix for episode {episode_id}")
            return False
            
        # Check if already migrated (for resumption)
        if self.is_already_migrated(episode_id):
            logger.debug(f"Episode {episode_id} already migrated, skipping")
            self.stats['skipped'] += 1
            return True
            
        # Download transcript from S3
        transcript_data = self.download_transcript_from_s3(s3_stage_prefix)
        if not transcript_data:
            return False
            
        # Get topics for this episode
        topics = self.get_episode_topics(episode_id)
        
        # Create MongoDB document
        document = self.create_mongodb_document(episode, transcript_data, topics)
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would migrate episode {episode_id[:8]}... "
                       f"({document['word_count']} words, {len(topics)} topics)")
            return True
            
        # Insert into MongoDB
        try:
            self.transcripts_collection.insert_one(document)
            logger.debug(f"✅ Migrated episode {episode_id}")
            self.stats['migrated'] += 1
            return True
        except PyMongoError as e:
            logger.error(f"Failed to insert episode {episode_id}: {e}")
            self.stats['errors'] += 1
            return False
            
    def run_migration(self, limit: Optional[int] = None):
        """Run the complete migration process"""
        logger.info("🚀 Starting transcript migration to MongoDB")
        
        # Get episodes from Supabase
        episodes = self.get_episodes_from_supabase(limit)
        self.stats['total'] = len(episodes)
        
        if not episodes:
            logger.warning("No episodes found to migrate")
            return
            
        if self.dry_run:
            logger.info(f"[DRY RUN] Would process {len(episodes)} episodes")
        else:
            logger.info(f"Processing {len(episodes)} episodes")
            
        # Create progress bar
        with tqdm(total=len(episodes), desc="Migrating episodes") as pbar:
            for episode in episodes:
                self.migrate_single_episode(episode)
                pbar.update(1)
                
                # Update progress bar description
                pbar.set_postfix({
                    'migrated': self.stats['migrated'],
                    'errors': self.stats['errors'],
                    'missing': self.stats['missing_transcripts']
                })
                
                # Small delay to avoid overwhelming connections
                time.sleep(0.1)
                
        self.print_final_report()
        
    def print_final_report(self):
        """Print final migration statistics"""
        print("\n" + "="*60)
        print("📊 MIGRATION COMPLETE")
        print("="*60)
        print(f"Total episodes:        {self.stats['total']}")
        print(f"Successfully migrated: {self.stats['migrated']}")
        print(f"Already existed:       {self.stats['skipped']}")
        print(f"Missing transcripts:   {self.stats['missing_transcripts']}")
        print(f"Errors:               {self.stats['errors']}")
        
        success_rate = ((self.stats['migrated'] + self.stats['skipped']) / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        print(f"Success rate:         {success_rate:.1f}%")
        
        if self.dry_run:
            print("\n[DRY RUN] No data was actually migrated")
        else:
            print(f"\n✅ Migration completed successfully!")
            print("Next steps:")
            print("1. Run verification script")
            print("2. Update search API to use MongoDB")
            print("3. Test search functionality")

def main():
    parser = argparse.ArgumentParser(description='Migrate transcripts from S3 to MongoDB')
    parser.add_argument('--limit', type=int, help='Limit number of episodes to migrate (for testing)')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run without actually migrating')
    
    args = parser.parse_args()
    
    try:
        migrator = TranscriptMigrator(dry_run=args.dry_run)
        migrator.run_migration(limit=args.limit)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        print("You can resume by running the script again - it will skip already migrated episodes")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()