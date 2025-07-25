"""
768D Embeddings using Modal.com hosted Instructor-XL
Replaces local model with Modal serverless function
"""

import os
import logging
import aiohttp
from typing import List, Optional, Tuple, Union
import asyncio
import json
import time
from datetime import datetime

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

    async def _encode_query_async_with_retry(self, query: str, retries: int = 1,
                                            session_id: Optional[str] = None,
                                            return_timing: bool = False) -> Union[Optional[List[float]], Optional[Tuple[List[float], float]]]:
        """
        Async method with retry logic for cold starts

        Args:
            query: Search query text
            retries: Number of retries (default 1)
            session_id: Optional session ID for tracking
            return_timing: If True, returns (embedding, elapsed_time) tuple

        Returns:
            List of 768 float values or None if error
            If return_timing=True, returns (embedding, elapsed_time) tuple or None
        """
        total_start = time.time()

        for attempt in range(retries + 1):
            try:
                result = await self._encode_query_async(query, session_id, return_timing)
                if result is not None:
                    return result
            except asyncio.TimeoutError:
                if attempt < retries:
                    logger.info(f"Modal timeout on attempt {attempt + 1}, retrying...")
                    await asyncio.sleep(0.5)  # Short delay before retry
                else:
                    total_elapsed = time.time() - total_start
                    logger.error(f"Modal timeout after {retries + 1} attempts, total time: {total_elapsed:.2f}s")

                    # Log failure analytics
                    analytics_data = {
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "session_id": session_id,
                        "request_type": "embedding",
                        "modal": {
                            "response_time": total_elapsed,
                            "is_cold_start": True,  # Timeouts are usually cold starts
                            "error": "timeout",
                            "attempts": retries + 1
                        }
                    }
                    logger.info(f"MODAL_ANALYTICS: {json.dumps(analytics_data)}")
                    raise
        return None

    async def _encode_query_async(self, query: str, session_id: Optional[str] = None,
                                  return_timing: bool = False) -> Union[Optional[List[float]], Optional[Tuple[List[float], float]]]:
        """
        Async method to encode search query to 768D vector using Modal

        Args:
            query: Search query text
            session_id: Optional session ID for tracking
            return_timing: If True, returns (embedding, elapsed_time) tuple

        Returns:
            List of 768 float values or None if error
            If return_timing=True, returns (embedding, elapsed_time) tuple or None
        """
        start_time = time.time()
        logger.info(f"🔄 Starting Modal embedding request for: '{query[:50]}...'")

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
                    timeout=aiohttp.ClientTimeout(total=25)  # 25s timeout to handle cold starts
                ) as response:
                    elapsed = time.time() - start_time
                    is_cold_start = elapsed > 5.0

                    # Extract instance information from headers
                    response_headers = dict(response.headers)
                    instance_id = (response_headers.get('X-Modal-Container-ID') or
                                 response_headers.get('X-Modal-Task-ID') or
                                 response_headers.get('X-Instance-ID') or
                                 response_headers.get('X-Served-By'))

                    # Log analytics data
                    analytics_data = {
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "session_id": session_id,
                        "request_type": "embedding",
                        "modal": {
                            "response_time": elapsed,
                            "is_cold_start": is_cold_start,
                            "status_code": response.status,
                            "headers": response_headers,
                            "instance_id": instance_id,
                            "connection_reused": False  # Will enhance this later
                        }
                    }
                    logger.info(f"MODAL_ANALYTICS: {json.dumps(analytics_data)}")

                    # Log based on response time to identify cold/warm starts
                    if is_cold_start:
                        logger.info(f"🥶 Modal API responded in {elapsed:.2f}s (cold start) with status {response.status}")
                    else:
                        logger.info(f"🔥 Modal API responded in {elapsed:.2f}s (warm) with status {response.status}")

                    if response.status == 200:
                        data = await response.json()
                        embedding = data.get("embedding", data)  # Handle different response formats

                        # Un-nest accidental double list
                        if isinstance(embedding, list) and len(embedding) == 1 and isinstance(embedding[0], list):
                            logger.warning(f"Detected nested embedding array, flattening...")
                            embedding = embedding[0]

                        logger.info(f"✅ Generated 768D embedding via Modal for: {query[:50]}... (dim: {len(embedding) if embedding else 0}, total time: {elapsed:.2f}s)")

                        if return_timing:
                            return embedding, elapsed
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
