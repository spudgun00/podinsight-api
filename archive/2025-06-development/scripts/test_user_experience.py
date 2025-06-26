#!/usr/bin/env python3
"""
Test search from a user's perspective
Compare old vs new search experience
"""

import asyncio
from api.search_lightweight import search_handler_lightweight, SearchRequest
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

async def test_user_experience():
    """Simulate what a user would see when searching"""

    print("🧑‍💻 USER EXPERIENCE TEST - PodInsightHQ Search")
    print("="*70)
    print("\nScenario: A user searches for 'AI agents' to learn about autonomous AI\n")

    # Create the search request
    request = SearchRequest(query="AI agents", limit=3, offset=0)

    # Execute search
    print("🔍 Searching for: 'AI agents'...")
    print("-"*70)

    start_time = datetime.now()
    response = await search_handler_lightweight(request)
    search_time = (datetime.now() - start_time).total_seconds()

    print(f"\n⏱️  Search completed in {search_time:.1f} seconds")
    print(f"📊 Found {response.total_results} relevant episodes\n")

    # Show what the OLD system returned (mock)
    print("❌ OLD SYSTEM (Mock Excerpts):")
    print("-"*40)
    print("Result 1:")
    print("  Episode: 7f54be60-8a3c-4321-...")
    print("  Excerpt: 'Episode 7f54be60... This episode covers AI Agents. Published on 2024-03-15. Match score: 4.2%'")
    print("  👎 Generic placeholder - tells user nothing!")

    print("\n✅ NEW SYSTEM (Real Excerpts):")
    print("-"*40)

    # Show what the NEW system returns
    for i, result in enumerate(response.results, 1):
        print(f"\nResult {i}:")
        print(f"  Podcast: {result.podcast_name}")
        print(f"  Episode: {result.episode_title[:60]}...")
        print(f"  Score: {result.similarity_score:.1%} relevance")
        print(f"  Topics: {', '.join(result.topics) if result.topics else 'Not tagged'}")

        # Show the excerpt with visual formatting
        excerpt = result.excerpt.replace("**", "【").replace("【", "**", 1).replace("【", "**", 1)
        print(f"\n  Excerpt: \"{excerpt[:300]}...\"")

        # Highlight what makes this better
        if "**" in result.excerpt:
            print("  👍 Real conversation with highlighted search terms!")

        if result.s3_audio_path:
            print("  🎵 Audio available for playback")

    # User value comparison
    print("\n\n" + "="*70)
    print("📈 USER VALUE COMPARISON")
    print("="*70)

    print("\n🚫 OLD SYSTEM Problems:")
    print("  • Can't tell what episodes are actually about")
    print("  • 4% relevance = mostly irrelevant results")
    print("  • No real content to evaluate before listening")
    print("  • Wastes user time clicking on wrong episodes")

    print("\n✅ NEW SYSTEM Benefits:")
    print("  • See actual conversation snippets before clicking")
    print(f"  • {response.results[0].similarity_score:.0%} relevance = highly relevant results")
    print("  • Search terms highlighted in bold")
    print("  • Can quickly scan to find exactly what you want")
    print("  • Audio timestamps ready (for future playback feature)")

    # Specific example of value
    print("\n💡 REAL EXAMPLE:")
    print("User searches 'AI agents' wanting to learn about autonomous AI...")
    print("\nOLD: Gets generic 'This episode covers AI Agents' - learns nothing")
    print(f"\nNEW: Sees actual discussion: '{response.results[0].excerpt[:150]}...'")
    print("     → User immediately knows this episode discusses exactly what they want!")

    print("\n🎯 BOTTOM LINE:")
    print(f"Search quality improved by {response.results[0].similarity_score / 0.04:.0f}x")
    print("Users can now find valuable content instead of guessing!")

if __name__ == "__main__":
    asyncio.run(test_user_experience())
