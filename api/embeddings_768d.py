#!/usr/bin/env python3
"""
768D Embeddings using Instructor-XL model
Optimized for venture capital podcast content
"""

import os
import logging
from typing import List, Optional
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

class InstructorXLEmbedder:
    """Handles 768D embeddings for improved semantic search"""
    
    def __init__(self):
        """Initialize the Instructor-XL model"""
        self.model = None
        self.instruction = "Represent the venture capital podcast discussion:"
        self._initialize_model()
        
    def _initialize_model(self):
        """Load the model (cached after first download)"""
        try:
            logger.info("Loading Instructor-XL model...")
            self.model = SentenceTransformer('hkunlp/instructor-xl')
            logger.info("Instructor-XL model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Instructor-XL model: {e}")
            raise
    
    def encode_query(self, query: str) -> List[float]:
        """
        Encode search query to 768D vector
        
        Args:
            query: Search query text
            
        Returns:
            List of 768 float values
        """
        if not self.model:
            raise RuntimeError("Model not initialized")
            
        # Format for Instructor model: [instruction, text]
        embedding = self.model.encode([[self.instruction, query]])[0]
        
        # Convert to list for JSON serialization
        return embedding.tolist()
    
    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Encode multiple texts to 768D vectors
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors
        """
        if not self.model:
            raise RuntimeError("Model not initialized")
            
        # Format for Instructor model
        formatted_texts = [[self.instruction, text] for text in texts]
        
        embeddings = self.model.encode(formatted_texts)
        
        # Convert to list for JSON serialization
        return [emb.tolist() for emb in embeddings]

# Singleton instance
_embedder = None

def get_embedder() -> InstructorXLEmbedder:
    """Get or create singleton embedder instance"""
    global _embedder
    if _embedder is None:
        _embedder = InstructorXLEmbedder()
    return _embedder