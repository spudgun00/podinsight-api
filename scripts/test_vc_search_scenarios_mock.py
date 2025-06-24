#!/usr/bin/env python3
"""
Mock test of VC-focused search queries for PodInsight API
Demonstrates what the output would look like with a working API
"""

import json
import time
import random
from typing import Dict, List, Any
from datetime import datetime

# Mock data for demonstration
MOCK_EPISODES = [
    {"show": "All-In Podcast", "host": "Chamath Palihapitiya, Jason Calacanis, David Sacks, David Friedberg"},
    {"show": "The Twenty Minute VC", "host": "Harry Stebbings"},
    {"show": "This Week in Startups", "host": "Jason Calacanis"},
    {"show": "Acquired", "host": "Ben Gilbert, David Rosenthal"},
    {"show": "Invest Like the Best", "host": "Patrick O'Shaughnessy"},
    {"show": "Masters of Scale", "host": "Reid Hoffman"},
    {"show": "a16z Podcast", "host": "Andreessen Horowitz"},
    {"show": "The Tim Ferriss Show", "host": "Tim Ferriss"},
]

# Mock content templates
MOCK_CONTENT = {
    "AI/ML Trends & Valuations": [
        "The AI startup valuations in 2024 have been absolutely insane. We're seeing seed rounds at $50-100M valuations for teams with just a demo. The question is whether this is sustainable or if we're in for a major correction.",
        "What's interesting about the current AI market is that the infrastructure layer is getting commoditized quickly. The real value is moving up the stack to vertical-specific applications. We invested in a healthcare AI company that's doing $5M ARR already.",
        "The moat question in AI is critical. Most founders think their data is their moat, but that's rarely true. The real moats are network effects, switching costs, and deep customer integration. OpenAI has a moat because of brand and ecosystem, not just technology.",
    ],
    "Series A/B Funding": [
        "For Series A in 2024, you need at least $1-2M ARR growing 3x year-over-year. The bar has gotten much higher than it was in 2021. VCs are looking for real traction, not just promises.",
        "The jump from Series A to B is brutal right now. You need to show not just growth but efficient growth. The rule of 40 is back - your growth rate plus profit margin should exceed 40%. We're seeing companies with great growth fail to raise because their burn is too high.",
        "Timing your fundraise is everything. Start when you have 18 months of runway, not 6. And always raise when you don't need to. The best deals I've seen were companies that had multiple term sheets because they were crushing it, not desperate.",
    ],
    "Product-Market Fit": [
        "Product-market fit isn't binary - it's a spectrum. The early signs are when customers start pulling your product rather than you pushing it. When your NPS goes above 50 and people are referring others without being asked.",
        "The biggest mistake founders make is optimizing for vanity metrics before finding PMF. Forget about MAU and focus on retention cohorts. If your 6-month retention is below 20%, you don't have product-market fit, period.",
        "Customer validation is about quality, not quantity. I'd rather have 10 customers who absolutely love the product and use it daily than 1000 who try it once. Deep engagement beats broad adoption in the early days.",
    ],
}

# VC-focused test queries
VC_QUERIES = [
    {
        "category": "AI/ML Trends & Valuations",
        "queries": [
            "AI startup valuations 2024",
            "machine learning market opportunities",
            "generative AI business models",
            "AI moat defensibility"
        ]
    },
    {
        "category": "Series A/B Funding",
        "queries": [
            "Series A metrics benchmarks",
            "Series B growth requirements",
            "fundraising strategy timing",
            "investor pitch deck essentials"
        ]
    },
    {
        "category": "Product-Market Fit",
        "queries": [
            "product market fit indicators",
            "customer validation strategies",
            "pivot decisions timing",
            "early user feedback loops"
        ]
    },
]

def mock_search_api(query: str, category: str) -> Dict[str, Any]:
    """Generate mock search results"""
    start_time = time.time()
    
    # Simulate API delay
    time.sleep(random.uniform(0.1, 0.3))
    
    # Generate mock results
    num_results = random.randint(5, 15)
    results = []
    
    # Get relevant content for the category
    content_pool = MOCK_CONTENT.get(category, MOCK_CONTENT["AI/ML Trends & Valuations"])
    
    for i in range(min(num_results, 3)):  # Top 3 results
        episode = random.choice(MOCK_EPISODES)
        content = random.choice(content_pool)
        
        # Add some context around the main content
        full_content = f"...{content} And that's really the key insight here. {episode['host']} makes a great point about this..."
        
        results.append({
            "episode_title": f"EP{random.randint(100, 500)}: {query.title()} Deep Dive",
            "show_name": episode["show"],
            "relevance_score": random.uniform(0.75, 0.95),
            "content": full_content,
            "timestamp": f"{random.randint(10, 45)}:{random.randint(10, 59):02d}",
            "date": f"2024-{random.randint(1, 6):02d}-{random.randint(1, 28):02d}"
        })
    
    elapsed_time = time.time() - start_time
    
    return {
        "results": results,
        "response_time": elapsed_time,
        "total_results": num_results
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
        output.append(f"    Date: {item.get('date', 'N/A')}")
        output.append(f"    Timestamp: {item.get('timestamp', 'N/A')}")
        output.append(f"    Relevance Score: {item.get('relevance_score', 0):.3f}")
        
        # Clean and truncate content
        content = item.get('content', '').strip()
        if len(content) > 300:
            content = content[:297] + "..."
        output.append(f"    Excerpt: {content}")
    
    return "\n".join(output)

def run_tests():
    """Run mock VC search query tests"""
    print("=" * 80)
    print("PodInsight API - VC Search Query Test Results (MOCK)")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Note: Using mock data for demonstration purposes")
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
            
            # Execute mock search
            result = mock_search_api(query, category)
            
            # Track metrics
            response_time = result.get('response_time', 0)
            total_time += response_time
            
            successful_queries += 1
            results_count = len(result.get('results', []))
            total_results = result.get('total_results', results_count)
            
            print(f"Results Found: {total_results} (showing top {min(3, results_count)})")
            print(f"Response Time: {response_time:.2f}s")
            
            # Show top results
            if results_count > 0:
                print("\nTop Results:")
                print(format_result(result))
    
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
    
    print("\n📊 Key Insights from Mock Test:")
    print("- AI/ML queries return highly relevant content from top VC podcasts")
    print("- Series A/B funding queries provide specific metrics and benchmarks")
    print("- Product-market fit queries surface actionable founder advice")
    print("- Response times average 150-200ms per query")
    print("- Relevance scores typically range from 0.75 to 0.95")

if __name__ == "__main__":
    run_tests()