"""
Lightweight Search API with 768D Vector Search
Primary: MongoDB Atlas Vector Search (768D)
Secondary: MongoDB Text Search
Tertiary: Supabase pgvector (384D)
"""
import os
import logging
from bson import ObjectId
logging.basicConfig(level="INFO")
logging.info("[BOOT-FILE] %s  commit=%s",
             __file__,
             os.getenv("VERCEL_GIT_COMMIT_SHA", "?"))

from fastapi import HTTPException
from typing import Dict, List, Optional, Any
from datetime import datetime
logging.getLogger(__name__).warning(
    "[BOOT] commit=%s  python=%s",                # <- shows up once per cold-start
    os.getenv("VERCEL_GIT_COMMIT_SHA", "local"),  # Vercel auto-injects this
    os.environ.get("PYTHON_VERSION", "unknown"))
import hashlib
import json
import asyncio
import aiohttp
import time
from pydantic import BaseModel, Field, validator
from .database import get_pool
from .mongodb_search import get_search_handler
from .mongodb_vector_search import get_vector_search_handler
# Import from root lib directory
from lib.embedding_utils import embed_query, validate_embedding
from .synthesis import synthesize_with_retry, Citation

# Configure logging
logger = logging.getLogger(__name__)

# Debug mode from environment
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Use same request/response models
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(10, ge=1, le=50, description="Number of results to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")

    @validator('query')
    def query_not_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Query cannot be empty")
        return v.strip()

class SearchResult(BaseModel):
    episode_id: str
    podcast_name: str
    episode_title: str
    published_at: str
    published_date: str  # Human-readable date
    similarity_score: float
    excerpt: str
    word_count: int
    duration_seconds: int
    topics: List[str]
    s3_audio_path: Optional[str]
    timestamp: Optional[Dict[str, float]]  # start_time, end_time for playback

class AnswerObject(BaseModel):
    """Synthesized answer with citations"""
    text: str
    citations: List[Citation]

class SearchResponse(BaseModel):
    answer: Optional[AnswerObject] = None  # Optional synthesized answer
    results: List[SearchResult]
    total_results: int
    cache_hit: bool
    search_id: str
    query: str
    limit: int
    offset: int
    search_method: str  # "vector_768d", "text", or "vector_384d"
    processing_time_ms: Optional[int] = None
    raw_chunks: Optional[List[Dict[str, Any]]] = None  # Original chunks for debugging


async def generate_embedding_768d_local(text: str) -> List[float]:
    """
    Generate 768D embedding using standardized function
    """
    try:
        # Use standardized embedding function
        embedding = embed_query(text)

        # Validate before returning
        if embedding and validate_embedding(embedding):
            return embedding
        else:
            logger.error(f"Embedding validation failed for: {text}")
            return None
    except Exception as e:
        logger.error(f"Error generating 768D embedding: {e}")
        return None


async def generate_embedding_384d_api(text: str) -> List[float]:
    """
    Generate 384D embedding using Hugging Face API (existing fallback)
    """
    api_url = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
    api_key = os.environ.get("HUGGINGFACE_API_KEY")

    if not api_key:
        logger.error("HUGGINGFACE_API_KEY not found")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": text,
        "options": {"wait_for_model": True}
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    embedding = result

                    # Normalize to unit length
                    norm = sum(x**2 for x in embedding) ** 0.5
                    if norm > 0:
                        embedding = [x / norm for x in embedding]

                    return embedding
                else:
                    logger.error(f"Embedding API error: {response.status}")
                    return None

    except Exception as e:
        logger.error(f"Error calling embedding API: {str(e)}")
        return None


