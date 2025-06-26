import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import time

load_dotenv()

# MongoDB connection with longer timeout
MONGODB_URI = os.getenv("MONGODB_URI")
client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=60000, connectTimeoutMS=60000, socketTimeoutMS=60000)
db = client.podinsight
chunks_collection = db.transcript_chunks_768d

async def emergency_cleanup():
    """Execute immediate cleanup without checks"""
    print("🔥 EMERGENCY CLEANUP - NO VERIFICATION")
    print("Removing duplicated fields immediately...")

    try:
        # Direct cleanup operation
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

        print(f"✅ Modified {result.modified_count:,} documents")
        print("Storage space should now be recovered!")

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        print("You may need to use MongoDB Compass or wait for cluster recovery")

if __name__ == "__main__":
    asyncio.run(emergency_cleanup())
