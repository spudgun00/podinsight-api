#!/usr/bin/env python3
"""
List all unique podcasts from MongoDB and S3 buckets
"""
import os
import sys
import asyncio
from dotenv import load_dotenv
from pymongo import MongoClient
import boto3
from collections import defaultdict
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

def get_mongodb_podcasts():
    """Get all unique podcasts from MongoDB"""
    print("🔍 Fetching podcasts from MongoDB...")

    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        print("❌ MONGODB_URI not found in environment")
        return set()

    try:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        db = client.podinsight

        # Get unique podcast names from transcript_chunks_768d
        podcasts = set()

        # Method 1: From transcript_chunks_768d collection
        print("  Checking transcript_chunks_768d collection...")
        chunks_podcasts = db.transcript_chunks_768d.distinct("feed_slug")
        podcasts.update(chunks_podcasts)
        print(f"  Found {len(chunks_podcasts)} unique podcasts in transcript_chunks_768d")

        # Method 2: From episode_metadata if it exists
        if "episode_metadata" in db.list_collection_names():
            print("  Checking episode_metadata collection...")
            # Get sample to see structure
            sample = db.episode_metadata.find_one()
            if sample and "podcast_name" in sample:
                metadata_podcasts = db.episode_metadata.distinct("podcast_name")
                podcasts.update(metadata_podcasts)
                print(f"  Found {len(metadata_podcasts)} unique podcasts in episode_metadata")

        return podcasts

    except Exception as e:
        print(f"❌ MongoDB error: {str(e)}")
        return set()

def get_s3_podcasts():
    """Get all unique podcasts from S3 buckets"""
    print("\n🔍 Fetching podcasts from S3 buckets...")

    # Check for AWS credentials
    if not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        print("❌ AWS credentials not found in environment")
        return set()

    try:
        s3 = boto3.client('s3')
        podcasts = set()

        # S3 buckets to check
        buckets = [
            "pod-insights-raw",
            "pod-insights-stage",
            "pod-insights-prod"
        ]

        for bucket in buckets:
            print(f"\n  Checking bucket: {bucket}")
            try:
                # List objects with pagination
                paginator = s3.get_paginator('list_objects_v2')
                page_iterator = paginator.paginate(
                    Bucket=bucket,
                    Delimiter='/',
                    MaxKeys=1000
                )

                # Get top-level directories (podcast names)
                bucket_podcasts = set()
                for page in page_iterator:
                    if 'CommonPrefixes' in page:
                        for prefix in page['CommonPrefixes']:
                            podcast_name = prefix['Prefix'].rstrip('/')
                            if podcast_name and not podcast_name.startswith('.'):
                                bucket_podcasts.add(podcast_name)

                podcasts.update(bucket_podcasts)
                print(f"    Found {len(bucket_podcasts)} podcasts")

            except Exception as e:
                print(f"    ❌ Error accessing {bucket}: {str(e)}")

        return podcasts

    except Exception as e:
        print(f"❌ S3 error: {str(e)}")
        return set()

def format_podcast_name(name):
    """Format podcast name for display"""
    # Replace hyphens with spaces and title case
    formatted = name.replace('-', ' ').replace('_', ' ')
    # Title case but preserve certain words
    words = formatted.split()
    formatted_words = []
    for word in words:
        if word.lower() in ['the', 'in', 'on', 'with', 'and', 'or', 'for', 'of', 'a']:
            formatted_words.append(word.lower())
        else:
            formatted_words.append(word.title())

    # Capitalize first word
    if formatted_words:
        formatted_words[0] = formatted_words[0].title()

    return ' '.join(formatted_words)

def main():
    print("📊 PodInsights Podcast Inventory\n")

    # Get podcasts from MongoDB
    mongodb_podcasts = get_mongodb_podcasts()

    # Get podcasts from S3
    s3_podcasts = get_s3_podcasts()

    # Combine all unique podcasts
    all_podcasts = mongodb_podcasts | s3_podcasts

    print("\n" + "="*60)
    print("📋 COMPLETE PODCAST LIST")
    print("="*60)

    if all_podcasts:
        # Sort podcasts alphabetically
        sorted_podcasts = sorted(all_podcasts, key=lambda x: x.lower())

        print(f"\nTotal unique podcasts: {len(sorted_podcasts)}\n")

        # Group by first letter
        grouped = defaultdict(list)
        for podcast in sorted_podcasts:
            first_letter = podcast[0].upper() if podcast else '?'
            grouped[first_letter].append(podcast)

        # Display grouped
        for letter in sorted(grouped.keys()):
            print(f"\n{letter}:")
            for podcast in grouped[letter]:
                formatted = format_podcast_name(podcast)
                print(f"  • {podcast}")
                if formatted != podcast:
                    print(f"    ({formatted})")

        # Summary statistics
        print("\n" + "="*60)
        print("📊 SUMMARY")
        print("="*60)
        print(f"Total unique podcasts: {len(all_podcasts)}")
        print(f"Podcasts in MongoDB: {len(mongodb_podcasts)}")
        print(f"Podcasts in S3: {len(s3_podcasts)}")
        print(f"Podcasts in both: {len(mongodb_podcasts & s3_podcasts)}")
        print(f"MongoDB only: {len(mongodb_podcasts - s3_podcasts)}")
        print(f"S3 only: {len(s3_podcasts - mongodb_podcasts)}")

        # Export to file
        output_file = "podcast_inventory.json"
        with open(output_file, 'w') as f:
            json.dump({
                "total": len(all_podcasts),
                "podcasts": sorted_podcasts,
                "mongodb_podcasts": sorted(list(mongodb_podcasts)),
                "s3_podcasts": sorted(list(s3_podcasts)),
                "formatted_names": {p: format_podcast_name(p) for p in sorted_podcasts}
            }, f, indent=2)

        print(f"\n✅ Full list exported to: {output_file}")

    else:
        print("\n❌ No podcasts found!")

if __name__ == "__main__":
    main()
