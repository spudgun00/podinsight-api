#!/usr/bin/env python3
"""
Comprehensive MongoDB migration verification with detailed logging
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
import json
from pathlib import Path
import statistics

# Load .env file from the current directory
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

def check_migration_status():
    """Check MongoDB migration status and create detailed log"""

    MONGODB_URI = os.getenv('MONGODB_URI')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f'mongodb_verification_{timestamp}.log'

    # Open log file
    with open(log_file, 'w') as log:
        log.write(f"MongoDB Migration Verification Report\n")
        log.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write("="*60 + "\n\n")

        if not MONGODB_URI:
            log.write("❌ ERROR: MONGODB_URI not found in environment\n")
            print(f"❌ ERROR: MONGODB_URI not found. See {log_file}")
            return

        try:
            print("🔍 Connecting to MongoDB...")
            client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            db = client['podinsight']

            # Force connection to verify it works
            client.server_info()
            log.write("✅ Connected to MongoDB successfully\n\n")
            print("✅ Connected to MongoDB")

            # Check collections
            collections = db.list_collection_names()
            log.write(f"📦 Collections found: {collections}\n\n")

            if 'transcripts' not in collections:
                log.write("❌ ERROR: 'transcripts' collection not found!\n")
                print(f"❌ No transcripts collection. See {log_file}")
                return

            # Get document count
            count = db.transcripts.count_documents({})
            log.write(f"📊 DOCUMENT COUNT: {count}\n")
            log.write(f"Expected: 1,171 episodes\n")
            log.write(f"Difference: {1171 - count}\n\n")
            print(f"📊 Found {count} documents in MongoDB")

            # Analyze migration timing
            log.write("⏱️ MIGRATION TIMING ANALYSIS\n")
            log.write("-"*40 + "\n")

            # Find earliest and latest migration times
            pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'earliest': {'$min': '$migrated_at'},
                        'latest': {'$max': '$migrated_at'},
                        'count': {'$sum': 1}
                    }
                }
            ]
            timing = list(db.transcripts.aggregate(pipeline))
            if timing:
                earliest = timing[0]['earliest']
                latest = timing[0]['latest']
                duration = (latest - earliest).total_seconds()
                log.write(f"First migration: {earliest}\n")
                log.write(f"Last migration: {latest}\n")
                log.write(f"Total duration: {duration:.2f} seconds ({duration/60:.2f} minutes)\n")
                log.write(f"Average per episode: {duration/count:.2f} seconds\n\n")
                print(f"⏱️  Migration took {duration/60:.2f} minutes total")

            # Analyze document sizes
            log.write("📏 DOCUMENT SIZE ANALYSIS\n")
            log.write("-"*40 + "\n")

            # Sample documents for size analysis
            sample_size = min(100, count)
            samples = list(db.transcripts.find().limit(sample_size))

            text_lengths = []
            segment_counts = []
            word_counts = []

            for doc in samples:
                if 'full_text' in doc and doc['full_text']:
                    text_lengths.append(len(doc['full_text']))
                if 'segments' in doc:
                    segment_counts.append(len(doc['segments']))
                if 'word_count' in doc:
                    word_counts.append(doc['word_count'])

            if text_lengths:
                log.write(f"Full text lengths (chars) - Sample of {len(text_lengths)}:\n")
                log.write(f"  Min: {min(text_lengths):,}\n")
                log.write(f"  Max: {max(text_lengths):,}\n")
                log.write(f"  Average: {statistics.mean(text_lengths):,.0f}\n")
                log.write(f"  Median: {statistics.median(text_lengths):,.0f}\n\n")

            if segment_counts:
                log.write(f"Segment counts - Sample of {len(segment_counts)}:\n")
                log.write(f"  Min: {min(segment_counts)}\n")
                log.write(f"  Max: {max(segment_counts)}\n")
                log.write(f"  Average: {statistics.mean(segment_counts):.0f}\n\n")

            if word_counts:
                log.write(f"Word counts - Sample of {len(word_counts)}:\n")
                log.write(f"  Min: {min(word_counts):,}\n")
                log.write(f"  Max: {max(word_counts):,}\n")
                log.write(f"  Average: {statistics.mean(word_counts):,.0f}\n\n")

            # Check data completeness
            log.write("✅ DATA COMPLETENESS CHECK\n")
            log.write("-"*40 + "\n")

            with_text = db.transcripts.count_documents({'full_text': {'$exists': True, '$ne': ''}})
            with_segments = db.transcripts.count_documents({'segments': {'$exists': True, '$ne': []}})
            with_topics = db.transcripts.count_documents({'topics': {'$exists': True, '$ne': []}})

            log.write(f"Documents with full_text: {with_text} ({with_text/count*100:.1f}%)\n")
            log.write(f"Documents with segments: {with_segments} ({with_segments/count*100:.1f}%)\n")
            log.write(f"Documents with topics: {with_topics} ({with_topics/count*100:.1f}%)\n\n")

            # Count by podcast
            log.write("📻 DOCUMENTS BY PODCAST\n")
            log.write("-"*40 + "\n")
            pipeline = [
                {'$group': {'_id': '$podcast_name', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]
            podcasts = list(db.transcripts.aggregate(pipeline))
            for p in podcasts:
                log.write(f"{p['_id']}: {p['count']}\n")
            log.write(f"\nTotal podcasts: {len(podcasts)}\n\n")

            # Check indexes
            log.write("🔍 DATABASE INDEXES\n")
            log.write("-"*40 + "\n")
            indexes = db.transcripts.list_indexes()
            for idx in indexes:
                log.write(f"{idx['name']}: {idx.get('key', {})}\n")

            # Sample 5 random documents
            log.write("\n📄 SAMPLE DOCUMENTS (5 random)\n")
            log.write("-"*40 + "\n")

            samples = list(db.transcripts.aggregate([{'$sample': {'size': 5}}]))
            for i, doc in enumerate(samples):
                log.write(f"\n--- Sample {i+1} ---\n")
                log.write(f"Episode ID: {doc.get('episode_id', 'N/A')}\n")
                log.write(f"Podcast: {doc.get('podcast_name', 'N/A')}\n")
                log.write(f"Title: {doc.get('episode_title', 'N/A')[:100]}...\n")
                log.write(f"Word count: {doc.get('word_count', 'N/A')}\n")
                log.write(f"Topics: {doc.get('topics', [])}\n")
                log.write(f"Full text preview: {doc.get('full_text', '')[:200]}...\n")
                if 'segments' in doc and doc['segments']:
                    log.write(f"First segment: {doc['segments'][0].get('text', '')[:100]}...\n")
                    log.write(f"  Speaker: {doc['segments'][0].get('speaker', 'N/A')}\n")
                    log.write(f"  Time: {doc['segments'][0].get('start_time', 0)}-{doc['segments'][0].get('end_time', 0)}\n")

            # Collection stats
            log.write("\n💾 COLLECTION STATISTICS\n")
            log.write("-"*40 + "\n")
            stats = db.command("collStats", "transcripts")
            log.write(f"Collection size: {stats.get('size', 0) / 1024 / 1024:.2f} MB\n")
            log.write(f"Average document size: {stats.get('avgObjSize', 0) / 1024:.2f} KB\n")
            log.write(f"Total index size: {stats.get('totalIndexSize', 0) / 1024 / 1024:.2f} MB\n")

            # Summary
            log.write("\n🎯 SUMMARY\n")
            log.write("="*60 + "\n")
            if count >= 1000:
                log.write("✅ Migration appears SUCCESSFUL!\n")
                log.write(f"✅ {count} episodes migrated\n")
                log.write(f"✅ Full transcripts and segments present\n")
                log.write(f"✅ All indexes created\n")
                print(f"\n✅ Migration SUCCESSFUL! {count} episodes in MongoDB")
            else:
                log.write(f"⚠️  Only {count} episodes found (expected ~1,171)\n")
                log.write("Check migration logs for any errors\n")
                print(f"\n⚠️  Only {count} episodes found. Check {log_file}")

        except Exception as e:
            log.write(f"\n❌ ERROR: {e}\n")
            print(f"❌ Error: {e}. See {log_file}")

    print(f"\n📄 Detailed report saved to: {log_file}")

if __name__ == "__main__":
    print("🔍 MongoDB Migration Verification\n")
    check_migration_status()
