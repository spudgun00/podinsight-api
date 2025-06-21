#!/usr/bin/env python3
"""
Test context expansion on vector search results only
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from api.search_lightweight_768d import search_handler_lightweight_768d, SearchRequest

async def test_vector_search_expansion():
    """Test queries that should use vector search"""
    
    # These queries have worked well with vector search
    queries = [
        "confidence with humility",
        "AI automation",
        "venture capital returns",
        "founder psychology"
    ]
    
    print("🔍 TESTING VECTOR SEARCH WITH CONTEXT EXPANSION")
    print("=" * 60)
    
    for query in queries:
        print(f"\n{'='*50}")
        print(f"Query: '{query}'")
        print('='*50)
        
        request = SearchRequest(query=query, limit=1, offset=0)
        
        try:
            response = await search_handler_lightweight_768d(request)
            
            if response.results and response.search_method == "vector_768d":
                result = response.results[0]
                
                print(f"\n✅ Vector search successful!")
                print(f"📻 Podcast: {result.podcast_name}")
                print(f"⭐ Score: {result.similarity_score:.3f}")
                print(f"⏱️  Timestamp: {result.timestamp['start_time']:.1f}s - {result.timestamp['end_time']:.1f}s")
                
                # Check expansion quality
                print(f"\n📊 Expansion Statistics:")
                print(f"   Characters: {len(result.excerpt)}")
                print(f"   Words (correct count): {len(result.excerpt.split())}")
                print(f"   Words (from API): {result.word_count}")
                
                # Check if original search term appears
                term_count = result.excerpt.lower().count(query.split()[0].lower())
                print(f"   Search term '{query.split()[0]}' appears: {term_count} times")
                
                # Show the context
                print(f"\n📝 Expanded Context:")
                print("-" * 50)
                # Show in chunks for readability
                words = result.excerpt.split()
                for i in range(0, len(words), 15):
                    chunk = ' '.join(words[i:i+15])
                    print(f"   {chunk}")
                print("-" * 50)
                
            elif response.search_method != "vector_768d":
                print(f"\n⚠️  Fell back to {response.search_method} search")
            else:
                print("\n❌ No results found")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


async def check_single_chunk_expansion():
    """Directly test the expansion logic"""
    
    print("\n\n🔬 DIRECT EXPANSION TEST")
    print("=" * 60)
    
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client.podinsight
    
    # Get a chunk we know exists
    chunk = db.transcript_chunks_768d.find_one({
        'text': {'$regex': 'confidence', '$options': 'i'}
    })
    
    if chunk:
        print(f"\n📍 Found chunk:")
        print(f"   Episode: {chunk['episode_id']}")
        print(f"   Time: {chunk['start_time']:.1f}s - {chunk['end_time']:.1f}s")
        print(f"   Original text: '{chunk['text']}'")
        
        # Manually fetch context
        context_seconds = 20.0
        surrounding = list(db.transcript_chunks_768d.find({
            'episode_id': chunk['episode_id'],
            'start_time': {
                '$gte': chunk['start_time'] - context_seconds,
                '$lte': chunk['end_time'] + context_seconds
            }
        }).sort('start_time', 1))
        
        print(f"\n📊 Found {len(surrounding)} chunks in ±{context_seconds}s window")
        
        # Show time coverage
        if surrounding:
            time_span = surrounding[-1]['end_time'] - surrounding[0]['start_time']
            print(f"   Time span covered: {time_span:.1f} seconds")
            print(f"   From {surrounding[0]['start_time']:.1f}s to {surrounding[-1]['end_time']:.1f}s")
            
            # Concatenate
            texts = [c['text'].strip() for c in surrounding]
            expanded = ' '.join(texts)
            
            print(f"\n📝 Expanded text ({len(expanded)} chars, {len(expanded.split())} words):")
            print("-" * 50)
            print(expanded)
            print("-" * 50)


async def main():
    await test_vector_search_expansion()
    await check_single_chunk_expansion()


if __name__ == "__main__":
    asyncio.run(main())