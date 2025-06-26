#!/usr/bin/env python3
"""
Batch Sentiment Analysis Processor

Processes all sentiment data nightly and stores pre-computed results in MongoDB.
This runs without time constraints, allowing processing of 800k+ chunks.
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import re
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('batch_sentiment.log') if os.path.exists('.') else logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BatchSentimentProcessor:
    def __init__(self):
        """Initialize the batch sentiment processor"""
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MONGODB_URI environment variable not set")

        self.client = MongoClient(mongodb_uri)
        self.db = self.client['podinsight']
        self.chunks_collection = self.db['transcript_chunks_768d']
        self.episodes_collection = self.db['episode_metadata']
        self.results_collection = self.db['sentiment_results']

        # Ensure unique index on topic + week + year
        self.results_collection.create_index([
            ("topic", 1),
            ("week", 1),
            ("year", 1)
        ], unique=True)

        # Default topics to analyze
        self.topics = [
            "AI Agents",
            "Capital Efficiency",
            "DePIN",
            "B2B SaaS",
            "Crypto/Web3"
        ]

        # Comprehensive sentiment keywords with weights
        self.sentiment_keywords = {
            # Strong positive
            'amazing': 1.0, 'incredible': 1.0, 'revolutionary': 1.0, 'breakthrough': 1.0,
            'phenomenal': 1.0, 'outstanding': 0.9, 'exceptional': 0.9, 'brilliant': 0.8,
            'excellent': 0.8, 'fantastic': 0.8, 'superb': 0.8, 'wonderful': 0.7,

            # Positive
            'great': 0.7, 'love': 0.7, 'awesome': 0.7, 'impressive': 0.6,
            'exciting': 0.6, 'excited': 0.6, 'innovative': 0.6, 'powerful': 0.6,
            'successful': 0.5, 'valuable': 0.5, 'promising': 0.5, 'strong': 0.5,
            'good': 0.4, 'positive': 0.4, 'useful': 0.4, 'helpful': 0.4,
            'interesting': 0.3, 'solid': 0.3, 'nice': 0.3, 'cool': 0.3,

            # Negative
            'bad': -0.4, 'poor': -0.5, 'disappointing': -0.6, 'failed': -0.6,
            'failing': -0.6, 'struggle': -0.4, 'struggling': -0.4, 'difficult': -0.3,
            'challenging': -0.2, 'concerning': -0.4, 'worried': -0.4, 'risky': -0.4,
            'problem': -0.5, 'problems': -0.5, 'issue': -0.3, 'issues': -0.3,

            # Strong negative
            'terrible': -0.8, 'horrible': -0.8, 'awful': -0.8, 'useless': -0.7,
            'disaster': -1.0, 'catastrophe': -1.0, 'failure': -0.8, 'worst': -0.8,
            'broken': -0.6, 'dangerous': -0.6, 'threat': -0.5, 'crisis': -0.7
        }

    def get_week_ranges(self, weeks: int = 12) -> List[Dict[str, Any]]:
        """Generate week ranges for analysis"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(weeks=weeks)

        week_ranges = []
        for week_offset in range(weeks):
            week_start = start_date + timedelta(weeks=week_offset)
            week_end = week_start + timedelta(days=7)

            # Calculate ISO week number
            iso_week = week_start.isocalendar()

            week_ranges.append({
                'week_label': f"W{week_offset + 1}",
                'iso_week': iso_week.week,
                'year': iso_week.year,
                'start_date': week_start,
                'end_date': week_end
            })

        return week_ranges

    def calculate_sentiment_for_chunks(self, chunks: List[Dict], topic_pattern) -> Dict[str, Any]:
        """Calculate sentiment score for a list of chunks"""
        if not chunks:
            return {
                'sentiment_score': 0.0,
                'confidence': 0.0,
                'keywords_found': [],
                'analyzed_chunks': 0
            }

        total_sentiment = 0
        analyzed_count = 0
        all_keywords_found = []

        for chunk in chunks:
            content = chunk.get('text', '').lower()

            # Find context around topic mentions (±200 characters)
            contexts = []
            for match in topic_pattern.finditer(content, re.IGNORECASE):
                start = max(0, match.start() - 200)
                end = min(len(content), match.end() + 200)
                contexts.append(content[start:end])

            if not contexts:
                continue

            # Calculate sentiment for each context
            context_sentiments = []
            chunk_keywords = []

            for context in contexts[:3]:  # Limit to 3 contexts per chunk
                sentiment_score = 0
                keyword_hits = 0

                # Check for sentiment keywords
                for keyword, weight in self.sentiment_keywords.items():
                    if keyword in context:
                        sentiment_score += weight
                        keyword_hits += 1
                        chunk_keywords.append(keyword)

                # Only count if we found sentiment keywords
                if keyword_hits > 0:
                    context_sentiments.append(sentiment_score / keyword_hits)

            # Average sentiment across contexts for this chunk
            if context_sentiments:
                chunk_sentiment = sum(context_sentiments) / len(context_sentiments)
                total_sentiment += chunk_sentiment
                analyzed_count += 1
                all_keywords_found.extend(chunk_keywords)

        # Calculate final metrics
        if analyzed_count > 0:
            avg_sentiment = total_sentiment / analyzed_count
            confidence = min(1.0, analyzed_count / 10)  # Higher confidence with more analyzed chunks
        else:
            avg_sentiment = 0.0
            confidence = 0.0

        # Clamp sentiment to [-1, 1] range
        avg_sentiment = max(-1, min(1, avg_sentiment))

        # Get unique keywords found
        unique_keywords = list(set(all_keywords_found))

        return {
            'sentiment_score': round(avg_sentiment, 3),
            'confidence': round(confidence, 3),
            'keywords_found': unique_keywords[:10],  # Top 10 keywords
            'analyzed_chunks': analyzed_count
        }

    def process_topic_week(self, topic: str, week_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process sentiment for a specific topic and week"""
        logger.info(f"Processing {topic} for {week_info['week_label']} ({week_info['year']})")

        # Create flexible search pattern
        # For multi-word topics, search for any of the key words
        words = topic.lower().split()

        if topic == "AI Agents":
            # Specific AI agent and autonomous system terms
            search_pattern = "\\b(ai agent|ai agents|autonomous agent|agentic|llm agent|gpt agent|claude|chatgpt|copilot|ai assistant|langchain|autogpt|babyagi|crew ai|multi.agent)\\b"
        elif topic == "Capital Efficiency":
            # Specific capital efficiency and burn rate terms
            search_pattern = "\\b(capital efficiency|burn rate|runway|unit economics|ltv.cac|gross margin|path to profitability|cash flow positive|default alive|ramen profitable)\\b"
        elif topic == "DePIN":
            # Specific DePIN and decentralized infrastructure terms
            search_pattern = "\\b(depin|decentralized physical infrastructure|helium|filecoin|arweave|akash|render network|hivemapper|dimo|physical infrastructure network)\\b"
        elif topic == "B2B SaaS":
            # Specific B2B SaaS metrics and terms
            search_pattern = "\\b(b2b saas|arr|mrr|annual recurring revenue|monthly recurring|net retention|gross retention|churn rate|acv|sales.led growth|product.led growth|plg)\\b"
        elif topic == "Crypto/Web3":
            # Specific crypto/web3 investment terms
            search_pattern = "\\b(web3|crypto startup|token economics|tokenomics|defi protocol|layer 1|layer 2|zk.rollup|blockchain infrastructure|onchain|stablecoin|smart contract)\\b"
        else:
            # Default: escape the topic as-is
            search_pattern = re.escape(topic)

        topic_pattern = re.compile(search_pattern, re.IGNORECASE)

        # First, find episodes in this date range
        start_date_iso = week_info['start_date'].strftime("%Y-%m-%d")
        end_date_iso = week_info['end_date'].strftime("%Y-%m-%d")

        episode_ids = []
        episodes = self.episodes_collection.find({
            "raw_entry_original_feed.published_date_iso": {
                "$gte": start_date_iso,
                "$lt": end_date_iso
            }
        }, {"guid": 1})

        episode_ids = [ep['guid'] for ep in episodes]

        if not episode_ids:
            logger.info(f"No episodes found in date range {start_date_iso} to {end_date_iso}")
            chunk_count = 0
        else:
            # Query chunks from these episodes that mention the topic
            query = {
                "text": {"$regex": search_pattern, "$options": "i"},
                "episode_id": {"$in": episode_ids}
            }

            # Count total chunks
            chunk_count = self.chunks_collection.count_documents(query)

        if chunk_count == 0:
            logger.info(f"No chunks found for {topic} in {week_info['week_label']}")
            return {
                'topic': topic,
                'week': week_info['week_label'],
                'year': week_info['year'],
                'sentiment_score': 0.0,
                'episode_count': 0,
                'chunk_count': 0,
                'sample_size': 0,
                'confidence': 0.0,
                'keywords_found': [],
                'computed_at': datetime.now(timezone.utc),
                'metadata': {
                    'date_range': f"{week_info['start_date'].strftime('%Y-%m-%d')} to {week_info['end_date'].strftime('%Y-%m-%d')}",
                    'analyzed_chunks': 0
                }
            }

        # Use sampling for large datasets to improve performance
        sample_size = min(chunk_count, 200)  # Sample up to 200 chunks

        if sample_size < chunk_count:
            # Use MongoDB $sample for random sampling
            pipeline = [
                {"$match": query},
                {"$sample": {"size": sample_size}},
                {"$project": {"text": 1, "episode_id": 1, "_id": 0}}
            ]
            chunks = list(self.chunks_collection.aggregate(pipeline))
        else:
            # Get all chunks if small dataset
            chunks = list(self.chunks_collection.find(query, {
                "text": 1, "episode_id": 1, "_id": 0
            }))

        # Calculate sentiment (pass original topic for context finding)
        sentiment_result = self.calculate_sentiment_for_chunks(chunks, topic_pattern)

        # Estimate episode count (approximate: 30 chunks per episode)
        episode_count = max(1, chunk_count // 30) if chunk_count > 0 else 0

        result = {
            'topic': topic,
            'week': week_info['week_label'],
            'year': week_info['year'],
            'sentiment_score': sentiment_result['sentiment_score'],
            'episode_count': episode_count,
            'chunk_count': chunk_count,
            'sample_size': sample_size,
            'confidence': sentiment_result['confidence'],
            'keywords_found': sentiment_result['keywords_found'],
            'computed_at': datetime.now(timezone.utc),
            'metadata': {
                'date_range': f"{week_info['start_date'].strftime('%Y-%m-%d')} to {week_info['end_date'].strftime('%Y-%m-%d')}",
                'analyzed_chunks': sentiment_result['analyzed_chunks'],
                'iso_week': week_info['iso_week']
            }
        }

        logger.info(f"  Result: sentiment={sentiment_result['sentiment_score']:.3f}, "
                   f"chunks={chunk_count}, analyzed={sentiment_result['analyzed_chunks']}")

        return result

    def store_result(self, result: Dict[str, Any]) -> bool:
        """Store result in MongoDB, handling duplicates"""
        try:
            # Use upsert to insert or update
            filter_query = {
                'topic': result['topic'],
                'week': result['week'],
                'year': result['year']
            }

            # Remove _id if it exists to avoid update errors
            update_doc = {k: v for k, v in result.items() if k != '_id'}

            update_result = self.results_collection.update_one(
                filter_query,
                {'$set': update_doc},
                upsert=True
            )

            if update_result.upserted_id:
                logger.debug(f"Inserted new result for {result['topic']} {result['week']} {result['year']}")
            else:
                logger.info(f"Updated existing result for {result['topic']} {result['week']} {result['year']}")

            return True
        except Exception as e:
            logger.error(f"Failed to store result: {e}, full error: {e.args[0] if e.args else 'No details'}")
            return False

    def run_batch_process(self, weeks: int = 12) -> Dict[str, Any]:
        """Run the complete batch sentiment analysis process"""
        start_time = time.time()
        logger.info(f"Starting batch sentiment analysis for {weeks} weeks, {len(self.topics)} topics")

        # Get week ranges
        week_ranges = self.get_week_ranges(weeks)
        logger.info(f"Processing {len(week_ranges)} weeks from {week_ranges[0]['start_date'].date()} to {week_ranges[-1]['end_date'].date()}")

        total_operations = len(week_ranges) * len(self.topics)
        completed_operations = 0
        failed_operations = 0

        # Process each combination of topic and week
        for week_info in week_ranges:
            for topic in self.topics:
                try:
                    result = self.process_topic_week(topic, week_info)
                    success = self.store_result(result)

                    if success:
                        completed_operations += 1
                    else:
                        failed_operations += 1

                except Exception as e:
                    logger.error(f"Failed to process {topic} for {week_info['week_label']}: {e}")
                    failed_operations += 1

                # Progress logging
                if (completed_operations + failed_operations) % 10 == 0:
                    progress = ((completed_operations + failed_operations) / total_operations) * 100
                    logger.info(f"Progress: {progress:.1f}% ({completed_operations}/{total_operations})")

        elapsed_time = time.time() - start_time

        summary = {
            'total_operations': total_operations,
            'completed_operations': completed_operations,
            'failed_operations': failed_operations,
            'elapsed_seconds': elapsed_time,
            'success_rate': (completed_operations / total_operations) * 100 if total_operations > 0 else 0
        }

        logger.info(f"Batch process completed in {elapsed_time:.1f}s")
        logger.info(f"Success: {completed_operations}/{total_operations} ({summary['success_rate']:.1f}%)")

        return summary

    def cleanup_old_results(self, days_to_keep: int = 30):
        """Remove old sentiment results to prevent collection bloat"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        result = self.results_collection.delete_many({
            'computed_at': {'$lt': cutoff_date}
        })

        logger.info(f"Cleaned up {result.deleted_count} old sentiment results (older than {days_to_keep} days)")

    def close(self):
        """Close MongoDB connection"""
        self.client.close()

def main():
    """Main function to run batch sentiment processing"""
    logger.info("=" * 60)
    logger.info("BATCH SENTIMENT ANALYSIS PROCESSOR")
    logger.info("=" * 60)

    processor = BatchSentimentProcessor()

    try:
        # Run the batch process
        summary = processor.run_batch_process(weeks=12)

        # Cleanup old results
        processor.cleanup_old_results(days_to_keep=30)

        # Log final summary
        logger.info("\n" + "=" * 60)
        logger.info("BATCH PROCESS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total operations: {summary['total_operations']}")
        logger.info(f"Completed: {summary['completed_operations']}")
        logger.info(f"Failed: {summary['failed_operations']}")
        logger.info(f"Success rate: {summary['success_rate']:.1f}%")
        logger.info(f"Total time: {summary['elapsed_seconds']:.1f} seconds")
        logger.info("=" * 60)

        # Exit with appropriate code
        if summary['failed_operations'] == 0:
            logger.info("✅ Batch process completed successfully!")
            sys.exit(0)
        else:
            logger.warning(f"⚠️  Batch process completed with {summary['failed_operations']} failures")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Batch process failed: {e}")
        sys.exit(1)

    finally:
        processor.close()

if __name__ == "__main__":
    main()
