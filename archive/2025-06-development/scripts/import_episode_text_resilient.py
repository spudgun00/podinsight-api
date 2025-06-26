import os
import asyncio
import json
import boto3
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from dotenv import load_dotenv
import time

load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = AsyncIOMotorClient(MONGODB_URI)
db = client.podinsight
chunks_collection = db.transcript_chunks_768d

# S3 setup
s3_client = boto3.client('s3')
BUCKET_NAME = 'pod-insights-stage'

async def get_episodes_needing_text():
    """Get episodes that don't have full_episode_text yet"""
    print("Finding episodes that need text import...")

    # Find episodes without full_episode_text
    pipeline = [
        {"$match": {"full_episode_text": {"$exists": False}}},
        {"$group": {
            "_id": "$episode_id",
            "feed_slug": {"$first": "$feed_slug"},
            "chunk_count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]

    episodes = await chunks_collection.aggregate(pipeline).to_list(None)
    print(f"Found {len(episodes)} episodes needing text import")
    return episodes

async def get_import_status():
    """Check current import status"""
    total_episodes = len(await chunks_collection.distinct("episode_id"))
    episodes_with_text = len(await chunks_collection.distinct("episode_id", {"full_episode_text": {"$exists": True}}))

    print(f"Import Status: {episodes_with_text}/{total_episodes} episodes ({episodes_with_text/total_episodes*100:.1f}%) have full text")
    return episodes_with_text, total_episodes

async def import_batch(episodes, batch_size=10):
    """Import text for a batch of episodes with error handling"""
    success_count = 0
    error_count = 0

    for i in range(0, len(episodes), batch_size):
        batch = episodes[i:i+batch_size]

        print(f"\nProcessing batch {i//batch_size + 1}/{(len(episodes) + batch_size - 1)//batch_size}")
        print(f"Episodes {i+1}-{min(i+batch_size, len(episodes))} of {len(episodes)}")

        for j, episode in enumerate(batch, 1):
            episode_id = episode['_id']
            feed_slug = episode['feed_slug']

            try:
                print(f"  {i+j}. {feed_slug} / {episode_id[:12]}...", end=" ")

                # Download text file
                s3_key = f"{feed_slug}/{episode_id}/transcripts/{episode_id}_text.json"
                response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
                content = response['Body'].read()
                data = json.loads(content)

                # Verify GUID
                if data.get('guid') != episode_id:
                    print(f"GUID mismatch!")
                    error_count += 1
                    continue

                full_text = data.get('text', '')
                if not full_text:
                    print(f"No text content!")
                    error_count += 1
                    continue

                # Update chunks
                result = await chunks_collection.update_many(
                    {"episode_id": episode_id},
                    {"$set": {
                        "full_episode_text": full_text,
                        "episode_title_full": data.get('title', f"Episode {episode_id[:8]}..."),
                        "text_imported_at": datetime.utcnow(),
                        "text_word_count": len(full_text.split()),
                        "text_char_count": len(full_text)
                    }}
                )

                print(f"✅ Updated {result.modified_count} chunks ({len(full_text):,} chars)")
                success_count += 1

                # Small delay to avoid overwhelming MongoDB
                await asyncio.sleep(0.1)

            except s3_client.exceptions.NoSuchKey:
                print(f"❌ Text file not found")
                error_count += 1
            except Exception as e:
                print(f"❌ Error: {e}")
                error_count += 1

        # Longer delay between batches
        if i + batch_size < len(episodes):
            print(f"  Batch complete. Waiting 2 seconds before next batch...")
            await asyncio.sleep(2)

    return success_count, error_count

async def main():
    print("="*70)
    print("RESILIENT EPISODE TEXT IMPORT")
    print("="*70)

    # Check current status
    await get_import_status()

    # Get episodes that need text
    episodes_needing_text = await get_episodes_needing_text()

    if not episodes_needing_text:
        print("\n✅ All episodes already have full text!")
        return

    print(f"\nWill process {len(episodes_needing_text)} episodes in batches of 10")

    start_time = time.time()
    success_count, error_count = await import_batch(episodes_needing_text, batch_size=10)
    elapsed = time.time() - start_time

    # Final summary
    print("\n" + "="*70)
    print("IMPORT SUMMARY")
    print("="*70)

    print(f"\nResults:")
    print(f"  ✅ Successfully imported: {success_count}")
    print(f"  ❌ Errors: {error_count}")
    print(f"  ⏱️  Time taken: {elapsed/60:.1f} minutes")
    print(f"  📊 Average per episode: {elapsed/max(success_count, 1):.1f} seconds")

    # Final status check
    print(f"\n📊 FINAL STATUS:")
    await get_import_status()

    # Verify some random samples
    print(f"\n🔍 SAMPLE VERIFICATION:")
    sample_episodes = await chunks_collection.aggregate([
        {"$match": {"full_episode_text": {"$exists": True}}},
        {"$group": {"_id": "$episode_id", "text_length": {"$first": {"$strLenCP": "$full_episode_text"}}}},
        {"$sample": {"size": 3}}
    ]).to_list(None)

    for sample in sample_episodes:
        print(f"  Episode {sample['_id'][:12]}...: {sample['text_length']:,} characters")

if __name__ == "__main__":
    asyncio.run(main())
