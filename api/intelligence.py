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
def extract_key_insights(signals: List[Signal]) -> List[str]:
    """Extract key insights from signals"""
    insights = []

    # Group signals by type
    signal_groups = {}
    for signal in signals:
        signal_type = signal.type
        if signal_type not in signal_groups:
            signal_groups[signal_type] = []
        signal_groups[signal_type].append(signal)

    # Extract top insights based on signal types
    if "investable" in signal_groups and signal_groups["investable"]:
        insights.append(f"Investment opportunity: {signal_groups['investable'][0].content[:100]}")

    if "competitive" in signal_groups and signal_groups["competitive"]:
        insights.append(f"Market intelligence: {signal_groups['competitive'][0].content[:100]}")

    if "portfolio" in signal_groups and signal_groups["portfolio"]:
        insights.append(f"Portfolio update: {signal_groups['portfolio'][0].content[:100]}")

    # If we have fewer than 3 insights, add some from sound bites
    if len(insights) < 3 and "sound_bite" in signal_groups:
        for signal in signal_groups["sound_bite"][:3-len(insights)]:
            insights.append(signal.content[:100])

    # If still no insights, return generic ones
    if not insights:
        insights = [
            "Episode contains valuable industry insights",
            "Strategic discussions on market trends",
            "Key perspectives from industry leaders"
        ]

    return insights[:3]  # Return top 3

def get_episode_signals(db, episode_id: str) -> List[Signal]:
    """Get signals for a specific episode from MongoDB"""
    try:
        # Query the episode_intelligence collection for real signals
        intelligence_collection = db.get_collection("episode_intelligence")

        # Find the intelligence data for this episode
        intelligence_doc = intelligence_collection.find_one({"episode_id": episode_id})

        if not intelligence_doc:
            logger.info(f"No intelligence data found for episode {episode_id}")
            return []

        # Extract signals from the document
        signals = []
        signal_data = intelligence_doc.get("signals", {})

        # Process each signal type
        for signal_type in ["investable", "competitive", "portfolio", "soundbites"]:
            if signal_type in signal_data:
                for signal_item in signal_data[signal_type]:
                    # Map soundbites to sound_bite for consistency
                    display_type = "sound_bite" if signal_type == "soundbites" else signal_type

                    signal = Signal(
                        type=display_type,
                        content=signal_item.get("signal_text", ""),
                        confidence=signal_item.get("confidence", 0.8),
                        timestamp=signal_item.get("timestamp")  # Optional timestamp
                    )
                    signals.append(signal)

        logger.info(f"Found {len(signals)} signals for episode {episode_id}")
        return signals

    except Exception as e:
        logger.error(f"Error fetching signals for episode {episode_id}: {str(e)}")
        return []

