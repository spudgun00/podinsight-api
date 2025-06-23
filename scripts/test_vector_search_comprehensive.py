#!/usr/bin/env python3
"""
Comprehensive Vector Search Quality Testing
Tests search across full 823k+ chunk dataset to validate production readiness
Focuses on search quality based on MongoDB Coverage Verification findings
"""

import asyncio
import aiohttp
import json
import statistics
from typing import Dict, List, Any, Set
from datetime import datetime
from dataclasses import dataclass
import time

# API Configuration
API_BASE = "https://podinsight-api.vercel.app"

@dataclass
class SearchAnalysis:
    query: str
    results_count: int
    avg_similarity: float
    top_similarity: float
    unique_podcasts: int
    unique_episodes: int
    response_time: float
    topics_found: Set[str]
    has_context_expansion: bool
    temporal_coverage: Dict[str, int]  # Episodes by year/month

class VectorSearchTester:
    def __init__(self):
        self.session = None
        self.analyses: List[SearchAnalysis] = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def search_query(self, query: str, limit: int = 20) -> Dict:
        """Execute search query and return results"""
        try:
            search_data = {"query": query, "limit": limit}
            async with self.session.post(f"{API_BASE}/api/search", json=search_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}

    def analyze_search_results(self, query: str, response_data: Dict, response_time: float) -> SearchAnalysis:
        """Analyze search results for quality metrics"""
        results = response_data.get('results', [])
        
        if not results:
            return SearchAnalysis(
                query=query,
                results_count=0,
                avg_similarity=0,
                top_similarity=0,
                unique_podcasts=0,
                unique_episodes=0,
                response_time=response_time,
                topics_found=set(),
                has_context_expansion=False,
                temporal_coverage={}
            )
        
        # Extract metrics
        similarities = [r.get('similarity_score', 0) for r in results]
        podcasts = set(r.get('podcast_name', '') for r in results if r.get('podcast_name'))
        episodes = set(r.get('episode_id', '') for r in results if r.get('episode_id'))
        
        # Collect all topics mentioned
        all_topics = set()
        for result in results:
            all_topics.update(result.get('topics', []))
        
        # Check for context expansion (indicated by longer excerpts)
        has_context = any(len(r.get('excerpt', '')) > 200 for r in results)
        
        # Temporal coverage analysis
        temporal_coverage = {}
        for result in results:
            pub_date = result.get('published_at', '')
            if pub_date:
                try:
                    # Extract year-month from date
                    date_key = pub_date[:7]  # YYYY-MM format
                    temporal_coverage[date_key] = temporal_coverage.get(date_key, 0) + 1
                except:
                    pass
        
        return SearchAnalysis(
            query=query,
            results_count=len(results),
            avg_similarity=statistics.mean(similarities) if similarities else 0,
            top_similarity=max(similarities) if similarities else 0,
            unique_podcasts=len(podcasts),
            unique_episodes=len(episodes),
            response_time=response_time,
            topics_found=all_topics,
            has_context_expansion=has_context,
            temporal_coverage=temporal_coverage
        )

    async def test_search_coverage(self):
        """Test search coverage across different dimensions"""
        print("🎯 Testing Vector Search Coverage")
        print("=" * 60)
        
        # Test queries designed to hit different parts of the dataset
        coverage_queries = [
            # Technology & AI
            ("artificial intelligence", "AI/ML coverage"),
            ("machine learning algorithms", "Technical ML terms"),
            ("GPT models", "Specific AI models"),
            ("neural networks", "Deep tech AI"),
            
            # Business & Strategy  
            ("venture capital funding", "VC/Investment"),
            ("product market fit", "Startup fundamentals"),
            ("go to market strategy", "Business strategy"),
            ("unit economics", "Business metrics"),
            
            # Crypto & Web3
            ("bitcoin price", "Crypto markets"),
            ("ethereum smart contracts", "Blockchain tech"),
            ("DeFi protocols", "Decentralized finance"),
            ("NFT marketplace", "Digital assets"),
            
            # Infrastructure & Hardware
            ("cloud computing", "Infrastructure"),
            ("semiconductor chips", "Hardware"),
            ("data centers", "Physical infrastructure"),
            ("5G networks", "Telecommunications"),
            
            # Emerging Topics
            ("climate technology", "Climate/Green tech"),
            ("autonomous vehicles", "Transportation"),
            ("biotechnology", "Life sciences"),
            ("quantum computing", "Quantum tech"),
            
            # Company & People Specific
            ("Elon Musk", "Specific person"),
            ("Google", "Specific company"),
            ("OpenAI", "AI companies"),
            ("Y Combinator", "Accelerators"),
            
            # Market & Financial
            ("IPO public offering", "Financial events"),
            ("market valuation", "Valuations"),
            ("inflation interest rates", "Economic factors"),
            ("supply chain", "Operations"),
        ]
        
        for query, category in coverage_queries:
            start_time = time.time()
            response = await self.search_query(query, limit=15)
            response_time = time.time() - start_time
            
            if 'error' not in response:
                analysis = self.analyze_search_results(query, response, response_time)
                self.analyses.append(analysis)
                
                print(f"✅ {category}: '{query}'")
                print(f"   Results: {analysis.results_count}, "
                      f"Podcasts: {analysis.unique_podcasts}, "
                      f"Episodes: {analysis.unique_episodes}")
                print(f"   Top Score: {analysis.top_similarity:.3f}, "
                      f"Avg Score: {analysis.avg_similarity:.3f}")
                print(f"   Topics: {len(analysis.topics_found)}, "
                      f"Time: {analysis.response_time:.3f}s")
                print()
            else:
                print(f"❌ {category}: '{query}' - {response['error']}")

    async def test_search_precision(self):
        """Test search precision with specific, targeted queries"""
        print("🔍 Testing Search Precision")
        print("=" * 60)
        
        # Precise queries that should return highly relevant results
        precision_queries = [
            ("Marc Andreessen", "Should find a16z content"),
            ("Jason Calacanis", "Should find This Week in Startups"),
            ("Ben Gilbert David Rosenthal", "Should find Acquired podcast"),
            ("Chamath Palihapitiya", "Should find All-In podcast"),
            ("Series A funding round", "Should find startup content"),
            ("Bitcoin halving event", "Should find crypto content"),
            ("iPhone app store", "Should find mobile/Apple content"),
            ("Tesla autonomous driving", "Should find Tesla/automotive content"),
        ]
        
        precision_results = []
        
        for query, expectation in precision_queries:
            start_time = time.time()
            response = await self.search_query(query, limit=10)
            response_time = time.time() - start_time
            
            if 'error' not in response:
                analysis = self.analyze_search_results(query, response, response_time)
                precision_results.append(analysis)
                
                # Calculate precision score (top result relevance)
                precision_score = analysis.top_similarity
                
                print(f"{'✅' if precision_score > 0.7 else '⚠️'} '{query}'")
                print(f"   Expectation: {expectation}")
                print(f"   Precision Score: {precision_score:.3f}")
                print(f"   Results: {analysis.results_count} across {analysis.unique_podcasts} podcasts")
                print()
            else:
                print(f"❌ '{query}' - {response['error']}")
        
        # Calculate overall precision
        if precision_results:
            avg_precision = statistics.mean([a.top_similarity for a in precision_results])
            high_precision = len([a for a in precision_results if a.top_similarity > 0.7])
            
            print(f"📊 PRECISION SUMMARY:")
            print(f"Average Precision: {avg_precision:.3f}")
            print(f"High Precision Results: {high_precision}/{len(precision_results)} ({high_precision/len(precision_results)*100:.1f}%)")

    async def test_search_recall(self):
        """Test search recall - ability to find relevant content across dataset"""
        print("\n📈 Testing Search Recall")
        print("=" * 60)
        
        # Broad queries that should find content across multiple podcasts/episodes
        recall_queries = [
            ("startup", "Should find content across all business podcasts"),
            ("technology", "Should find tech content broadly"),
            ("investment", "Should find investment-related content"),
            ("artificial intelligence", "Should find AI content across shows"),
            ("market", "Should find market-related discussions"),
        ]
        
        recall_results = []
        
        for query, expectation in recall_queries:
            start_time = time.time()
            response = await self.search_query(query, limit=25)  # Higher limit for recall
            response_time = time.time() - start_time
            
            if 'error' not in response:
                analysis = self.analyze_search_results(query, response, response_time)
                recall_results.append(analysis)
                
                # Calculate recall indicators
                podcast_diversity = analysis.unique_podcasts
                episode_diversity = analysis.unique_episodes  
                temporal_diversity = len(analysis.temporal_coverage)
                
                print(f"✅ '{query}'")
                print(f"   Expectation: {expectation}")
                print(f"   Podcast Diversity: {podcast_diversity} different shows")
                print(f"   Episode Diversity: {episode_diversity} different episodes")
                print(f"   Temporal Spread: {temporal_diversity} time periods")
                print(f"   Total Results: {analysis.results_count}")
                print()
            else:
                print(f"❌ '{query}' - {response['error']}")
        
        # Calculate overall recall metrics
        if recall_results:
            avg_podcast_diversity = statistics.mean([a.unique_podcasts for a in recall_results])
            avg_episode_diversity = statistics.mean([a.unique_episodes for a in recall_results])
            
            print(f"📊 RECALL SUMMARY:")
            print(f"Average Podcast Diversity: {avg_podcast_diversity:.1f}")
            print(f"Average Episode Diversity: {avg_episode_diversity:.1f}")

    async def generate_vector_search_report(self):
        """Generate comprehensive vector search quality report"""
        print("\n" + "=" * 80)
        print("📋 VECTOR SEARCH QUALITY REPORT")
        print("Dataset: 823,763 chunks across 1,171 episodes (from MongoDB Coverage Verification)")
        print("=" * 80)
        
        if not self.analyses:
            print("❌ No search analyses available")
            return
        
        # Overall metrics
        total_queries = len(self.analyses)
        successful_queries = len([a for a in self.analyses if a.results_count > 0])
        avg_response_time = statistics.mean([a.response_time for a in self.analyses])
        
        print(f"\n📊 OVERALL METRICS")
        print(f"Total Queries Tested: {total_queries}")
        print(f"Successful Queries: {successful_queries}/{total_queries} ({successful_queries/total_queries*100:.1f}%)")
        print(f"Average Response Time: {avg_response_time:.3f}s")
        
        # Search quality metrics
        valid_analyses = [a for a in self.analyses if a.results_count > 0]
        if valid_analyses:
            avg_similarity = statistics.mean([a.avg_similarity for a in valid_analyses])
            avg_top_similarity = statistics.mean([a.top_similarity for a in valid_analyses])
            avg_results = statistics.mean([a.results_count for a in valid_analyses])
            
            print(f"\n🎯 SEARCH QUALITY")
            print(f"Average Similarity Score: {avg_similarity:.3f}")
            print(f"Average Top Result Score: {avg_top_similarity:.3f}")
            print(f"Average Results per Query: {avg_results:.1f}")
            
            # Coverage metrics
            all_podcasts = set()
            all_topics = set()
            for analysis in valid_analyses:
                all_podcasts.update([f"podcast_{i}" for i in range(analysis.unique_podcasts)])
                all_topics.update(analysis.topics_found)
            
            print(f"\n📡 COVERAGE METRICS")
            print(f"Unique Topics Discovered: {len(all_topics)}")
            print(f"Cross-Podcast Results: {statistics.mean([a.unique_podcasts for a in valid_analyses]):.1f} avg podcasts/query")
            print(f"Episode Diversity: {statistics.mean([a.unique_episodes for a in valid_analyses]):.1f} avg episodes/query")
            
            # Context expansion
            context_queries = len([a for a in valid_analyses if a.has_context_expansion])
            print(f"\n🔍 CONTEXT EXPANSION")
            print(f"Queries with Expanded Context: {context_queries}/{len(valid_analyses)} ({context_queries/len(valid_analyses)*100:.1f}%)")
        
        # Performance assessment
        fast_queries = len([a for a in self.analyses if a.response_time < 2.0])
        slow_queries = len([a for a in self.analyses if a.response_time > 5.0])
        
        print(f"\n⚡ PERFORMANCE ASSESSMENT")
        print(f"Fast Queries (<2s): {fast_queries}/{total_queries} ({fast_queries/total_queries*100:.1f}%)")
        print(f"Slow Queries (>5s): {slow_queries}/{total_queries} ({slow_queries/total_queries*100:.1f}%)")
        
        # Production readiness assessment
        print(f"\n🏥 PRODUCTION READINESS")
        
        success_rate = successful_queries / total_queries
        performance_rate = fast_queries / total_queries
        quality_score = avg_top_similarity if valid_analyses else 0
        
        if success_rate >= 0.90 and performance_rate >= 0.80 and quality_score >= 0.6:
            print("✅ VECTOR SEARCH: PRODUCTION READY")
            print("High success rate, good performance, quality results")
        elif success_rate >= 0.75 and performance_rate >= 0.60:
            print("⚠️  VECTOR SEARCH: NEEDS OPTIMIZATION")
            print("Acceptable but has room for improvement")
        else:
            print("❌ VECTOR SEARCH: NOT READY")
            print("Requires significant improvements before production")
        
        # Save detailed report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "dataset_info": {
                "total_chunks": 823763,
                "total_episodes": 1171,
                "source": "MongoDB Coverage Verification Report"
            },
            "analyses": [
                {
                    "query": a.query,
                    "results_count": a.results_count,
                    "avg_similarity": a.avg_similarity,
                    "top_similarity": a.top_similarity,
                    "unique_podcasts": a.unique_podcasts,
                    "unique_episodes": a.unique_episodes,
                    "response_time": a.response_time,
                    "topics_found": list(a.topics_found),
                    "has_context_expansion": a.has_context_expansion,
                    "temporal_coverage": a.temporal_coverage
                }
                for a in self.analyses
            ],
            "summary": {
                "total_queries": total_queries,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "avg_quality_score": quality_score,
                "production_ready": success_rate >= 0.90 and performance_rate >= 0.80 and quality_score >= 0.6
            }
        }
        
        with open('vector_search_quality_report.json', 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n💾 Detailed report saved to vector_search_quality_report.json")

    async def run_comprehensive_search_tests(self):
        """Run all vector search quality tests"""
        print("🚀 Starting Comprehensive Vector Search Testing")
        print("Target: Production API with 823k+ chunk dataset")
        print("=" * 80)
        
        await self.test_search_coverage()
        await self.test_search_precision() 
        await self.test_search_recall()
        await self.generate_vector_search_report()

async def main():
    async with VectorSearchTester() as tester:
        await tester.run_comprehensive_search_tests()

if __name__ == "__main__":
    asyncio.run(main())