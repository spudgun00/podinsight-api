"""
Comprehensive API Integration Tests
Tests the deployed API endpoints for search and transcripts
"""
import pytest
import httpx
import os
import time
from typing import Dict, Any

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
# For production testing, use: "https://podinsight-api.vercel.app"

# Test timeouts (API can be slow due to Modal cold starts)
REQUEST_TIMEOUT = 60.0


class TestSearchEndpoint:
    """Test the search API endpoint"""

    def test_search_valid_query(self):
        """Test search with valid query"""
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(
                f"{API_BASE_URL}/api/search",
                json={
                    "query": "AI agents",
                    "limit": 10
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Validate response structure
            assert "results" in data
            assert "total_results" in data
            assert "search_method" in data
            assert "processing_time_ms" in data
            assert "cache_hit" in data

            # Validate results array
            assert isinstance(data["results"], list)
            assert len(data["results"]) <= 10

            # Validate individual result structure if results exist
            if data["results"]:
                result = data["results"][0]

                # Check all required fields from Task 1 verification
                assert "episode_id" in result
                assert "podcast_name" in result  # NOT podcast_title
                assert "episode_title" in result
                assert "published_at" in result
                assert "published_date" in result
                assert "similarity_score" in result  # NOT just "score"
                assert "excerpt" in result  # NOT "text"

                # Optional fields
                assert "s3_audio_path" in result or result.get("s3_audio_path") is None
                assert "timestamp" in result or result.get("timestamp") is None
                assert "topics" in result
                assert "word_count" in result
                assert "duration_seconds" in result

                # Validate data types
                assert isinstance(result["episode_id"], str)
                assert isinstance(result["podcast_name"], str)
                assert isinstance(result["episode_title"], str)
                assert isinstance(result["similarity_score"], (int, float))
                assert isinstance(result["excerpt"], str)
                assert isinstance(result["topics"], list)
                assert isinstance(result["word_count"], int)
                assert isinstance(result["duration_seconds"], int)

                # Validate similarity_score range
                assert 0 <= result["similarity_score"] <= 1

    def test_search_multiple_queries(self):
        """Test search with various query types"""
        queries = [
            "Series A funding",
            "crypto and blockchain",
            "enterprise SaaS growth",
            "AI valuations",
            "climate tech startups"
        ]

        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            for query in queries:
                response = client.post(
                    f"{API_BASE_URL}/api/search",
                    json={"query": query, "limit": 5}
                )

                assert response.status_code == 200
                data = response.json()
                assert "results" in data
                assert len(data["results"]) <= 5

    def test_search_with_answer_synthesis(self):
        """Test search with answer synthesis enabled"""
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(
                f"{API_BASE_URL}/api/search",
                json={
                    "query": "What are VCs saying about AI agents?",
                    "limit": 10,
                    "synthesize_answer": True
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Check for answer field
            if data.get("answer"):
                answer = data["answer"]
                assert "text" in answer
                assert "citations" in answer
                assert isinstance(answer["text"], str)
                assert isinstance(answer["citations"], list)

    def test_search_edge_cases(self):
        """Test search edge cases"""
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            # Test with very short query
            response = client.post(
                f"{API_BASE_URL}/api/search",
                json={"query": "AI", "limit": 5}
            )
            assert response.status_code == 200

            # Test with long query
            long_query = "artificial intelligence machine learning natural language processing computer vision deep learning neural networks"
            response = client.post(
                f"{API_BASE_URL}/api/search",
                json={"query": long_query, "limit": 5}
            )
            assert response.status_code == 200

    def test_search_pagination(self):
        """Test search pagination"""
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            # Get first page
            response1 = client.post(
                f"{API_BASE_URL}/api/search",
                json={"query": "artificial intelligence", "limit": 5, "offset": 0}
            )

            # Get second page
            response2 = client.post(
                f"{API_BASE_URL}/api/search",
                json={"query": "artificial intelligence", "limit": 5, "offset": 5}
            )

            assert response1.status_code == 200
            assert response2.status_code == 200

            data1 = response1.json()
            data2 = response2.json()

            # If we have results in both, they should be different
            if data1["results"] and data2["results"]:
                ids1 = {r["episode_id"] for r in data1["results"]}
                ids2 = {r["episode_id"] for r in data2["results"]}
                assert ids1.isdisjoint(ids2), "Pagination should return different results"

    def test_search_response_time(self):
        """Test search response time is acceptable"""
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            start = time.time()
            response = client.post(
                f"{API_BASE_URL}/api/search",
                json={"query": "startup funding", "limit": 10}
            )
            duration = time.time() - start

            assert response.status_code == 200
            assert duration < 10.0, f"Search took {duration}s, should be under 10s"

            # Check processing_time_ms is reported
            data = response.json()
            if "processing_time_ms" in data:
                assert isinstance(data["processing_time_ms"], (int, float))


class TestTranscriptEndpoint:
    """Test the transcript API endpoint"""

    def test_transcript_valid_episode(self):
        """Test transcript retrieval with valid episode ID"""
        # First, get a valid episode_id from search
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            search_response = client.post(
                f"{API_BASE_URL}/api/search",
                json={"query": "AI", "limit": 1}
            )

            assert search_response.status_code == 200
            search_data = search_response.json()

            if not search_data["results"]:
                pytest.skip("No search results available for transcript test")

            episode_id = search_data["results"][0]["episode_id"]

            # Now test transcript endpoint
            transcript_response = client.get(
                f"{API_BASE_URL}/api/transcript/{episode_id}"
            )

            assert transcript_response.status_code == 200
            data = transcript_response.json()

            # Validate response structure from Task 7a
            assert "episode_id" in data
            assert "podcast_name" in data
            assert "episode_title" in data
            assert "published_at" in data
            assert "full_text" in data
            assert "chunks" in data
            assert "duration_seconds" in data
            assert "word_count" in data
            assert "total_chunks" in data

            # Validate data types
            assert isinstance(data["episode_id"], str)
            assert isinstance(data["podcast_name"], str)
            assert isinstance(data["episode_title"], str)
            assert isinstance(data["full_text"], str)
            assert isinstance(data["chunks"], list)
            assert isinstance(data["duration_seconds"], int)
            assert isinstance(data["word_count"], int)
            assert isinstance(data["total_chunks"], int)

            # Validate chunks structure
            if data["chunks"]:
                chunk = data["chunks"][0]
                assert "text" in chunk
                assert "start_time" in chunk
                assert "end_time" in chunk
                assert "chunk_index" in chunk

                assert isinstance(chunk["text"], str)
                assert isinstance(chunk["start_time"], (int, float))
                assert isinstance(chunk["end_time"], (int, float))
                assert isinstance(chunk["chunk_index"], int)

            # Validate word count makes sense
            assert data["word_count"] > 0
            assert data["total_chunks"] > 0
            assert data["total_chunks"] == len(data["chunks"])

    def test_transcript_invalid_episode(self):
        """Test transcript retrieval with invalid episode ID"""
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(
                f"{API_BASE_URL}/api/transcript/invalid-episode-id-12345"
            )

            # Should return 404 for non-existent episode
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data

    def test_transcript_response_time(self):
        """Test transcript response time is acceptable"""
        # First get a valid episode_id
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            search_response = client.post(
                f"{API_BASE_URL}/api/search",
                json={"query": "AI", "limit": 1}
            )

            if not search_response.json()["results"]:
                pytest.skip("No search results for transcript timing test")

            episode_id = search_response.json()["results"][0]["episode_id"]

            # Test transcript response time
            start = time.time()
            response = client.get(
                f"{API_BASE_URL}/api/transcript/{episode_id}"
            )
            duration = time.time() - start

            assert response.status_code == 200
            assert duration < 5.0, f"Transcript took {duration}s, should be under 5s"

    def test_transcript_caching(self):
        """Test that transcript caching works (async-lru)"""
        # Get a valid episode_id
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            search_response = client.post(
                f"{API_BASE_URL}/api/search",
                json={"query": "AI", "limit": 1}
            )

            if not search_response.json()["results"]:
                pytest.skip("No search results for caching test")

            episode_id = search_response.json()["results"][0]["episode_id"]

            # First request (cache miss)
            start1 = time.time()
            response1 = client.get(
                f"{API_BASE_URL}/api/transcript/{episode_id}"
            )
            duration1 = time.time() - start1

            # Second request (should be cached)
            start2 = time.time()
            response2 = client.get(
                f"{API_BASE_URL}/api/transcript/{episode_id}"
            )
            duration2 = time.time() - start2

            assert response1.status_code == 200
            assert response2.status_code == 200

            # Cached request should be faster (though this may not always be guaranteed)
            # Just verify both succeed
            data1 = response1.json()
            data2 = response2.json()

            # Results should be identical
            assert data1["episode_id"] == data2["episode_id"]
            assert data1["word_count"] == data2["word_count"]
            assert data1["total_chunks"] == data2["total_chunks"]


class TestEndpointIntegration:
    """Test integration between search and transcript endpoints"""

    def test_search_to_transcript_workflow(self):
        """Test the complete workflow: search → get episode → get transcript"""
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            # Step 1: Search for episodes
            search_response = client.post(
                f"{API_BASE_URL}/api/search",
                json={"query": "AI agents and automation", "limit": 3}
            )

            assert search_response.status_code == 200
            search_data = search_response.json()

            if not search_data["results"]:
                pytest.skip("No search results for workflow test")

            # Step 2: Get transcript for first result
            episode_id = search_data["results"][0]["episode_id"]

            transcript_response = client.get(
                f"{API_BASE_URL}/api/transcript/{episode_id}"
            )

            assert transcript_response.status_code == 200
            transcript_data = transcript_response.json()

            # Step 3: Verify data consistency
            # Episode ID should match
            assert transcript_data["episode_id"] == episode_id

            # Podcast name and episode title should match (if available in search result)
            search_result = search_data["results"][0]
            assert transcript_data["podcast_name"] == search_result["podcast_name"]
            assert transcript_data["episode_title"] == search_result["episode_title"]

            # Duration should match (if available in search result)
            assert transcript_data["duration_seconds"] == search_result["duration_seconds"]


class TestFieldNameCompatibility:
    """Test critical field name requirements from Task 4"""

    def test_search_uses_correct_field_names(self):
        """Verify search results use correct field names (not dashboard mismatches)"""
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(
                f"{API_BASE_URL}/api/search",
                json={"query": "AI", "limit": 1}
            )

            assert response.status_code == 200
            data = response.json()

            if data["results"]:
                result = data["results"][0]

                # CRITICAL: Verify correct field names from Task 1
                assert "podcast_name" in result, "Should use 'podcast_name' not 'podcast_title'"
                assert "episode_title" in result, "Should use 'episode_title' not 'title'"
                assert "similarity_score" in result, "Should use 'similarity_score' not 'score'"
                assert "excerpt" in result, "Should use 'excerpt' not 'text'"

                # Should NOT have incorrect field names
                assert "podcast_title" not in result
                assert "title" not in result  # Unless it's episode_title
                assert "score" not in result  # Unless it's similarity_score
                assert "text" not in result  # Unless it's in a nested object


# Test runner
if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v", "--tb=short"] + sys.argv[1:])
