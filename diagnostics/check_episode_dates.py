#!/usr/bin/env python3
"""
Check episode metadata for published dates
"""

import os
from pymongo import MongoClient

def check_episode_dates():
    """Check episode metadata for published date information"""

    mongodb_uri = os.getenv('MONGODB_URI')
    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client['podinsight']

    metadata_collection = db['episode_metadata']

    print("📅 Checking Episode Published Dates")
    print("=" * 40)

    # Get a few samples to understand date formats
    samples = list(metadata_collection.find().limit(10))

    print(f"Sample episodes: {len(samples)}")

    for i, episode in enumerate(samples[:3]):
        print(f"\nEpisode {i+1}:")
        print(f"  _id: {episode['_id']}")
        title = episode.get('episode_title', 'N/A')
        title_preview = title[:50] + "..." if title and len(title) > 50 else title
        print(f"  title: {title_preview}")

        # Check all potential published date fields
        date_fields = ['published_original_format', 'published', 'published_at', 'date', 'pubDate']

        for field in date_fields:
            if field in episode:
                value = episode[field]
                print(f"  {field}: {type(value)} = {value}")

        # Check _import_timestamp as potential fallback
        if '_import_timestamp' in episode:
            print(f"  _import_timestamp: {episode['_import_timestamp']}")

    # Check if any episodes have non-null published dates
    print(f"\nChecking published date availability:")

    # Count episodes with non-null published_original_format
    published_count = metadata_collection.count_documents({
        "published_original_format": {"$ne": None, "$exists": True}
    })
    print(f"Episodes with published_original_format: {published_count}")

    # Check for other possible date fields
    for field in ['published', 'published_at', 'pubDate', 'date']:
        count = metadata_collection.count_documents({field: {"$exists": True}})
        if count > 0:
            print(f"Episodes with {field}: {count}")
            sample = metadata_collection.find_one({field: {"$exists": True}})
            print(f"  Sample value: {sample[field]}")

    # If no published dates, we'll need to use _import_timestamp or created_at
    print(f"\nFallback options:")
    import_count = metadata_collection.count_documents({
        "_import_timestamp": {"$exists": True}
    })
    print(f"Episodes with _import_timestamp: {import_count}")

    client.close()

if __name__ == "__main__":
    check_episode_dates()
