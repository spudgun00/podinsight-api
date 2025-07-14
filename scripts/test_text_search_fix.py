#!/usr/bin/env python3
"""
Test script to verify text search fix for MongoDB
Tests the query: "What are VCs saying about AI valuations?"
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from api.improved_hybrid_search import ImprovedHybridSearch
from lib.embeddings_768d_modal import generate_embedding_768d
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_text_search():
    """Test the text search with the previously failing query"""

    # Initialize search handler
    search_handler = ImprovedHybridSearch()

    # Test query that was failing
    test_query = "What are VCs saying about AI valuations?"
    logger.info(f"Testing query: '{test_query}'")

    try:
        # Generate embedding for the query
        logger.info("Generating embedding...")
        embedding = await generate_embedding_768d(test_query.lower())

        # Run hybrid search
        logger.info("Running hybrid search...")
        results = await search_handler.search(
            query=test_query,
            query_vector=embedding,
            limit=10
        )

        # Analyze results
        logger.info(f"\n{'='*60}")
        logger.info(f"SEARCH RESULTS:")
        logger.info(f"{'='*60}")
        logger.info(f"Total results: {len(results)}")

        if len(results) > 0:
            logger.info(f"\nTop 3 results:")
            for i, result in enumerate(results[:3]):
                logger.info(f"\n{i+1}. {result.get('podcast_name', 'Unknown')} - {result.get('episode_title', 'Unknown')}")
                logger.info(f"   Score: {result.get('score', 0):.3f}")
                logger.info(f"   Text preview: {result.get('text', '')[:100]}...")
        else:
            logger.warning("NO RESULTS FOUND!")

        logger.info(f"\n{'='*60}")

        # Check if text search is contributing
        if len(results) > 0:
            has_text_score = any(r.get('text_score', 0) > 0 for r in results)
            if has_text_score:
                logger.info("✅ Text search is working and contributing to results!")
            else:
                logger.warning("⚠️ Results found but text search may not be contributing")

    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close the MongoDB connection
        if hasattr(search_handler, 'client'):
            search_handler.client.close()

if __name__ == "__main__":
    asyncio.run(test_text_search())
