"""
Improved Hybrid Search Implementation for PodInsightHQ API
Combines vector search with text matching for better relevance
Adapted from ETL version with async Motor client
"""

import os
import re
import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError, AutoReconnect, NotPrimaryError
import numpy as np
import json
import time
from datetime import datetime, timezone

# Ensure correct environment loading
from lib.env_loader import load_env_safely
load_env_safely()

logger = logging.getLogger(__name__)

# Global instance for connection pooling
_hybrid_handler_instance = None


async def with_mongodb_retry(func, max_retries=2, operation_name="mongodb_operation", session_id=None):
    """Retry MongoDB operations during replica set elections"""
    start_time = time.time()

    for attempt in range(max_retries + 1):
        try:
            result = await func()
            elapsed = time.time() - start_time

            # Log successful operation analytics
            analytics_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "operation": operation_name,
                "mongodb": {
                    "response_time": elapsed,
                    "attempts": attempt + 1,
                    "success": True,
                    "election_detected": attempt > 0  # If we needed retries, likely an election
                }
            }
            logger.info(f"MONGODB_ANALYTICS: {json.dumps(analytics_data)}")

            return result
        except (ServerSelectionTimeoutError, AutoReconnect, NotPrimaryError) as e:
            if attempt < max_retries:
                logger.warning(f"MongoDB transient error: {type(e).__name__}, retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(1)  # Wait 1s before retry
            else:
                elapsed = time.time() - start_time
                logger.error(f"MongoDB failed after {max_retries + 1} attempts: {e}")

                # Log failed operation analytics
                analytics_data = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "operation": operation_name,
                    "mongodb": {
                        "response_time": elapsed,
                        "attempts": max_retries + 1,
                        "success": False,
                        "error": type(e).__name__,
                        "election_detected": True
                    }
                }
                logger.info(f"MONGODB_ANALYTICS: {json.dumps(analytics_data)}")

                raise


@dataclass
class HybridSearchResult:
    """Enhanced search result with hybrid scoring"""
    chunk_id: str
    text: str
    episode_id: str
    vector_score: float
    text_score: float
    hybrid_score: float
    matches: Dict[str, List[str]]
    metadata: Dict[str, Any]


