# This file is the entry point for Vercel
# It serves as the composition root, assembling all API features

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .topic_velocity import app as topic_velocity_app
from .routers.audio_clips import router as audio_clips_router
from .routers.intelligence import router as intelligence_router
from .routers.prewarm import router as prewarm_router
from .routers.transcripts import router as transcript_router

# Create the main app that will compose all features
app = FastAPI(
    title="PodInsightHQ API - Unified",
    description="Unified API for all PodInsight features",
    version="1.0.0"
)

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

# Include the intelligence router for episode intelligence endpoints
# This adds all intelligence endpoints at /api/intelligence/*
app.include_router(intelligence_router)

# Include the prewarm router for Modal pre-warming
# This adds the /api/prewarm endpoint
app.include_router(prewarm_router)

# Include the transcript router for episode transcript retrieval
# This adds the /api/transcript/{episode_id} endpoint
app.include_router(transcript_router)


# Mount the existing topic_velocity app at the root
# This preserves ALL existing endpoints exactly as they are
# The topic_velocity.py file remains completely untouched
app.mount("/", topic_velocity_app)

# Note: The mount order matters - specific routes (audio_clips) before the catch-all mount
# This ensures audio routes are handled by the router, not the mounted app

# Vercel expects a variable named 'app'
# This exports our composed FastAPI app to Vercel
