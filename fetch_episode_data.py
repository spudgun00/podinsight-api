#!/usr/bin/env python3
"""
Fetch raw episode intelligence data to examine structure differences
"""
import os
import json
from pymongo import MongoClient

# Get MongoDB connection
mongodb_uri = os.getenv("MONGODB_URI")
if not mongodb_uri:
    print("MONGODB_URI not configured")
    exit(1)

client = MongoClient(mongodb_uri)
db = client["podinsight"]

# Test episodes
working_episode = "02fc268c-61dc-4074-b7ec-882615bc6d85"
failing_episode = "1216c2e7-42b8-42ca-92d7-bad784f80af2"

def analyze_episode_data(episode_id, label):
    """Fetch and analyze episode intelligence data"""
    print(f"\n{'='*60}")
    print(f"Analyzing {label} episode: {episode_id}")
    print('='*60)
    
    # Fetch the intelligence document
    intel_doc = db.episode_intelligence.find_one({"episode_id": episode_id})
    
    if not intel_doc:
        print(f"No intelligence document found!")
        return
    
    # Check signals structure
    signals = intel_doc.get("signals", {})
    print(f"\nSignals type: {type(signals)}")
    print(f"Signal categories: {list(signals.keys())}")
    
    # Analyze each signal type
    for signal_type in ["investable", "competitive", "portfolio", "soundbites"]:
        if signal_type in signals:
            signal_list = signals[signal_type]
            print(f"\n{signal_type.upper()}:")
            print(f"  Type: {type(signal_list)}")
            print(f"  Count: {len(signal_list) if isinstance(signal_list, list) else 'N/A'}")
            
            if isinstance(signal_list, list) and len(signal_list) > 0:
                first_signal = signal_list[0]
                print(f"  First signal keys: {list(first_signal.keys())}")
                
                # Check for content fields
                has_content = 'content' in first_signal
                has_signal_text = 'signal_text' in first_signal
                print(f"  Has 'content' field: {has_content}")
                print(f"  Has 'signal_text' field: {has_signal_text}")
                
                # Check timestamp format
                if 'timestamp' in first_signal:
                    timestamp = first_signal['timestamp']
                    print(f"  Timestamp type: {type(timestamp)}")
                    if isinstance(timestamp, dict):
                        print(f"  Timestamp keys: {list(timestamp.keys())}")

# Run analysis
analyze_episode_data(working_episode, "WORKING")
analyze_episode_data(failing_episode, "FAILING")

# Check a few more episodes
print(f"\n{'='*60}")
print("Checking additional episodes...")
print('='*60)

# Get 5 more random episodes
additional_episodes = list(db.episode_intelligence.find({}, {"episode_id": 1}).limit(5))
for doc in additional_episodes:
    episode_id = doc.get("episode_id")
    if episode_id not in [working_episode, failing_episode]:
        intel_doc = db.episode_intelligence.find_one({"episode_id": episode_id})
        signals = intel_doc.get("signals", {})
        
        # Count total signals
        total_signals = 0
        has_issues = False
        
        for signal_type in ["investable", "competitive", "portfolio", "soundbites"]:
            if signal_type in signals:
                signal_list = signals[signal_type]
                if isinstance(signal_list, list):
                    total_signals += len(signal_list)
                    # Check first signal for issues
                    if len(signal_list) > 0:
                        first_signal = signal_list[0]
                        if 'content' not in first_signal and 'signal_text' not in first_signal:
                            has_issues = True
                else:
                    has_issues = True
        
        status = "❌ ISSUE" if has_issues else "✅ OK"
        print(f"\n{episode_id}: {total_signals} signals {status}")