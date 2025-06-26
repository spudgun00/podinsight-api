#!/usr/bin/env python3
"""
Test Batch Sentiment Processor

Quick test script to verify the batch processor works before deploying to production.
"""

import os
import sys
import logging
from batch_sentiment import BatchSentimentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_batch_processor():
    """Test the batch processor with a small dataset"""

    logger.info("🧪 Testing Batch Sentiment Processor")
    logger.info("=" * 40)

    try:
        processor = BatchSentimentProcessor()

        # Test with just 1 week and 2 topics for speed
        processor.topics = ["AI", "Crypto"]  # Shorter topic names for testing

        logger.info("Running batch process (1 week, 2 topics)")
        summary = processor.run_batch_process(weeks=1)

        logger.info("\n📊 Test Results:")
        logger.info(f"Total operations: {summary['total_operations']}")
        logger.info(f"Completed: {summary['completed_operations']}")
        logger.info(f"Failed: {summary['failed_operations']}")
        logger.info(f"Success rate: {summary['success_rate']:.1f}%")
        logger.info(f"Time taken: {summary['elapsed_seconds']:.1f} seconds")

        # Check if results were stored
        results_count = processor.results_collection.count_documents({})
        logger.info(f"Total results in collection: {results_count}")

        # Show sample result
        sample_result = processor.results_collection.find_one()
        if sample_result:
            logger.info(f"\n📄 Sample Result:")
            logger.info(f"Topic: {sample_result['topic']}")
            logger.info(f"Week: {sample_result['week']} ({sample_result['year']})")
            logger.info(f"Sentiment: {sample_result['sentiment_score']}")
            logger.info(f"Chunks: {sample_result['chunk_count']}")
            logger.info(f"Keywords: {sample_result['keywords_found'][:3]}")

        processor.close()

        if summary['failed_operations'] == 0:
            logger.info("✅ Test passed! Batch processor is working correctly.")
            return True
        else:
            logger.warning(f"⚠️  Test completed with {summary['failed_operations']} failures")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_batch_processor()
    sys.exit(0 if success else 1)
