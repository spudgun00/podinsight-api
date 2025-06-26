import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import time

load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = AsyncIOMotorClient(MONGODB_URI)
db = client.podinsight
chunks_collection = db.transcript_chunks_768d

async def check_current_damage():
    """Check how much duplicated data we have"""
    print("="*60)
    print("CHECKING CURRENT STORAGE DAMAGE")
    print("="*60)

    # Count chunks with duplicated text
    chunks_with_text = await chunks_collection.count_documents({"full_episode_text": {"$exists": True}})
    total_chunks = await chunks_collection.count_documents({})

    print(f"Total chunks: {total_chunks:,}")
    print(f"Chunks with duplicated text: {chunks_with_text:,}")
    print(f"Percentage affected: {chunks_with_text/total_chunks*100:.1f}%")

    # Sample a few to estimate size
    sample = await chunks_collection.find_one({"full_episode_text": {"$exists": True}})
    if sample:
        text_size = len(sample.get('full_episode_text', ''))
        estimated_waste = chunks_with_text * text_size
        print(f"\nEstimated duplicated data:")
        print(f"  Sample text size: {text_size:,} bytes")
        print(f"  Total duplicated: {estimated_waste/1024/1024:.1f} MB")
        print(f"  Storage waste: ~{estimated_waste/1024/1024/1024:.1f} GB")

    return chunks_with_text

async def remove_duplicated_fields():
    """Remove the duplicated text fields from all chunks"""
    print("\n" + "="*60)
    print("REMOVING DUPLICATED FIELDS")
    print("="*60)

    print("⚠️  This will remove the following fields from ALL chunks:")
    print("   - full_episode_text")
    print("   - episode_title_full")
    print("   - text_word_count")
    print("   - text_char_count")
    print("   - text_imported_at")

    # DRY RUN first
    print("\n🧪 DRY RUN - Checking what would be removed...")

    # Count affected documents
    affected = await chunks_collection.count_documents({
        "$or": [
            {"full_episode_text": {"$exists": True}},
            {"episode_title_full": {"$exists": True}},
            {"text_word_count": {"$exists": True}},
            {"text_char_count": {"$exists": True}},
            {"text_imported_at": {"$exists": True}}
        ]
    })

    print(f"Documents that would be modified: {affected:,}")

    if affected == 0:
        print("✅ No duplicated fields found - nothing to clean!")
        return True

    print(f"\n⚠️  CRITICAL: This will modify {affected:,} documents!")
    print("This action cannot be undone!")

    # WAIT - let user confirm this is safe
    print("\n" + "="*60)
    print("CONFIRMATION REQUIRED")
    print("="*60)
    print("This script will:")
    print("1. Remove duplicated text fields from chunks")
    print("2. Free up significant storage space")
    print("3. NOT affect the original chunk text or embeddings")
    print("4. NOT affect search functionality")

    return False  # Don't proceed automatically

async def execute_cleanup():
    """Execute the actual cleanup - ONLY if explicitly called"""
    print("\n🔥 EXECUTING CLEANUP...")

    start_time = time.time()

    # Remove the duplicated fields
    result = await chunks_collection.update_many(
        {},
        {"$unset": {
            "full_episode_text": "",
            "episode_title_full": "",
            "text_word_count": "",
            "text_char_count": "",
            "text_imported_at": ""
        }}
    )

    elapsed = time.time() - start_time

    print(f"✅ Cleanup complete!")
    print(f"   Modified documents: {result.modified_count:,}")
    print(f"   Time taken: {elapsed:.1f} seconds")

    # Verify cleanup
    remaining = await chunks_collection.count_documents({"full_episode_text": {"$exists": True}})
    if remaining == 0:
        print(f"✅ Verification: No duplicated fields remain")
    else:
        print(f"⚠️  Warning: {remaining} documents still have duplicated fields")

    return True

async def main():
    print("EMERGENCY CLEANUP - DUPLICATED TEXT FIELDS")
    print("This script will remove storage-wasting duplicated data")

    # Check the damage
    affected_chunks = await check_current_damage()

    if affected_chunks == 0:
        print("\n✅ No cleanup needed!")
        return

    # Show what we'll do (but don't execute)
    await remove_duplicated_fields()

    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("1. Review the output above")
    print("2. If you want to proceed, run:")
    print("   python emergency_cleanup.py --execute")
    print("3. This will free up the duplicated storage")

if __name__ == "__main__":
    import sys
    if "--execute" in sys.argv:
        asyncio.run(execute_cleanup())
    else:
        asyncio.run(main())
