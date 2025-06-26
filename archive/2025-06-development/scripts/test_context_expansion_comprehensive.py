#!/usr/bin/env python3
"""
Comprehensive testing of context expansion feature
"""

import asyncio
import time
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

from api.search_lightweight_768d import search_handler_lightweight_768d, SearchRequest

async def test_various_queries():
    """Test different types of queries to ensure context expansion works"""

    test_cases = [
        # (query, description)
        ("AI venture capital", "Technical/business term"),
        ("confidence with humility", "Abstract concept"),
        ("what makes a great founder", "Question-based search"),
        ("DePIN infrastructure", "Acronym/technical term"),
        ("2025", "Date/number search"),
        ("you know", "Common filler phrase"),
    ]

    results_summary = defaultdict(list)

    print("🧪 COMPREHENSIVE CONTEXT EXPANSION TEST")
    print("=" * 80)

    for query, description in test_cases:
        print(f"\n{'='*60}")
        print(f"📍 Test Case: {description}")
        print(f"🔍 Query: '{query}'")
        print('='*60)

        start_time = time.time()
        request = SearchRequest(query=query, limit=2, offset=0)

        try:
            response = await search_handler_lightweight_768d(request)
            elapsed = time.time() - start_time

            print(f"\n⏱️  Search time: {elapsed:.2f}s")
            print(f"📊 Total results: {response.total_results}")
            print(f"🔧 Method: {response.search_method}")

            if response.results:
                for i, result in enumerate(response.results):
                    print(f"\n--- Result {i+1} ---")
                    print(f"📻 {result.podcast_name}")
                    print(f"⭐ Score: {result.similarity_score:.3f}")
                    print(f"⏰ Timestamp: {result.timestamp['start_time']:.1f}s")

                    # Analyze the expansion
                    excerpt_len = len(result.excerpt)
                    word_count = result.word_count

                    print(f"\n📈 Context Expansion Stats:")
                    print(f"   Characters: {excerpt_len}")
                    print(f"   Words: {word_count}")
                    print(f"   Avg word length: {excerpt_len/word_count if word_count > 0 else 0:.1f} chars")

                    # Show a preview
                    print(f"\n📝 Preview (first 200 chars):")
                    print(f"   \"{result.excerpt[:200]}...\"")

                    # Track stats
                    results_summary['char_lengths'].append(excerpt_len)
                    results_summary['word_counts'].append(word_count)
                    results_summary['scores'].append(result.similarity_score)
            else:
                print("\n❌ No results found")
                results_summary['no_results'].append(query)

        except Exception as e:
            print(f"\n❌ Error: {e}")
            results_summary['errors'].append((query, str(e)))

    # Print summary statistics
    print("\n" + "="*80)
    print("📊 SUMMARY STATISTICS")
    print("="*80)

    if results_summary['char_lengths']:
        avg_chars = sum(results_summary['char_lengths']) / len(results_summary['char_lengths'])
        avg_words = sum(results_summary['word_counts']) / len(results_summary['word_counts'])
        avg_score = sum(results_summary['scores']) / len(results_summary['scores'])

        print(f"\n📈 Average expanded excerpt:")
        print(f"   Characters: {avg_chars:.0f}")
        print(f"   Words: {avg_words:.0f}")
        print(f"   Similarity score: {avg_score:.3f}")

        print(f"\n📊 Range of expansions:")
        print(f"   Min chars: {min(results_summary['char_lengths'])}")
        print(f"   Max chars: {max(results_summary['char_lengths'])}")
        print(f"   Min words: {min(results_summary['word_counts'])}")
        print(f"   Max words: {max(results_summary['word_counts'])}")

    if results_summary['no_results']:
        print(f"\n⚠️  Queries with no results: {results_summary['no_results']}")

    if results_summary['errors']:
        print(f"\n❌ Queries with errors: {results_summary['errors']}")


