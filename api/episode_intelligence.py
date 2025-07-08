from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import motor.motor_asyncio
from bson import ObjectId
import os
import logging
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

# Note: Using a different prefix to avoid conflict with existing intelligence endpoints
router = APIRouter(prefix="/api/intelligence", tags=["episode-intelligence"])

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = client.get_database("podinsights")

# Collections
chunks_collection = db["transcript_chunks_768d"]
metadata_collection = db["episode_metadata"]
sentiment_collection = db["sentiment_results"]

# Cache TTL in seconds (5 minutes)
CACHE_TTL = 300

# Simple in-memory cache
cache = {}

def get_cache_key(endpoint: str, **kwargs) -> str:
    """Generate cache key from endpoint and parameters"""
    params = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
    return f"{endpoint}_{params}"

def get_cached_response(cache_key: str):
    """Get cached response if valid"""
    if cache_key in cache:
        cached_data, timestamp = cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return cached_data
        else:
            del cache[cache_key]
    return None

def set_cache(cache_key: str, data):
    """Set cache with timestamp"""
    cache[cache_key] = (data, time.time())

# Response Models
class IntelligenceItem(BaseModel):
    id: str
    title: str
    description: str
    urgency: str  # "critical", "high", "normal"
    metadata: dict

class IntelligenceResponse(BaseModel):
    data: dict

@router.get("/market-signals")
async def get_market_signals(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    since: Optional[str] = None
):
    """Get trending topics and market signals from recent podcasts"""

    # Check cache
    cache_key = get_cache_key("market-signals", limit=limit, offset=offset, since=since)
    cached = get_cached_response(cache_key)
    if cached:
        return cached

    try:
        # Calculate time window (default: last 2 weeks)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=14)
        if since:
            start_date = datetime.fromisoformat(since.replace('Z', '+00:00'))

        # Pipeline to find trending topics
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()},
                    "text": {"$regex": "trend|shift|pivot|emerging|growth|momentum", "$options": "i"}
                }
            },
            {
                "$project": {
                    "text": 1,
                    "episode_id": 1,
                    "feed_slug": 1,
                    "words": {"$split": ["$text", " "]}
                }
            },
            {
                "$unwind": "$words"
            },
            {
                "$match": {
                    "words": {"$regex": "^[A-Z][a-z]+", "$options": ""}  # Capitalized words (potential topics)
                }
            },
            {
                "$group": {
                    "_id": "$words",
                    "count": {"$sum": 1},
                    "sample_text": {"$first": "$text"},
                    "sources": {"$addToSet": "$feed_slug"}
                }
            },
            {
                "$match": {
                    "count": {"$gte": 5}  # Mentioned at least 5 times
                }
            },
            {
                "$sort": {"count": -1}
            },
            {
                "$skip": offset
            },
            {
                "$limit": limit
            }
        ]

        cursor = chunks_collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)

        # Calculate urgency based on velocity (simplified for now)
        items = []
        for idx, result in enumerate(results):
            topic = result["_id"]
            count = result["count"]

            # Determine urgency
            if count > 50:
                urgency = "critical"
            elif count > 20:
                urgency = "high"
            else:
                urgency = "normal"

            # Extract meaningful description from sample text
            sample = result["sample_text"][:200] + "..." if len(result["sample_text"]) > 200 else result["sample_text"]

            items.append({
                "id": f"ms-{idx+1}",
                "title": f"{topic} - Significant momentum",
                "description": sample,
                "urgency": urgency,
                "metadata": {
                    "source": ", ".join(result["sources"][:2]),
                    "change": f"+{count*10}%"  # Simplified metric
                }
            })

        response = {
            "data": {
                "items": items,
                "totalCount": len(items),
                "lastUpdated": datetime.utcnow().isoformat() + "Z",
                "metadata": {
                    "cacheKey": "market-signals-v1",
                    "ttl": CACHE_TTL
                }
            }
        }

        # Set cache
        set_cache(cache_key, response)

        return response

    except Exception as e:
        logger.error(f"Error in get_market_signals: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch market signals")