def calculate_relevance_score(db, episode_id: str, user_preferences: Dict) -> float:
    """Calculate relevance score based on user preferences and episode content"""
    try:
        # First check if episode_intelligence collection has a relevance score
        intelligence_collection = db.get_collection("episode_intelligence")
        intelligence_doc = intelligence_collection.find_one({"episode_id": episode_id})

        if intelligence_doc and "relevance_score" in intelligence_doc:
            # Use the pre-calculated relevance score from Story 2
            base_score = intelligence_doc["relevance_score"] / 100.0  # Convert to 0-1 range
        else:
            # Fallback to calculating based on signals and authority
            base_score = 0.5

            # Get podcast authority score (try episode_id first, then guid)
            episode_metadata = db.get_collection("episode_metadata").find_one({"episode_id": episode_id})
            if not episode_metadata:
                # Fallback to guid field
                episode_metadata = db.get_collection("episode_metadata").find_one({"guid": episode_id})
            if episode_metadata:
                raw_entry = episode_metadata.get("raw_entry_original_feed", {})
                podcast_name = raw_entry.get("podcast_title", "")

                # Look up podcast authority
                authority_collection = db.get_collection("podcast_authority")
                authority_doc = authority_collection.find_one({"podcast_name": podcast_name})

                if authority_doc:
                    # Higher tier = lower number (tier 1 is best)
                    tier = authority_doc.get("tier", 5)
                    authority_score = authority_doc.get("authority_score", 50)

                    # Boost score based on tier and authority
                    tier_boost = (6 - tier) * 0.05  # 0.25 for tier 1, down to 0.05 for tier 5
                    authority_boost = (authority_score / 100.0) * 0.1

                    base_score += tier_boost + authority_boost

        # Apply user preference boosts
        user_prefs_collection = db.get_collection("user_intelligence_prefs")
        user_prefs_doc = user_prefs_collection.find_one({"user_id": user_preferences.get("user_id", "demo-user")})

        if user_prefs_doc and intelligence_doc:
            prefs = user_prefs_doc.get("preferences", {})

            # Check if episode signals match user's interests
            portfolio_companies = prefs.get("portfolio_companies", [])
            interest_topics = prefs.get("topics", [])
            keywords = prefs.get("keywords", [])

            # Check signals for matches
            signals = intelligence_doc.get("signals", {})
            all_signal_text = []

            for signal_type in signals.values():
                for signal in signal_type:
                    all_signal_text.append(signal.get("signal_text", "").lower())

            combined_text = " ".join(all_signal_text)

            # Boost for portfolio company mentions
            for company in portfolio_companies:
                if company.lower() in combined_text:
                    base_score += 0.15
                    break

            # Boost for topic/keyword matches
            for topic in interest_topics + keywords:
                if topic.lower() in combined_text:
                    base_score += 0.05

        return min(base_score, 1.0)

    except Exception as e:
        logger.error(f"Error calculating relevance score for episode {episode_id}: {str(e)}")
        # Return a default score on error
        return 0.7

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

        episodes = []

        try:
            # Get ALL episodes and filter for those with intelligence data
            logger.info(f"Searching all episodes for those with intelligence data")
            cursor = episodes_collection.find()  # No limit - check all episodes

            episode_count = 0
            episodes_with_signals = 0
            for episode_doc in cursor:
                episode_count += 1
                if episode_count % 100 == 0:
                    logger.info(f"Processed {episode_count} episodes, found {episodes_with_signals} with signals")

                # Try multiple ID fields for episode_intelligence lookups
                episode_guid = episode_doc.get("episode_id")
                if not episode_guid:
                    # Fallback to guid field if episode_id not present
                    episode_guid = episode_doc.get("guid")

                # Also get the ObjectId as string
                object_id_str = str(episode_doc.get("_id"))

                # Try to find signals using different ID formats
                signals = get_episode_signals(db, episode_guid)

                # If no signals found with GUID, try ObjectId
                if not signals:
                    logger.info(f"No signals found with GUID {episode_guid}, trying ObjectId {object_id_str}")
                    signals = get_episode_signals(db, object_id_str)

                # Skip episodes without signals
                if not signals:
                    continue  # Just skip, don't log warnings for each one

                episodes_with_signals += 1

                # Calculate relevance score using the ID that worked
                relevance_score = calculate_relevance_score(db, episode_guid, user_prefs)

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
                    key_insights=extract_key_insights(signals),
                    audio_url=episode_doc.get("s3_audio_path")
                )

                episodes.append(episode_brief)

            logger.info(f"Processed {episode_count} total episodes, found {episodes_with_signals} with intelligence data")

        except Exception as e:
            logger.error(f"Error fetching episodes from MongoDB: {str(e)}", exc_info=True)
            # Return mock data if MongoDB fails
            episodes = []

        # Log results
        if not episodes:
            logger.warning(f"No episodes found with intelligence data after checking {episode_count} episodes")
            # Check collection counts for debugging
            intelligence_count = db.get_collection("episode_intelligence").count_documents({})
            logger.info(f"Total episode_intelligence documents: {intelligence_count}")

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

        # Get the episode_id for intelligence lookups (now contains GUID value)
        episode_guid = episode_doc.get("episode_id")
        if not episode_guid:
            # Fallback to guid field if episode_id not present
            episode_guid = episode_doc.get("guid")
            if not episode_guid:
                # If neither field exists, try to use the episode_id parameter as guid
                episode_guid = episode_id
                logger.warning(f"Episode {episode_doc.get('_id')} has no episode_id or guid field, using {episode_id}")

        # Calculate relevance score using guid
        relevance_score = calculate_relevance_score(db, episode_guid, user_prefs)

        # Get signals using guid
        signals = get_episode_signals(db, episode_guid)

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
            key_insights=extract_key_insights(signals),
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

        # Get collection names for debugging
        collections = db.list_collection_names()

        # Count documents in episode_metadata if it exists
        episode_count = 0
        if "episode_metadata" in collections:
            episode_count = db.get_collection("episode_metadata").count_documents({})

        return {
            "status": "healthy",
            "service": "intelligence-api",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mongodb": "connected",
            "database_name": db.name,
            "collections": collections[:10],  # First 10 collections
            "episode_metadata_count": episode_count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "intelligence-api",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }

