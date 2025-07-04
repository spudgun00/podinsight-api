"""
Episode Intelligence API Endpoints
Provides AI-generated briefs and insights from podcast episodes
"""
import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from bson import ObjectId

# Import authentication middleware
from .middleware.auth import require_auth, get_current_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])

# MongoDB connection
_mongodb_client = None
_db = None

async def get_mongodb():
    """Get MongoDB connection"""
    global _mongodb_client, _db
    
    if _mongodb_client is None:
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not configured")
        
        _mongodb_client = AsyncIOMotorClient(mongodb_uri)
        _db = _mongodb_client["podinsight"]
    
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
async def get_episode_signals(db, episode_id: str) -> List[Signal]:
    """Get signals for a specific episode from MongoDB"""
    try:
        # Check if we have a signals collection
        signals_collection = db.get_collection("episode_signals")
        
        # Query for signals by episode_id
        signals_cursor = signals_collection.find({"episode_id": episode_id})
        signals = []
        
        async for signal_doc in signals_cursor:
            signals.append(Signal(
                type=signal_doc.get("signal_type", "sound_bite"),
                content=signal_doc.get("content", ""),
                confidence=signal_doc.get("confidence", 0.8),
                timestamp=signal_doc.get("timestamp")
            ))
        
        # If no signals in dedicated collection, generate some mock signals
        if not signals:
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
                    type="sound_bite",
                    content="'The future of work is not remote, it's hybrid with AI augmentation'",
                    confidence=0.9
                )
            ]
        
        return signals
        
    except Exception as e:
        logger.error(f"Error fetching signals for episode {episode_id}: {str(e)}")
        return []

async def calculate_relevance_score(db, episode_id: str, user_preferences: Dict) -> float:
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
    limit: int = 8,
    user = Depends(require_auth)
) -> DashboardResponse:
    """
    Get top episodes by relevance score for the dashboard
    
    Returns the most relevant episodes based on:
    - User preferences (portfolio companies, interests)
    - Signal strength and quality
    - Recency
    """
    try:
        db = await get_mongodb()
        
        # Get user preferences
        user_id = user["user_id"]
        preferences_collection = db.get_collection("user_preferences")
        user_prefs = await preferences_collection.find_one({"user_id": user_id}) or {}
        
        # Get recent episodes with metadata
        episodes_collection = db.get_collection("episode_metadata")
        
        # Query for recent episodes (last 30 days)
        thirty_days_ago = datetime.utcnow().timestamp() - (30 * 24 * 60 * 60)
        
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": thirty_days_ago}
                }
            },
            {
                "$sort": {"created_at": -1}
            },
            {
                "$limit": limit * 3  # Get more to filter by relevance
            }
        ]
        
        cursor = episodes_collection.aggregate(pipeline)
        episodes = []
        
        async for episode_doc in cursor:
            # Calculate relevance score
            relevance_score = await calculate_relevance_score(db, str(episode_doc["_id"]), user_prefs)
            
            # Get signals for this episode
            signals = await get_episode_signals(db, str(episode_doc["_id"]))
            
            # Extract episode data
            raw_entry = episode_doc.get("raw_entry_original_feed", {})
            
            episode_brief = EpisodeBrief(
                episode_id=str(episode_doc["_id"]),
                title=raw_entry.get("episode_title", "Untitled Episode"),
                podcast_name=raw_entry.get("podcast_name", "Unknown Podcast"),
                published_at=datetime.fromtimestamp(
                    episode_doc.get("created_at", datetime.utcnow().timestamp())
                ).isoformat(),
                duration_seconds=episode_doc.get("duration_seconds", 0),
                relevance_score=relevance_score,
                signals=signals,
                summary=episode_doc.get("summary", "Episode summary not available"),
                key_insights=[
                    "AI agents are becoming more sophisticated",
                    "Enterprise adoption is accelerating",
                    "New funding models emerging"
                ],
                audio_url=episode_doc.get("audio_url")
            )
            
            episodes.append(episode_brief)
        
        # Sort by relevance score and take top N
        episodes.sort(key=lambda x: x.relevance_score, reverse=True)
        episodes = episodes[:limit]
        
        return DashboardResponse(
            episodes=episodes,
            total_episodes=len(episodes),
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate dashboard: {str(e)}"
        )

