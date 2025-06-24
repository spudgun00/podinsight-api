#!/usr/bin/env python3
"""
Test VC-focused search queries against the PodInsight API
Tests various common search scenarios that VCs would use
"""

import requests
import json
import time
from typing import Dict, List, Any
from datetime import datetime

# API configuration
# Try Modal endpoint instead
API_URL = "https://jamesgill--podinsight-web-endpoint.modal.run/search"

# VC-focused test queries
VC_QUERIES = [
    # AI/ML startup trends and valuations
    {
        "category": "AI/ML Trends & Valuations",
        "queries": [
            "AI startup valuations 2024",
            "machine learning market opportunities",
            "generative AI business models",
            "AI moat defensibility"
        ]
    },
    # Series A/B funding insights
    {
        "category": "Series A/B Funding",
        "queries": [
            "Series A metrics benchmarks",
            "Series B growth requirements",
            "fundraising strategy timing",
            "investor pitch deck essentials"
        ]
    },
    # Product-market fit strategies
    {
        "category": "Product-Market Fit",
        "queries": [
            "product market fit indicators",
            "customer validation strategies",
            "pivot decisions timing",
            "early user feedback loops"
        ]
    },
    # Crypto/Web3 discussions
    {
        "category": "Crypto/Web3",
        "queries": [
            "web3 investment opportunities",
            "crypto startup fundamentals",
            "blockchain use cases enterprise",
            "DeFi protocol economics"
        ]
    },
    # Remote work and productivity
    {
        "category": "Remote Work & Productivity",
        "queries": [
            "remote team building strategies",
            "distributed company culture",
            "async communication best practices",
            "remote hiring challenges"
        ]
    },
    # Founder advice and lessons
    {
        "category": "Founder Advice",
        "queries": [
            "founder mistakes to avoid",
            "startup lessons learned",
            "founder mental health",
            "co-founder conflict resolution"
        ]
    },
    # Market timing and cycles
    {
        "category": "Market Timing & Cycles",
        "queries": [
            "market downturn strategies",
            "bull market fundraising",
            "recession startup opportunities",
            "market cycle timing"
        ]
    },
    # Competition and moats
    {
        "category": "Competition & Moats",
        "queries": [
            "competitive advantage building",
            "network effects strategies",
            "switching costs creation",
            "market monopoly tactics"
        ]
    },
    # Exit strategies
    {
        "category": "Exit Strategies",
        "queries": [
            "acquisition negotiation tactics",
            "IPO readiness checklist",
            "strategic buyer targeting",
            "exit valuation multiples"
        ]
    },
    # Team building
    {
        "category": "Team Building",
        "queries": [
            "hiring senior executives",
            "equity compensation strategies",
            "engineering culture building",
            "talent retention tactics"
        ]
    }
]

def search_api(query: str) -> Dict[str, Any]:
    """Send search request to PodInsight API"""
    start_time = time.time()
    
    try:
        response = requests.post(
            API_URL,
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        
        elapsed_time = time.time() - start_time
        result = response.json()
        result['response_time'] = elapsed_time
        
        return result
    except requests.exceptions.RequestException as e:
        return {
            "error": str(e),
            "response_time": time.time() - start_time,
            "results": []
        }

def format_result(result: Dict[str, Any], max_excerpts: int = 3) -> str:
    """Format a single search result for display"""
    output = []
    
    # Get results array
    results = result.get('results', [])
    if not results:
        return "  No results found"
    
    # Display top excerpts
    for i, item in enumerate(results[:max_excerpts]):
        output.append(f"\n  Result {i+1}:")
        output.append(f"    Episode: {item.get('episode_title', 'N/A')}")
        output.append(f"    Show: {item.get('show_name', 'N/A')}")
        output.append(f"    Relevance Score: {item.get('relevance_score', 0):.3f}")
        
        # Clean and truncate content
        content = item.get('content', '').strip()
        if len(content) > 300:
            content = content[:297] + "..."
        output.append(f"    Excerpt: {content}")
    
    return "\n".join(output)

def run_tests():
    """Run all VC search query tests"""
    print("=" * 80)
    print("PodInsight API - VC Search Query Test Results")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    total_queries = 0
    total_time = 0
    successful_queries = 0
    
    for category_group in VC_QUERIES:
        category = category_group["category"]
        queries = category_group["queries"]
        
        print(f"\n\n{'#' * 60}")
        print(f"# {category}")
        print(f"{'#' * 60}")
        
        for query in queries:
            total_queries += 1
            print(f"\n{'=' * 60}")
            print(f"Query: \"{query}\"")
            print(f"{'=' * 60}")
            
            # Execute search
            result = search_api(query)
            
            # Track metrics
            response_time = result.get('response_time', 0)
            total_time += response_time
            
            if 'error' in result:
                print(f"ERROR: {result['error']}")
                print(f"Response Time: {response_time:.2f}s")
            else:
                successful_queries += 1
                results_count = len(result.get('results', []))
                print(f"Results Found: {results_count}")
                print(f"Response Time: {response_time:.2f}s")
                
                # Show top results
                if results_count > 0:
                    print("\nTop Results:")
                    print(format_result(result))
            
            # Small delay between requests
            time.sleep(0.5)
    
    # Summary statistics
    print(f"\n\n{'=' * 80}")
    print("SUMMARY STATISTICS")
    print(f"{'=' * 80}")
    print(f"Total Queries Tested: {total_queries}")
    print(f"Successful Queries: {successful_queries}")
    print(f"Failed Queries: {total_queries - successful_queries}")
    print(f"Success Rate: {(successful_queries/total_queries)*100:.1f}%")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Average Response Time: {total_time/total_queries:.2f}s")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    run_tests()