# Debug endpoint (temporary)
@router.get("/debug")
async def debug_mongodb():
    """Debug MongoDB connection and collections"""
    try:
        db = get_mongodb()

        # Get basic info
        info = {
            "database_name": db.name,
            "collections": db.list_collection_names(),
        }

        # Check episode_metadata
        if "episode_metadata" in info["collections"]:
            collection = db.get_collection("episode_metadata")
            info["episode_metadata"] = {
                "count": collection.count_documents({}),
                "sample": None
            }
            # Get one sample document
            sample = collection.find_one()
            if sample:
                info["episode_metadata"]["sample"] = {
                    "id": str(sample.get("_id")),
                    "guid": sample.get("guid"),
                    "episode_id": sample.get("episode_id"),
                    "has_raw_entry": "raw_entry_original_feed" in sample,
                    "guid_equals_episode_id": sample.get("guid") == sample.get("episode_id")
                }

        # Check episode_intelligence
        if "episode_intelligence" in info["collections"]:
            collection = db.get_collection("episode_intelligence")
            info["episode_intelligence"] = {
                "count": collection.count_documents({}),
                "sample": None
            }
            sample = collection.find_one()
            if sample:
                info["episode_intelligence"]["sample"] = {
                    "id": str(sample.get("_id")),
                    "episode_id": sample.get("episode_id"),
                    "has_signals": "signals" in sample,
                    "signal_types": list(sample.get("signals", {}).keys()) if "signals" in sample else []
                }

        # Check podcast_authority
        if "podcast_authority" in info["collections"]:
            collection = db.get_collection("podcast_authority")
            info["podcast_authority"] = {
                "count": collection.count_documents({}),
                "sample": None
            }
            sample = collection.find_one()
            if sample:
                info["podcast_authority"]["sample"] = {
                    "feed_slug": sample.get("feed_slug"),
                    "podcast_name": sample.get("podcast_name"),
                    "tier": sample.get("tier")
                }

        # Check user_intelligence_prefs
        if "user_intelligence_prefs" in info["collections"]:
            collection = db.get_collection("user_intelligence_prefs")
            info["user_intelligence_prefs"] = {
                "count": collection.count_documents({}),
                "demo_user_exists": collection.count_documents({"user_id": "demo-user"})
            }

        return info

    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__
        }

# Test endpoint to check data matching
@router.get("/test-match")
async def test_data_matching():
    """Test if episode IDs match between collections"""
    try:
        db = get_mongodb()

        # Get first episode from metadata
        episode_meta = db.get_collection("episode_metadata").find_one()
        if not episode_meta:
            return {"error": "No episodes in episode_metadata"}

        episode_guid = episode_meta.get("guid")
        episode_id = episode_meta.get("episode_id")

        # Try to find matching intelligence using episode_id first, then guid, then ObjectId
        intelligence = None
        if episode_id:
            intelligence = db.get_collection("episode_intelligence").find_one({"episode_id": episode_id})
        if not intelligence and episode_guid:
            intelligence = db.get_collection("episode_intelligence").find_one({"episode_id": episode_guid})
        if not intelligence:
            # Try using the ObjectId as string
            object_id_str = str(episode_meta.get("_id"))
            intelligence = db.get_collection("episode_intelligence").find_one({"episode_id": object_id_str})

        # Also check first intelligence record
        first_intelligence = db.get_collection("episode_intelligence").find_one()

        return {
            "episode_metadata_sample": {
                "id": str(episode_meta.get("_id")),
                "guid": episode_guid,
                "episode_id": episode_id,
                "has_episode_id_field": episode_id is not None
            },
            "intelligence_match_found": intelligence is not None,
            "intelligence_match_method": "episode_id" if episode_id and intelligence else ("guid" if episode_guid and intelligence else ("objectid" if intelligence else "none")),
            "first_intelligence_episode_id": first_intelligence.get("episode_id") if first_intelligence else None,
            "objectid_matches_intelligence": object_id_str == first_intelligence.get("episode_id") if first_intelligence else False,
            "episode_id_matches_intelligence": episode_id == first_intelligence.get("episode_id") if (episode_id and first_intelligence) else False,
            "guid_matches_intelligence": episode_guid == first_intelligence.get("episode_id") if (episode_guid and first_intelligence) else False
        }

    except Exception as e:
        return {"error": str(e)}

