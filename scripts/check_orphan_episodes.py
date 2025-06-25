#!/usr/bin/env python3
"""
Check for orphan episode IDs - chunks without metadata
"""

import os
from pymongo import MongoClient

# MongoDB connection
uri = os.environ.get('MONGODB_URI', '')
if not uri:
    print('Set MONGODB_URI environment variable')
    exit(1)

print("🔍 Checking for orphan episode IDs...")
print("=" * 60)

client = MongoClient(uri)
db = client.podinsight

# Get all unique episode IDs from chunks
print("\n📊 Getting unique episode IDs from transcript_chunks_768d...")
unique_chunk_ids = db.transcript_chunks_768d.distinct('episode_id')
print(f"Found {len(unique_chunk_ids)} unique episode IDs in chunks")

# Get all GUIDs from metadata
print("\n📋 Getting GUIDs from episode_metadata...")
metadata_guids = db.episode_metadata.distinct('guid')
print(f"Found {len(metadata_guids)} GUIDs in metadata")

# Convert to sets for comparison
chunk_ids_set = set(unique_chunk_ids)
metadata_guids_set = set(metadata_guids)

# Find orphans (chunks without metadata)
orphan_ids = chunk_ids_set - metadata_guids_set
print(f"\n🔴 Found {len(orphan_ids)} orphan episode IDs (chunks without metadata)")

# Find metadata without chunks (less common)
metadata_only = metadata_guids_set - chunk_ids_set
print(f"🟡 Found {len(metadata_only)} metadata entries without chunks")

# Show sample orphans
if orphan_ids:
    print("\n📝 Sample orphan IDs (first 5):")
    for i, orphan_id in enumerate(list(orphan_ids)[:5]):
        # Get a sample chunk to show which podcast
        sample_chunk = db.transcript_chunks_768d.find_one({'episode_id': orphan_id})
        feed_slug = sample_chunk.get('feed_slug', 'Unknown') if sample_chunk else 'Unknown'
        print(f"  {i+1}. {orphan_id} (feed: {feed_slug})")
    
    # Count by feed_slug
    print("\n📊 Orphan count by podcast:")
    orphan_counts = {}
    for orphan_id in orphan_ids:
        chunk = db.transcript_chunks_768d.find_one({'episode_id': orphan_id})
        if chunk:
            feed = chunk.get('feed_slug', 'Unknown')
            orphan_counts[feed] = orphan_counts.get(feed, 0) + 1
    
    for feed, count in sorted(orphan_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {feed}: {count} episodes")

# Summary
print("\n📈 Summary:")
print(f"  Total chunks: 823,763")
print(f"  Unique episodes in chunks: {len(unique_chunk_ids)}")
print(f"  Episodes with metadata: {len(metadata_guids)}")
print(f"  Orphan episodes: {len(orphan_ids)} ({len(orphan_ids)/len(unique_chunk_ids)*100:.1f}%)")
print(f"  Coverage: {len(unique_chunk_ids) - len(orphan_ids)} episodes have metadata ({(len(unique_chunk_ids) - len(orphan_ids))/len(unique_chunk_ids)*100:.1f}%)")

client.close()