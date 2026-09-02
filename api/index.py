# This file is the entry point for Vercel
# It serves as the composition root, assembling all API features

import hashlib
import os

# Load .env at the composition root, explicitly.
#
# This used to happen as a side effect of importing search_lightweight_768d,
# which ran load_env_safely() at module scope. Phase 1 removed that import
# (search moved to the AWS stack), and MONGODB_URI silently stopped being set -
# which broke the audio clip router, since it still maps GUID to S3 path
# through MongoDB. Env loading is now a deliberate step, not a side effect of
# import order.
from lib.env_loader import load_env_safely
load_env_safely()

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from .topic_velocity import app as topic_velocity_app
from .routers.audio_clips import router as audio_clips_router
from .routers.transcripts import router as transcript_router
from .routers.episodes import router as episodes_router
from .routers.entities import router as entities_router
from .routers.topic_mentions import router as topic_mentions_router
from .routers.topic_correlations import router as topic_correlations_router
from .routers.topic_drilldown import router as topic_drilldown_router
from .routers.briefings import router as briefings_router
from .routers.feed import router as feed_router
from .routers.companies import router as companies_router
from .routers.intelligence_brief import router as intelligence_brief_router
from .routers.signals import router as signals_router
from .routers.narratives import router as narratives_router
from .routers.themes import router as themes_router

# Create the main app that will compose all features
app = FastAPI(
    title="PodInsightHQ API - Unified",
    description="Unified API for all PodInsight features",
    version="1.0.0"
)

# ---------------------------------------------------------------- conditional GETs
#
# Nothing this API returns carried a validator before 28 Aug 2026, so every
# visit re-downloaded all of it - measured at 17 requests and ~1.1 MB on a
# reload where none of the data had changed.
#
# The corpus only moves when a build runs, but "when did it last move" is not a
# question this process can answer cheaply, so the posture is deliberately the
# conservative one: the browser always asks, and an unchanged answer comes back
# as a 304 with no body. Never a stale read.
#
# Audio clips are exempt. Their bodies carry presigned URLs that expire, and a
# 304 would tell the browser to keep reusing one past its expiry.
ETAG_EXEMPT_PREFIXES = ("/api/v1/audio_clips",)


@app.middleware("http")
async def conditional_get(request, call_next):
    response = await call_next(request)

    if (request.method not in ("GET", "HEAD")
            or response.status_code != 200
            or request.url.path.startswith(ETAG_EXEMPT_PREFIXES)
            or "etag" in response.headers):
        return response

    body = b""
    async for chunk in response.body_iterator:
        body += chunk

    etag = '"' + hashlib.sha256(body).hexdigest()[:32] + '"'
    headers = dict(response.headers)
    headers["etag"] = etag
    headers["cache-control"] = "private, max-age=0, must-revalidate"

    if request.headers.get("if-none-match") == etag:
        # 304 carries no body, so these must go; the rest of the headers stay,
        # which is what lets the browser keep using what it already has.
        for h in ("content-length", "content-encoding"):
            headers.pop(h, None)
        return Response(status_code=304, headers=headers)

    headers["content-length"] = str(len(body))
    return Response(content=body, status_code=200, headers=headers,
                    media_type=response.media_type)


# Configure CORS for the main app
# Get CORS origins from environment variable
ALLOWED_ORIGINS = os.getenv(
    'CORS_ORIGINS',
    'http://localhost:3000,http://localhost:5173'  # Default for local dev
).split(',')

# Strip whitespace from each origin
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Explicit methods
    allow_headers=["*"],
    expose_headers=["Content-Length", "X-Request-ID"],
)

# Include the new audio clips router with its own prefix
# This keeps audio endpoints completely separate at /api/v1/audio_clips/*
app.include_router(audio_clips_router)

# The intelligence router was removed in phase 2, 2026-08-27. Its 18 routes were
# DEAD everywhere (SOURCE_OF_TRUTH 2.9) - they depend on collections that were
# never built - and it was the last live import of pymongo.

# Prewarm removed 2026-08-27: it existed only to mask the Modal cold start,
# and Modal is no longer on the request path.

# Include the transcript router for episode transcript retrieval
# This adds the /api/transcript/{episode_id} endpoint
app.include_router(transcript_router)

# Include the episodes router for the episode catalogue
# This adds the /api/episodes endpoint
app.include_router(episodes_router)

# Include the entities router for entity rankings
# This adds the /api/entities endpoint
app.include_router(entities_router)

# Include the topic mentions router for the tracked-topic series
# This adds the /api/topic-mentions endpoint
app.include_router(topic_mentions_router)

# Include the topic correlations router for pairwise co-occurrence
# This adds the /api/topic-correlations endpoint
app.include_router(topic_correlations_router)

# The episodes behind a topic-mentions number (phase D).
app.include_router(topic_drilldown_router)

# Pre-generated episode briefs (phase D).
app.include_router(briefings_router)

# The Narrative Feed: the same brief store in date order (phase D).
app.include_router(feed_router)

# Company Tracking: the watchlist over the curated entity index (phase E).
app.include_router(companies_router)

# The Intelligence Brief: one cached document for the period (phase E).
app.include_router(intelligence_brief_router)

# Notable Signals: the honest strip (phase E).
app.include_router(signals_router)

# Market Narratives, from the discovery engine (phase E part B).
app.include_router(narratives_router)

# Theme series for the Narrative Pulse (v2).
app.include_router(themes_router)

# Finding 5: the wake call the page fires on load, and the snapshot status the
# weekly self-check reads.
from api.routers.wake import router as wake_router      # noqa: E402
app.include_router(wake_router)


# Mount the existing topic_velocity app at the root
# This preserves ALL existing endpoints exactly as they are
# The topic_velocity.py file remains completely untouched
app.mount("/", topic_velocity_app)

# Note: The mount order matters - specific routes (audio_clips) before the catch-all mount
# This ensures audio routes are handled by the router, not the mounted app

# Vercel expects a variable named 'app'
# This exports our composed FastAPI app to Vercel
