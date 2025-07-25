import os, sys, time
print(
    f"[BOOT-TOP] sha={os.getenv('VERCEL_GIT_COMMIT_SHA','local')} "
    f"py={sys.version.split()[0]}  ts={int(time.time())}",
    flush=True)

import logging
logging.basicConfig(level="INFO")
logging.info("[BOOT-FILE] %s  commit=%s",
             __file__,
             os.getenv("VERCEL_GIT_COMMIT_SHA", "?"))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from dateutil import parser
import os
import logging
from supabase import create_client, Client
from lib.database import get_pool, SupabasePool
# Use lightweight version for Vercel deployment
# from .search import search_handler, SearchRequest, SearchResponse
from .search_lightweight_768d import search_handler_lightweight_768d as search_handler, SearchRequest, SearchResponse
from .mongodb_search import get_search_handler
import asyncio
import time
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Environment variables are loaded from Vercel dashboard
# load_dotenv() is not needed in production

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="PodInsightHQ API",
    description="Track emerging topics in startup and VC podcasts",
    version="1.0.0"
)

# Add rate limit exceeded handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Warmup disabled - file moved to api_temp
# from .warmup import warmup_connections

# @app.on_event("startup")
# async def startup_event():
#     """Run warmup on startup"""
#     logger.info("Starting API warmup...")
#     await warmup_connections()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client (kept for backward compatibility)
def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

    # Debug logging
    logger.info(f"SUPABASE_URL present: {bool(url)}")
    logger.info(f"SUPABASE_KEY/ANON_KEY present: {bool(key)}")

    if not url or not key:
        logger.error(f"Missing Supabase configuration - URL: {bool(url)}, KEY: {bool(key)}")
        raise ValueError("Supabase configuration not found")

    return create_client(url, key)

