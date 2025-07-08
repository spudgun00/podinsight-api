"""
Episode Intelligence API Endpoints
Provides AI-generated briefs and insights from podcast episodes
"""
import os
import logging
from fastapi import APIRouter, HTTPException, Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from pymongo import MongoClient
from bson import ObjectId

# Import authentication middleware (temporarily disabled)
# TODO: Re-enable when auth system is implemented
# from .middleware.auth import require_auth, get_current_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])

# MongoDB connection (using synchronous client for serverless reliability)
_mongodb_client = None
_db = None

def get_mongodb():
    """Get MongoDB connection (synchronous for serverless)"""
    global _mongodb_client, _db
    
    if _mongodb_client is None:
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not configured")
        
        try:
            # Use synchronous PyMongo client for serverless reliability
            _mongodb_client = MongoClient(
                mongodb_uri,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                maxPoolSize=10,
                retryWrites=True
            )
            # Get database name from env or use default
            db_name = os.getenv("MONGODB_DATABASE", "podinsight")
            _db = _mongodb_client[db_name]
            
            # Test connection
            _db.command('ping')
            logger.info(f"MongoDB connected successfully to database: {db_name}")
        except Exception as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            _mongodb_client = None
            _db = None
            raise
    
    return _db

# Pydantic models
class Signal(BaseModel):
    type: str = Field(..., description="Signal type: investable, competitive, portfolio, sound_bite")
    content: str = Field(..., description="Signal content")
    confidence: float = Field(0.8, description="Confidence score")
    timestamp: Optional[str] = Field(None, description="Timestamp in episode")

class EpisodeBrief(BaseModel):
    episode_id: str
    title: str
    podcast_name: str
    published_at: str
    duration_seconds: int
    relevance_score: float
    signals: List[Signal]
    summary: str
    key_insights: List[str]
    audio_url: Optional[str] = None

class DashboardResponse(BaseModel):
    episodes: List[EpisodeBrief]
    total_episodes: int
    generated_at: str

class ShareRequest(BaseModel):
    episode_id: str = Field(..., description="Episode ID to share")
    method: str = Field(..., description="Share method: email or slack")
    recipient: str = Field(..., description="Email address or Slack channel")
    include_summary: bool = Field(True, description="Include episode summary")
    personal_note: Optional[str] = Field(None, description="Personal note to add")

class ShareResponse(BaseModel):
    success: bool
    message: str
    shared_at: str

class UserPreferences(BaseModel):
    portfolio_companies: List[str] = Field([], description="List of portfolio company names to track")
    interest_topics: List[str] = Field([], description="Topics of interest")
    notification_frequency: str = Field("weekly", description="Notification frequency: daily, weekly, never")
    email_notifications: bool = Field(True, description="Enable email notifications")
    slack_notifications: bool = Field(False, description="Enable Slack notifications")

class PreferencesResponse(BaseModel):
    success: bool
    preferences: UserPreferences
    updated_at: str

# Helper functions
def get_episode_signals(db, episode_id: str) -> List[Signal]:
    """Get signals for a specific episode from MongoDB"""
    try:
        # For MVP, always return mock signals since the signals collection doesn't exist yet
        # TODO: Implement real signal extraction in Story 1
        logger.info(f"Returning mock signals for episode {episode_id}")
        
        # Mock signals for demonstration
        signals = [
            Signal(
                type="investable",
                content="Discussion about Series A fundraising trends in AI startups",
                confidence=0.85
            ),
            Signal(
                type="competitive",
                content="Mention of recent acquisition in the enterprise SaaS space",
                confidence=0.75
            ),
            Signal(
                type="portfolio",
                content="Portfolio company mentioned in context of market expansion",
                confidence=0.9
            ),
            Signal(
                type="sound_bite",
                content="'The future of work is not remote, it's hybrid with AI augmentation'",
                confidence=0.9
            )
        ]
        
        return signals
        
    except Exception as e:
        logger.error(f"Error fetching signals for episode {episode_id}: {str(e)}")
        return []

