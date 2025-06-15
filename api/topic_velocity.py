from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dateutil import parser
import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    try:
        # Initialize Supabase client
        supabase = get_supabase_client()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)
        
        logger.info(f"Fetching topic velocity for past {weeks} weeks")
        
        # Default topics if none specified (exactly 4 as per playbook)
        default_topics = [
            "AI Agents",
            "Capital Efficiency", 
            "DePIN",
            "B2B SaaS"
        ]
        
        # Parse topics parameter
        if topics:
            topic_list = [t.strip() for t in topics.split(",")]
        else:
            topic_list = default_topics
            
        # Query topic mentions from database
        # Join with episodes to get publication dates
        response = supabase.table("topic_mentions") \
            .select("*, episodes!inner(published_at)") \
            .gte("mention_date", start_date.date().isoformat()) \
            .lte("mention_date", end_date.date().isoformat()) \
            .in_("topic_name", topic_list) \
            .execute()
        
        # Process data to create Recharts-compatible format
        # Group mentions by week and count
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
        
        # Build the data structure for Recharts
        data_by_topic = {topic: [] for topic in topic_list}
        
        for week in sorted_weeks:
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
                mentions = weekly_data[week].get(topic, 0)
                data_by_topic[topic].append({
                    "week": week,
                    "mentions": mentions,
                    "date": date_range
                })
        
        # Get total episodes count
        total_episodes_response = supabase.table("episodes").select("id", count="exact").execute()
        total_episodes = total_episodes_response.count if hasattr(total_episodes_response, 'count') else 1171
        
        # Get date range from episodes
        date_range_response = supabase.table("episodes") \
            .select("published_at") \
            .order("published_at", desc=False) \
            .limit(1) \
            .execute()
        
        date_range_response_end = supabase.table("episodes") \
            .select("published_at") \
            .order("published_at", desc=True) \
            .limit(1) \
            .execute()
        
        start_date_str = date_range_response.data[0]["published_at"][:10] if date_range_response.data else "2025-01-01"
        end_date_str = date_range_response_end.data[0]["published_at"][:10] if date_range_response_end.data else "2025-06-14"
        
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

@app.get("/api/topics")
async def get_available_topics() -> Dict[str, List[str]]:
    """Get list of all available topics being tracked"""
    try:
        supabase = get_supabase_client()
        
        # Get unique topics from database
        response = supabase.table("topic_mentions") \
            .select("topic_name") \
            .execute()
        
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

# Handler for Vercel
handler = app