#!/usr/bin/env python3
"""
Test MongoDB search handler functionality
"""

import asyncio
import time
from api.mongodb_search import MongoSearchHandler
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

async def test_search_handler():
    """Run comprehensive tests on MongoDB search"""

    print("🧪 Testing MongoDB Search Handler\n")

    # Initialize handler
    handler = MongoSearchHandler()

    if handler.db is None:
        print("❌ MongoDB not connected - check MONGODB_URI")
        return

    # Test 1: Basic search
    print("Test 1: Basic search for 'AI agents'")
    start = time.time()
    results = await handler.search_transcripts("AI agents", limit=5)
    elapsed = time.time() - start

    print(f"✅ Found {len(results)} results in {elapsed:.2f}s")
    if results:
        print(f"   Top result: {results[0]['podcast_name']} - Score: {results[0]['relevance_score']:.2f}")
        print(f"   Excerpt preview: {results[0]['excerpt'][:100]}...")

    # Test 2: Verify real excerpts
    print("\nTest 2: Verify excerpts contain search terms")
    if results:
        excerpt = results[0]['excerpt']
        if '**AI**' in excerpt or '**agents**' in excerpt:
            print("✅ Search terms are highlighted in excerpt")
        else:
            print("⚠️  Search terms not highlighted")

        if '...' in excerpt:
            print("✅ Excerpt properly truncated with ellipsis")

    # Test 3: Different queries
    print("\nTest 3: Testing various queries")
    test_queries = [
        "venture capital",
        "GPT-4",
        "cryptocurrency",
        "startup funding"
    ]

    for query in test_queries:
        results = await handler.search_transcripts(query, limit=3)
        print(f"   '{query}': {len(results)} results")
        if results:
            print(f"      Top score: {results[0]['relevance_score']:.2f}")

    # Test 4: Cache performance
    print("\nTest 4: Cache performance")
    start = time.time()
    results1 = await handler.search_transcripts("blockchain", limit=5)
    time1 = time.time() - start

    start = time.time()
    results2 = await handler.search_transcripts("blockchain", limit=5)
    time2 = time.time() - start

    print(f"   First query: {time1:.3f}s")
    print(f"   Cached query: {time2:.3f}s")
    if time2 < time1 / 2:
        print("✅ Cache is working effectively")

    # Test 5: Excerpt extraction
    print("\nTest 5: Excerpt extraction")
    test_text = "This is a long discussion about artificial intelligence and how AI agents are transforming the software development landscape. We explore various aspects of machine learning and deep learning technologies."

    excerpt = handler.extract_excerpt(test_text, "AI agents", max_words=20)
    print(f"   Original: {len(test_text)} chars")
    print(f"   Excerpt: {excerpt}")
    if "**AI agents**" in excerpt:
        print("✅ Terms properly highlighted")

    # Test 6: Episode retrieval
    print("\nTest 6: Get episode by ID")
    if results:
        episode_id = results[0]['episode_id']
        episode = await handler.get_episode_by_id(episode_id)
        if episode:
            print(f"✅ Retrieved episode: {episode.get('podcast_name', 'Unknown')}")
            print(f"   Word count: {episode.get('word_count', 0)}")
            print(f"   Has segments: {'segments' in episode}")

    # Test 7: Timestamp extraction
    print("\nTest 7: Timestamp extraction")
    if results and results[0].get('timestamp'):
        ts = results[0]['timestamp']
        print(f"✅ Found timestamp: {ts['start_time']:.1f}s - {ts['end_time']:.1f}s")
    else:
        print("⚠️  No timestamp found (segments may not have speaker labels)")

    await handler.close()
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_search_handler())