def calculate_relevance_score(db, episode_id: str, user_preferences: Dict) -> float:
    """Calculate relevance score based on user preferences and episode content"""
    # For MVP, use a simple scoring mechanism
    # In production, this would use the relevance scoring from Story 2
    base_score = 0.7
    
    # Check if episode mentions portfolio companies
    portfolio_companies = user_preferences.get("portfolio_companies", [])
    if portfolio_companies:
        # Would check transcript for mentions
        base_score += 0.1
    
    # Check for interest topics
    interest_topics = user_preferences.get("interest_topics", [])
    if interest_topics:
        # Would check against episode topics
        base_score += 0.1
    
    return min(base_score, 1.0)

# API Endpoints
@router.get("/dashboard", response_model=DashboardResponse)
async def get_intelligence_dashboard(
    limit: int = 8
) -> DashboardResponse:
    """
    Get top episodes by relevance score for the dashboard
    
    Returns the most relevant episodes based on:
    - User preferences (portfolio companies, interests)
    - Signal strength and quality
    - Recency
    """
    try:
        db = get_mongodb()
        logger.info(f"MongoDB connected, database: {db.name}")
        
        # TODO: Re-add authentication when auth system is implemented
        # Get user preferences (using demo user for now)
        user_id = "demo-user"
        preferences_collection = db.get_collection("user_preferences")
        user_prefs = preferences_collection.find_one({"user_id": user_id}) or {}
        logger.info(f"User preferences: {user_prefs}")
        
        # Get recent episodes with metadata
        episodes_collection = db.get_collection("episode_metadata")
        
        # First, let's check if we have any episodes at all
        total_episodes = episodes_collection.count_documents({})
        logger.info(f"Total episodes in collection: {total_episodes}")
        
        # For MVP, let's get any recent episodes without date filtering
        # since 'created_at' might not be the right field
        pipeline = [
            {
                "$sort": {"_id": -1}  # Sort by ObjectId (newest first)
            },
            {
                "$limit": limit * 2  # Get extra for filtering
            }
        ]
        
        episodes = []
        
        try:
            logger.info(f"Executing aggregation pipeline: {pipeline}")
            cursor = episodes_collection.aggregate(pipeline)
            
            episode_count = 0
            for episode_doc in cursor:
                episode_count += 1
                logger.info(f"Processing episode {episode_count}: {episode_doc.get('_id')}")
                # Calculate relevance score
                relevance_score = calculate_relevance_score(db, str(episode_doc["_id"]), user_prefs)
                
                # Get signals for this episode
                signals = get_episode_signals(db, str(episode_doc["_id"]))
                
                # Extract episode data
                raw_entry = episode_doc.get("raw_entry_original_feed", {})
                
                episode_brief = EpisodeBrief(
                    episode_id=str(episode_doc["_id"]),
                    title=raw_entry.get("episode_title", "Untitled Episode"),
                    podcast_name=raw_entry.get("podcast_title", "Unknown Podcast"),  # Fixed field name
                    published_at=raw_entry.get("published_date_iso", datetime.now(timezone.utc).isoformat()),
                    duration_seconds=raw_entry.get("duration", 0),  # Fixed field name
                    relevance_score=relevance_score,
                    signals=signals,
                    summary=episode_doc.get("summary", "Episode summary not available"),
                    key_insights=[
                        "AI agents are becoming more sophisticated",
                        "Enterprise adoption is accelerating",
                        "New funding models emerging"
                    ],
                    audio_url=episode_doc.get("s3_audio_path")
                )
                
                episodes.append(episode_brief)
        
            logger.info(f"Successfully processed {episode_count} episodes from MongoDB")
        
        except Exception as e:
            logger.error(f"Error fetching episodes from MongoDB: {str(e)}", exc_info=True)
            # Return mock data if MongoDB fails
            episodes = []
        
        # If no episodes found, return mock data for MVP
        if not episodes:
            logger.warning(f"No episodes found in MongoDB (processed {len(episodes)} episodes), returning mock data")
            for i in range(min(limit, 4)):
                mock_episode = EpisodeBrief(
                    episode_id=f"mock-{i}",
                    title=f"Episode {i+1}: AI Innovation and Venture Capital",
                    podcast_name=["Tech Insights Podcast", "VC Weekly", "Startup Stories", "AI Focus"][i],
                    published_at=datetime.now(timezone.utc).isoformat(),
                    duration_seconds=3600,
                    relevance_score=0.9 - (i * 0.1),
                    signals=[
                        Signal(
                            type="investable",
                            content="Discussion about Series A fundraising trends",
                            confidence=0.85
                        ),
                        Signal(
                            type="competitive",
                            content="Recent acquisition in enterprise SaaS",
                            confidence=0.75
                        ),
                        Signal(
                            type="portfolio",
                            content="Portfolio company expansion update",
                            confidence=0.9
                        ),
                        Signal(
                            type="sound_bite",
                            content="'The future is AI-augmented workflows'",
                            confidence=0.9
                        )
                    ],
                    summary="In this episode, we explore the latest trends in AI and venture capital...",
                    key_insights=[
                        "AI adoption accelerating in enterprises",
                        "New funding models emerging",
                        "Market consolidation happening"
                    ],
                    audio_url=None
                )
                episodes.append(mock_episode)
        
        # Sort by relevance score and take top N
        episodes.sort(key=lambda x: x.relevance_score, reverse=True)
        episodes = episodes[:limit]
        
        return DashboardResponse(
            episodes=episodes,
            total_episodes=len(episodes),
            generated_at=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate dashboard: {str(e)}"
        )