# Test endpoint to check specific GUID
@router.get("/check-guid/{guid}")
async def check_guid_in_collections(guid: str):
    """Check if a specific GUID exists in various collections"""
    try:
        db = get_mongodb()

        results = {
            "searched_guid": guid,
            "found_in": []
        }

        # Check episode_metadata by guid field
        metadata_by_guid = db.get_collection("episode_metadata").find_one({"guid": guid})
        if metadata_by_guid:
            results["found_in"].append("episode_metadata.guid")
            results["episode_metadata_by_guid"] = {
                "id": str(metadata_by_guid.get("_id")),
                "title": metadata_by_guid.get("raw_entry_original_feed", {}).get("episode_title", "Unknown"),
                "guid": metadata_by_guid.get("guid"),
                "episode_id": metadata_by_guid.get("episode_id")
            }

        # Check episode_metadata by episode_id field
        metadata_by_episode_id = db.get_collection("episode_metadata").find_one({"episode_id": guid})
        if metadata_by_episode_id and metadata_by_episode_id != metadata_by_guid:
            results["found_in"].append("episode_metadata.episode_id")
            results["episode_metadata_by_episode_id"] = {
                "id": str(metadata_by_episode_id.get("_id")),
                "title": metadata_by_episode_id.get("raw_entry_original_feed", {}).get("episode_title", "Unknown"),
                "guid": metadata_by_episode_id.get("guid"),
                "episode_id": metadata_by_episode_id.get("episode_id")
            }

        # Check episode_intelligence
        intelligence = db.get_collection("episode_intelligence").find_one({"episode_id": guid})
        if intelligence:
            results["found_in"].append("episode_intelligence.episode_id")
            results["episode_intelligence"] = {
                "id": str(intelligence.get("_id")),
                "episode_id": intelligence.get("episode_id"),
                "has_signals": bool(intelligence.get("signals"))
            }

        # Check episode_transcripts
        transcript = db.get_collection("episode_transcripts").find_one({"episode_id": guid})
        if transcript:
            results["found_in"].append("episode_transcripts.episode_id")
            results["episode_transcripts"] = {
                "id": str(transcript.get("_id")),
                "episode_id": transcript.get("episode_id"),
                "word_count": transcript.get("word_count")
            }

        return results

    except Exception as e:
        return {"error": str(e)}

# Test endpoint to find episodes with intelligence
@router.get("/find-episodes-with-intelligence")
async def find_episodes_with_intelligence():
    """Find episodes that have matching intelligence data"""
    try:
        db = get_mongodb()

        # Get all episode_intelligence documents
        intelligence_collection = db.get_collection("episode_intelligence")
        intelligence_docs = list(intelligence_collection.find().limit(10))

        matches = []
        for intel in intelligence_docs:
            episode_id = intel.get("episode_id")

            # Try to find this episode in metadata
            metadata = db.get_collection("episode_metadata").find_one({
                "$or": [
                    {"guid": episode_id},
                    {"episode_id": episode_id},
                    {"_id": ObjectId(episode_id) if ObjectId.is_valid(episode_id) else None}
                ]
            })

            if metadata:
                matches.append({
                    "intelligence_id": str(intel.get("_id")),
                    "episode_id_in_intelligence": episode_id,
                    "metadata_id": str(metadata.get("_id")),
                    "metadata_guid": metadata.get("guid"),
                    "metadata_episode_id": metadata.get("episode_id"),
                    "title": metadata.get("raw_entry_original_feed", {}).get("episode_title", "Unknown"),
                    "has_signals": bool(intel.get("signals", {}))
                })

        return {
            "total_intelligence_docs": len(intelligence_docs),
            "matches_found": len(matches),
            "matches": matches
        }

    except Exception as e:
        return {"error": str(e)}

# Debug endpoint to test get_episode_signals
@router.get("/test-signals/{episode_id}")
async def test_get_signals(episode_id: str):
    """Test getting signals for a specific episode ID"""
    try:
        db = get_mongodb()

        # Direct query to episode_intelligence
        intelligence_collection = db.get_collection("episode_intelligence")
        intelligence_doc = intelligence_collection.find_one({"episode_id": episode_id})

        # Also try using get_episode_signals function
        signals = get_episode_signals(db, episode_id)

        return {
            "searched_episode_id": episode_id,
            "direct_query_found": intelligence_doc is not None,
            "direct_query_has_signals": bool(intelligence_doc.get("signals", {})) if intelligence_doc else False,
            "get_episode_signals_count": len(signals),
            "signals_from_function": [{"type": s.type, "content": s.content[:50] + "..."} for s in signals[:3]]
        }

    except Exception as e:
        return {"error": str(e)}

# Export router for inclusion in main app
