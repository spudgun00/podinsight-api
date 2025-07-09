#!/usr/bin/env python3
"""
Verify all 50 episode_intelligence documents by bypassing the API limit
"""
import os
from pymongo import MongoClient
from collections import Counter

# Get MongoDB URI from environment
mongodb_uri = os.getenv("MONGODB_URI")
if not mongodb_uri:
    # Use the one from .env.vercel
    mongodb_uri = "mongodb+srv://podinsight-api:uqBMsQzHMI7bTV3e@podinsight-cluster.bgknvz.mongodb.net/?retryWrites=true&w=majority&appName=podinsight-cluster"

try:
    client = MongoClient(mongodb_uri)
    db = client["podinsight"]
    
    # Get ALL episode_intelligence documents
    intelligence_collection = db.episode_intelligence
    all_intel_docs = list(intelligence_collection.find({}))
    
    print(f"Total episode_intelligence documents: {len(all_intel_docs)}")
    print("=" * 60)
    
    # Analyze signal population
    populated = 0
    empty = 0
    signal_counts = Counter()
    
    for doc in all_intel_docs:
        episode_id = doc.get("episode_id", "Unknown")
        signals = doc.get("signals", {})
        
        total_signals = 0
        for signal_type in ["investable", "competitive", "portfolio", "soundbites"]:
            if signal_type in signals and isinstance(signals[signal_type], list):
                count = len(signals[signal_type])
                total_signals += count
                signal_counts[signal_type] += count
        
        if total_signals > 0:
            populated += 1
        else:
            empty += 1
            print(f"Empty signals: {episode_id[:40]}")
    
    print("\nSUMMARY:")
    print(f"Documents with signals: {populated}")
    print(f"Documents with empty signals: {empty}")
    print(f"Success rate: {(populated / len(all_intel_docs) * 100):.1f}%")
    
    print("\nSignal distribution:")
    for signal_type, count in signal_counts.items():
        print(f"  {signal_type}: {count} total signals")
    
except Exception as e:
    print(f"Error: {e}")
    print("Note: This script needs direct MongoDB access")