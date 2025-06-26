#!/usr/bin/env python3
"""
Run Batch Sentiment Analysis Once

Quick script to run the batch processor with minimal data for testing.
"""

import os
import sys
import logging
from batch_sentiment import BatchSentimentProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_batch_minimal():
    """Run batch with minimal scope for testing"""

    logger.info("🚀 Running Minimal Batch Sentiment Analysis")

    processor = BatchSentimentProcessor()

    # Reduce scope for faster testing
    processor.topics = ["AI", "Crypto"]  # Just 2 topics

    try:
        # Run just 2 weeks of data
        summary = processor.run_batch_process(weeks=2)

        logger.info(f"✅ Batch completed: {summary['completed_operations']}/{summary['total_operations']} operations")
        logger.info(f"Time taken: {summary['elapsed_seconds']:.1f} seconds")

        # Check results
        results_count = processor.results_collection.count_documents({})
        logger.info(f"📊 Total results stored: {results_count}")

        # Show sample results
        for result in processor.results_collection.find().limit(3):
            logger.info(f"  {result['topic']} {result['week']}: sentiment={result['sentiment_score']:.3f}, chunks={result['chunk_count']}")

        return True

    except Exception as e:
        logger.error(f"❌ Batch failed: {e}")
        return False

    finally:
        processor.close()

if __name__ == "__main__":
    success = run_batch_minimal()
    sys.exit(0 if success else 1)
