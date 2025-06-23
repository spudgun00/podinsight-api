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
            self.collection = self.db['transcript_chunks_768d']
        
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
                
                # Generate meaningful episode title if empty
                episode_title = doc.get('episode_title', '').strip()
                if not episode_title:
                    published_date = doc.get('published_at', datetime.now())
                    if isinstance(published_date, str):
                        published_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                    episode_title = f"Episode from {published_date.strftime('%B %d, %Y')}"
                
                # Format date for user display
                published_date = doc.get('published_at', datetime.now())
                if isinstance(published_date, str):
                    published_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                formatted_date = published_date.strftime('%B %d, %Y')
                
                result = {
                    'episode_id': doc['episode_id'],
                    'podcast_name': doc.get('podcast_name', 'Unknown'),
                    'episode_title': episode_title,
                    'published_at': doc.get('published_at', datetime.now()).isoformat(),
                    'published_date': formatted_date,  # Human-readable date
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
    
    def extract_excerpt(self, full_text: str, query: str, max_chars: int = 150) -> str:
        """
        Extract focused excerpt around search query match
        Returns 1-2 sentences with highlighted terms (Google-style snippet)
        """
        if not full_text:
            return "No transcript available."
        
        # Clean up the query and create case-insensitive pattern
        query_terms = [term.strip('"') for term in query.split()]  # Remove quotes
        pattern = '|'.join(re.escape(term) for term in query_terms)
        
        # Find first match
        match = re.search(pattern, full_text, re.IGNORECASE)
        
        if not match:
            # No exact match, return beginning with ellipsis
            excerpt = full_text[:max_chars].strip()
            if len(full_text) > max_chars:
                # Find last complete word
                last_space = excerpt.rfind(' ')
                if last_space > 0:
                    excerpt = excerpt[:last_space]
                excerpt += '...'
            return excerpt
        
        # Get position of match
        match_pos = match.start()
        
        # Find sentence boundaries around the match
        # Look for sentence endings before the match
        sentence_start = 0
        for i in range(match_pos - 1, -1, -1):
            if full_text[i] in '.!?':
                sentence_start = i + 1
                break
        
        # Look for sentence endings after the match  
        sentence_end = len(full_text)
        for i in range(match_pos, len(full_text)):
            if full_text[i] in '.!?':
                sentence_end = i + 1
                break
        
        # Extract the sentence containing the match
        excerpt = full_text[sentence_start:sentence_end].strip()
        
        # If too long, truncate around the match
        if len(excerpt) > max_chars:
            # Center around the match position within the sentence
            match_in_excerpt = match_pos - sentence_start
            start_offset = max(0, match_in_excerpt - max_chars // 2)
            end_offset = start_offset + max_chars
            
            excerpt = excerpt[start_offset:end_offset]
            
            # Add ellipsis as needed
            if start_offset > 0:
                excerpt = '...' + excerpt
            if end_offset < (sentence_end - sentence_start):
                excerpt = excerpt + '...'
        
        # Highlight matched terms (wrap in **bold**)
        for term in query_terms:
            if term:  # Skip empty terms
                excerpt = re.sub(
                    f'({re.escape(term)})',
                    r'**\1**',
                    excerpt,
                    flags=re.IGNORECASE
                )
        
        return excerpt.strip()
    
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