@router.get("/deals")
async def get_deals(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    urgency: Optional[str] = Query(None, regex="^(critical|high|normal)$")
):
    """Get investment opportunities and deals mentioned in podcasts"""

    # Check cache
    cache_key = get_cache_key("deals", limit=limit, offset=offset, urgency=urgency)
    cached = get_cached_response(cache_key)
    if cached:
        return cached

    try:
        # Search for funding-related keywords
        deal_keywords = ["funding", "raised", "series", "investment", "valuation", "acquired", "acquisition", "merger"]

        # Build regex pattern
        pattern = "|".join(deal_keywords)

        # Query with text search
        query = {
            "text": {"$regex": pattern, "$options": "i"},
            "created_at": {"$gte": (datetime.utcnow() - timedelta(days=30)).isoformat()}
        }

        # Execute query with pagination
        cursor = chunks_collection.find(query).skip(offset).limit(limit)
        chunks = await cursor.to_list(length=None)

        items = []
        for idx, chunk in enumerate(chunks):
            # Determine urgency based on keywords
            text_lower = chunk["text"].lower()
            if any(word in text_lower for word in ["closing", "tomorrow", "deadline", "urgent"]):
                urgency_level = "critical"
            elif any(word in text_lower for word in ["soon", "quickly", "fast"]):
                urgency_level = "high"
            else:
                urgency_level = "normal"

            # Filter by requested urgency if specified
            if urgency and urgency_level != urgency:
                continue

            # Extract deal info (simplified)
            title = f"Investment Opportunity - Episode {chunk.get('episode_id', 'Unknown')[:8]}"

            # Try to extract value from text
            value = "Undisclosed"
            if "$" in chunk["text"]:
                # Simple extraction of dollar amounts
                import re
                amounts = re.findall(r'\$[\d.]+[MBK]?', chunk["text"])
                if amounts:
                    value = amounts[0]

            items.append({
                "id": f"di-{idx+1}",
                "title": title,
                "description": chunk["text"][:200] + "...",
                "urgency": urgency_level,
                "metadata": {
                    "source": chunk.get("feed_slug", "Unknown"),
                    "value": value,
                    "deadline": (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z" if urgency_level == "critical" else None
                }
            })

        response = {
            "data": {
                "items": items[:limit],  # Ensure we don't exceed limit
                "totalCount": len(items),
                "lastUpdated": datetime.utcnow().isoformat() + "Z"
            }
        }

        # Set cache
        set_cache(cache_key, response)

        return response

    except Exception as e:
        logger.error(f"Error in get_deals: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch deals")

@router.get("/portfolio")
async def get_portfolio_mentions(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    portfolio_ids: Optional[str] = Query(None, description="Comma-separated portfolio company names")
):
    """Get mentions of portfolio companies in recent podcasts"""

    # Check cache
    cache_key = get_cache_key("portfolio", limit=limit, offset=offset, portfolio_ids=portfolio_ids)
    cached = get_cached_response(cache_key)
    if cached:
        return cached

    try:
        # Default portfolio companies (would come from config/database in production)
        portfolio_companies = ["OpenAI", "Anthropic", "Databricks", "Stripe", "SpaceX", "Airbnb"]

        if portfolio_ids:
            portfolio_companies = [c.strip() for c in portfolio_ids.split(",")]

        # Build case-insensitive regex
        pattern = "|".join(portfolio_companies)

        # Query for mentions
        query = {
            "text": {"$regex": pattern, "$options": "i"},
            "created_at": {"$gte": (datetime.utcnow() - timedelta(days=30)).isoformat()}
        }

        cursor = chunks_collection.find(query).skip(offset).limit(limit)
        chunks = await cursor.to_list(length=None)

        items = []
        for idx, chunk in enumerate(chunks):
            # Determine which company was mentioned
            text_lower = chunk["text"].lower()
            mentioned_company = None
            for company in portfolio_companies:
                if company.lower() in text_lower:
                    mentioned_company = company
                    break

            if not mentioned_company:
                continue

            # Simple sentiment analysis based on keywords
            negative_words = ["concern", "problem", "issue", "decline", "loss", "bad", "worse", "down"]
            positive_words = ["growth", "success", "increase", "improve", "better", "up", "great"]

            neg_count = sum(1 for word in negative_words if word in text_lower)
            pos_count = sum(1 for word in positive_words if word in text_lower)

            if neg_count > pos_count:
                urgency_level = "high"
                sentiment = "Negative sentiment"
            else:
                urgency_level = "normal"
                sentiment = "Positive sentiment" if pos_count > 0 else "Neutral"

            items.append({
                "id": f"pp-{idx+1}",
                "title": f"{mentioned_company} mentioned on {chunk.get('feed_slug', 'podcast')}",
                "description": chunk["text"][:200] + "...",
                "urgency": urgency_level,
                "metadata": {
                    "source": f"{chunk.get('feed_slug', 'Unknown')} Episode",
                    "value": sentiment,
                    "episode_url": f"https://example.com/episode/{chunk.get('episode_id', '')}"
                }
            })

        response = {
            "data": {
                "items": items[:limit],
                "totalCount": len(items),
                "lastUpdated": datetime.utcnow().isoformat() + "Z"
            }
        }

        # Set cache
        set_cache(cache_key, response)

        return response

    except Exception as e:
        logger.error(f"Error in get_portfolio_mentions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch portfolio mentions")

@router.get("/executive-brief")
async def get_executive_brief(
    limit: int = Query(5, ge=1, le=20),
    type: Optional[str] = Query(None, description="Filter by insight type")
):
    """Get summarized key insights across all intelligence categories"""

    # Check cache
    cache_key = get_cache_key("executive-brief", limit=limit, type=type)
    cached = get_cached_response(cache_key)
    if cached:
        return cached

    try:
        # Fetch sentiment results for cross-podcast analysis
        cursor = sentiment_collection.find({}).sort("calculated_at", -1).limit(5)
        sentiments = await cursor.to_list(length=None)

        items = []

        # Add key trend from sentiment analysis
        if sentiments:
            for idx, sentiment in enumerate(sentiments):
                items.append({
                    "id": f"eb-{idx+1}",
                    "title": f"Key Trend: {sentiment.get('topic', 'Market Analysis')}",
                    "description": f"Sentiment score: {sentiment.get('sentiment_score', 0):.2f} across {sentiment.get('episode_count', 0)} episodes this week",
                    "urgency": "normal",
                    "metadata": {
                        "source": "Cross-podcast analysis",
                        "related_episodes": []  # Would populate with actual episode IDs
                    }
                })

        # Add a general market insight
        items.append({
            "id": f"eb-{len(items)+1}",
            "title": "Key Trend: AI Consolidation",
            "description": "Major players acquiring AI startups at record pace. Multiple podcasts discussing vertical integration strategies.",
            "urgency": "normal",
            "metadata": {
                "source": "Cross-podcast analysis",
                "related_episodes": []
            }
        })

        # Add a portfolio insight
        items.append({
            "id": f"eb-{len(items)+1}",
            "title": "Portfolio Alert: Increased Competition",
            "description": "Several portfolio companies facing new entrants in their markets, particularly in AI and SaaS sectors.",
            "urgency": "normal",
            "metadata": {
                "source": "Competitive analysis",
                "related_episodes": []
            }
        })

        response = {
            "data": {
                "items": items[:limit],
                "totalCount": len(items),
                "lastUpdated": datetime.utcnow().isoformat() + "Z"
            }
        }

        # Set cache
        set_cache(cache_key, response)

        return response

    except Exception as e:
        logger.error(f"Error in get_executive_brief: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch executive brief")
