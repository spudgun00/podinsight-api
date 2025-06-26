import os
import asyncio
import json
import boto3
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = AsyncIOMotorClient(MONGODB_URI)
db = client.podinsight
chunks_collection = db.transcript_chunks_768d

# S3 setup
s3_client = boto3.client('s3')
BUCKET_NAME = 'pod-insights-stage'

# Test with the episode we know has text file
TEST_EPISODE_ID = "1216c2e7-42b8-42ca-92d7-bad784f80af2"
TEST_FEED_SLUG = "a16z-podcast"

async def test_single_episode():
    """Test importing text for a single episode"""
    print("="*50)
    print("TESTING TEXT IMPORT FOR SINGLE EPISODE")
    print("="*50)

    print(f"\nTesting episode: {TEST_FEED_SLUG} / {TEST_EPISODE_ID}")

    # Check if episode exists in MongoDB
    chunks = await chunks_collection.find({"episode_id": TEST_EPISODE_ID}).to_list(None)
    print(f"Found {len(chunks)} chunks in MongoDB for this episode")

    if not chunks:
        print("❌ Episode not found in MongoDB!")
        return

    # Download text file
    s3_key = f"{TEST_FEED_SLUG}/{TEST_EPISODE_ID}/transcripts/{TEST_EPISODE_ID}_text.json"
    print(f"\nDownloading: s3://{BUCKET_NAME}/{s3_key}")

    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        content = response['Body'].read()
        data = json.loads(content)

        print(f"✅ Downloaded text file: {len(content):,} bytes")
        print(f"Keys in data: {list(data.keys())}")

        # Check GUID integrity
        text_guid = data.get('guid')
        text_feed = data.get('feed_slug')

        print(f"\nGUID Verification:")
        print(f"  MongoDB episode_id: {TEST_EPISODE_ID}")
        print(f"  Text file guid: {text_guid}")
        print(f"  Match: {'✅' if text_guid == TEST_EPISODE_ID else '❌'}")

        print(f"\nFeed Verification:")
        print(f"  MongoDB feed_slug: {TEST_FEED_SLUG}")
        print(f"  Text file feed_slug: {text_feed}")
        print(f"  Match: {'✅' if text_feed == TEST_FEED_SLUG else '❌'}")

        # Check text content
        full_text = data.get('text', '')
        if full_text:
            print(f"\nText Content:")
            print(f"  Length: {len(full_text):,} characters")
            print(f"  Words: {len(full_text.split()):,}")
            print(f"  Preview: {full_text[:200]}...")
        else:
            print("❌ No text content found!")
            return

        # Test the update (just for the known episode)
        print(f"\n🧪 TEST UPDATE - Updating {len(chunks)} chunks for verification")

        # Actually update the test episode
        result = await chunks_collection.update_many(
            {"episode_id": TEST_EPISODE_ID},
            {"$set": {
                "full_episode_text": full_text,
                "episode_title_full": data.get('title', f"Episode {TEST_EPISODE_ID[:8]}..."),
                "text_word_count": len(full_text.split()),
                "text_char_count": len(full_text)
            }}
        )

        print(f"✅ Updated {result.modified_count} chunks")

        # Verify the update
        updated_chunk = await chunks_collection.find_one(
            {"episode_id": TEST_EPISODE_ID, "full_episode_text": {"$exists": True}}
        )

        if updated_chunk:
            print(f"✅ Verification: Found chunk with full_episode_text")
            print(f"   Text length: {len(updated_chunk['full_episode_text']):,} chars")
            print(f"   Title: {updated_chunk.get('episode_title_full', 'N/A')}")
        else:
            print("❌ Verification failed: No chunks found with full_episode_text")

    except Exception as e:
        print(f"❌ Error: {e}")

async def test_a_few_episodes():
    """Test a few episodes to see pattern"""
    print("\n" + "="*50)
    print("TESTING A FEW EPISODES FOR PATTERN")
    print("="*50)

    # Get 5 random episodes
    pipeline = [
        {"$group": {"_id": "$episode_id", "feed_slug": {"$first": "$feed_slug"}}},
        {"$sample": {"size": 5}}
    ]

    episodes = await chunks_collection.aggregate(pipeline).to_list(None)

    for episode in episodes:
        episode_id = episode['_id']
        feed_slug = episode['feed_slug']

        print(f"\nChecking: {feed_slug} / {episode_id[:12]}...")

        # Check if text file exists
        s3_key = f"{feed_slug}/{episode_id}/transcripts/{episode_id}_text.json"

        try:
            response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
            content = response['Body'].read()
            data = json.loads(content)

            text_length = len(data.get('text', ''))
            print(f"  ✅ Text file found: {text_length:,} chars")
            print(f"     GUID match: {'✅' if data.get('guid') == episode_id else '❌'}")

        except s3_client.exceptions.NoSuchKey:
            print(f"  ❌ Text file not found")
        except Exception as e:
            print(f"  ⚠️  Error: {e}")

async def main():
    # Run both tests automatically
    await test_single_episode()
    await test_a_few_episodes()

if __name__ == "__main__":
    asyncio.run(main())
