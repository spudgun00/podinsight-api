from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os
import logging
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PodInsightHQ API",
    description="Track emerging topics in startup and VC podcasts",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client
def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    
    if not url or not key:
        logger.error("Missing Supabase configuration")
        raise ValueError("Supabase configuration not found")
    
    return create_client(url, key)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "PodInsightHQ API",
        "version": "1.0.0"
    }

@app.get("/api/topic-velocity")
async def get_topic_velocity(
    days: Optional[int] = 30,
    topics: Optional[str] = None
) -> Dict[str, any]:
    """
    Get topic velocity data showing trending topics across podcasts.
    
    Parameters:
    - days: Number of days to look back (default: 30)
    - topics: Comma-separated list of specific topics to track (optional)
    
    Returns:
    - Topic velocity data with trends and mention counts
    """
    try:
        # Initialize Supabase client
        supabase = get_supabase_client()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Fetching topic velocity for past {days} days")
        
        # Default topics if none specified
        default_topics = [
            "AI Agents",
            "Capital Efficiency", 
            "DePIN",
            "B2B SaaS",
            "Crypto/Web3"
        ]
        
        # Parse topics parameter
        if topics:
            topic_list = [t.strip() for t in topics.split(",")]
        else:
            topic_list = default_topics
            
        # Query topic mentions from database
        # This assumes a table structure with topic_mentions
        response = supabase.table("topic_mentions") \
            .select("*") \
            .gte("published_date", start_date.isoformat()) \
            .lte("published_date", end_date.isoformat()) \
            .in_("topic", topic_list) \
            .execute()
        
        # Process data to calculate velocity
        topic_data = {}
        
        for topic in topic_list:
            topic_mentions = [r for r in response.data if r["topic"] == topic]
            
            # Calculate weekly buckets
            weekly_counts = {}
            for mention in topic_mentions:
                week_start = datetime.fromisoformat(mention["published_date"]) \
                    .replace(hour=0, minute=0, second=0, microsecond=0)
                week_start = week_start - timedelta(days=week_start.weekday())
                week_key = week_start.isoformat()
                
                if week_key not in weekly_counts:
                    weekly_counts[week_key] = 0
                weekly_counts[week_key] += mention.get("mention_count", 1)
            
            # Calculate velocity (week-over-week growth)
            sorted_weeks = sorted(weekly_counts.keys())
            velocity = 0
            if len(sorted_weeks) >= 2:
                last_week = weekly_counts.get(sorted_weeks[-1], 0)
                prev_week = weekly_counts.get(sorted_weeks[-2], 0)
                if prev_week > 0:
                    velocity = ((last_week - prev_week) / prev_week) * 100
            
            topic_data[topic] = {
                "total_mentions": sum(weekly_counts.values()),
                "weekly_counts": weekly_counts,
                "velocity": round(velocity, 2),
                "trending": velocity > 10,  # Consider >10% growth as trending
                "weeks_tracked": len(weekly_counts)
            }
        
        # Sort topics by velocity
        sorted_topics = sorted(
            topic_data.items(), 
            key=lambda x: x[1]["velocity"], 
            reverse=True
        )
        
        return {
            "success": True,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "topics": dict(sorted_topics),
            "top_trending": [
                {
                    "topic": topic,
                    "velocity": data["velocity"],
                    "total_mentions": data["total_mentions"]
                }
                for topic, data in sorted_topics[:5]
                if data["trending"]
            ]
        }
        
    except Exception as e:
        logger.error(f"Error fetching topic velocity: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch topic velocity data: {str(e)}"
        )

@app.get("/api/topics")
async def get_available_topics() -> Dict[str, List[str]]:
    """Get list of all available topics being tracked"""
    try:
        supabase = get_supabase_client()
        
        # Get unique topics from database
        response = supabase.table("topic_mentions") \
            .select("topic") \
            .execute()
        
        unique_topics = list(set([r["topic"] for r in response.data]))
        
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

# Handler for Vercel
handler = app