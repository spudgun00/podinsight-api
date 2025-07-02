#!/usr/bin/env python3
"""
Diagnose 500 error in audio API
Tests each component to identify the failure point
"""
import os
import sys
import httpx
import asyncio
from dotenv import load_dotenv
from pymongo import MongoClient
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

async def diagnose_audio_api():
    print("🔍 Diagnosing Audio API 500 Error\n")

    # 1. Check environment variables
    print("1️⃣ Checking Environment Variables:")
    mongodb_uri = os.environ.get("MONGODB_URI")
    lambda_url = os.environ.get("AUDIO_LAMBDA_URL")
    lambda_key = os.environ.get("AUDIO_LAMBDA_API_KEY")

    print(f"   MONGODB_URI: {'✅ Set' if mongodb_uri else '❌ NOT SET'}")
    print(f"   AUDIO_LAMBDA_URL: {'✅ Set' if lambda_url else '❌ NOT SET'}")
    print(f"   AUDIO_LAMBDA_API_KEY: {'✅ Set' if lambda_key else '❌ NOT SET'}")

    if not mongodb_uri or not lambda_url:
        print("\n❌ Missing required environment variables!")
        return

    # 2. Test MongoDB connection
    print("\n2️⃣ Testing MongoDB Connection:")
    try:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        # Force connection
        client.server_info()
        print("   ✅ MongoDB connection successful")

        # Check database and collections
        db = client.podinsight
        collections = db.list_collection_names()
        print(f"   ✅ Database 'podinsight' accessible")
        print(f"   ✅ Collections found: {len(collections)}")

        # Check specific collections
        has_chunks = "transcript_chunks_768d" in collections
        has_episodes = "episode_metadata" in collections
        print(f"   {'✅' if has_chunks else '❌'} transcript_chunks_768d collection exists")
        print(f"   {'✅' if has_episodes else '❌'} episode_metadata collection exists")

    except Exception as e:
        print(f"   ❌ MongoDB connection failed: {str(e)}")
        return

    # 3. Test sample episode lookup
    print("\n3️⃣ Testing Episode Data:")
    test_cases = [
        ("GUID", "673b06c4-cf90-11ef-b9e1-0b761165641d"),
        ("ObjectId", "685ba776e4f9ec2f0756267a"),  # pragma: allowlist secret
        ("Substack", "substack:post:162914366"),
        ("Flightcast", "flightcast:01JV6G3ACFK3J2T4C4KSAYSBX5")
    ]

    for test_type, episode_id in test_cases:
        print(f"\n   Testing {test_type} format: {episode_id}")

        try:
            # For ObjectId, need to look up GUID first
            if len(episode_id) == 24:
                from bson import ObjectId
                episode = db.episode_metadata.find_one(
                    {"_id": ObjectId(episode_id)},
                    {"guid": 1}
                )
                if episode:
                    guid = episode.get("guid")
                    print(f"   ✅ ObjectId -> GUID: {guid}")
                else:
                    print(f"   ❌ ObjectId not found in episode_metadata")
                    continue
            else:
                guid = episode_id

            # Look up feed_slug
            chunk = db.transcript_chunks_768d.find_one(
                {"episode_id": guid},
                {"feed_slug": 1}
            )

            if chunk:
                feed_slug = chunk.get("feed_slug")
                if feed_slug:
                    print(f"   ✅ Found feed_slug: {feed_slug}")
                else:
                    print(f"   ❌ Episode has no feed_slug!")
            else:
                print(f"   ❌ No transcript chunks found for this episode")

        except Exception as e:
            print(f"   ❌ Error during lookup: {str(e)}")

    # 4. Test Lambda connectivity
    print("\n4️⃣ Testing Lambda Function:")
    headers = {}
    if lambda_key:
        headers["x-api-key"] = lambda_key

    # Test with a known working episode
    test_payload = {
        "feed_slug": "unchained",
        "guid": "022f8502-14c3-11f0-9b7c-bf77561f0071",
        "start_time_ms": 30000,
        "duration_ms": 30000
    }

    print(f"   Testing Lambda with: {test_payload['feed_slug']}/{test_payload['guid']}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                lambda_url,
                json=test_payload,
                headers=headers
            )

        print(f"   Lambda response status: {response.status_code}")

        if response.status_code == 200:
            print("   ✅ Lambda call successful")
            result = response.json()
            print(f"   ✅ Got clip URL: {result.get('clip_url', 'No URL in response')[:50]}...")
        else:
            print(f"   ❌ Lambda error: {response.text}")

    except httpx.TimeoutException:
        print("   ❌ Lambda timeout (>30 seconds)")
    except Exception as e:
        print(f"   ❌ Lambda call failed: {str(e)}")

    # 5. Test full API endpoint
    print("\n5️⃣ Testing Full Audio API Endpoint:")
    api_url = "https://podinsight-api.vercel.app/api/v1/audio_clips"

    for test_type, episode_id in test_cases[:2]:  # Test first 2 cases
        print(f"\n   Testing {test_type}: {episode_id}")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_url}/{episode_id}",
                    params={"start_time_ms": 30000}
                )

            print(f"   Response status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Success!")
            else:
                print(f"   ❌ Error: {response.text}")

        except Exception as e:
            print(f"   ❌ Request failed: {str(e)}")

    print("\n📋 Diagnosis Complete!")

if __name__ == "__main__":
    asyncio.run(diagnose_audio_api())