# TODO: Implement MongoDB caching instead of Supabase
# async def check_query_cache_768d(query_hash: str) -> Optional[List[float]]:
#     """Check if 768D query embedding exists in cache"""
#     pool = get_pool()
#
#     try:
#         def get_cache(client):
#             return client.table("query_cache_768d") \
#                 .select("embedding_768d") \
#                 .eq("query_hash", query_hash) \
#                 .execute()
#
#         result = await pool.execute_with_retry(get_cache)
#
#         if result.data and len(result.data) > 0:
#             embedding = result.data[0]["embedding_768d"]
#             if isinstance(embedding, str):
#                 embedding = json.loads(embedding)
#             return embedding
#
#         return None
#
#     except Exception as e:
#         logger.warning(f"768D cache check failed: {str(e)}")
#         return None


# TODO: Implement MongoDB caching instead of Supabase
# async def store_query_cache_768d(query: str, query_hash: str, embedding: List[float]) -> None:
#     """Store 768D query embedding in cache"""
#     pool = get_pool()
#
#     try:
#         embedding_str = json.dumps(embedding)
#
#         def insert_cache(client):
#             return client.table("query_cache_768d") \
#                 .upsert({
#                     "query_hash": query_hash,
#                     "query_text": query[:500],
#                     "embedding_768d": embedding_str,
#                     "created_at": datetime.now().isoformat()
#                 }) \
#                 .execute()
#
#         await pool.execute_with_retry(insert_cache)
#         logger.info(f"Cached 768D embedding for query: {query[:50]}...")
#
#     except Exception as e:
#         logger.warning(f"Failed to cache 768D query: {str(e)}")


async def expand_chunk_context(chunk: Dict[str, Any], context_seconds: float = 20.0) -> str:
    """
    Expand a single chunk by fetching surrounding chunks for context

    Args:
        chunk: The chunk hit from vector search
        context_seconds: How many seconds before/after to include (default ±20s)

    Returns:
        Expanded text with context
    """
    try:
        # Get MongoDB connection
        from .mongodb_vector_search import get_vector_search_handler
        vector_handler = await get_vector_search_handler()

        # Get collection directly
        collection = vector_handler._get_collection()
        if collection is None:
            return chunk.get("text", "")

        # Calculate time window
        start_window = chunk.get("start_time", 0) - context_seconds
        end_window = chunk.get("end_time", 0) + context_seconds

        # Fetch surrounding chunks from same episode
        # Use simpler logic: get all chunks where start_time is within our window
        cursor = collection.find({
            "episode_id": chunk["episode_id"],
            "start_time": {"$gte": start_window, "$lte": end_window}
        }).sort("start_time", 1)
        surrounding_chunks = await cursor.to_list(None)

        # Concatenate texts
        texts = []
        for c in surrounding_chunks:
            texts.append(c.get("text", "").strip())

        # Join with spaces and clean up
        expanded_text = " ".join(texts)
        expanded_text = " ".join(expanded_text.split())  # Normalize whitespace

        # If we got good context, return it
        if len(expanded_text) > len(chunk.get("text", "")):
            logger.info(f"Expanded chunk from {len(chunk.get('text', ''))} to {len(expanded_text)} chars")
            return expanded_text
        else:
            # Fallback to original if expansion failed
            return chunk.get("text", "")

    except Exception as e:
        logger.warning(f"Context expansion failed: {e}")
        return chunk.get("text", "")


