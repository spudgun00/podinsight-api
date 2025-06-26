#!/usr/bin/env python3
"""
Test the embedder that's being used by the search handler
"""

import asyncio
import sys
sys.path.append('/Users/jamesgill/PodInsights/podinsight-api')

from api.embeddings_768d_modal import get_embedder
from api.search_lightweight_768d import generate_embedding_768d_local

async def test_embedder():
    """Test the exact embedder used by the search handler"""

    print("🔗 Testing ModalInstructorXLEmbedder...")

    try:
        # Test direct embedder
        print("   Testing direct embedder...")
        embedder = get_embedder()
        print(f"   Embedder created: {embedder}")

        # Test the sync method
        try:
            result = embedder.encode_query("AI startup valuations")
            print(f"   ✅ Direct embedding generated: length={len(result) if result else 'None'}")
        except Exception as e:
            print(f"   ❌ Direct embedding failed: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")

        # Test the async wrapper (what the search handler uses)
        print("\n   Testing async wrapper...")
        try:
            result = await generate_embedding_768d_local("AI startup valuations")
            print(f"   ✅ Async embedding generated: length={len(result) if result else 'None'}")
        except Exception as e:
            print(f"   ❌ Async embedding failed: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")

    except Exception as e:
        print(f"   ❌ Embedder creation failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_embedder())
