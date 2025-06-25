#!/usr/bin/env python3
"""Quick test to verify MongoDB metadata enrichment is working"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.mongodb_vector_search import MongoDBVectorSearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_metadata_enrichment():
    """Test that metadata enrichment works with MongoDB"""
    
    # Initialize search
    search = MongoDBVectorSearch()
    
    # Test with a known GUID
    test_guid = "0e983347-7815-4b62-87a6-84d988a772b7"
    
    # Create a mock chunk
    test_chunks = [{
        'episode_id': test_guid,
        'chunk_text': 'Test chunk about crypto',
        'feed_slug': 'a16z-podcast',
        'score': 0.95
    }]
    
    # Enrich with metadata
    enriched = search._enrich_with_metadata(test_chunks)
    
    if enriched:
        result = enriched[0]
        print("\n✅ Metadata Enrichment Results:")
        print(f"Episode Title: {result.get('episode_title')}")
        print(f"Podcast Name: {result.get('podcast_name')}")
        print(f"Published At: {result.get('published_at')}")
        print(f"Guests: {result.get('guests', [])}")
        print(f"Segment Count: {result.get('segment_count', 0)}")
        
        # Check if we got real data
        if result.get('episode_title') != 'Unknown Episode':
            print("\n🎉 SUCCESS: Real episode metadata retrieved from MongoDB!")
            return True
        else:
            print("\n❌ FAIL: Still showing placeholder data")
            return False
    else:
        print("\n❌ FAIL: No enriched results returned")
        return False

if __name__ == "__main__":
    try:
        success = test_metadata_enrichment()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)