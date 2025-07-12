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
import numpy as np

# Ensure correct environment loading
from lib.env_loader import load_env_safely
load_env_safely()

logger = logging.getLogger(__name__)

# Global instance for connection pooling
_hybrid_handler_instance = None


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

    def _get_collection(self):
        """Always return a collection bound to *this* event loop."""
        uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DATABASE", "podinsight")

        if not uri:
            logger.warning("MONGODB_URI not set, hybrid search disabled")
            return None

        # Get client for current event loop
        loop_id = id(asyncio.get_running_loop())
        client = ImprovedHybridSearch._client_per_loop.get(loop_id)

        if client is None:
            logger.info(f"Creating MongoDB client for hybrid search, event loop {loop_id}")
            client = AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=20000,  # Increased to 20s for text search reliability
                connectTimeoutMS=20000,  # Increased to 20s
                socketTimeoutMS=20000,  # Increased to 20s
                maxPoolSize=10,
                retryWrites=True
            )
            ImprovedHybridSearch._client_per_loop[loop_id] = client

        # Never cache the collection – it inherits the loop from its client
        db = client[db_name]
        return db["transcript_chunks_768d"]

    async def search(self, query: str, limit: int = 50, query_embedding: Optional[List[float]] = None) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector and text matching
        Returns dict format compatible with existing API

        Args:
            query: The search query string
            limit: Maximum number of results to return
            query_embedding: Pre-computed query embedding (optional) to avoid duplicate generation
        """
        logger.info(f"[HYBRID_SEARCH] Starting search for: '{query}' with limit={limit}")

        # Get collection
        collection = self._get_collection()
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
        vector_task = self._vector_search(collection, query_vector, limit * 2)
        text_task = self._text_search(collection, query_terms, limit * 2)

        vector_results, text_results = await asyncio.gather(vector_task, text_task)
        logger.info(f"[HYBRID_SEARCH] Vector search returned {len(vector_results)} results")
        logger.info(f"[HYBRID_SEARCH] Text search returned {len(text_results)} results")

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

        # Weight terms based on domain importance
        terms = {}
        for word in words:
            if word in stop_words:
                continue
            elif word in self.domain_terms:
                terms[word] = self.domain_terms[word]
            elif word in important_short_words:
                terms[word] = 1.5  # Boost important short words
            elif len(word) > 2:  # Include slightly shorter words
                terms[word] = 1.0

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

    async def _vector_search(self, collection, query_vector: List[float], limit: int) -> List[Dict]:
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
                {"$match": {"score": {"$gte": 0.4}}},  # Lowered threshold for better recall
                # Add lookup to join episode_metadata for missing fields
                {
                    "$lookup": {
                        "from": "episode_metadata",
                        "localField": "episode_id",  # episode_id in chunks = guid in metadata
                        "foreignField": "guid",
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
                        "vector_score": "$score",
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

            results = await collection.aggregate(pipeline, allowDiskUse=True).to_list(limit)
            return results

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    async def _text_search(self, collection, query_terms: Dict[str, float], limit: int) -> List[Dict]:
        """Perform text-based search using MongoDB text index"""
        # Build search string for MongoDB $text operator
        # Focus on important single words and meaningful phrases only
        search_terms = []

        # Common stop words to exclude
        stop_words = {'what', 'are', 'is', 'the', 'a', 'an', 'about', 'saying', 'doing', 'with', 'for', 'on', 'in', 'at'}

        for term in query_terms:
            if ' ' in term:
                # Only include multi-word terms if they're meaningful domain phrases
                words_in_phrase = term.split()
                if len(words_in_phrase) == 2:
                    # Check if both words are meaningful (not stop words)
                    if not any(w in stop_words for w in words_in_phrase):
                        search_terms.append(f'"{term}"')
            else:
                # Single words - only add if not a stop word and has weight > 1.0
                if term not in stop_words and query_terms[term] >= 1.0:
                    search_terms.append(term)

        # Join all terms with spaces (MongoDB $text uses OR logic by default)
        search_string = ' '.join(search_terms)
        logger.info(f"[TEXT_SEARCH] Using search string: {search_string}")

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
                        "foreignField": "guid",
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

            results = await collection.aggregate(pipeline, allowDiskUse=True).to_list(limit)
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
                            "foreignField": "guid",
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

                results = await collection.aggregate(pipeline, allowDiskUse=True).to_list(limit)
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
                # Default: Vector: 40%, Text: 40%, Domain boost: 20%
                hybrid_score = (
                    0.4 * chunk_data['vector_score'] +
                    0.4 * chunk_data['text_score'] +
                    0.2 * domain_boost
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