class ImprovedHybridSearch:
    """
    Production-ready hybrid search that properly combines:
    1. Vector similarity (semantic search)
    2. Text matching (keyword/phrase search)
    3. Domain-specific scoring

    Async version for API compatibility
    """

    # Per-event-loop client storage
    _client_per_loop = {}

    def __init__(self):
        # VC-specific term weights
        self.domain_terms = {
            'valuation': 2.0,
            'valuations': 2.0,  # Add plural form
            'series': 1.5,
            'funding': 1.5,
            'investment': 1.5,
            'portfolio': 1.3,
            'unicorn': 1.8,
            'billion': 1.5,
            'acquisition': 1.5,
            'exit': 1.5,
            'ipo': 1.5,
            'arr': 1.5,
            'revenue': 1.3,
            'burn': 1.3,
            'runway': 1.3,
            'cap table': 1.5,
            'dilution': 1.3
        }

    def _get_collection(self, modal_response_time: float = 0.0):
        """Always return a collection bound to *this* event loop."""
        uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DATABASE", "podinsight")

        if not uri:
            logger.warning("MONGODB_URI not set, hybrid search disabled")
            return None

        # Use pragmatic fixed timeouts for serverless environment
        # 10s allows for normal replica set failovers while leaving 20s for actual operations
        # This is better than 30s which would consume the entire Vercel timeout
        # Time budget: Connection (10s) + Query (15s) + Buffer (5s) = 30s total
        connection_timeout = 10000  # 10 seconds for server selection (handles most failovers)
        connect_timeout = 5000      # 5 seconds for initial socket connection
        socket_timeout = 45000      # 45 seconds for long-running queries (can span multiple requests)

        # Log MongoDB configuration analytics
        config_analytics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "mongodb_config",
            "mongodb": {
                "modal_response_time": modal_response_time,
                "connection_timeout_ms": connection_timeout,
                "connect_timeout_ms": connect_timeout,
                "socket_timeout_ms": socket_timeout,
                "read_preference": "secondaryPreferred",
                "strategy": "fail-fast with time budget"
            }
        }
        logger.info(f"MONGODB_ANALYTICS: {json.dumps(config_analytics)}")

        # Get client for current event loop
        loop_id = id(asyncio.get_running_loop())

        # Create unique key for this timeout configuration
        client_key = f"{loop_id}_{connection_timeout}"
        client = ImprovedHybridSearch._client_per_loop.get(client_key)

        if client is None:
            logger.info(f"Creating MongoDB client for hybrid search, event loop {loop_id}, connection timeout {connection_timeout}ms")
            connection_start = time.time()
            client = AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=connection_timeout,  # 10s for server selection
                connectTimeoutMS=connect_timeout,             # 5s for initial connection
                socketTimeoutMS=socket_timeout,               # 45s for long queries
                maxPoolSize=100,                              # Increased from 10 for better concurrency
                minPoolSize=10,                               # Keep connections warm
                maxIdleTimeMS=60000,                          # Keep idle connections for 1 minute
                retryWrites=True,
                retryReads=True,                              # Add retry for read operations
                readPreference='secondaryPreferred',          # Read from secondaries during elections
                w='majority'                                  # Ensure write durability
            )
            ImprovedHybridSearch._client_per_loop[client_key] = client

            connection_time = time.time() - connection_start
            if connection_time > 5:
                logger.warning(f"Slow MongoDB client creation: {connection_time:.2f}s")
            else:
                logger.info(f"MongoDB client created in {connection_time:.2f}s")

        # Never cache the collection – it inherits the loop from its client
        db = client[db_name]
        return db["transcript_chunks_768d"]

    async def search(self, query: str, limit: int = 50, query_embedding: Optional[List[float]] = None,
                    modal_response_time: float = 0.0, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector and text matching
        Returns dict format compatible with existing API

        Args:
            query: The search query string
            limit: Maximum number of results to return
            query_embedding: Pre-computed query embedding (optional) to avoid duplicate generation
            modal_response_time: Time taken by Modal to respond (for dynamic timeout calculation)
        """
        logger.info(f"[HYBRID_SEARCH] Starting search for: '{query}' with limit={limit}")

        # Get collection with dynamic timeout based on Modal response time
        collection = self._get_collection(modal_response_time)
        if collection is None:
            logger.error("MongoDB not connected for hybrid search")
            return []

        # Step 1: Extract query terms and encode query
        query_terms = self._extract_query_terms(query)
        logger.info(f"[HYBRID_SEARCH] Extracted terms: {list(query_terms.keys())}")

        # Step 2: Use provided embedding or generate one
        if query_embedding:
            query_vector = query_embedding
            logger.info(f"[HYBRID_SEARCH] Using pre-computed embedding (dim: {len(query_vector)})")
        else:
            # Generate embedding using Modal service
            from .search_lightweight_768d import generate_embedding_768d_local
            query_vector = await generate_embedding_768d_local(query)

        if not query_vector:
            logger.error("Failed to get query embedding")
            return []

        # Step 3 & 4: Run vector and text searches in parallel to save time
        import asyncio
        vector_task = self._vector_search(collection, query_vector, limit * 2, session_id)
        text_task = self._text_search(collection, query_terms, limit * 2, session_id)

        vector_results, text_results = await asyncio.gather(vector_task, text_task)
        logger.info(f"[HYBRID_SEARCH] Vector search returned {len(vector_results)} results")
        logger.info(f"[HYBRID_SEARCH] Text search returned {len(text_results)} results")

        # Log warning if text search returns 0 results but vector search has results
        if len(text_results) == 0 and len(vector_results) > 0:
            logger.warning(f"[HYBRID_SEARCH] Text search returned 0 results while vector search found {len(vector_results)} - possible text index issue")
            logger.warning(f"[HYBRID_SEARCH] Query: '{query}'")

        # Step 5: Merge and re-rank results
        final_results = self._merge_and_rerank(
            vector_results,
            text_results,
            query_terms,
            limit
        )

        logger.info(f"[HYBRID_SEARCH] Final hybrid results: {len(final_results)}")

        # Convert to API format
        return self._convert_to_api_format(final_results)

    def _extract_query_terms(self, query: str) -> Dict[str, float]:
        """Extract important terms from query with weights"""
        # Basic tokenization and cleaning
        words = re.findall(r'\b\w+\b', query.lower())

        # Important short words in VC domain
        important_short_words = {'ai', 'vc', 'vcs', 'ipo', 'arr', 'b2b', 'b2c', 'yc', 'sfr', 'mvp'}

        # Stop words to skip
        stop_words = {'what', 'are', 'is', 'the', 'a', 'an', 'about', 'saying', 'doing', 'with', 'for', 'on', 'in', 'at', 'to', 'of'}

        # Synonym mapping for common VC terms (limited to 2-3 per term to prevent query explosion)
        synonyms = {
            'ai': ['artificial intelligence', 'ml'],  # Removed 'machine learning', 'deep learning'
            'vcs': ['venture capitalists', 'investors'],  # Removed 'venture capital'
            'vc': ['venture capitalist', 'investor'],  # Removed 'venture capital'
            'valuations': ['valuation', 'pricing'],  # Removed 'valued', 'price', 'worth'
            'valuation': ['valuations', 'pricing'],  # Removed 'valued', 'price', 'worth'
            'startup': ['startups', 'company'],  # Removed 'companies'
            'startups': ['startup', 'company'],  # Removed 'companies'
            'funding': ['investment', 'raise'],  # Removed 'round', 'capital'
            'crypto': ['cryptocurrency', 'blockchain'],  # Removed 'web3'
            'saas': ['software as a service']  # Removed 'subscription'
        }

        # Weight terms based on domain importance
        terms = {}
        for word in words:
            if word in stop_words:
                continue
            elif word in self.domain_terms:
                terms[word] = self.domain_terms[word]
                # Add synonyms for domain terms
                if word.lower() in synonyms:
                    for syn in synonyms[word.lower()]:
                        terms[syn] = self.domain_terms[word] * 0.8  # Slightly lower weight for synonyms
            elif word in important_short_words:
                terms[word] = 1.5  # Boost important short words
                # Add synonyms for important terms
                if word.lower() in synonyms:
                    for syn in synonyms[word.lower()]:
                        terms[syn] = 1.2
            elif len(word) > 2:  # Include slightly shorter words
                terms[word] = 1.0
                # Check for synonyms
                if word.lower() in synonyms:
                    for syn in synonyms[word.lower()]:
                        terms[syn] = 0.8

        # Add meaningful bigrams only
        meaningful_bigram_patterns = [
            ('ai', 'valuation'), ('ai', 'valuations'),
            ('ai', 'agent'), ('ai', 'agents'),
            ('series', 'a'), ('series', 'b'), ('series', 'c'),
            ('venture', 'capital'), ('vc', 'funding'),
            ('artificial', 'intelligence'), ('machine', 'learning'),
            ('startup', 'valuation'), ('startup', 'funding'),
            ('burn', 'rate'), ('growth', 'rate')
        ]

        for i in range(len(words) - 1):
            word1, word2 = words[i].lower(), words[i+1].lower()
            # Check if this bigram is meaningful
            if (word1, word2) in meaningful_bigram_patterns or \
               (word1 in self.domain_terms and word2 in self.domain_terms) or \
               (word1 in important_short_words and word2 not in stop_words):
                bigram = f"{word1} {word2}"
                terms[bigram] = 2.0  # Higher boost for meaningful phrases

        return terms

    async def _vector_search(self, collection, query_vector: List[float], limit: int, session_id: Optional[str] = None) -> List[Dict]:
        """Perform vector similarity search using MongoDB Atlas Vector Search"""
        try:
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index_768d",
                        "path": "embedding_768d",
                        "queryVector": query_vector,
                        "numCandidates": 200,  # Increased for better recall
                        "limit": limit
                    }
                },
                {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
                # Project only essential fields first to reduce document size
                {
                    "$project": {
                        "_id": 1,
                        "text": 1,
                        "episode_id": 1,
                        "vector_score": "$score",
                        "chunk_index": 1,
                        "start_time": 1,
                        "end_time": 1,
                        "feed_slug": 1
                    }
                },
                # Limit BEFORE lookup to reduce join operations
                {"$limit": limit},
                # Now lookup only for the limited results
                {
                    "$lookup": {
                        "from": "episode_metadata",
                        "localField": "episode_id",
                        "foreignField": "episode_id",  # Now using aligned field names
                        "as": "metadata"
                    }
                },
                # Unwind the metadata array (should be single document)
                {"$unwind": {"path": "$metadata", "preserveNullAndEmptyArrays": True}},
                {
                    "$project": {
                        "_id": 1,
                        "text": 1,
                        "episode_id": 1,
                        "vector_score": "$vector_score",  # Reference the already projected field
                        "chunk_index": 1,
                        "start_time": 1,
                        "end_time": 1,
                        "feed_slug": 1,
                        # Extract metadata fields with proper paths
                        "podcast_name": "$metadata.podcast_title",  # Map to podcast_name for API
                        "episode_title": "$metadata.raw_entry_original_feed.episode_title",
                        "published": "$metadata.raw_entry_original_feed.published_date_iso"
                    }
                }
            ]

            results = await with_mongodb_retry(
                lambda: collection.aggregate(pipeline, allowDiskUse=True).to_list(limit),
                operation_name="vector_search",
                session_id=session_id
            )
            return results

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    async def _text_search(self, collection, query_terms: Dict[str, float], limit: int, session_id: Optional[str] = None) -> List[Dict]:
        """Perform text-based search using MongoDB text index"""
        # Build search string for MongoDB $text operator
        # Focus on important single words and meaningful phrases only
        search_terms = []

        # Common stop words to exclude
        stop_words = {'what', 'are', 'is', 'the', 'a', 'an', 'about', 'saying', 'doing', 'with', 'for', 'on', 'in', 'at'}

        # Limit total search terms to prevent query explosion
        MAX_SEARCH_TERMS = 6  # Reduced from 12 for better performance

        for term in query_terms:
            if len(search_terms) >= MAX_SEARCH_TERMS:
                break  # Stop adding terms once we hit the limit

            if ' ' in term:
                # Only include multi-word terms if they're meaningful domain phrases
                words_in_phrase = term.split()
                if len(words_in_phrase) == 2:
                    # Check if both words are meaningful (not stop words)
                    if not any(w in stop_words for w in words_in_phrase):
                        search_terms.append(term)
            else:
                # Single words - only add if not a stop word and has weight > 1.0
                if term not in stop_words and query_terms[term] >= 1.0:
                    search_terms.append(term)

        # Join all terms with spaces (MongoDB $text uses OR logic by default)
        search_string = ' '.join(search_terms)
        logger.info(f"[TEXT_SEARCH] Using search string: {search_string}")
        logger.info(f"[TEXT_SEARCH] Number of search terms: {len(search_terms)}")
        logger.info(f"[TEXT_SEARCH] Terms breakdown - Single words: {sum(1 for t in search_terms if ' ' not in t)}, Multi-word phrases: {sum(1 for t in search_terms if ' ' in t)}")

        try:
            # Use MongoDB text index for efficient searching
            pipeline = [
                {
                    "$match": {
                        "$text": {"$search": search_string}
                    }
                },
                {
                    "$addFields": {
                        "text_score": {"$meta": "textScore"}
                    }
                },
                {"$sort": {"text_score": -1}},
                {"$limit": limit},
                # Add lookup to join episode_metadata for missing fields
                {
                    "$lookup": {
                        "from": "episode_metadata",
                        "localField": "episode_id",
                        "foreignField": "episode_id",  # Now using aligned field names
                        "as": "metadata"
                    }
                },
                # Unwind the metadata array
                {"$unwind": {"path": "$metadata", "preserveNullAndEmptyArrays": True}},
                {
                    "$project": {
                        "_id": 1,
                        "text": 1,
                        "episode_id": 1,
                        "text_score": 1,  # Use text score instead of text_matches
                        "chunk_index": 1,
                        "start_time": 1,
                        "end_time": 1,
                        "feed_slug": 1,
                        # Extract metadata fields with proper paths
                        "podcast_name": "$metadata.podcast_title",
                        "episode_title": "$metadata.raw_entry_original_feed.episode_title",
                        "published": "$metadata.raw_entry_original_feed.published_date_iso"
                    }
                }
            ]

            import time
            text_search_start = time.time()

            results = await with_mongodb_retry(
                lambda: collection.aggregate(pipeline, allowDiskUse=True).to_list(limit),
                operation_name="text_search",
                session_id=session_id
            )

            text_search_time = time.time() - text_search_start
            logger.info(f"[TEXT_SEARCH] Execution time: {text_search_time:.2f}s")
            logger.info(f"[TEXT_SEARCH] Number of results: {len(results)}")

            if len(results) == 0:
                logger.warning(f"[TEXT_SEARCH] ZERO RESULTS for query: '{search_string}'")
                logger.warning(f"[TEXT_SEARCH] Original query terms: {list(query_terms.keys())}")

            return results

        except Exception as e:
            logger.error(f"Text search error: {e}")
            logger.info("[TEXT_SEARCH] Falling back to regex search due to text index error")

            # Fallback to regex search if text index fails
            try:
                # Build regex pattern from search terms
                patterns = []
                for term in query_terms:
                    escaped_term = re.escape(term)
                    patterns.append(f"\\b{escaped_term}\\b")

                combined_pattern = '|'.join(patterns)

                # Simple regex search without complex aggregation
                pipeline = [
                    {
                        "$match": {
                            "text": {"$regex": combined_pattern, "$options": "i"}
                        }
                    },
                    {"$limit": limit},
                    # Add lookup for metadata
                    {
                        "$lookup": {
                            "from": "episode_metadata",
                            "localField": "episode_id",
                            "foreignField": "episode_id",  # Now using aligned field names
                            "as": "metadata"
                        }
                    },
                    {"$unwind": {"path": "$metadata", "preserveNullAndEmptyArrays": True}},
                    {
                        "$project": {
                            "_id": 1,
                            "text": 1,
                            "episode_id": 1,
                            "text_score": {"$literal": 1.0},  # Default score for regex matches
                            "chunk_index": 1,
                            "start_time": 1,
                            "end_time": 1,
                            "feed_slug": 1,
                            "podcast_name": "$metadata.podcast_title",
                            "episode_title": "$metadata.raw_entry_original_feed.episode_title",
                            "published": "$metadata.raw_entry_original_feed.published_date_iso"
                        }
                    }
                ]

                results = await with_mongodb_retry(
                    lambda: collection.aggregate(pipeline, allowDiskUse=True).to_list(limit),
                    operation_name="text_search_fallback",
                    session_id=session_id
                )
                logger.info(f"[TEXT_SEARCH] Regex fallback returned {len(results)} results")
                return results

            except Exception as e2:
                logger.error(f"Regex search also failed: {e2}")
                return []

    def _merge_and_rerank(
        self,
        vector_results: List[Dict],
        text_results: List[Dict],
        query_terms: Dict[str, float],
        limit: int
    ) -> List[HybridSearchResult]:
        """Merge vector and text results with hybrid scoring"""
        # Create result map
        results_map = {}

        # Process vector results
        for vr in vector_results:
            chunk_id = str(vr['_id'])
            results_map[chunk_id] = {
                'chunk_id': chunk_id,
                'text': vr['text'],
                'episode_id': vr['episode_id'],
                'vector_score': vr.get('vector_score', 0),
                'text_score': 0.0,
                'metadata': {
                    'chunk_index': vr.get('chunk_index'),
                    'start_time': vr.get('start_time'),
                    'end_time': vr.get('end_time'),
                    'feed_slug': vr.get('feed_slug'),
                    'podcast_name': vr.get('podcast_name'),  # Changed from podcast_title
                    'episode_title': vr.get('episode_title'),
                    'published': vr.get('published')
                }
            }

        # Process text results and merge
        for tr in text_results:
            chunk_id = str(tr['_id'])
            if chunk_id in results_map:
                # Update text score for existing result
                # Normalize MongoDB text score (typically 0-5 range) to 0-1 range
                results_map[chunk_id]['text_score'] = min(tr.get('text_score', 0) / 5.0, 1.0)
            else:
                # Add new result from text search
                results_map[chunk_id] = {
                    'chunk_id': chunk_id,
                    'text': tr['text'],
                    'episode_id': tr['episode_id'],
                    'vector_score': 0.0,
                    'text_score': min(tr.get('text_score', 0) / 5.0, 1.0),
                    'metadata': {
                        'chunk_index': tr.get('chunk_index'),
                        'start_time': tr.get('start_time'),
                        'end_time': tr.get('end_time'),
                        'feed_slug': tr.get('feed_slug'),
                        'podcast_name': tr.get('podcast_name'),  # Changed from podcast_title
                        'episode_title': tr.get('episode_title'),
                        'published': tr.get('published')
                    }
                }

        # Calculate hybrid scores and create SearchResult objects
        final_results = []
        for chunk_data in results_map.values():
            # Find actual term matches
            matches = self._find_term_matches(chunk_data['text'], query_terms)

            # Calculate hybrid score with weights
            # Adjust weights based on whether specific terms are present
            domain_boost = self._calculate_domain_boost(chunk_data['text'])

            # If we have strong text matches, weight text more heavily
            if chunk_data['text_score'] > 0.5:
                # Text: 50%, Vector: 30%, Domain boost: 20%
                hybrid_score = (
                    0.3 * chunk_data['vector_score'] +
                    0.5 * chunk_data['text_score'] +
                    0.2 * domain_boost
                )
            else:
                # Adjusted weights: Vector: 60%, Text: 25%, Domain boost: 15%
                # Increased vector weight since text search often fails in transcripts
                hybrid_score = (
                    0.6 * chunk_data['vector_score'] +
                    0.25 * chunk_data['text_score'] +
                    0.15 * domain_boost
                )

            # Boost if contains exact phrases
            if self._contains_exact_phrases(chunk_data['text'], query_terms):
                hybrid_score *= 1.2

            result = HybridSearchResult(
                chunk_id=chunk_data['chunk_id'],
                text=chunk_data['text'],
                episode_id=chunk_data['episode_id'],
                vector_score=chunk_data['vector_score'],
                text_score=chunk_data['text_score'],
                hybrid_score=min(hybrid_score, 1.0),  # Cap at 1.0
                matches=matches,
                metadata=chunk_data['metadata']
            )

            final_results.append(result)

        # Sort by hybrid score and return top results
        final_results.sort(key=lambda x: x.hybrid_score, reverse=True)

        # Log top results for debugging
        for i, result in enumerate(final_results[:3]):
            logger.info(f"[HYBRID_TOP_{i+1}] Score: {result.hybrid_score:.3f}, "
                       f"Vector: {result.vector_score:.3f}, Text: {result.text_score:.3f}, "
                       f"Matches: {list(result.matches.keys())}")

        return final_results[:limit]

    def _find_term_matches(self, text: str, query_terms: Dict[str, float]) -> Dict[str, List[str]]:
        """Find which query terms appear in text"""
        text_lower = text.lower()
        matches = {}

        for term in query_terms:
            pattern = rf'\b{re.escape(term)}\b'
            found = re.findall(pattern, text_lower, re.IGNORECASE)
            if found:
                matches[term] = found

        return matches

    def _contains_exact_phrases(self, text: str, query_terms: Dict[str, float]) -> bool:
        """Check if text contains multi-word phrases from query"""
        text_lower = text.lower()
        for term in query_terms:
            if ' ' in term and term in text_lower:
                return True
        return False

    def _calculate_domain_boost(self, text: str) -> float:
        """Calculate domain-specific relevance boost"""
        text_lower = text.lower()
        boost = 0.0

        # Check for VC-specific patterns
        vc_patterns = [
            r'\$\d+[MBK]',  # Funding amounts
            r'series [A-F]',  # Funding rounds
            r'valuation',
            r'portfolio company',
            r'venture capital',
            r'term sheet',
            r'cap table',
            r'unicorn',
            r'IPO',
            r'acquisition',
            r'overvalued',  # Added for valuation queries
            r'undervalued',  # Added for valuation queries
            r'pricing',  # Added for valuation context
            r'multiple',  # Added for valuation multiples
            r'revenue multiple'  # Added for specific metrics
        ]

        for pattern in vc_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                boost += 0.2

        return min(boost, 1.0)

    def _convert_to_api_format(self, results: List[HybridSearchResult]) -> List[Dict[str, Any]]:
        """Convert HybridSearchResult to API-compatible dict format"""
        api_results = []

        for result in results:
            api_results.append({
                '_id': result.chunk_id,
                'text': result.text,
                'episode_id': result.episode_id,
                'score': result.hybrid_score,  # Use hybrid score as main score
                'chunk_index': result.metadata.get('chunk_index'),
                'start_time': result.metadata.get('start_time'),
                'end_time': result.metadata.get('end_time'),
                'feed_slug': result.metadata.get('feed_slug'),
                'podcast_name': result.metadata.get('podcast_name'),  # API expects podcast_name
                'episode_title': result.metadata.get('episode_title'),
                'published': result.metadata.get('published'),
                # Additional hybrid search info
                'vector_score': result.vector_score,
                'text_score': result.text_score,
                'hybrid_score': result.hybrid_score,
                'matches': list(result.matches.keys()) if result.matches else []
            })

        return api_results

    async def close(self):
        """Close MongoDB connections for all event loops"""
        for loop_id, client in ImprovedHybridSearch._client_per_loop.items():
            logger.info(f"Closing MongoDB client for hybrid search, event loop {loop_id}")
            client.close()
        ImprovedHybridSearch._client_per_loop.clear()


# Use global instance for connection pooling
async def get_hybrid_search_handler() -> ImprovedHybridSearch:
    global _hybrid_handler_instance
    if _hybrid_handler_instance is None:
        _hybrid_handler_instance = ImprovedHybridSearch()
    return _hybrid_handler_instance


async def warm_mongodb_connection():
    """
    Warm up MongoDB connection on startup to avoid cold start penalties.
    This should be called during application initialization.
    """
    try:
        logger.info("Starting MongoDB connection warming...")
        start_time = time.time()

        # Get the hybrid search handler to initialize connection
        handler = await get_hybrid_search_handler()

        # Get collection to force connection establishment
        collection = handler._get_collection(modal_response_time=0.0)

        if collection is not None:
            # Ping to verify connection
            await collection.database.client.admin.command('ping')

            # Do a simple query to warm up the connection pool
            await collection.find_one()

            elapsed = time.time() - start_time
            logger.info(f"✅ MongoDB connection warmed up successfully in {elapsed:.2f}s")

            # Log warming analytics
            analytics = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation": "connection_warming",
                "mongodb": {
                    "warming_time": elapsed,
                    "success": True
                }
            }
            logger.info(f"MONGODB_ANALYTICS: {json.dumps(analytics)}")
        else:
            logger.warning("⚠️ MongoDB connection warming skipped - no collection available")

    except Exception as e:
        elapsed = time.time() - start_time
        logger.warning(f"⚠️ MongoDB warmup failed after {elapsed:.2f}s (non-critical): {e}")

        # Log warming failure analytics
        analytics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": "connection_warming",
            "mongodb": {
                "warming_time": elapsed,
                "success": False,
                "error": str(e)
            }
        }
        logger.info(f"MONGODB_ANALYTICS: {json.dumps(analytics)}")
