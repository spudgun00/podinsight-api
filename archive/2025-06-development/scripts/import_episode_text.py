import os
import asyncio
import json
import boto3
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = AsyncIOMotorClient(MONGODB_URI)
db = client.podinsight
chunks_collection = db.transcript_chunks_768d

# S3 setup
s3_client = boto3.client('s3')
BUCKET_NAME = 'pod-insights-stage'

async def get_all_episodes():
    """Get all unique episodes from MongoDB"""
    print("Getting all episodes from MongoDB...")

    pipeline = [
        {"$group": {
            "_id": "$episode_id",
            "feed_slug": {"$first": "$feed_slug"},
            "chunk_count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]

    episodes = await chunks_collection.aggregate(pipeline).to_list(None)
    print(f"Found {len(episodes)} unique episodes in MongoDB")
    return episodes

def download_episode_text(feed_slug, episode_id):
    """Download episode text file from S3"""
    # Path pattern for text files
    s3_key = f"{feed_slug}/{episode_id}/transcripts/{episode_id}_text.json"

    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        content = response['Body'].read()
        data = json.loads(content)
        return data
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        print(f"Error downloading {s3_key}: {e}")
        return None

async def update_episode_chunks(episode_id, episode_data):
    """Update all chunks for an episode with full text"""
    full_text = episode_data.get('text', '')
    episode_title = episode_data.get('title', f"Episode {episode_id[:8]}...")

    if not full_text:
        print(f"  ⚠️  No text content found for {episode_id}")
        return False

    # Update all chunks for this episode
    result = await chunks_collection.update_many(
        {"episode_id": episode_id},
        {"$set": {
            "full_episode_text": full_text,
            "episode_title_full": episode_title,
            "text_imported_at": datetime.utcnow(),
            "text_word_count": len(full_text.split()),
            "text_char_count": len(full_text)
        }}
    )

    print(f"  ✅ Updated {result.modified_count} chunks with full text ({len(full_text):,} chars)")
    return True

async def verify_guid_integrity(episode_id, episode_data):
    """Verify that the text file guid matches the MongoDB episode_id"""
    text_guid = episode_data.get('guid')
    text_feed = episode_data.get('feed_slug')

    if text_guid != episode_id:
        print(f"  ⚠️  GUID MISMATCH: MongoDB={episode_id}, Text file={text_guid}")
        return False

    return True

async def main():
    print("="*70)
    print("IMPORTING EPISODE TEXT FILES TO MONGODB")
    print("="*70)

    # Get all episodes from MongoDB
    episodes = await get_all_episodes()

    # Track results
    success_count = 0
    not_found_count = 0
    error_count = 0
    total_text_size = 0
    guid_mismatches = []

    print(f"\nProcessing {len(episodes)} episodes...")

    for i, episode in enumerate(episodes, 1):
        episode_id = episode['_id']
        feed_slug = episode['feed_slug']

        if i % 50 == 0:
            print(f"\nProgress: {i}/{len(episodes)} ({i/len(episodes)*100:.1f}%)")

        print(f"\n{i}. {feed_slug} / {episode_id[:12]}...")

        # Download text file
        episode_data = download_episode_text(feed_slug, episode_id)

        if not episode_data:
            print(f"  ❌ Text file not found")
            not_found_count += 1
            continue

        # Verify GUID integrity
        if not await verify_guid_integrity(episode_id, episode_data):
            guid_mismatches.append({
                'episode_id': episode_id,
                'text_guid': episode_data.get('guid'),
                'feed_slug': feed_slug
            })
            error_count += 1
            continue

        # Update chunks with full text
        if await update_episode_chunks(episode_id, episode_data):
            success_count += 1
            total_text_size += len(episode_data.get('text', ''))
        else:
            error_count += 1

    # Summary
    print("\n" + "="*70)
    print("IMPORT SUMMARY")
    print("="*70)

    print(f"\nResults:")
    print(f"  ✅ Successfully imported: {success_count}")
    print(f"  ❌ Text files not found: {not_found_count}")
    print(f"  ⚠️  Errors/mismatches: {error_count}")
    print(f"  📊 Total episodes processed: {len(episodes)}")
    print(f"  📝 Total text imported: {total_text_size:,} characters ({total_text_size/1024/1024:.1f} MB)")

    if guid_mismatches:
        print(f"\n⚠️  GUID MISMATCHES FOUND:")
        for mismatch in guid_mismatches[:5]:  # Show first 5
            print(f"  {mismatch['feed_slug']} / {mismatch['episode_id']} → {mismatch['text_guid']}")
        if len(guid_mismatches) > 5:
            print(f"  ... and {len(guid_mismatches) - 5} more")

    # Verify the import worked
    print(f"\n📊 VERIFICATION:")
    chunks_with_text = await chunks_collection.count_documents({"full_episode_text": {"$exists": True}})
    total_chunks = await chunks_collection.count_documents({})

    print(f"  Chunks with full text: {chunks_with_text:,}")
    print(f"  Total chunks: {total_chunks:,}")
    print(f"  Coverage: {chunks_with_text/total_chunks*100:.1f}%")

    # Sample check
    sample = await chunks_collection.find_one({"full_episode_text": {"$exists": True}})
    if sample:
        text_length = len(sample.get('full_episode_text', ''))
        word_count = sample.get('text_word_count', 0)
        print(f"\n📋 SAMPLE EPISODE:")
        print(f"  Episode ID: {sample['episode_id']}")
        print(f"  Feed: {sample['feed_slug']}")
        print(f"  Text length: {text_length:,} characters")
        print(f"  Word count: {word_count:,} words")
        print(f"  Title: {sample.get('episode_title_full', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(main())
