#!/usr/bin/env python3
"""
Sentiment Analysis Performance Testing

Tests different optimization strategies for the sentiment analysis API
to find the fastest approach that stays within Vercel's 300-second timeout.
"""

import os
import time
import json
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
import re
from typing import List, Dict, Any

class SentimentPerformanceTester:
    def __init__(self):
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not configured")

        self.client = MongoClient(mongodb_uri)
        self.db = self.client['podinsight']
        self.collection = self.db['transcript_chunks_768d']

        # Sentiment keywords (simplified for testing)
        self.sentiment_keywords = {
            'great': 0.7, 'love': 0.7, 'amazing': 1.0, 'excellent': 0.8,
            'good': 0.4, 'interesting': 0.3, 'useful': 0.4,
            'bad': -0.4, 'poor': -0.5, 'terrible': -0.8, 'awful': -0.8,
            'problematic': -0.5, 'concerning': -0.4, 'difficult': -0.3
        }

    def test_current_approach(self, weeks: int = 4, topics: List[str] = None) -> Dict[str, Any]:
        """Test the current sentiment analysis approach"""
        if topics is None:
            topics = ["AI", "Crypto"]

        print(f"\n🧪 Testing Current Approach ({weeks} weeks, {len(topics)} topics)")
        start_time = time.time()

        results = []
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(weeks=weeks)

        total_chunks_processed = 0

        for week_offset in range(weeks):
            week_start = start_date + timedelta(weeks=week_offset)
            week_end = week_start + timedelta(days=7)
            week_label = f"W{week_offset + 1}"

            for topic in topics:
                topic_pattern = re.compile(re.escape(topic), re.IGNORECASE)

                query = {
                    "text": {"$regex": topic_pattern},
                    "published_at": {
                        "$gte": week_start,
                        "$lt": week_end
                    }
                }

                chunk_count = self.collection.count_documents(query)
                total_chunks_processed += chunk_count

                if chunk_count > 0:
                    # Get sample chunks
                    chunks = list(self.collection.find(query, {
                        "text": 1, "_id": 0
                    }).limit(50))

                    # Calculate sentiment (simplified)
                    sentiment = self._calculate_simple_sentiment(chunks, topic_pattern)
                else:
                    sentiment = 0.0

                results.append({
                    "topic": topic,
                    "week": week_label,
                    "sentiment": sentiment,
                    "chunk_count": chunk_count
                })

        elapsed = time.time() - start_time

        return {
            "method": "current",
            "elapsed_seconds": elapsed,
            "results": results,
            "total_chunks_processed": total_chunks_processed,
            "chunks_per_second": total_chunks_processed / elapsed if elapsed > 0 else 0
        }

    def test_aggregation_approach(self, weeks: int = 4, topics: List[str] = None) -> Dict[str, Any]:
        """Test using MongoDB aggregation pipeline"""
        if topics is None:
            topics = ["AI", "Crypto"]

        print(f"\n🧪 Testing Aggregation Approach ({weeks} weeks, {len(topics)} topics)")
        start_time = time.time()

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(weeks=weeks)

        results = []
        total_chunks_processed = 0

        for topic in topics:
            topic_pattern = re.compile(re.escape(topic), re.IGNORECASE)

            # Use aggregation to group by week and calculate stats
            pipeline = [
                {
                    "$match": {
                        "text": {"$regex": topic_pattern},
                        "published_at": {
                            "$gte": start_date,
                            "$lt": end_date
                        }
                    }
                },
                {
                    "$addFields": {
                        "week_number": {
                            "$week": "$published_at"
                        }
                    }
                },
                {
                    "$group": {
                        "_id": "$week_number",
                        "chunk_count": {"$sum": 1},
                        "sample_texts": {"$push": {"$substr": ["$text", 0, 500]}}
                    }
                },
                {
                    "$limit": weeks
                }
            ]

            agg_results = list(self.collection.aggregate(pipeline))

            for week_data in agg_results:
                week_num = week_data["_id"]
                chunk_count = week_data["chunk_count"]
                sample_texts = week_data["sample_texts"][:10]  # Limit sample size

                total_chunks_processed += chunk_count

                # Calculate sentiment on sample
                sentiment = self._calculate_sentiment_from_texts(sample_texts)

                results.append({
                    "topic": topic,
                    "week": f"W{week_num}",
                    "sentiment": sentiment,
                    "chunk_count": chunk_count
                })

        elapsed = time.time() - start_time

        return {
            "method": "aggregation",
            "elapsed_seconds": elapsed,
            "results": results,
            "total_chunks_processed": total_chunks_processed,
            "chunks_per_second": total_chunks_processed / elapsed if elapsed > 0 else 0
        }

    def test_sampling_approach(self, weeks: int = 4, topics: List[str] = None, sample_size: int = 100) -> Dict[str, Any]:
        """Test using statistical sampling"""
        if topics is None:
            topics = ["AI", "Crypto"]

        print(f"\n🧪 Testing Sampling Approach ({weeks} weeks, {len(topics)} topics, sample={sample_size})")
        start_time = time.time()

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(weeks=weeks)

        results = []
        total_chunks_processed = 0

        for week_offset in range(weeks):
            week_start = start_date + timedelta(weeks=week_offset)
            week_end = week_start + timedelta(days=7)
            week_label = f"W{week_offset + 1}"

            for topic in topics:
                topic_pattern = re.compile(re.escape(topic), re.IGNORECASE)

                query = {
                    "text": {"$regex": topic_pattern},
                    "published_at": {
                        "$gte": week_start,
                        "$lt": week_end
                    }
                }

                # Get total count
                chunk_count = self.collection.count_documents(query)
                total_chunks_processed += min(chunk_count, sample_size)

                if chunk_count > 0:
                    # Use MongoDB $sample for random sampling
                    pipeline = [
                        {"$match": query},
                        {"$sample": {"size": min(sample_size, chunk_count)}},
                        {"$project": {"text": 1, "_id": 0}}
                    ]

                    chunks = list(self.collection.aggregate(pipeline))
                    sentiment = self._calculate_simple_sentiment(chunks, topic_pattern)
                else:
                    sentiment = 0.0

                results.append({
                    "topic": topic,
                    "week": week_label,
                    "sentiment": sentiment,
                    "chunk_count": chunk_count,
                    "sampled_chunks": min(chunk_count, sample_size)
                })

        elapsed = time.time() - start_time

        return {
            "method": f"sampling_{sample_size}",
            "elapsed_seconds": elapsed,
            "results": results,
            "total_chunks_processed": total_chunks_processed,
            "chunks_per_second": total_chunks_processed / elapsed if elapsed > 0 else 0
        }

    def _calculate_simple_sentiment(self, chunks: List[Dict], topic_pattern) -> float:
        """Simplified sentiment calculation for testing"""
        if not chunks:
            return 0.0

        total_sentiment = 0
        analyzed_count = 0

        for chunk in chunks:
            content = chunk.get('text', '').lower()

            # Find context around topic mentions
            matches = list(topic_pattern.finditer(content, re.IGNORECASE))
            if not matches:
                continue

            # Get context around first match
            match = matches[0]
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 100)
            context = content[start:end]

            # Calculate sentiment for context
            sentiment_score = 0
            keyword_count = 0

            for keyword, weight in self.sentiment_keywords.items():
                if keyword in context:
                    sentiment_score += weight
                    keyword_count += 1

            if keyword_count > 0:
                total_sentiment += sentiment_score / keyword_count
                analyzed_count += 1

        return total_sentiment / analyzed_count if analyzed_count > 0 else 0.0

    def _calculate_sentiment_from_texts(self, texts: List[str]) -> float:
        """Calculate sentiment from list of text strings"""
        if not texts:
            return 0.0

        total_sentiment = 0
        analyzed_count = 0

        for text in texts:
            content = text.lower()
            sentiment_score = 0
            keyword_count = 0

            for keyword, weight in self.sentiment_keywords.items():
                if keyword in content:
                    sentiment_score += weight
                    keyword_count += 1

            if keyword_count > 0:
                total_sentiment += sentiment_score / keyword_count
                analyzed_count += 1

        return total_sentiment / analyzed_count if analyzed_count > 0 else 0.0

    def run_performance_comparison(self):
        """Run all performance tests and compare results"""
        print("🚀 Sentiment Analysis Performance Testing")
        print("=" * 60)

        test_results = []

        # Test 1: Current approach (small scale)
        try:
            result1 = self.test_current_approach(weeks=2, topics=["AI"])
            test_results.append(result1)
        except Exception as e:
            print(f"❌ Current approach failed: {e}")

        # Test 2: Aggregation approach
        try:
            result2 = self.test_aggregation_approach(weeks=2, topics=["AI"])
            test_results.append(result2)
        except Exception as e:
            print(f"❌ Aggregation approach failed: {e}")

        # Test 3: Sampling approaches
        for sample_size in [50, 100, 200]:
            try:
                result3 = self.test_sampling_approach(weeks=2, topics=["AI"], sample_size=sample_size)
                test_results.append(result3)
            except Exception as e:
                print(f"❌ Sampling approach ({sample_size}) failed: {e}")

        # Summary
        print("\n📊 Performance Summary:")
        print("-" * 60)
        print(f"{'Method':<20} {'Time (s)':<10} {'Chunks':<10} {'Rate':<15}")
        print("-" * 60)

        for result in test_results:
            method = result['method']
            elapsed = result['elapsed_seconds']
            chunks = result['total_chunks_processed']
            rate = result['chunks_per_second']

            print(f"{method:<20} {elapsed:<10.2f} {chunks:<10} {rate:<15.1f}")

        # Recommendations
        print("\n💡 Recommendations:")
        if test_results:
            fastest = min(test_results, key=lambda x: x['elapsed_seconds'])
            print(f"  - Fastest method: {fastest['method']} ({fastest['elapsed_seconds']:.2f}s)")

            # Extrapolate to full workload
            full_scale_time = fastest['elapsed_seconds'] * 30  # Rough estimate for 12 weeks, 5 topics
            if full_scale_time < 300:
                print(f"  - ✅ Estimated full scale time: {full_scale_time:.1f}s (within 300s limit)")
            else:
                print(f"  - ⚠️  Estimated full scale time: {full_scale_time:.1f}s (exceeds 300s limit)")
                print("  - Consider further optimization or caching")

        return test_results

    def close(self):
        """Close MongoDB connection"""
        self.client.close()

def main():
    """Main function to run performance tests"""
    tester = SentimentPerformanceTester()

    try:
        results = tester.run_performance_comparison()

        # Save results
        output_file = "diagnostics/performance_test_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results saved to {output_file}")

    finally:
        tester.close()

if __name__ == "__main__":
    main()
