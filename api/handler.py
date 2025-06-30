"""
Vercel serverless function handler for FastAPI
"""
from .index import app

# Vercel expects a handler function
handler = app