async def test_edge_cases():
    """Test edge cases for context expansion"""

    print("\n\n🔬 EDGE CASE TESTING")
    print("=" * 80)

    # Test 1: Very long query
    print("\n1️⃣ Testing very long query...")
    long_query = "What are the most important considerations when building a venture capital firm focused on artificial intelligence and machine learning startups in the current market environment"
    request = SearchRequest(query=long_query[:500], limit=1)  # Truncate to max length

    try:
        response = await search_handler_lightweight_768d(request)
        if response.results:
            print(f"✅ Handled long query successfully")
            print(f"   Result word count: {response.results[0].word_count}")
    except Exception as e:
        print(f"❌ Failed on long query: {e}")

    # Test 2: Special characters
    print("\n2️⃣ Testing special characters...")
    special_query = "AI & ML: what's next?"
    request = SearchRequest(query=special_query, limit=1)

    try:
        response = await search_handler_lightweight_768d(request)
        print(f"✅ Handled special characters successfully")
    except Exception as e:
        print(f"❌ Failed on special characters: {e}")

    # Test 3: Pagination
    print("\n3️⃣ Testing pagination...")
    request1 = SearchRequest(query="startup", limit=2, offset=0)
    request2 = SearchRequest(query="startup", limit=2, offset=2)

    try:
        response1 = await search_handler_lightweight_768d(request1)
        response2 = await search_handler_lightweight_768d(request2)

        # Check that results are different
        if response1.results and response2.results:
            ids1 = {r.episode_id for r in response1.results}
            ids2 = {r.episode_id for r in response2.results}

            if ids1.isdisjoint(ids2):
                print(f"✅ Pagination working correctly")
            else:
                print(f"⚠️  Pagination may have overlapping results")
    except Exception as e:
        print(f"❌ Failed on pagination: {e}")


async def test_performance():
    """Test performance with multiple concurrent searches"""

    print("\n\n⚡ PERFORMANCE TESTING")
    print("=" * 80)

    queries = ["AI", "startup", "venture", "founder", "investment"]

    # Sequential test
    print("\n📊 Sequential searches:")
    start = time.time()
    for query in queries:
        request = SearchRequest(query=query, limit=1)
        await search_handler_lightweight_768d(request)
    sequential_time = time.time() - start
    print(f"   Total time: {sequential_time:.2f}s")
    print(f"   Avg per search: {sequential_time/len(queries):.2f}s")

    # Concurrent test
    print("\n📊 Concurrent searches:")
    start = time.time()
    tasks = [
        search_handler_lightweight_768d(SearchRequest(query=query, limit=1))
        for query in queries
    ]
    await asyncio.gather(*tasks)
    concurrent_time = time.time() - start
    print(f"   Total time: {concurrent_time:.2f}s")
    print(f"   Speedup: {sequential_time/concurrent_time:.1f}x")


async def test_context_quality():
    """Test the quality of context expansion"""

    print("\n\n📖 CONTEXT QUALITY TESTING")
    print("=" * 80)

    # Search for something specific and check if context makes sense
    request = SearchRequest(query="data entry", limit=1)
    response = await search_handler_lightweight_768d(request)

    if response.results:
        result = response.results[0]
        print(f"\n🔍 Query: 'data entry'")
        print(f"📍 Found at: {result.timestamp['start_time']:.1f}s")

        # Check if the expanded text contains the search term
        search_term_count = result.excerpt.lower().count("data entry")
        print(f"\n✅ Search term appears {search_term_count} time(s) in expanded context")

        # Check coherence by looking for sentence markers
        sentences = [s.strip() for s in result.excerpt.split('.') if s.strip()]
        print(f"📝 Approximate sentences in context: {len(sentences)}")

        # Check if context seems continuous (no huge jumps)
        print(f"\n📊 Context quality indicators:")
        print(f"   - Has punctuation: {'.' in result.excerpt}")
        print(f"   - Has speaker changes: {'?' in result.excerpt or '!' in result.excerpt}")
        print(f"   - Average sentence length: {len(result.excerpt)/len(sentences) if sentences else 0:.0f} chars")

        # Show the full context for manual inspection
        print(f"\n📄 Full expanded context ({result.word_count} words):")
        print("-" * 60)
        print(result.excerpt)
        print("-" * 60)


async def main():
    """Run all tests"""

    print("🚀 Starting Comprehensive Context Expansion Tests")
    print("=" * 80)

    # Run different test suites
    await test_various_queries()
    await test_edge_cases()
    await test_performance()
    await test_context_quality()

    print("\n\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
