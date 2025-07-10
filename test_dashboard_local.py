#!/usr/bin/env python3
"""Test dashboard endpoint logic locally"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Connect to MongoDB
mongodb_uri = os.getenv("MONGODB_URI")
client = MongoClient(mongodb_uri)
db = client["podinsight"]

# Get collections
intelligence_collection = db["episode_intelligence"]
metadata_collection = db["episode_metadata"]

# Count documents
intel_count = intelligence_collection.count_documents({})
metadata_count = metadata_collection.count_documents({})

print(f"Intelligence documents: {intel_count}")
print(f"Metadata documents: {metadata_count}")

# Get all intelligence documents
intelligence_docs = list(intelligence_collection.find().limit(10))
print(f"\nFound {len(intelligence_docs)} intelligence documents (limited to 10)")

# For each intelligence doc, try to find metadata
matched = 0
for intel_doc in intelligence_docs:
    episode_id = intel_doc.get("episode_id")

    # Try to find metadata
    metadata_doc = metadata_collection.find_one({
        "$or": [
            {"episode_id": episode_id},
            {"guid": episode_id}
        ]
    })

    if metadata_doc:
        matched += 1
        print(f"\n✅ Match found for {episode_id}")
        print(f"   Title: {metadata_doc.get('raw_entry_original_feed', {}).get('episode_title', 'Unknown')}")

        # Check signals
        signals = intel_doc.get("signals", {})
        signal_count = 0
        for signal_type in ["investable", "competitive", "portfolio", "soundbites"]:
            if signal_type in signals and isinstance(signals[signal_type], list):
                signal_count += len(signals[signal_type])
        print(f"   Signals: {signal_count}")
    else:
        print(f"\n❌ No metadata found for {episode_id}")

print(f"\n\nSummary: {matched}/{len(intelligence_docs)} intelligence docs have matching metadata")
