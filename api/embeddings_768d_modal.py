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
                    timeout=aiohttp.ClientTimeout(total=30)  # Increased timeout for cold starts
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        embedding = data.get("embedding", data)  # Handle different response formats
                        logger.info(f"Generated 768D embedding via Modal for: {query[:50]}...")
                        return embedding
                    else:
                        error_text = await response.text()
                        logger.error(f"Modal API error {response.status}: {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("Modal API timeout - function may be cold starting (30s timeout)")
            return None
        except Exception as e:
            logger.error(f"Modal embedding error: {e}")
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