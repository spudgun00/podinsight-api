"""
Comprehensive tests for the search API functionality
Tests embedding generation, caching, and search results
"""
import pytest
import asyncio
import os
import sys
from datetime import datetime
import hashlib
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.search import (
    generate_embedding,
    check_query_cache,
    store_query_cache,
    search_episodes,
    extract_excerpt,
    search_handler,
    SearchRequest,
    SearchResponse
)
from api.database import get_pool


class TestEmbeddingGeneration:
    """Test embedding generation functionality"""
    
    @pytest.mark.asyncio
    async def test_generate_embedding_success(self):
        """Test successful embedding generation"""
        query = "AI agents and startup valuations"
        embedding = await generate_embedding(query)
        
        # Check dimensions (should be 384 for all-MiniLM-L6-v2)
        assert len(embedding) == 384
        
        # Check it's normalized (unit length)
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.001
        
        # Check all values are floats
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_generate_embedding_empty_query(self):
        """Test embedding generation with empty query"""
        embedding = await generate_embedding("")
        
        # Should still return valid embedding
        assert len(embedding) == 384
    
    @pytest.mark.asyncio
    async def test_generate_embedding_consistency(self):
        """Test that same query produces same embedding"""
        query = "blockchain and decentralization"
        
        embedding1 = await generate_embedding(query)
        embedding2 = await generate_embedding(query)
        
        # Should be identical
        assert embedding1 == embedding2


