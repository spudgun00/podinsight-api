#!/usr/bin/env python3
"""
Display synthesis results from the PodInsight API
"""
import requests
import json
import sys

def format_time(seconds):
    """Convert seconds to MM:SS format"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"

def view_synthesis(query: str = "AI valuations", limit: int = 3):
    """Display synthesized answer and search results"""
    url = "https://podinsight-api.vercel.app/api/search"

    print(f"\n🔍 Query: '{query}' (showing {limit} results)")
    print("=" * 80)

    try:
        response = requests.post(
            url,
            json={"query": query, "limit": limit},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()

            # Display synthesized answer
            if "answer" in data and data["answer"]:
                answer = data["answer"]
                print("\n📝 SYNTHESIZED ANSWER:")
                print("-" * 80)
                print(answer["text"])

                # Display citations
                if answer.get("citations"):
                    print("\n📚 CITATIONS:")
                    for citation in answer["citations"]:
                        print(f"\n  ⁽{citation['index']}⁾ {citation['episode_title']}")
                        print(f"      📻 {citation['podcast_name']}")
                        print(f"      ⏱️  {citation['timestamp']} ({format_time(citation['start_seconds'])})")
                        print(f"      📄 \"{citation['chunk_text'][:100]}...\"")

            # Display search results
            print("\n\n🎯 SEARCH RESULTS:")
            print("-" * 80)
            for i, result in enumerate(data["results"], 1):
                print(f"\n{i}. {result['episode_title']}")
                print(f"   📻 {result['podcast_name']}")
                print(f"   📅 {result['published_date']}")
                print(f"   📊 Score: {result['similarity_score']:.3f}")
                print(f"   ⏱️  {format_time(result['timestamp']['start_time'])} - {format_time(result['timestamp']['end_time'])}")
                print(f"   📝 \"{result['excerpt'][:150]}...\"")

            # Display metadata
            print(f"\n\n📊 PERFORMANCE:")
            print("-" * 80)
            print(f"✅ Total results: {data['total_results']}")
            print(f"⏱️  Response time: {data.get('processing_time_ms', 'N/A')}ms")
            print(f"🔍 Search method: {data['search_method']}")
            print(f"💾 Cache hit: {'Yes' if data['cache_hit'] else 'No'}")

        else:
            print(f"❌ Error {response.status_code}: {response.text}")

    except requests.Timeout:
        print("❌ Request timed out after 30 seconds")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Check if query provided as command line argument
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        view_synthesis(query)
    else:
        # Run some example queries
        queries = [
            ("AI valuations", 3),
            ("machine learning healthcare", 2),
            ("venture capital AI investments", 4)
        ]

        for query, limit in queries:
            view_synthesis(query, limit)
            print("\n" + "=" * 80 + "\n")