async def search_handler_lightweight_768d(request: SearchRequest) -> SearchResponse:
    """
    Enhanced search handler with 768D vector search
    Fallback chain: 768D Vector → Text Search → 384D Vector
    """
    handler_start = time.time()

    # Log at the very beginning with timestamp
    logger.info(f"=== SEARCH HANDLER START === Query: '{request.query}', Limit: {request.limit}, Time: {handler_start:.3f}")

    # Normalize query for consistent processing
    clean_query = request.query.strip().lower()

    # Debug logging
    if DEBUG_MODE:
        logger.info(f"[DEBUG] Original query: '{request.query}'")
        logger.info(f"[DEBUG] Clean query: '{clean_query}'")
        logger.info(f"[DEBUG] Offset: {request.offset}, Limit: {request.limit}")

    # Generate query hash for caching using normalized query
    query_hash = hashlib.sha256(clean_query.encode()).hexdigest()
    search_id = f"search_{query_hash[:8]}_{datetime.now().timestamp()}"

    # Try 768D Vector Search first
    try:
        # Check cache for 768D embedding
        # TODO: Implement MongoDB caching instead of Supabase
        # embedding_768d = await check_query_cache_768d(query_hash)
        # cache_hit = bool(embedding_768d)
        embedding_768d = None
        cache_hit = False

        if not embedding_768d:
            # Generate new 768D embedding
            pre_embed = time.time()
            logger.info(f"[TIMING] Pre-embedding: {pre_embed - handler_start:.3f}s elapsed. Generating 768D embedding for: {clean_query}")
            embed_start = time.time()
            embedding_768d = await generate_embedding_768d_local(clean_query)
            embed_time = time.time() - embed_start
            logger.info(f"[TIMING] Embedding generation took {embed_time:.2f}s, total elapsed: {time.time() - handler_start:.3f}s")

            if DEBUG_MODE and embedding_768d:
                logger.info(f"[DEBUG] Embedding length: {len(embedding_768d)}")
                logger.info(f"[DEBUG] First 5 values: {embedding_768d[:5]}")
                # Calculate embedding norm
                import math
                norm = math.sqrt(sum(x*x for x in embedding_768d))
                logger.info(f"[DEBUG] Embedding norm: {norm:.4f} (should be ~1.0 if normalized)")

            # TODO: Cache to MongoDB instead of Supabase
            # if embedding_768d:
            #     # Cache it asynchronously
            #     asyncio.create_task(store_query_cache_768d(request.query, query_hash, embedding_768d))

        if embedding_768d:
            # Get MongoDB vector search handler
            pre_vector = time.time()
            logger.info(f"[TIMING] Pre-vector handler: {pre_vector - handler_start:.3f}s elapsed")
            vector_handler = await get_vector_search_handler()
            logger.info(f"[TIMING] Vector handler created: {time.time() - handler_start:.3f}s elapsed")

            # Always try vector search if we have an embedding
            logger.info(f"Using MongoDB 768D vector search: {clean_query}")

            # Always fetch 10 chunks for synthesis, regardless of requested limit
            # But also fetch enough for pagination
            num_for_synthesis = 10
            num_to_fetch = max(num_for_synthesis, request.limit + request.offset)
            logger.info(f"Calling vector search with limit={num_to_fetch}, min_score=0.0")
            logger.warning(
                "[VECTOR_HANDLER] about to call %s from module %s",
                vector_handler.__class__.__qualname__,
                vector_handler.__class__.__module__,
            )
            try:
                start = time.time()
                vector_results = await vector_handler.vector_search(
                    embedding_768d,
                    limit=num_to_fetch,
                    min_score=0.0  # Lowered threshold to debug - was 0.7
                )
                logger.info("[VECTOR_LATENCY] %.1f ms", (time.time()-start)*1000)
            except Exception as ve:
                logger.error(f"[VECTOR_SEARCH_ERROR] Exception during vector search: {str(ve)}")
                logger.error(f"[VECTOR_SEARCH_ERROR] Type: {type(ve).__name__}")
                import traceback
                logger.error(f"[VECTOR_SEARCH_ERROR] Traceback: {traceback.format_exc()}")
                vector_results = []
            logger.info(f"Vector search returned {len(vector_results)} results")

            # ALWAYS log first result for debugging
            if vector_results:
                first_result = vector_results[0]
                logger.info(f"[ALWAYS_LOG] First result score: {first_result.get('score', 'NO_SCORE')}")
                logger.info(f"[ALWAYS_LOG] First result keys: {list(first_result.keys())[:10]}")
            else:
                logger.info(f"[ALWAYS_LOG] Vector search returned EMPTY results for '{clean_query}'")

            if DEBUG_MODE:
                logger.info(f"[DEBUG] search_id: {search_id}")
                logger.info(f"[DEBUG] clean_query: {clean_query}")
                logger.info(f"[DEBUG] vector_results_raw_count: {len(vector_results)}")
                if vector_results:
                    logger.info(f"[DEBUG] vector_results_top_score: {vector_results[0].get('score', 0):.4f}")
                    # Add raw dump of first 3 results
                    logger.info(f"[DEBUG] raw vector hits: {json.dumps(vector_results[:3], default=str)[:500]}")
                else:
                    logger.info(f"[DEBUG] vector_results_top_score: N/A (no results)")

            # Apply offset - slice from offset to end, not offset+limit
            paginated_results = vector_results[request.offset:]
            if len(paginated_results) > request.limit:
                paginated_results = paginated_results[:request.limit]
            logger.info(f"After pagination: {len(paginated_results)} results (offset={request.offset}, limit={request.limit})")

            # Convert to API format with expanded context
            formatted_results = []
            expansion_start = time.time()
            logger.info(f"Starting context expansion for {len(paginated_results)} results")

            for idx, result in enumerate(paginated_results):
                try:
                    # TEMPORARY: Skip expansion to fix performance issue
                    # TODO: Implement batch expansion after confirming this is the bottleneck

                    # Log timing for each expansion
                    chunk_start = time.time()

                    # Expand context for better readability
                    try:
                        # COMMENTED OUT: This is causing N+1 query problem
                        # expanded_text = await expand_chunk_context(result, context_seconds=20.0)
                        expanded_text = result.get("text", "")  # Temporary: use original text
                        logger.info(f"Skipping expansion for chunk {idx+1}/{len(paginated_results)} to fix N+1 query issue")
                    except Exception as e:
                        logger.warning(f"Context expansion failed: {e} - using original text")
                        expanded_text = result.get("text", "")

                    chunk_time = time.time() - chunk_start
                    if chunk_time > 0.5:  # Log if any single expansion takes > 500ms
                        logger.warning(f"Chunk {idx+1} expansion took {chunk_time:.2f}s")

                    # Vector search provides chunks with timestamps
                    # Handle published_at - it comes as string from Supabase
                    published_at_str = result.get("published_at")
                    if published_at_str:
                        try:
                            from dateutil import parser
                            published_dt = parser.parse(published_at_str)
                            published_at_iso = published_dt.isoformat()
                            published_date = published_dt.strftime('%B %d, %Y')
                        except:
                            published_at_iso = published_at_str
                            published_date = "Unknown date"
                    else:
                        published_at_iso = datetime.now().isoformat()
                        published_date = "Unknown date"

                    # Format episode title with number if available
                    episode_title = result.get("episode_title", "Unknown Episode")
                    episode_number = result.get("episode_number")
                    if episode_number:
                        episode_title = f"Episode {episode_number}: {episode_title}"

                    # Format published date
                    published_iso = result.get("published")
                    if published_iso:
                        try:
                            from dateutil import parser
                            published_dt = parser.parse(published_iso)
                            published_date = published_dt.strftime('%B %d, %Y')
                        except:
                            published_date = published_iso
                    else:
                        published_iso = published_at_iso
                        published_date = "Unknown date"

                    formatted_results.append(SearchResult(
                        episode_id=result.get("episode_id", "unknown"),
                        podcast_name=result.get("podcast_title", "Unknown Podcast"),
                        episode_title=episode_title,
                        published_at=published_iso,
                        published_date=published_date,
                        similarity_score=float(result.get("score", 0.0)) if result.get("score") is not None else 0.0,
                        excerpt=expanded_text,  # Use expanded text instead of single chunk
                        word_count=len(expanded_text.split()),
                        duration_seconds=result.get("duration_seconds", 0),
                        topics=result.get("topics", []),
                        s3_audio_path=result.get("s3_audio_path"),
                        timestamp={
                            "start_time": result.get("start_time", 0),  # Keep original timestamp for audio sync
                            "end_time": result.get("end_time", 0)
                        }
                    ))
                except Exception as e:
                    logger.error(f"Failed to format result: {e} - skipping this result")
                    logger.error(f"Result data: {result}")
                    continue  # Skip this result but process others

            # Log total expansion time
            expansion_time = time.time() - expansion_start
            logger.info(f"Context expansion completed in {expansion_time:.2f}s for {len(paginated_results)} results")
            if expansion_time > 5.0:
                logger.warning(f"PERFORMANCE WARNING: Context expansion took {expansion_time:.2f}s!")

            # Audio paths and durations are now included in vector search results
            # from the fixed mongodb_vector_search.py enrichment
            for result, vector_result in zip(formatted_results, paginated_results):
                result.s3_audio_path = vector_result.get("s3_audio_path")
                result.duration_seconds = vector_result.get("duration_seconds", 0)

            # Only return vector results if we actually got some
            if len(formatted_results) > 0:
                logger.info(f"Returning {len(formatted_results)} formatted results")

                # --- SAFE DIAGNOSTIC LOGGING ---
                logger.info("--- PRE-SYNTHESIS ENVIRONMENT CHECK ---")
                synthesis_enabled_env = os.getenv("ANSWER_SYNTHESIS_ENABLED", "not_set")
                openai_key_env = os.getenv("OPENAI_API_KEY")

                logger.info(f"ENV CHECK: Reading ANSWER_SYNTHESIS_ENABLED: '{synthesis_enabled_env}'")
                logger.info(f"ENV CHECK: OPENAI_API_KEY is set: {openai_key_env is not None and len(openai_key_env) > 0}")
                # --- END SAFE DIAGNOSTIC LOGGING ---

                # Try to synthesize an answer from the top chunks
                answer_object = None
                synthesis_start = time.time()
                try:
                    # Use the first 10 raw vector results for synthesis (before pagination)
                    # Clean ObjectIds from chunks to avoid serialization issues
                    chunks_for_synthesis = []
                    for chunk in vector_results[:num_for_synthesis]:
                        # Make a copy to avoid modifying original
                        clean_chunk = chunk.copy()
                        # Convert ObjectId to string if present
                        if "_id" in clean_chunk:
                            clean_chunk["_id"] = str(clean_chunk["_id"])
                        chunks_for_synthesis.append(clean_chunk)

                    logger.info(f"Synthesizing answer from {len(chunks_for_synthesis)} chunks")

                    synthesis_result = await synthesize_with_retry(chunks_for_synthesis, request.query)
                    if synthesis_result:
                        answer_object = AnswerObject(
                            text=synthesis_result.text,
                            citations=synthesis_result.citations
                        )
                        logger.info(f"Synthesis successful: {len(synthesis_result.citations)} citations")
                    else:
                        logger.warning("Synthesis returned None")
                except Exception as e:
                    logger.error(f"Synthesis failed: {str(e)}")
                    # Continue without answer - graceful degradation

                synthesis_time = int((time.time() - synthesis_start) * 1000)
                total_time = int((time.time() - start) * 1000)

                if DEBUG_MODE:
                    logger.info(f"[DEBUG] fallback_used: vector_768d")
                    logger.info(f"[DEBUG] synthesis_time_ms: {synthesis_time}")
                    logger.info(f"[DEBUG] total_time_ms: {total_time}")

                # Create the response object
                response = SearchResponse(
                    answer=answer_object,
                    results=formatted_results,
                    total_results=len(vector_results),
                    cache_hit=cache_hit,
                    search_id=search_id,
                    query=request.query,
                    limit=request.limit,
                    offset=request.offset,
                    search_method="vector_768d",
                    processing_time_ms=total_time,
                    raw_chunks=chunks_for_synthesis if DEBUG_MODE else None
                )

                # Simple logging before return
                logger.info("Response object created, about to return to FastAPI...")
                logger.info(f"Response has {len(formatted_results)} results")
                if answer_object:
                    logger.info(f"Answer synthesis included with {len(answer_object.citations)} citations")

                # Final timing
                logger.info(f"[TIMING] SEARCH HANDLER END - Total time: {time.time() - handler_start:.3f}s")

                # Return the response object (let FastAPI serialize it)
                return response
            else:
                logger.warning(f"Vector search returned 0 results, falling back to text search")
                if DEBUG_MODE:
                    logger.info(f"[DEBUG] fallback_used: text (vector returned 0)")

    except Exception as e:
        logger.error(f"768D vector search failed for query '{request.query}': {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

    # Fallback to MongoDB text search
    try:
        mongo_handler = await get_search_handler()

        if mongo_handler.db is not None:
            logger.info(f"Falling back to MongoDB text search: {clean_query}")

            mongo_results = await mongo_handler.search_transcripts(
                clean_query,
                limit=request.limit + request.offset
            )

            # Apply offset
            paginated_results = mongo_results[request.offset:request.offset + request.limit]

            # Convert MongoDB results to API format
            formatted_results = []
            for result in paginated_results:
                formatted_results.append(SearchResult(
                    episode_id=result["episode_id"],
                    podcast_name=result["podcast_name"],
                    episode_title=result["episode_title"],
                    published_at=result["published_at"],
                    published_date=result.get("published_date", "Unknown date"),
                    similarity_score=float(result.get("relevance_score", 0.0)) if result.get("relevance_score") is not None else 0.0,
                    excerpt=result["excerpt"],
                    word_count=result.get("word_count", 0),
                    duration_seconds=0,
                    topics=result.get("topics", []),
                    s3_audio_path=None,
                    timestamp=result.get("timestamp")
                ))

            # Skip Supabase enrichment to avoid UUID errors
            # if formatted_results:
            #     pool = get_pool()
            #     episode_ids = [r.episode_id for r in formatted_results]
            #
            #     def get_audio_paths(client):
            #         return client.table("episodes") \
            #             .select("id, s3_audio_path, duration_seconds") \
            #             .in_("id", episode_ids) \
            #             .execute()
            #
            #     audio_data = await pool.execute_with_retry(get_audio_paths)
            #
            #     audio_by_id = {
            #         ep["id"]: {
            #             "s3_audio_path": ep.get("s3_audio_path"),
            #             "duration_seconds": ep.get("duration_seconds", 0)
            #         }
            #         for ep in audio_data.data
            #     }
            #
            #     for result in formatted_results:
            #         if result.episode_id in audio_by_id:
            #             result.s3_audio_path = audio_by_id[result.episode_id]["s3_audio_path"]
            #             result.duration_seconds = audio_by_id[result.episode_id]["duration_seconds"]

            return SearchResponse(
                results=formatted_results,
                total_results=len(mongo_results),
                cache_hit=False,
                search_id=search_id,
                query=request.query,
                limit=request.limit,
                offset=request.offset,
                search_method="text"
            )

    except Exception as e:
        logger.warning(f"MongoDB text search failed: {str(e)}")

    # No more fallbacks - this is a problem
    logger.error(f"All search methods failed for: {request.query}")

    # TEMPORARILY DISABLED FOR DEBUGGING
    # Return empty results instead of 503 to see what's happening
    logger.warning("Returning empty results instead of 503 for debugging")
    return SearchResponse(
        results=[],
        total_results=0,
        cache_hit=False,
        search_id=search_id,
        query=request.query,
        limit=request.limit,
        offset=request.offset,
        search_method="none_all_failed"
    )

    # # Fail fast to alert monitoring
    # raise HTTPException(
    #     status_code=503,
    #     detail="SEARCH_BACKEND_EMPTY - Both vector and text search returned no results"
    # )
