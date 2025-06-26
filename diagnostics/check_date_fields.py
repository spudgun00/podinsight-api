#!/usr/bin/env python3
"""
Check available date fields in transcript_chunks_768d collection
"""

import os
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone

def check_date_fields():
    """Check what date fields are available"""

    mongodb_uri = os.getenv('MONGODB_URI')
    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client['podinsight']
    collection = db['transcript_chunks_768d']

    print("🔍 Checking Date Fields in transcript_chunks_768d")
    print("=" * 50)

    # Get sample document
    sample = collection.find_one()
    print(f"Available fields: {list(sample.keys())}")

    # Check date-related fields
    date_fields = []
    for field, value in sample.items():
        if isinstance(value, datetime) or 'date' in field.lower() or 'time' in field.lower() or 'at' in field.lower():
            date_fields.append((field, type(value), value))

    print(f"\nDate-related fields:")
    for field, field_type, value in date_fields:
        print(f"  {field}: {field_type} = {value}")

    # Check if we need to join with episodes collection
    print(f"\nEpisode ID: {sample.get('episode_id', 'N/A')}")

    # Check if episodes collection exists and has published_at
    episodes_collection = db['episodes']
    if episodes_collection.estimated_document_count() > 0:
        episode_sample = episodes_collection.find_one()
        print(f"\nEpisodes collection fields: {list(episode_sample.keys())}")

        # Look for published date fields in episodes
        episode_date_fields = []
        for field, value in episode_sample.items():
            if isinstance(value, datetime) or 'date' in field.lower() or 'published' in field.lower():
                episode_date_fields.append((field, type(value), value))

        print(f"Episode date fields:")
        for field, field_type, value in episode_date_fields:
            print(f"  {field}: {field_type} = {value}")

    client.close()

if __name__ == "__main__":
    check_date_fields()