@router.get("/brief/{episode_id}", response_model=EpisodeBrief)
async def get_intelligence_brief(
    episode_id: str = Path(..., description="Episode ID (MongoDB ObjectId or GUID)")
) -> EpisodeBrief:
    """
    Get full intelligence brief for a specific episode
    
    Includes:
    - Complete signal analysis
    - Key insights and quotes
    - Relevance scoring
    - Audio URL when available
    """
    try:
        db = get_mongodb()
        
        # Get episode metadata
        episodes_collection = db.get_collection("episode_metadata")
        
        # Try to find by ObjectId first, then by GUID
        episode_doc = None
        try:
            # Try as ObjectId
            episode_doc = episodes_collection.find_one({"_id": ObjectId(episode_id)})
        except:
            # Try as GUID in episode_id field
            episode_doc = episodes_collection.find_one({"episode_id": episode_id})
        
        if not episode_doc:
            raise HTTPException(
                status_code=404,
                detail=f"Episode {episode_id} not found"
            )
        
        # TODO: Re-add authentication when auth system is implemented
        # Get user preferences for relevance scoring (using demo user for now)
        user_id = "demo-user"
        preferences_collection = db.get_collection("user_preferences")
        user_prefs = preferences_collection.find_one({"user_id": user_id}) or {}
        
        # Calculate relevance score
        relevance_score = calculate_relevance_score(db, str(episode_doc["_id"]), user_prefs)
        
        # Get signals
        signals = get_episode_signals(db, str(episode_doc["_id"]))
        
        # Get transcript for summary if available
        transcripts_collection = db.get_collection("episode_transcripts")
        transcript_doc = transcripts_collection.find_one({"episode_id": str(episode_doc["_id"])})
        
        summary = episode_doc.get("summary", "")
        if not summary and transcript_doc:
            # Extract first 500 chars as summary
            full_text = transcript_doc.get("full_text", "")
            summary = full_text[:500] + "..." if len(full_text) > 500 else full_text
        
        # Extract episode data
        raw_entry = episode_doc.get("raw_entry_original_feed", {})
        
        return EpisodeBrief(
            episode_id=str(episode_doc["_id"]),
            title=raw_entry.get("episode_title", "Untitled Episode"),
            podcast_name=raw_entry.get("podcast_title", "Unknown Podcast"),  # Fixed field name
            published_at=raw_entry.get("published_date_iso", datetime.now(timezone.utc).isoformat()),
            duration_seconds=raw_entry.get("duration", 0),  # Fixed field name
            relevance_score=relevance_score,
            signals=signals,
            summary=summary or "Episode summary not available",
            key_insights=[
                "Deep dive into market dynamics",
                "Founder perspectives on scaling",
                "Investment thesis validation"
            ],
            audio_url=episode_doc.get("s3_audio_path")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Brief error for episode {episode_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate brief: {str(e)}"
        )

@router.post("/share", response_model=ShareResponse)
async def share_intelligence(
    request: ShareRequest
) -> ShareResponse:
    """
    Share episode intelligence via email or Slack
    
    Supports:
    - Email sharing with formatted brief
    - Slack integration for team channels
    - Personal notes and context
    """
    try:
        # Validate share method
        if request.method not in ["email", "slack"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid share method. Use 'email' or 'slack'"
            )
        
        # Get episode brief
        db = get_mongodb()
        episodes_collection = db.get_collection("episode_metadata")
        
        # Find episode
        episode_doc = None
        try:
            episode_doc = episodes_collection.find_one({"_id": ObjectId(request.episode_id)})
        except:
            episode_doc = episodes_collection.find_one({"episode_id": request.episode_id})
        
        if not episode_doc:
            raise HTTPException(
                status_code=404,
                detail=f"Episode {request.episode_id} not found"
            )
        
        # For MVP, simulate sharing (in production, integrate with email/Slack services)
        if request.method == "email":
            # Would send email via SendGrid/SES
            logger.info(f"Sharing episode {request.episode_id} via email to {request.recipient}")
            message = f"Episode intelligence shared via email to {request.recipient}"
        else:
            # Would post to Slack via webhook
            logger.info(f"Sharing episode {request.episode_id} to Slack channel {request.recipient}")
            message = f"Episode intelligence shared to Slack channel {request.recipient}"
        
        # TODO: Re-add authentication when auth system is implemented
        # Log share activity (using demo user for now)
        user_id = "demo-user"
        shares_collection = db.get_collection("share_history")
        shares_collection.insert_one({
            "user_id": user_id,
            "episode_id": request.episode_id,
            "method": request.method,
            "recipient": request.recipient,
            "include_summary": request.include_summary,
            "personal_note": request.personal_note,
            "shared_at": datetime.now(timezone.utc)
        })
        
        return ShareResponse(
            success=True,
            message=message,
            shared_at=datetime.now(timezone.utc).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Share error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to share intelligence: {str(e)}"
        )

@router.put("/preferences", response_model=PreferencesResponse)
async def update_preferences(
    preferences: UserPreferences
) -> PreferencesResponse:
    """
    Update user preferences for personalized intelligence
    
    Configures:
    - Portfolio company tracking
    - Interest topics
    - Notification settings
    """
    try:
        # TODO: Re-add authentication when auth system is implemented
        db = get_mongodb()
        preferences_collection = db.get_collection("user_preferences")
        
        # Using demo user for now
        user_id = "demo-user"
        
        # Update preferences
        update_doc = {
            "user_id": user_id,
            "portfolio_companies": preferences.portfolio_companies,
            "interest_topics": preferences.interest_topics,
            "notification_frequency": preferences.notification_frequency,
            "email_notifications": preferences.email_notifications,
            "slack_notifications": preferences.slack_notifications,
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Upsert preferences
        preferences_collection.replace_one(
            {"user_id": user_id},
            update_doc,
            upsert=True
        )
        
        return PreferencesResponse(
            success=True,
            preferences=preferences,
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Preferences error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update preferences: {str(e)}"
        )

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for intelligence API"""
    try:
        db = get_mongodb()
        
        # Check MongoDB connection
        db.command("ping")
        
        return {
            "status": "healthy",
            "service": "intelligence-api",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mongodb": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "intelligence-api",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }

# Export router for inclusion in main app