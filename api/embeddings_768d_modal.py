"""
768D Embeddings using Modal.com hosted Instructor-XL
Replaces local model with Modal serverless function
"""

import os
import logging
import aiohttp
from typing import List, Optional
import asyncio

logger = logging.getLogger(__name__)

class ModalInstructorXLEmbedder:
    """Handles 768D embeddings via Modal.com"""

    def __init__(self):
        """Initialize Modal configuration"""
        # Get from environment or Modal dashboard
        self.modal_url = os.getenv('MODAL_EMBEDDING_URL', 'https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run')
        self.modal_token = None  # Public endpoint, no auth needed

    def encode_query(self, query: str) -> Optional[List[float]]:
        """
        Encode search query to 768D vector using Modal (synchronous wrapper)

        Args:
            query: Search query text

        Returns:
            List of 768 float values or None if error
        """
        # Check if there's already an event loop running
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._encode_query_async(query))
                return future.result()
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._encode_query_async(query))

    async def _encode_query_async(self, query: str) -> Optional[List[float]]:
        """
        Async method to encode search query to 768D vector using Modal

        Args:
            query: Search query text

        Returns:
            List of 768 float values or None if error
        """
        import time
        start_time = time.time()
        logger.info(f"Starting Modal embedding request for: '{query[:50]}...'")

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json"
                }
                # No auth header since it's a public endpoint

                payload = {"text": query}

                # Use the correct endpoint (no /embed suffix)
                embed_url = self.modal_url

                async with session.post(
                    embed_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=20)  # Reduced to 20s to leave room for other operations
                ) as response:
                    elapsed = time.time() - start_time
                    logger.info(f"Modal API responded in {elapsed:.2f}s with status {response.status}")

                    if response.status == 200:
                        data = await response.json()
                        embedding = data.get("embedding", data)  # Handle different response formats

                        # Un-nest accidental double list
                        if isinstance(embedding, list) and len(embedding) == 1 and isinstance(embedding[0], list):
                            logger.warning(f"Detected nested embedding array, flattening...")
                            embedding = embedding[0]

                        logger.info(f"Generated 768D embedding via Modal for: {query[:50]}... (dim: {len(embedding) if embedding else 0})")
                        return embedding
                    else:
                        error_text = await response.text()
                        logger.error(f"Modal API error {response.status}: {error_text}")
                        return None

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"Modal API timeout after {elapsed:.2f}s - function may be cold starting")
            return None
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Modal embedding error after {elapsed:.2f}s: {e}")
            return None

    async def encode_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """
        Encode multiple texts to 768D vectors

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors or None if error
        """
        # No auth needed for public endpoint

        try:
            # Use the batch endpoint
            batch_url = f"{self.modal_url}/embed_batch"

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json"
                }
                # No auth header since it's a public endpoint

                payload = {"texts": texts}

                async with session.post(
                    batch_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)  # Longer timeout for batch
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        embeddings = data.get("embeddings", data)
                        logger.info(f"Generated {len(embeddings)} embeddings via Modal")
                        return embeddings
                    else:
                        # Fallback to individual requests
                        logger.warning("Batch endpoint failed, falling back to individual requests")
                        results = []
                        for text in texts:
                            embedding = await self._encode_query_async(text)
                            if embedding:
                                results.append(embedding)
                            else:
                                return None  # Fail if any request fails
                        return results

        except Exception as e:
            logger.error(f"Modal batch embedding error: {e}")
            return None

# Singleton instance
_embedder = None

def get_embedder() -> ModalInstructorXLEmbedder:
    """Get or create singleton embedder instance"""
    global _embedder
    if _embedder is None:
        _embedder = ModalInstructorXLEmbedder()
    return _embedder
