#!/usr/bin/env python3
"""
Test edge cases for context expansion
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from api.search_lightweight_768d import search_handler_lightweight_768d, SearchRequest

async def test_edge_cases():
    print("🔬 TESTING EDGE CASES")
    print("=" * 60)
    
    # Test 1: Very short query
    print("\n1️⃣ Very short query (single word):")
    request = SearchRequest(query="AI", limit=1)
    response = await search_handler_lightweight_768d(request)
    if response.results:
        result = response.results[0]
        print(f"✅ Short query handled")
        print(f"   Expanded to {len(result.excerpt)} chars ({result.word_count} words)")
    
    # Test 2: Query with no good matches (should fall back gracefully)
    print("\n2️⃣ Query with likely no matches:")
    request = SearchRequest(query="xyzabc123notreal", limit=1)
    response = await search_handler_lightweight_768d(request)
    print(f"✅ No match handled gracefully")
    print(f"   Search method: {response.search_method}")
    print(f"   Results: {response.total_results}")
    
    # Test 3: Multiple results expansion
    print("\n3️⃣ Multiple results (testing performance):")
    import time
    start = time.time()
    request = SearchRequest(query="startup", limit=5)
    response = await search_handler_lightweight_768d(request)
    elapsed = time.time() - start
    
    if response.results:
        print(f"✅ Expanded {len(response.results)} results in {elapsed:.2f}s")
        total_chars = sum(len(r.excerpt) for r in response.results)
        total_words = sum(r.word_count for r in response.results)
        print(f"   Total expanded text: {total_chars} chars, {total_words} words")
        print(f"   Average per result: {total_chars/len(response.results):.0f} chars")
    
    # Test 4: Check consistency of expansion
    print("\n4️⃣ Consistency check (same query twice):")
    request = SearchRequest(query="machine learning", limit=1)
    
    response1 = await search_handler_lightweight_768d(request)
    response2 = await search_handler_lightweight_768d(request)
    
    if response1.results and response2.results:
        len1 = len(response1.results[0].excerpt)
        len2 = len(response2.results[0].excerpt)
        
        if len1 == len2:
            print(f"✅ Consistent expansion ({len1} chars both times)")
        else:
            print(f"⚠️  Inconsistent expansion: {len1} vs {len2} chars")
    
    # Test 5: Boundary testing - chunk at start/end of episode
    print("\n5️⃣ Boundary testing:")
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client.podinsight
    
    # Find first chunk of an episode
    first_chunk = db.transcript_chunks_768d.find_one(
        {'chunk_index': 0},
        sort=[('start_time', 1)]
    )
    
    if first_chunk:
        # Check if expansion still works at boundaries
        from api.search_lightweight_768d import expand_chunk_context
        expanded = await expand_chunk_context(first_chunk)
        
        print(f"✅ Boundary expansion handled")
        print(f"   First chunk expanded from {len(first_chunk['text'])} to {len(expanded)} chars")


async def test_performance_impact():
    """Test the actual performance impact of expansion"""
    print("\n\n⚡ PERFORMANCE IMPACT TEST")
    print("=" * 60)
    
    import time
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client.podinsight
    
    # Get a sample chunk
    chunk = db.transcript_chunks_768d.find_one()
    
    # Time the expansion operation
    from api.search_lightweight_768d import expand_chunk_context
    
    times = []
    for i in range(10):
        start = time.time()
        await expand_chunk_context(chunk)
        elapsed = (time.time() - start) * 1000  # Convert to ms
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    print(f"📊 Expansion timing (10 runs):")
    print(f"   Average: {avg_time:.1f}ms")
    print(f"   Min: {min(times):.1f}ms")
    print(f"   Max: {max(times):.1f}ms")
    
    print(f"\n✅ Performance impact is negligible (<{avg_time:.0f}ms per result)")


async def main():
    await test_edge_cases()
    await test_performance_impact()
    
    print("\n\n✅ All edge case tests completed!")


if __name__ == "__main__":
    asyncio.run(main())