@router.get("/brief/{episode_id}", response_model=EpisodeBrief)
async def get_intelligence_brief(
    episode_id: str = Path(..., description="Episode ID (MongoDB ObjectId or GUID)"),
    user = Depends(require_auth)
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
        db = await get_mongodb()
        
        # Get episode metadata
        episodes_collection = db.get_collection("episode_metadata")
        
        # Try to find by ObjectId first, then by GUID
        episode_doc = None
        try:
            # Try as ObjectId
            episode_doc = await episodes_collection.find_one({"_id": ObjectId(episode_id)})
        except:
            # Try as GUID in episode_id field
            episode_doc = await episodes_collection.find_one({"episode_id": episode_id})
        
        if not episode_doc:
            raise HTTPException(
                status_code=404,
                detail=f"Episode {episode_id} not found"
            )
        
        # Get user preferences for relevance scoring
        user_id = user["user_id"]
        preferences_collection = db.get_collection("user_preferences")
        user_prefs = await preferences_collection.find_one({"user_id": user_id}) or {}
        
        # Calculate relevance score
        relevance_score = await calculate_relevance_score(db, str(episode_doc["_id"]), user_prefs)
        
        # Get signals
        signals = await get_episode_signals(db, str(episode_doc["_id"]))
        
        # Get transcript for summary if available
        transcripts_collection = db.get_collection("episode_transcripts")
        transcript_doc = await transcripts_collection.find_one({"episode_id": str(episode_doc["_id"])})
        
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
            podcast_name=raw_entry.get("podcast_name", "Unknown Podcast"),
            published_at=datetime.fromtimestamp(
                episode_doc.get("created_at", datetime.utcnow().timestamp())
            ).isoformat(),
            duration_seconds=episode_doc.get("duration_seconds", 0),
            relevance_score=relevance_score,
            signals=signals,
            summary=summary or "Episode summary not available",
            key_insights=[
                "Deep dive into market dynamics",
                "Founder perspectives on scaling",
                "Investment thesis validation"
            ],
            audio_url=episode_doc.get("audio_url")
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
    request: ShareRequest,
    user = Depends(require_auth)
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
        db = await get_mongodb()
        episodes_collection = db.get_collection("episode_metadata")
        
        # Find episode
        episode_doc = None
        try:
            episode_doc = await episodes_collection.find_one({"_id": ObjectId(request.episode_id)})
        except:
            episode_doc = await episodes_collection.find_one({"episode_id": request.episode_id})
        
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
        
        # Log share activity
        shares_collection = db.get_collection("share_history")
        await shares_collection.insert_one({
            "user_id": user["user_id"],
            "episode_id": request.episode_id,
            "method": request.method,
            "recipient": request.recipient,
            "include_summary": request.include_summary,
            "personal_note": request.personal_note,
            "shared_at": datetime.utcnow()
        })
        
        return ShareResponse(
            success=True,
            message=message,
            shared_at=datetime.utcnow().isoformat()
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
    preferences: UserPreferences,
    user = Depends(require_auth)
) -> PreferencesResponse:
    """
    Update user preferences for personalized intelligence
    
    Configures:
    - Portfolio company tracking
    - Interest topics
    - Notification settings
    """
    try:
        db = await get_mongodb()
        preferences_collection = db.get_collection("user_preferences")
        
        user_id = user["user_id"]
        
        # Update preferences
        update_doc = {
            "user_id": user_id,
            "portfolio_companies": preferences.portfolio_companies,
            "interest_topics": preferences.interest_topics,
            "notification_frequency": preferences.notification_frequency,
            "email_notifications": preferences.email_notifications,
            "slack_notifications": preferences.slack_notifications,
            "updated_at": datetime.utcnow()
        }
        
        # Upsert preferences
        await preferences_collection.replace_one(
            {"user_id": user_id},
            update_doc,
            upsert=True
        )
        
        return PreferencesResponse(
            success=True,
            preferences=preferences,
            updated_at=datetime.utcnow().isoformat()
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
        db = await get_mongodb()
        
        # Check MongoDB connection
        await db.command("ping")
        
        return {
            "status": "healthy",
            "service": "intelligence-api",
            "timestamp": datetime.utcnow().isoformat(),
            "mongodb": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "intelligence-api",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

# Export router for inclusion in main app