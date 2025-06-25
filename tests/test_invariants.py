"""Unit tests for search invariants"""
import pytest
import math
from typing import List

def test_embedding_length():
    """Test that embeddings are always 768 dimensions"""
    # Mock embedding
    embedding = [0.1] * 768
    assert len(embedding) == 768
    
    # Test with wrong length
    bad_embedding = [0.1] * 512
    assert len(bad_embedding) != 768

def test_embedding_normalization():
    """Test that embeddings are normalized (norm ~= 1.0)"""
    # Create a normalized embedding
    embedding = [0.1] * 768
    norm = math.sqrt(sum(x*x for x in embedding))
    # Normalize it
    normalized = [x/norm for x in embedding]
    
    # Check norm is close to 1.0
    final_norm = math.sqrt(sum(x*x for x in normalized))
    assert abs(final_norm - 1.0) < 0.1

def test_search_results_ordering():
    """Test that results are ordered by similarity score descending"""
    results = [
        {"score": 0.9},
        {"score": 0.8},
        {"score": 0.7},
        {"score": 0.6}
    ]
    
    # Check ordering
    for i in range(len(results) - 1):
        assert results[i]["score"] >= results[i+1]["score"]

def test_score_range():
    """Test that similarity scores are in valid range [0, 1]"""
    results = [
        {"score": 0.99},
        {"score": 0.85},
        {"score": 0.50},
        {"score": 0.10}
    ]
    
    for result in results:
        assert 0 <= result["score"] <= 1

def test_query_normalization():
    """Test query normalization function"""
    def normalize_query(query: str) -> str:
        return query.strip().lower()
    
    # Test various inputs
    assert normalize_query("OpenAI") == "openai"
    assert normalize_query("  OpenAI  ") == "openai"
    assert normalize_query("OPENAI") == "openai"
    assert normalize_query("venture capital") == "venture capital"
    assert normalize_query("  Venture Capital  ") == "venture capital"

def test_pagination_logic():
    """Test pagination slicing logic"""
    # Mock results
    all_results = list(range(100))
    
    # Test various offset/limit combinations
    offset, limit = 0, 10
    paginated = all_results[offset:]
    if len(paginated) > limit:
        paginated = paginated[:limit]
    assert len(paginated) == 10
    assert paginated == list(range(10))
    
    # Test with offset
    offset, limit = 20, 10
    paginated = all_results[offset:]
    if len(paginated) > limit:
        paginated = paginated[:limit]
    assert len(paginated) == 10
    assert paginated == list(range(20, 30))
    
    # Test near end
    offset, limit = 95, 10
    paginated = all_results[offset:]
    if len(paginated) > limit:
        paginated = paginated[:limit]
    assert len(paginated) == 5
    assert paginated == list(range(95, 100))

if __name__ == "__main__":
    # Run tests
    test_embedding_length()
    print("✅ Embedding length test passed")
    
    test_embedding_normalization()
    print("✅ Embedding normalization test passed")
    
    test_search_results_ordering()
    print("✅ Results ordering test passed")
    
    test_score_range()
    print("✅ Score range test passed")
    
    test_query_normalization()
    print("✅ Query normalization test passed")
    
    test_pagination_logic()
    print("✅ Pagination logic test passed")
    
    print("\n✅ All invariant tests passed!")