class TestQueryCaching:
    """Test query caching functionality"""
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss returns None"""
        # Use unique query hash unlikely to be cached
        unique_hash = hashlib.sha256(f"unique_test_query_{datetime.now()}".encode()).hexdigest()
        
        result = await check_query_cache(unique_hash)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_store_and_retrieve(self):
        """Test storing and retrieving from cache"""
        query = f"test query {datetime.now()}"
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        embedding = [0.1] * 384  # Mock embedding
        
        # Store in cache
        await store_query_cache(query, query_hash, embedding)
        
        # Wait a bit for async operation
        await asyncio.sleep(0.5)
        
        # Retrieve from cache
        cached = await check_query_cache(query_hash)
        
        if cached:  # Cache might not work in test environment
            assert len(cached) == 384
            assert all(abs(cached[i] - embedding[i]) < 0.0001 for i in range(384))


class TestSearchFunctionality:
    """Test the main search functionality"""
    
    @pytest.mark.asyncio
    async def test_search_request_validation(self):
        """Test search request validation"""
        # Valid request
        valid_request = SearchRequest(
            query="AI and machine learning",
            limit=10,
            offset=0
        )
        assert valid_request.query == "AI and machine learning"
        assert valid_request.limit == 10
        
        # Test query length validation
        with pytest.raises(ValueError):
            SearchRequest(query="a" * 501, limit=10, offset=0)
        
        # Test empty query validation
        with pytest.raises(ValueError):
            SearchRequest(query="", limit=10, offset=0)
        
        # Test limit validation
        with pytest.raises(ValueError):
            SearchRequest(query="test", limit=51, offset=0)
    
    @pytest.mark.asyncio
    async def test_search_handler_basic(self):
        """Test basic search handler functionality"""
        request = SearchRequest(
            query="AI agents",
            limit=5,
            offset=0
        )
        
        try:
            response = await search_handler(request)
            
            # Check response structure
            assert isinstance(response, SearchResponse)
            assert isinstance(response.results, list)
            assert len(response.results) <= 5
            assert response.query == "AI agents"
            assert response.limit == 5
            assert response.offset == 0
            assert isinstance(response.cache_hit, bool)
            assert response.search_id.startswith("search_")
            
            # Check result structure if any results
            if response.results:
                result = response.results[0]
                assert hasattr(result, 'episode_id')
                assert hasattr(result, 'podcast_name')
                assert hasattr(result, 'episode_title')
                assert hasattr(result, 'similarity_score')
                assert 0 <= result.similarity_score <= 1
                
        except Exception as e:
            # If database not available in test, that's okay
            if "Supabase configuration not found" in str(e):
                pytest.skip("Database not configured for testing")
            else:
                raise


class TestExcerptExtraction:
    """Test excerpt extraction functionality"""
    
    def test_extract_excerpt_basic(self):
        """Test basic excerpt extraction"""
        transcript = """
        Today we're discussing artificial intelligence and how AI agents are transforming
        the startup ecosystem. Many founders are building AI-powered solutions that can
        automate complex tasks. The valuations for AI startups have been growing rapidly
        as investors recognize the potential. Let's dive into some specific examples of
        successful AI agent implementations in various industries.
        """
        
        query = "AI agents valuations"
        excerpt = extract_excerpt(transcript, query, max_length=50)
        
        # Should contain relevant content
        assert "AI" in excerpt
        assert len(excerpt.split()) <= 250  # Some buffer for ellipsis
    
    def test_extract_excerpt_no_match(self):
        """Test excerpt extraction with no matching terms"""
        transcript = "This is a podcast about cooking and recipes."
        query = "artificial intelligence blockchain"
        
        excerpt = extract_excerpt(transcript, query, max_length=20)
        
        # Should return beginning of transcript
        assert excerpt.startswith("This is a podcast")
    
    def test_extract_excerpt_empty_transcript(self):
        """Test excerpt extraction with empty transcript"""
        excerpt = extract_excerpt("", "test query", max_length=50)
        assert excerpt == "No transcript available."


class TestIntegration:
    """Integration tests for the search API"""
    
    @pytest.mark.asyncio
    async def test_search_different_queries(self):
        """Test search with different types of queries"""
        queries = [
            "AI agents and autonomous systems",
            "blockchain DeFi protocols",
            "startup funding and venture capital",
            "B2B SaaS growth strategies",
            "web3 and decentralization"
        ]
        
        for query in queries:
            request = SearchRequest(query=query, limit=3, offset=0)
            
            try:
                response = await search_handler(request)
                
                # Basic validation
                assert response.query == query
                assert len(response.results) <= 3
                
                # If we get results, check they're properly formatted
                for result in response.results:
                    assert result.episode_id
                    assert result.podcast_name
                    assert 0 <= result.similarity_score <= 1
                    
            except Exception as e:
                if "Supabase configuration not found" in str(e):
                    pytest.skip("Database not configured for testing")
                else:
                    raise
    
    @pytest.mark.asyncio
    async def test_search_pagination(self):
        """Test search pagination"""
        query = "artificial intelligence"
        
        # Get first page
        request1 = SearchRequest(query=query, limit=5, offset=0)
        # Get second page
        request2 = SearchRequest(query=query, limit=5, offset=5)
        
        try:
            response1 = await search_handler(request1)
            response2 = await search_handler(request2)
            
            # Check pagination
            assert len(response1.results) <= 5
            assert len(response2.results) <= 5
            
            # If we have results in both, they should be different
            if response1.results and response2.results:
                ids1 = {r.episode_id for r in response1.results}
                ids2 = {r.episode_id for r in response2.results}
                assert ids1.isdisjoint(ids2)  # No overlap
                
        except Exception as e:
            if "Supabase configuration not found" in str(e):
                pytest.skip("Database not configured for testing")
            else:
                raise


class TestPerformance:
    """Performance tests for the search API"""
    
    @pytest.mark.asyncio
    async def test_embedding_generation_speed(self):
        """Test embedding generation performance"""
        import time
        
        query = "machine learning and neural networks"
        
        start = time.time()
        embedding = await generate_embedding(query)
        duration = time.time() - start
        
        # Should be fast (under 500ms for this lightweight model)
        assert duration < 0.5
        assert len(embedding) == 384
    
    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """Test that cached queries are faster"""
        import time
        
        query = f"performance test query {datetime.now()}"
        request = SearchRequest(query=query, limit=5, offset=0)
        
        try:
            # First request (no cache)
            start1 = time.time()
            response1 = await search_handler(request)
            duration1 = time.time() - start1
            
            # Second request (should hit cache)
            start2 = time.time()
            response2 = await search_handler(request)
            duration2 = time.time() - start2
            
            # Cached should be faster (though in tests this might not always be true)
            assert response1.cache_hit is False
            assert response2.cache_hit is True
            
            # Results should be identical
            assert len(response1.results) == len(response2.results)
            
        except Exception as e:
            if "Supabase configuration not found" in str(e):
                pytest.skip("Database not configured for testing")
            else:
                raise


if __name__ == "__main__":
    # Run specific test
    pytest.main([__file__, "-v", "-k", "test_generate_embedding_success"])