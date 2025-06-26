#!/usr/bin/env python3
"""
Test the full API flow exactly as it happens in production
"""

import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from supabase import create_client, Client
import aiohttp
import time

async def test_full_flow():
    """Test the complete search flow"""

    query = "AI startup valuations"
    limit = 5

    # Step 1: Generate embedding
    print(f"🔍 Testing search for: '{query}'")
    print("=" * 60)
    print("\n1️⃣ GENERATING EMBEDDING")

    modal_url = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"
    async with aiohttp.ClientSession() as session:
        start = time.time()
        async with session.post(modal_url, json={"text": query}) as response:
            if response.status != 200:
                print(f"❌ Modal failed: {response.status}")
                return
            modal_data = await response.json()
            embedding = modal_data["embedding"]
            print(f"✅ Got {len(embedding)}D embedding in {(time.time()-start)*1000:.0f}ms")

    # Step 2: MongoDB Vector Search
    print("\n2️⃣ MONGODB VECTOR SEARCH")
    mongodb_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongodb_uri)
    db = client.podinsight
    collection = db.transcript_chunks_768d

    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index_768d",
                "path": "embedding_768d",
                "queryVector": embedding,
                "numCandidates": 100,
                "limit": limit,
                "filter": {}
            }
        },
        {"$limit": limit},
        {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
        {"$match": {"score": {"$exists": True, "$ne": None}}},
        {
            "$project": {
                "episode_id": 1,
                "feed_slug": 1,
                "chunk_index": 1,
                "text": 1,
                "start_time": 1,
                "end_time": 1,
                "speaker": 1,
                "score": 1
            }
        }
    ]

    start = time.time()
    cursor = collection.aggregate(pipeline)
    chunks = await cursor.to_list(None)
    print(f"✅ Found {len(chunks)} chunks in {(time.time()-start)*1000:.0f}ms")

    if not chunks:
        print("❌ No chunks found!")
        client.close()
        return

    # Show chunk details
    episode_guids = list(set(chunk['episode_id'] for chunk in chunks))
    print(f"📊 Unique episodes: {len(episode_guids)}")
    for guid in episode_guids[:3]:
        print(f"   - {guid}")

    # Step 3: Supabase Enrichment
    print("\n3️⃣ SUPABASE ENRICHMENT")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not all([supabase_url, supabase_key]):
        print("❌ Missing Supabase credentials")
        client.close()
        return

    supabase: Client = create_client(supabase_url, supabase_key)

    # Query exactly as the API does
    print(f"🔍 Looking up {len(episode_guids)} episodes in Supabase...")
    start = time.time()
    result = supabase.table('episodes').select('*').in_('guid', episode_guids).execute()
    print(f"✅ Found {len(result.data)} episodes in {(time.time()-start)*1000:.0f}ms")

    # Create lookup dict
    episodes = {}
    for episode in result.data:
        episodes[episode['guid']] = episode
        print(f"   - {episode['guid']}: {episode.get('episode_title', 'Unknown')[:30]}...")

    # Step 4: Enrichment Process
    print("\n4️⃣ ENRICHMENT PROCESS")
    enriched = []
    for chunk in chunks:
        episode_guid = chunk['episode_id']
        if episode_guid in episodes:
            episode = episodes[episode_guid]
            enriched_chunk = {
                **chunk,
                'podcast_name': episode.get('podcast_name', chunk.get('feed_slug', 'Unknown')),
                'episode_title': episode.get('episode_title', 'Unknown Episode'),
                'published_at': episode.get('published_at'),
                'topics': [],
                's3_audio_path': episode.get('s3_audio_path'),
                'duration_seconds': episode.get('duration_seconds', 0)
            }
            enriched.append(enriched_chunk)
            print(f"✅ Enriched chunk from episode: {episode.get('episode_title', 'Unknown')[:30]}...")
        else:
            print(f"❌ Episode not found in Supabase: {episode_guid}")

    print(f"\n📊 FINAL RESULTS:")
    print(f"   MongoDB chunks: {len(chunks)}")
    print(f"   Supabase episodes: {len(result.data)}")
    print(f"   Enriched results: {len(enriched)}")

    # Step 5: Format results (pagination)
    print("\n5️⃣ PAGINATION")
    offset = 0
    limit = 3
    paginated_results = enriched[offset:offset + limit]
    print(f"   Returning {len(paginated_results)} results (offset={offset}, limit={limit})")

    client.close()

    # Final output
    print("\n✅ SEARCH COMPLETE")
    print(f"   Total results: {len(enriched)}")
    print(f"   Returned results: {len(paginated_results)}")

    if paginated_results:
        print("\n📋 Results:")
        for i, result in enumerate(paginated_results):
            print(f"\n{i+1}. {result['episode_title']}")
            print(f"   Podcast: {result['podcast_name']}")
            print(f"   Score: {result['score']:.2%}")
            print(f"   Text: {result['text'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test_full_flow())
