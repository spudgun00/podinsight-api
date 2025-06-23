#!/usr/bin/env python3
"""
Test the similarity_search_ranked function directly
"""
import asyncio
from api.database import get_pool
import json

async def test_db_function():
    """Test similarity_search_ranked function"""
    pool = get_pool()
    
    # Create a test embedding (384D vector)
    test_embedding = [0.1] * 384
    embedding_str = "[" + ",".join(map(str, test_embedding)) + "]"
    
    def search_query(client):
        return client.rpc(
            "similarity_search_ranked",
            {
                "query_embedding": embedding_str,
                "match_count": 5
            }
        ).execute()
    
    try:
        results = await pool.execute_with_retry(search_query)
        print(f"Results count: {len(results.data) if results.data else 0}")
        
        if results.data and len(results.data) > 0:
            print("\nFirst result structure:")
            first_result = results.data[0]
            print(json.dumps(first_result, indent=2))
            print("\nFields available:", list(first_result.keys()))
        else:
            print("No results returned")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_db_function())