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
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                maxPoolSize=10,
                retryWrites=True
            )
            ImprovedHybridSearch._client_per_loop[loop_id] = client

        # Never cache the collection – it inherits the loop from its client
        db = client[db_name]
        return db["transcript_chunks_768d"]

    async def search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector and text matching
        Returns dict format compatible with existing API
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

        # Step 2: Generate embedding using Modal service
        from .search_lightweight_768d import generate_embedding_768d_local
        query_vector = await generate_embedding_768d_local(query)

        if not query_vector:
            logger.error("Failed to generate query embedding")
            return []

        # Step 3: Vector search with MongoDB aggregation
        vector_results = await self._vector_search(collection, query_vector, limit * 2)
        logger.info(f"[HYBRID_SEARCH] Vector search returned {len(vector_results)} results")

        # Step 4: Text search for chunks containing query terms
        text_results = await self._text_search(collection, query_terms, limit * 2)
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

        # Weight terms based on domain importance
        terms = {}
        for word in words:
            if word in self.domain_terms:
                terms[word] = self.domain_terms[word]
            elif len(word) > 3:  # Skip short words
                terms[word] = 1.0

        # Add bigrams for phrase matching
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            terms[bigram] = 1.5  # Boost phrase matches

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
                {"$match": {"score": {"$gte": 0.5}}},  # Min threshold
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
                        "podcast_title": 1,
                        "episode_title": 1,
                        "published": 1
                    }
                }
            ]

            results = await collection.aggregate(pipeline, allowDiskUse=True).to_list(limit)
            return results

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    async def _text_search(self, collection, query_terms: Dict[str, float], limit: int) -> List[Dict]:
        """Perform text-based search for query terms"""
        # Build regex patterns for all terms
        patterns = []
        for term in query_terms:
            # Escape special regex characters
            escaped_term = re.escape(term)
            patterns.append(f"\\b{escaped_term}\\b")

        # Combine patterns with OR
        combined_pattern = '|'.join(patterns)

        try:
            # Use text index if available, otherwise regex
            pipeline = [
                {
                    "$match": {
                        "$or": [
                            {"$text": {"$search": " ".join(query_terms.keys())}},
                            {"text": {"$regex": combined_pattern, "$options": "i"}}
                        ]
                    }
                },
                {
                    "$addFields": {
                        "text_matches": {
                            "$size": {
                                "$filter": {
                                    "input": {"$split": [{"$toLower": "$text"}, " "]},
                                    "cond": {
                                        "$in": ["$$this", [term.lower() for term in query_terms]]
                                    }
                                }
                            }
                        }
                    }
                },
                {"$match": {"text_matches": {"$gt": 0}}},
                {"$sort": {"text_matches": -1}},
                {"$limit": limit},
                {
                    "$project": {
                        "_id": 1,
                        "text": 1,
                        "episode_id": 1,
                        "text_matches": 1,
                        "chunk_index": 1,
                        "start_time": 1,
                        "end_time": 1,
                        "feed_slug": 1,
                        "podcast_title": 1,
                        "episode_title": 1,
                        "published": 1
                    }
                }
            ]

            results = await collection.aggregate(pipeline, allowDiskUse=True).to_list(limit)
            return results

        except Exception as e:
            logger.error(f"Text search error: {e}")
            # Fallback to simple regex if text index not available
            try:
                results = await collection.find(
                    {"text": {"$regex": combined_pattern, "$options": "i"}}
                ).limit(limit).to_list(limit)
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
                    'podcast_title': vr.get('podcast_title'),
                    'episode_title': vr.get('episode_title'),
                    'published': vr.get('published')
                }
            }

        # Process text results and merge
        for tr in text_results:
            chunk_id = str(tr['_id'])
            if chunk_id in results_map:
                # Update text score for existing result
                results_map[chunk_id]['text_score'] = tr.get('text_matches', 0) / len(query_terms)
            else:
                # Add new result from text search
                results_map[chunk_id] = {
                    'chunk_id': chunk_id,
                    'text': tr['text'],
                    'episode_id': tr['episode_id'],
                    'vector_score': 0.0,
                    'text_score': tr.get('text_matches', 0) / len(query_terms),
                    'metadata': {
                        'chunk_index': tr.get('chunk_index'),
                        'start_time': tr.get('start_time'),
                        'end_time': tr.get('end_time'),
                        'feed_slug': tr.get('feed_slug'),
                        'podcast_title': tr.get('podcast_title'),
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
            # Vector: 40%, Text: 40%, Domain boost: 20%
            domain_boost = self._calculate_domain_boost(chunk_data['text'])

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
            r'acquisition'
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
                'podcast_title': result.metadata.get('podcast_title'),
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
