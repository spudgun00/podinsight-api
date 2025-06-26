#!/usr/bin/env python3
"""
Check what fields exist in episode_metadata
"""

import os
from pymongo import MongoClient

def check_episode_fields():
    mongodb_uri = os.getenv('MONGODB_URI')
    if not mongodb_uri:
        print("❌ MONGODB_URI not set")
        return

    # Add database name if missing
    if '/podinsight?' not in mongodb_uri and mongodb_uri.endswith('mongodb.net/?'):
        mongodb_uri = mongodb_uri.replace('mongodb.net/?', 'mongodb.net/podinsight?')

    try:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        db = client['podinsight']
        episodes_collection = db['episode_metadata']

        print("🔍 Checking episode_metadata fields...")

        # Get a sample episode
        sample = episodes_collection.find_one({})
        if sample:
            print("\n📋 Available fields in episode_metadata:")
            for field in sorted(sample.keys()):
                value = sample[field]
                if 'date' in field.lower() or 'time' in field.lower() or 'published' in field.lower():
                    print(f"  ⭐ {field}: {value} (type: {type(value).__name__})")
                else:
                    print(f"  - {field}: {type(value).__name__}")

        # Look for date-related fields specifically
        print("\n📅 Checking for date fields...")
        sample_with_dates = episodes_collection.find_one({
            "$or": [
                {"published_date_iso": {"$exists": True}},
                {"published_at": {"$exists": True}},
                {"date": {"$exists": True}},
                {"publishedAt": {"$exists": True}},
                {"raw_entry_original_feed.published_date_iso": {"$exists": True}}
            ]
        })

        if sample_with_dates:
            print("\n✅ Found episode with date fields:")
            for field in sorted(sample_with_dates.keys()):
                value = sample_with_dates[field]
                if 'date' in field.lower() or 'published' in field.lower():
                    print(f"  {field}: {value}")
                elif field == 'raw_entry_original_feed' and isinstance(value, dict):
                    for subfield, subvalue in value.items():
                        if 'date' in subfield.lower() or 'published' in subfield.lower():
                            print(f"  raw_entry_original_feed.{subfield}: {subvalue}")

        client.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_episode_fields()