@app.get("/")
async def root():
    """Health check endpoint"""
    pool = get_pool()
    pool_health = await pool.health_check()

    return {
        "status": "healthy",
        "service": "PodInsightHQ API",
        "version": "1.0.0",
        "deployment_time": datetime.now().isoformat(),  # Cache busting verification
        "env_check": {
            "SUPABASE_URL": bool(os.environ.get("SUPABASE_URL")),
            "SUPABASE_KEY": bool(os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")),
            "HUGGINGFACE_API_KEY": bool(os.environ.get("HUGGINGFACE_API_KEY")),
            "MONGODB_URI": bool(os.environ.get("MONGODB_URI")),
            "PYTHON_VERSION": os.environ.get("PYTHON_VERSION", "not set")
        },
        "connection_pool": pool_health
    }

@app.get("/api/debug/mongodb")
async def debug_mongodb():
    """Debug MongoDB connection and search capabilities"""

    mongodb_uri_set = bool(os.environ.get('MONGODB_URI'))

    try:
        handler = await get_search_handler()

        if handler.db is None:
            return {
                "status": "error",
                "mongodb_uri_set": mongodb_uri_set,
                "connection": "failed",
                "message": "MongoDB handler not connected"
            }

        # Test multiple search queries
        test_queries = ["bitcoin", "AI", "AI agents", "crypto"]
        test_results = {}

        for query in test_queries:
            try:
                results = await handler.search_transcripts(query, limit=1)
                test_results[query] = {
                    "count": len(results),
                    "score": results[0]["relevance_score"] if results else 0,
                    "has_highlights": "**" in results[0]["excerpt"] if results else False
                }
            except Exception as e:
                test_results[query] = {"error": str(e)}

        return {
            "status": "success",
            "mongodb_uri_set": mongodb_uri_set,
            "connection": "connected",
            "database_name": "podinsight",
            "collection_name": "transcripts",
            "test_searches": test_results
        }

    except Exception as e:
        return {
            "status": "error",
            "mongodb_uri_set": mongodb_uri_set,
            "connection": "error",
            "error": str(e)
        }

@app.get("/api/topic-velocity")
async def get_topic_velocity(
    weeks: Optional[int] = 12,
    topics: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get topic velocity data showing trending topics across podcasts.

    Parameters:
    - weeks: Number of weeks to return (default: 12)
    - topics: Comma-separated list of specific topics to track (optional)

    Returns:
    - Topic velocity data formatted for Recharts line chart
    """
    pool = get_pool()
    request_start = time.time()

    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)

        logger.info(f"Fetching topic velocity for past {weeks} weeks")

        # Default topics if none specified (exactly 5 as per playbook)
        default_topics = [
            "AI Agents",
            "Capital Efficiency",
            "DePIN",
            "B2B SaaS",
            "Crypto/Web3"  # NO SPACES around the slash!
        ]

        # Parse topics parameter
        if topics:
            topic_list = [t.strip() for t in topics.split(",")]
        else:
            topic_list = default_topics

        # Define query function for the pool (sync function since Supabase client is sync)
        # FIXED: Query ALL mentions to ensure consistent historical data
        def query_topic_mentions(client):
            return client.table("topic_mentions") \
                .select("*, episodes!inner(published_at)") \
                .in_("topic_name", topic_list) \
                .execute()

        # Execute with retry
        query_start = time.time()
        response = await pool.execute_with_retry(query_topic_mentions)
        query_time = (time.time() - query_start) * 1000
        logger.info(f"Topic mentions query took {query_time:.2f}ms")

        # Process data to create Recharts-compatible format
        # Group mentions by week and count
        process_start = time.time()
        weekly_data = {}

        for mention in response.data:
            topic = mention["topic_name"]
            week_num = mention["week_number"]  # Already stored as string like "1", "2", etc.

            # Parse the episode's published_at date to get year
            # Use dateutil.parser for robust datetime parsing
            published_at = parser.parse(mention["episodes"]["published_at"])
            year = published_at.year

            # Convert week number to ISO week format
            week_key = f"{year}-W{week_num.zfill(2)}"  # e.g., "2025-W01"

            if week_key not in weekly_data:
                weekly_data[week_key] = {topic: 0 for topic in topic_list}

            if topic in weekly_data[week_key]:
                weekly_data[week_key][topic] += 1  # Each row is one mention

        # Sort weeks chronologically
        sorted_weeks = sorted(weekly_data.keys())

        # FIXED: Generate ALL weeks in the requested range (including empty weeks)
        # This ensures we return exactly the number of weeks requested
        all_weeks_in_range = []
        current_date = end_date

        # Generate weeks from end_date backwards to start_date
        while current_date >= start_date:
            # Get ISO week number and year
            iso_year, iso_week, _ = current_date.isocalendar()
            week_key = f"{iso_year}-W{str(iso_week).zfill(2)}"
            all_weeks_in_range.append(week_key)

            # Move to previous week
            current_date -= timedelta(weeks=1)

        # Sort chronologically (oldest first)
        all_weeks_in_range.reverse()

        logger.info(f"Generated {len(all_weeks_in_range)} weeks for requested range, {len(sorted_weeks)} weeks have data")

        # Build the data structure for Recharts
        data_by_topic = {topic: [] for topic in topic_list}

        for week in all_weeks_in_range:
            # Parse week to get date range for display
            year, week_num = week.split('-W')
            week_num = int(week_num)

            # Calculate the start date of the week
            jan1 = datetime(int(year), 1, 1)
            week_start = jan1 + timedelta(weeks=week_num-1) - timedelta(days=jan1.weekday())
            week_end = week_start + timedelta(days=6)

            date_range = f"{week_start.strftime('%b %-d')}-{week_end.strftime('%-d')}"

            # Add data point for each topic
            for topic in topic_list:
                # Check if we have data for this week, otherwise default to 0
                mentions = 0
                if week in weekly_data and topic in weekly_data[week]:
                    mentions = weekly_data[week][topic]

                data_by_topic[topic].append({
                    "week": week,
                    "mentions": mentions,
                    "date": date_range
                })

        # Get total episodes count
        def query_total_episodes(client):
            return client.table("episodes").select("id", count="exact").execute()

        total_episodes_response = await pool.execute_with_retry(query_total_episodes)
        total_episodes = total_episodes_response.count if hasattr(total_episodes_response, 'count') else 1171

        # Get date range from episodes
        def query_date_range_start(client):
            return client.table("episodes") \
                .select("published_at") \
                .order("published_at", desc=False) \
                .limit(1) \
                .execute()

        def query_date_range_end(client):
            return client.table("episodes") \
                .select("published_at") \
                .order("published_at", desc=True) \
                .limit(1) \
                .execute()

        date_range_response = await pool.execute_with_retry(query_date_range_start)
        date_range_response_end = await pool.execute_with_retry(query_date_range_end)

        start_date_str = date_range_response.data[0]["published_at"][:10] if date_range_response.data else "2025-01-01"
        end_date_str = date_range_response_end.data[0]["published_at"][:10] if date_range_response_end.data else "2025-06-14"

        # Log processing time
        process_time = (time.time() - process_start) * 1000
        total_time = (time.time() - request_start) * 1000
        logger.info(f"Data processing took {process_time:.2f}ms")
        logger.info(f"Total request time: {total_time:.2f}ms")

        return {
            "data": data_by_topic,
            "metadata": {
                "total_episodes": total_episodes,
                "date_range": f"{start_date_str} to {end_date_str}",
                "data_completeness": "topics_only"  # Note: entities available in v2
            }
        }

    except Exception as e:
        logger.error(f"Error fetching topic velocity: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch topic velocity data: {str(e)}"
        )

@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring"""
    # Check Hugging Face API key
    hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
    has_hf_key = bool(hf_api_key and hf_api_key.startswith("hf_"))

    # Check Supabase connection
    try:
        pool = get_pool()
        pool_stats = pool.get_stats()
        db_connected = True
    except Exception:
        pool_stats = None
        db_connected = False

    return {
        "status": "healthy" if (has_hf_key and db_connected) else "degraded",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "huggingface_api_key": "configured" if has_hf_key else "missing",
            "database": "connected" if db_connected else "disconnected",
            "connection_pool": pool_stats if pool_stats else "unavailable"
        },
        "version": "1.0.0"
    }

@app.get("/api/pool-stats")
async def get_pool_stats() -> Dict[str, Any]:
    """Get connection pool statistics and monitoring data"""
    pool = get_pool()
    return {
        "success": True,
        "stats": pool.get_stats(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/topics")
async def get_available_topics() -> Dict[str, List[str]]:
    """Get list of all available topics being tracked"""
    pool = get_pool()

    try:
        # Define query function
        def query_topics(client):
            return client.table("topic_mentions") \
                .select("topic_name") \
                .execute()

        # Execute with retry
        response = await pool.execute_with_retry(query_topics)

        unique_topics = list(set([r["topic_name"] for r in response.data]))

        return {
            "success": True,
            "topics": sorted(unique_topics),
            "count": len(unique_topics)
        }

    except Exception as e:
        logger.error(f"Error fetching topics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch topics: {str(e)}"
        )

@app.get("/api/signals")
async def get_topic_signals(
    signal_type: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get pre-computed topic signals for dashboard SIGNAL bar

    This endpoint returns:
    - Topic correlations (which topics appear together)
    - Topic spikes (unusual activity)
    - Trending combinations (fast-growing topic pairs)

    Query parameters:
    - signal_type: Filter by type ('correlation', 'spike', 'trending_combo')
    - limit: Maximum number of signals to return (default 10)

    Example:
    ```
    GET /api/signals?signal_type=correlation&limit=5
    ```
    """
    try:
        pool = get_pool()

        # Build query
        def query_signals(client):
            query = client.table("topic_signals") \
                .select("*") \
                .order("calculated_at", desc=True)

            if signal_type:
                query = query.eq("signal_type", signal_type)

            return query.limit(limit).execute()

        # Execute query
        signals_response = await pool.execute_with_retry(query_signals)

        # Group signals by type
        signals_by_type = {}
        for signal in signals_response.data:
            sig_type = signal["signal_type"]
            if sig_type not in signals_by_type:
                signals_by_type[sig_type] = []
            signals_by_type[sig_type].append(signal["signal_data"])

        # Generate SIGNAL bar messages from the data
        signal_messages = []

        # Get the BEST correlations only (sorted by percentage)
        if "correlation" in signals_by_type:
            # Sort by correlation percentage to get the most impressive
            sorted_correlations = sorted(
                signals_by_type["correlation"],
                key=lambda x: x["co_occurrence_percent"],
                reverse=True
            )

            # Only show truly impressive correlations
            for corr in sorted_correlations[:5]:
                topics = corr["topics"]
                percent = corr["co_occurrence_percent"]
                count = corr["episode_count"]

                # Show top correlations with better framing
                if percent > 20:
                    signal_messages.append(
                        f"{topics[0]} + {topics[1]} appear together in {int(percent)}% of episodes ({count} co-occurrences)"
                    )
                elif percent > 10 and count > 15:
                    # Frame medium correlations as notable
                    signal_messages.append(
                        f"{topics[0]} + {topics[1]} linked in {count} episodes ({int(percent)}% correlation)"
                    )
                elif percent > 5 and count > 10:
                    # Frame smaller correlations by volume
                    signal_messages.append(
                        f"{topics[0]} + {topics[1]} discussed together {count} times"
                    )

        # Add spike insights only if actually impressive
        if "spike" in signals_by_type:
            for spike in signals_by_type["spike"][:2]:
                topic = spike["topic"]
                factor = spike["spike_factor"]
                current = spike.get("current_week_mentions", 0)
                # Only show if truly spiking (3x or more)
                if factor >= 3:
                    signal_messages.append(
                        f"{topic} exploding with {factor}x normal activity ({current} mentions this week)"
                    )

        # Add growth insights with clearer language
        if "trending_combo" in signals_by_type:
            for trend in signals_by_type["trending_combo"][:3]:
                topics = trend["topics"]
                growth = trend["growth_rate"]
                current = trend["current_period_mentions"]
                base = trend["base_period_mentions"]

                # Show growth with clearer thresholds
                if growth > 75 and current >= 5:
                    signal_messages.append(
                        f"{topics[0]} + {topics[1]} growing fast: {base}→{current} co-occurrences (+{int(growth)}%)"
                    )
                elif growth > 30 and current >= 8:
                    signal_messages.append(
                        f"{topics[0]} + {topics[1]} trending up: {base}→{current} episodes"
                    )

        # Always ensure we have at least 3-4 good signals
        if len(signal_messages) < 4:
            # Add volume-based insights
            if "correlation" in signals_by_type and len(signals_by_type["correlation"]) > 3:
                # Find total episodes with multiple topics
                total_multi = sum(c["episode_count"] for c in signals_by_type["correlation"][:10])
                signal_messages.append(
                    f"Cross-topic discussions found in {total_multi}+ episodes (strong interconnection)"
                )

            # Add the highest absolute numbers
            if "correlation" in signals_by_type:
                for corr in sorted_correlations[len(signal_messages):]:
                    if len(signal_messages) >= 5:
                        break
                    if corr["episode_count"] > 10:
                        signal_messages.append(
                            f"{corr['topics'][0]} + {corr['topics'][1]} discussed in {corr['episode_count']} episodes"
                        )

        return {
            "signals": signals_by_type,
            "signal_messages": signal_messages,
            "last_updated": signals_response.data[0]["calculated_at"] if signals_response.data else None,
            "metadata": {
                "total_signals": len(signals_response.data),
                "signal_types": list(signals_by_type.keys())
            }
        }

    except Exception as e:
        logger.error(f"Error fetching signals: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch signals: {str(e)}"
        )

@app.get("/api/entities")
async def get_entities(
    search: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 20,
    timeframe: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search and track entities (people, companies, etc.) across all episodes

    Query parameters:
    - search: Optional search term for entity names (fuzzy match)
    - type: Filter by entity type (PERSON, ORG, GPE, MONEY)
    - limit: Maximum entities to return (default 20, max 100)
    - timeframe: Optional time filter (e.g., "30d", "90d")

    Example:
    ```
    GET /api/entities?search=Sequoia&type=ORG&limit=10
    ```

    CRITICAL: Uses 'label' field for entity type, NOT 'type' field!
    """
    try:
        pool = get_pool()

        # Validate limit
        if limit > 100:
            limit = 100
        elif limit < 1:
            limit = 20

        # Calculate date filter if timeframe specified
        date_filter = None
        if timeframe:
            days = 30  # default
            if timeframe.endswith('d'):
                try:
                    days = int(timeframe[:-1])
                except ValueError:
                    days = 30
            date_filter = datetime.now() - timedelta(days=days)
            # Ensure date_filter is timezone-aware for Supabase comparison
            if date_filter.tzinfo is None:
                date_filter = date_filter.replace(tzinfo=timezone.utc)

        # Build the entity search query
        def query_entities(client):
            # Base query with episode join for meaningful episode info
            query = client.table("extracted_entities") \
                .select("entity_name, entity_type, episode_id, episodes!inner(published_at, podcast_name, duration_seconds)")

            # Add search filter if provided
            if search:
                query = query.ilike("entity_name", f"%{search}%")

            # Add type filter if provided (using 'entity_type' field - playbook was wrong)
            if type:
                query = query.eq("entity_type", type.upper())

            # Add date filter if specified
            if date_filter:
                query = query.gte("episodes.published_at", date_filter.isoformat())

            return query.execute()

        # Execute query
        entities_response = await pool.execute_with_retry(query_entities)

        # Aggregate entity data
        entity_aggregates = {}

        for entity_record in entities_response.data:
            entity_name = entity_record["entity_name"]
            entity_type = entity_record["entity_type"]
            episode_data = entity_record["episodes"]

            if entity_name not in entity_aggregates:
                entity_aggregates[entity_name] = {
                    "name": entity_name,
                    "type": entity_type,
                    "mention_count": 0,
                    "episode_count": 0,
                    "episodes": [],
                    "recent_mentions": []
                }

            # Increment counts
            entity_aggregates[entity_name]["mention_count"] += 1

            # Track unique episodes
            episode_id = entity_record["episode_id"]
            if episode_id not in [ep["episode_id"] for ep in entity_aggregates[entity_name]["episodes"]]:
                entity_aggregates[entity_name]["episode_count"] += 1

                # Add episode info with meaningful title
                published_date = parser.parse(episode_data["published_at"])
                podcast_name = episode_data.get("podcast_name", "Unknown Podcast")
                duration_seconds = episode_data.get("duration_seconds", 0)

                # Create meaningful episode title: "Podcast Name - 65 min (Jun 12, 2025)"
                if duration_seconds and duration_seconds > 0:
                    duration_minutes = round(duration_seconds / 60)
                    display_title = f"{podcast_name} - {duration_minutes} min ({published_date.strftime('%b %d, %Y')})"
                else:
                    display_title = f"{podcast_name} ({published_date.strftime('%b %d, %Y')})"

                entity_aggregates[entity_name]["episodes"].append({
                    "episode_id": episode_id,
                    "episode_title": display_title,
                    "published_at": published_date.isoformat(),
                    "date": published_date.strftime("%B %d, %Y")
                })

        # Filter out unhelpful single-name PERSON entities
        filtered_entities = []
        for entity in entity_aggregates.values():
            entity_name = entity["name"]
            entity_type = entity["type"]

            # Skip single-name PERSON entities that are too generic
            if entity_type == "PERSON" and " " not in entity_name:
                # Common first names that aren't useful without context
                generic_names = {"Tom", "Tommy", "Mark", "Ben", "Mike", "John", "David", "Chris", "Matt", "Steve", "Dan", "Paul", "Tim", "Rob", "Jim", "Sam", "Alex", "Ryan", "Brian", "Kevin", "Jason", "Jeff", "Nick", "Eric", "Sean"}
                if entity_name in generic_names:
                    continue

            filtered_entities.append(entity)

        # Sort entities by mention count and limit results
        sorted_entities = sorted(
            filtered_entities,
            key=lambda x: x["mention_count"],
            reverse=True
        )[:limit]

        # Calculate trends for top entities (compare recent vs older mentions)
        for entity in sorted_entities:
            recent_count = 0
            older_count = 0
            cutoff_date = datetime.now() - timedelta(weeks=4)
            cutoff_date = cutoff_date.replace(tzinfo=None)  # Make naive for comparison

            for episode in entity["episodes"]:
                episode_date = parser.parse(episode["published_at"])
                # Ensure both dates are naive for comparison
                if episode_date.tzinfo:
                    episode_date = episode_date.replace(tzinfo=None)
                if episode_date > cutoff_date:
                    recent_count += 1
                else:
                    older_count += 1

            # Determine trend
            if recent_count > older_count * 1.5:
                entity["trend"] = "up"
            elif older_count > recent_count * 1.5:
                entity["trend"] = "down"
            else:
                entity["trend"] = "stable"

            # Add recent mentions (last 3)
            recent_episodes = sorted(
                entity["episodes"],
                key=lambda x: x["published_at"],
                reverse=True
            )[:3]

            entity["recent_mentions"] = [
                {
                    "episode_title": ep["episode_title"],
                    "date": ep["date"],
                    "context": f"Mentioned in {ep['episode_title']}"
                }
                for ep in recent_episodes
            ]

            # Clean up episodes list for response
            del entity["episodes"]

        # Get total count for pagination info
        total_entities = len(entity_aggregates)

        return {
            "success": True,
            "entities": sorted_entities,
            "total_entities": total_entities,
            "filters": {
                "search": search,
                "type": type,
                "timeframe": timeframe,
                "limit": limit
            },
            "metadata": {
                "available_types": ["PERSON", "ORG", "GPE", "MONEY"],
                "note": "Trends compare last 4 weeks to previous period"
            }
        }

    except Exception as e:
        logger.error(f"Error fetching entities: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch entities: {str(e)}"
        )

# Removed test endpoints to stay under 12 function limit

@app.post("/api/search", response_model=SearchResponse)
@limiter.limit("20/minute")
async def search_episodes_endpoint(
    request: Request,
    search_request: SearchRequest
) -> SearchResponse:
    """
    Search episodes using natural language queries

    This endpoint:
    - Accepts natural language search queries (max 500 chars)
    - Generates embeddings using sentence-transformers/all-MiniLM-L6-v2
    - Searches using pgvector similarity (ranked approach)
    - Returns relevant episodes with metadata and excerpts
    - Implements query caching for performance
    - Rate limited to 20 requests per minute per IP

    Example:
    ```
    POST /api/search
    {
        "query": "AI agents and startup valuations",
        "limit": 10,
        "offset": 0
    }
    ```
    """
    return await search_handler(search_request)

# Test endpoint disabled for production deployment
# from .test_search import test_search_handler, TestSearchRequest, TestSearchResponse
#
# @app.post("/api/test-search", response_model=TestSearchResponse)
# async def test_search_endpoint(request: TestSearchRequest) -> TestSearchResponse:
#     """Test MongoDB vector search without Modal embedding generation"""
#     return await test_search_handler(request)

# Import debug endpoints - temporarily disabled
# from .debug_search import router as debug_router
# app.include_router(debug_router)

@app.get("/__diag")
async def diag():
    """
    Diagnostic endpoint to check environment variables and index configuration
    """
    from pymongo import MongoClient

    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DATABASE", "podinsight")

    try:
        c = MongoClient(uri, serverSelectionTimeoutMS=3000)
        col = c[db_name].transcript_chunks_768d

        # List indexes
        idx = list(col.list_indexes())

        # Quick vector search with dummy embedding
        try:
            hit = col.aggregate([
                {"$vectorSearch": {
                    "index": "vector_index_768d",
                    "path": "embedding_768d",
                    "queryVector": [0]*768,
                    "numCandidates": 10,
                    "limit": 1
                }},
                {"$project": {"_id": 0, "episode_id": 1}}
            ]).try_next()
        except Exception as e:
            hit = None
            logger.error(f"Vector search test failed: {e}")

        # Get collection stats
        try:
            count = col.estimated_document_count()
        except:
            count = -1

        return {
            "db_name": db_name,
            "collection_count": count,
            "indexes": [i["name"] for i in idx],
            "vector_index_found": any(i["name"] == "vector_index_768d" for i in idx),
            "vector_dummy_hit": hit is not None,
            "env_vars_present": {
                "MONGODB_URI": bool(uri),
                "MONGODB_DATABASE": bool(db_name),
                "MODAL_EMBEDDING_URL": bool(os.getenv("MODAL_EMBEDDING_URL"))
            }
        }
    except Exception as e:
        return {
            "error": str(e),
            "db_name": db_name,
            "env_vars_present": {
                "MONGODB_URI": bool(uri),
                "MONGODB_DATABASE": bool(db_name),
                "MODAL_EMBEDDING_URL": bool(os.getenv("MODAL_EMBEDDING_URL"))
            }
        }

# ------------------------------------  diagnostics  ------------------------------------
from motor.motor_asyncio import AsyncIOMotorClient
import math, traceback, requests, os, time, logging

@app.get("/diag", tags=["diag"])
async def diag_root():
    """Very small health ping – proves Atlas connection"""
    t0 = time.time()
    uri = os.getenv("MONGODB_URI")
    db  = os.getenv("MONGODB_DATABASE", "podinsight")
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    cnt = await client[db].transcript_chunks_768d.estimated_document_count()
    return {
        "count": cnt,
        "elapsed_ms": round((time.time()-t0)*1e3),
        "db": db,
        "env_ok": {k: bool(os.getenv(k)) for k in
                   ["MONGODB_URI","MONGODB_DATABASE","MODAL_EMBEDDING_URL"]}
    }

@app.get("/diag/vc", tags=["diag"])
async def diag_vc():
    """End-to-end vector search for 'venture capital'"""
    try:
        t0 = time.time()
        vec = requests.post(
            os.getenv("MODAL_EMBEDDING_URL"),
            json={"text": "venture capital"}, timeout=15).json()["embedding"]
        embed_ms = round((time.time()-t0)*1e3)

        client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
        t1 = time.time()
        hits = await client.podinsight.transcript_chunks_768d.aggregate([
            {"$vectorSearch": {
                "index":"vector_index_768d",
                "path":"embedding_768d",
                "queryVector":vec,
                "numCandidates":100,
                "limit":3}},
            {"$addFields":{"score":{"$meta":"vectorSearchScore"}}},
            {"$project":{"score":1,"text":{"$substr":["$text",0,80]}}}
        ]).to_list(None)
        search_ms = round((time.time()-t1)*1e3)

        return {"hits": len(hits), "embed_ms": embed_ms,
                "search_ms": search_ms, "top": hits}
    except Exception as e:
        logging.exception("diag_vc failed")
        return {"error": str(e), "trace": traceback.format_exc()[:500]}
# ----------------------------------------------------------------------------------------

# Handler for Vercel
handler = app
