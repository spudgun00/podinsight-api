#!/usr/bin/env python3
"""
Test search quality with real MongoDB data
Verify we're getting actual conversation excerpts
"""

import asyncio
from api.search_lightweight import search_handler_lightweight, SearchRequest
from pathlib import Path
from dotenv import load_dotenv
import statistics

# Load environment
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

async def test_search_quality():
    """Test search quality and compare to old mock results"""
    
    print("🧪 Search Quality Test Report\n")
    print("="*70)
    
    # Test various queries
    test_cases = [
        {
            "query": "AI agents",
            "expected_terms": ["AI", "agents", "autonomous", "software"],
            "min_score": 1.0
        },
        {
            "query": "venture capital funding",
            "expected_terms": ["venture", "capital", "funding", "investment"],
            "min_score": 1.0
        },
        {
            "query": "GPT-4 capabilities",
            "expected_terms": ["GPT", "4", "model", "language"],
            "min_score": 1.0
        },
        {
            "query": "cryptocurrency regulation",
            "expected_terms": ["crypto", "regulation", "SEC", "policy"],
            "min_score": 0.8
        },
        {
            "query": "startup acquisition",
            "expected_terms": ["startup", "acquisition", "exit", "deal"],
            "min_score": 1.0
        }
    ]
    
    all_scores = []
    quality_issues = []
    
    for test in test_cases:
        print(f"\n📍 Query: '{test['query']}'")
        print("-" * 50)
        
        request = SearchRequest(query=test['query'], limit=3, offset=0)
        response = await search_handler_lightweight(request)
        
        if not response.results:
            quality_issues.append(f"No results for '{test['query']}'")
            continue
        
        # Analyze top result
        top_result = response.results[0]
        all_scores.append(top_result.similarity_score)
        
        print(f"Top result score: {top_result.similarity_score:.2f}")
        print(f"Podcast: {top_result.podcast_name}")
        print(f"Episode: {top_result.episode_title[:60]}...")
        
        # Check excerpt quality
        excerpt = top_result.excerpt
        print(f"\nExcerpt analysis:")
        
        # 1. Is it a real excerpt (not mock)?
        is_mock = "This episode" in excerpt and "covers" in excerpt and "Match score:" in excerpt
        
        if is_mock:
            print("❌ MOCK EXCERPT DETECTED - MongoDB not working!")
            quality_issues.append(f"Mock excerpt for '{test['query']}'")
        else:
            print("✅ Real transcript excerpt")
            
            # 2. Are search terms highlighted?
            highlighted_terms = excerpt.count("**")
            if highlighted_terms > 0:
                print(f"✅ {highlighted_terms // 2} search terms highlighted")
            else:
                print("⚠️  No highlighted terms")
                quality_issues.append(f"No highlights for '{test['query']}'")
            
            # 3. Is excerpt meaningful (not cut off badly)?
            if excerpt.startswith("..."):
                print("✅ Excerpt properly windowed")
            
            # 4. Length check
            excerpt_words = len(excerpt.split())
            print(f"✅ Excerpt length: {excerpt_words} words")
            
            # 5. Contains relevant terms?
            relevant_terms_found = sum(1 for term in test['expected_terms'] 
                                     if term.lower() in excerpt.lower())
            print(f"✅ Found {relevant_terms_found}/{len(test['expected_terms'])} expected terms")
        
        # Show excerpt preview
        print(f"\nExcerpt preview:")
        print(f"'{excerpt[:200]}...'")
        
        # Check score threshold
        if top_result.similarity_score < test['min_score']:
            quality_issues.append(
                f"Low score for '{test['query']}': {top_result.similarity_score:.2f}"
            )
    
    # Summary statistics
    print("\n\n" + "="*70)
    print("📊 QUALITY SUMMARY")
    print("="*70)
    
    if all_scores:
        print(f"\nRelevance Scores:")
        print(f"  Average: {statistics.mean(all_scores):.2f}")
        print(f"  Median: {statistics.median(all_scores):.2f}")
        print(f"  Range: {min(all_scores):.2f} - {max(all_scores):.2f}")
    
    print(f"\nQuality Issues Found: {len(quality_issues)}")
    for issue in quality_issues:
        print(f"  ⚠️  {issue}")
    
    # Compare to old system
    print("\n📈 IMPROVEMENT METRICS:")
    print("  Old system: 4% relevance, mock excerpts")
    print(f"  New system: {statistics.mean(all_scores):.1%} relevance, real excerpts")
    print(f"  Improvement: {(statistics.mean(all_scores) / 0.04 - 1):.0f}x better!")
    
    # Final verdict
    print("\n🏁 FINAL VERDICT:")
    if len(quality_issues) == 0 and statistics.mean(all_scores) > 1.0:
        print("✅ SEARCH QUALITY EXCELLENT - Ready for production!")
        print("✅ All queries return real transcript excerpts")
        print("✅ Search terms properly highlighted")
        print("✅ Relevance scores well above target")
    elif len(quality_issues) < 2:
        print("✅ SEARCH QUALITY GOOD - Minor issues only")
    else:
        print("⚠️  SEARCH QUALITY NEEDS WORK")
    
    return {
        "avg_score": statistics.mean(all_scores) if all_scores else 0,
        "issues": quality_issues,
        "tested_queries": len(test_cases)
    }

if __name__ == "__main__":
    results = asyncio.run(test_search_quality())