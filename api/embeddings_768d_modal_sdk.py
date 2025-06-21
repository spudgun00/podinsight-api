"""
768D Embeddings using Modal SDK (not REST API)
Direct Python SDK calls to Modal
"""

import os
import logging
from typing import List, Optional
import modal

logger = logging.getLogger(__name__)

class ModalSDKEmbedder:
    """Handles 768D embeddings via Modal Python SDK"""
    
    def __init__(self):
        """Initialize Modal SDK connection"""
        self.model_cls = None
        self._connect_to_modal()
    
    def _connect_to_modal(self):
        """Connect to deployed Modal function"""
        try:
            # Look up the deployed function
            self.model_cls = modal.Cls.lookup("podinsight-instructor-xl", "InstructorXLEmbedder")
            logger.info("Connected to Modal function")
        except Exception as e:
            logger.error(f"Failed to connect to Modal: {e}")
    
    async def encode_query(self, query: str) -> Optional[List[float]]:
        """
        Encode search query to 768D vector using Modal
        
        Args:
            query: Search query text
            
        Returns:
            List of 768 float values or None if error
        """
        if not self.model_cls:
            logger.error("Modal function not connected")
            return None
            
        try:
            # Call the remote function
            result = self.model_cls().embed_text.remote(query)
            logger.info(f"Generated 768D embedding for: {query[:50]}...")
            return result
            
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
        if not self.model_cls:
            logger.error("Modal function not connected")
            return None
            
        try:
            # Call the batch function
            result = self.model_cls().embed_batch.remote(texts)
            logger.info(f"Generated {len(result)} embeddings via Modal")
            return result
            
        except Exception as e:
            logger.error(f"Modal batch embedding error: {e}")
            return None

# Singleton instance
_embedder = None

def get_embedder() -> ModalSDKEmbedder:
    """Get or create singleton embedder instance"""
    global _embedder
    if _embedder is None:
        _embedder = ModalSDKEmbedder()
    return _embedder