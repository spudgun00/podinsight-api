#!/usr/bin/env python3
"""Test if environment variables are loading correctly"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Check MongoDB URI
mongodb_uri = os.getenv("MONGODB_URI")
print(f"MONGODB_URI is set: {mongodb_uri is not None}")
print(f"MONGODB_URI starts with: {mongodb_uri[:20] if mongodb_uri else 'None'}...")

# Check MongoDB database
mongodb_db = os.getenv("MONGODB_DATABASE", "podinsight")
print(f"MONGODB_DATABASE: {mongodb_db}")

# Check other relevant env vars
modal_key = os.getenv("MODAL_API_KEY")
print(f"MODAL_API_KEY is set: {modal_key is not None}")
