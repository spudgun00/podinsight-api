#!/usr/bin/env python3
"""
MongoDB Search Handler for PodInsightHQ
Provides async search functionality with real transcript excerpts
"""

import os
import re
import time
from typing import List, Dict, Optional, Any
from datetime import datetime
from pymongo import MongoClient, TEXT
import asyncio
from collections import OrderedDict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoSearchHandler:
    def __init__(self, mongodb_uri: Optional[str] = None):
        """Initialize MongoDB connection and search handler"""
        self.mongodb_uri = mongodb_uri or os.getenv('MONGODB_URI')
        if not self.mongodb_uri:
            logger.warning("MONGODB_URI not set - search will not work!")
            self.client = None
            self.db = None
        else:
            # Use synchronous PyMongo client for serverless reliability
            self.client = MongoClient(
                self.mongodb_uri,
                maxPoolSize=10,
                minPoolSize=2,
                serverSelectionTimeoutMS=5000
            )
            self.db = self.client['podinsight']
            self.collection = self.db['transcripts']
        
        # Simple in-memory cache (LRU with max 100 entries)
        self.cache = OrderedDict()
        self.cache_ttl = 300  # 5 minutes
        self.max_cache_size = 100
        
    async def search_transcripts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search transcripts using MongoDB text search
        Returns list of episodes with excerpts
        """
        if self.db is None:
            logger.error("MongoDB not connected")
            return []
            
        # Check cache first
        cache_key = f"{query}:{limit}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Cache hit for query: {query}")
            return cached_result
            
        try:
            start_time = time.time()
            
            # MongoDB text search with score projection (synchronous)
            cursor = self.collection.find(
                {"$text": {"$search": query}},
                {
                    "score": {"$meta": "textScore"},
                    "episode_id": 1,
                    "podcast_name": 1,
                    "episode_title": 1,
                    "published_at": 1,
                    "full_text": 1,
                    "topics": 1,
                    "word_count": 1,
                    "segments": 1
                }
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            results = []
            for doc in cursor:
                # Extract excerpt around search match
                excerpt = self.extract_excerpt(doc.get('full_text', ''), query)
                
                # Get timestamp if we can find the excerpt in segments
                timestamp = self._find_timestamp_for_excerpt(
                    doc.get('segments', []), 
                    excerpt
                )
                
                result = {
                    'episode_id': doc['episode_id'],
                    'podcast_name': doc.get('podcast_name', 'Unknown'),
                    'episode_title': doc.get('episode_title', 'Untitled'),
                    'published_at': doc.get('published_at', datetime.now()).isoformat(),
                    'excerpt': excerpt,
                    'relevance_score': doc['score'],
                    'topics': doc.get('topics', []),
                    'word_count': doc.get('word_count', 0),
                    'timestamp': timestamp
                }
                results.append(result)
            
            elapsed = time.time() - start_time
            logger.info(f"Search for '{query}' took {elapsed:.2f}s, found {len(results)} results")
            
            # Cache the results
            self._add_to_cache(cache_key, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def extract_excerpt(self, full_text: str, query: str, max_words: int = 200) -> str:
        """
        Extract excerpt around search query match
        Returns text window with highlighted terms
        """
        if not full_text:
            return "No transcript available."
            
        # Clean up the query and create case-insensitive pattern
        query_terms = query.split()
        pattern = '|'.join(re.escape(term) for term in query_terms)
        
        # Find first match
        match = re.search(pattern, full_text, re.IGNORECASE)
        
        if not match:
            # No exact match, return beginning of text
            words = full_text.split()[:max_words]
            excerpt = ' '.join(words)
            if len(full_text.split()) > max_words:
                excerpt += '...'
            return excerpt
        
        # Get position of match
        match_start = match.start()
        match_end = match.end()
        
        # Find word boundaries around match
        # Go back to find start of excerpt
        excerpt_start = match_start
        word_count = 0
        for i in range(match_start - 1, -1, -1):
            if full_text[i] == ' ':
                word_count += 1
                if word_count >= max_words // 2:
                    excerpt_start = i + 1
                    break
        else:
            excerpt_start = 0
            
        # Go forward to find end of excerpt
        excerpt_end = match_end
        word_count = 0
        for i in range(match_end, len(full_text)):
            if full_text[i] == ' ':
                word_count += 1
                if word_count >= max_words // 2:
                    excerpt_end = i
                    break
        else:
            excerpt_end = len(full_text)
        
        # Extract and format excerpt
        excerpt = full_text[excerpt_start:excerpt_end].strip()
        
        # Add ellipsis if needed
        if excerpt_start > 0:
            excerpt = '...' + excerpt
        if excerpt_end < len(full_text):
            excerpt = excerpt + '...'
            
        # Highlight matched terms (wrap in **bold**)
        for term in query_terms:
            excerpt = re.sub(
                f'({re.escape(term)})',
                r'**\1**',
                excerpt,
                flags=re.IGNORECASE
            )
            
        return excerpt
    
    async def get_episode_by_id(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch single episode by ID for playback
        """
        if self.db is None:
            logger.error("MongoDB not connected")
            return None
            
        try:
            doc = self.collection.find_one({'episode_id': episode_id})
            if doc:
                # Remove MongoDB _id field
                doc.pop('_id', None)
                return doc
            return None
        except Exception as e:
            logger.error(f"Error fetching episode {episode_id}: {e}")
            return None
    
    def _find_timestamp_for_excerpt(self, segments: List[Dict], excerpt: str) -> Optional[Dict]:
        """
        Find timestamp for excerpt in segments
        Returns {start_time, end_time} or None
        """
        if not segments or not excerpt:
            return None
            
        # Clean excerpt for matching (remove ellipsis and bold markers)
        clean_excerpt = excerpt.replace('...', '').replace('**', '').strip()
        
        # Try to find segment containing excerpt text
        for segment in segments:
            segment_text = segment.get('text', '')
            if clean_excerpt[:50] in segment_text or segment_text[:50] in clean_excerpt:
                return {
                    'start_time': segment.get('start_time', 0),
                    'end_time': segment.get('end_time', 0)
                }
        
        return None
    
    def _get_from_cache(self, key: str) -> Optional[List[Dict]]:
        """Get item from cache if not expired"""
        if key in self.cache:
            item = self.cache[key]
            if time.time() - item['timestamp'] < self.cache_ttl:
                # Move to end (LRU)
                self.cache.move_to_end(key)
                return item['data']
            else:
                # Expired
                del self.cache[key]
        return None
    
    def _add_to_cache(self, key: str, data: List[Dict]):
        """Add item to cache with LRU eviction"""
        # Remove oldest if at capacity
        if len(self.cache) >= self.max_cache_size:
            self.cache.popitem(last=False)
            
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()

# Create singleton instance
_search_handler = None

async def get_search_handler() -> MongoSearchHandler:
    """Get or create singleton search handler"""
    global _search_handler
    if _search_handler is None:
        _search_handler = MongoSearchHandler()
    return _search_handler