#!/usr/bin/env python3
"""
Audit all 50 episode_intelligence documents to check signal population
"""
import requests
import json

def audit_episodes():
    """Check signal population for all episodes"""
    # First get all episodes with intelligence
    url = "https://podinsight-api.vercel.app/api/intelligence/find-episodes-with-intelligence"
    response = requests.get(url)
    data = response.json()
    
    episodes = data.get("matches", [])
    
    print(f"Total episodes with intelligence documents: {len(episodes)}")
    print("=" * 60)
    
    populated_count = 0
    empty_count = 0
    empty_episodes = []
    
    for i, episode in enumerate(episodes):
        episode_id = episode["episode_id_in_intelligence"]
        
        # Check signal structure for this episode
        debug_url = f"https://podinsight-api.vercel.app/api/intelligence/debug-signal-structure/{episode_id}"
        debug_response = requests.get(debug_url)
        debug_data = debug_response.json()
        
        if "signal_analysis" in debug_data:
            # Count total signals
            total_signals = 0
            for signal_type, analysis in debug_data["signal_analysis"].items():
                if analysis.get("is_list"):
                    total_signals += analysis.get("count", 0)
            
            if total_signals > 0:
                populated_count += 1
                print(f"✅ {episode['title'][:50]}: {total_signals} signals")
            else:
                empty_count += 1
                empty_episodes.append({
                    "id": episode_id,
                    "title": episode["title"]
                })
                print(f"❌ {episode['title'][:50]}: EMPTY")
        
        # Progress indicator
        if (i + 1) % 5 == 0:
            print(f"Progress: {i + 1}/{len(episodes)} episodes checked...")
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Episodes with signals: {populated_count}")
    print(f"Episodes with EMPTY signals: {empty_count}")
    print(f"Success rate: {(populated_count / len(episodes) * 100):.1f}%")
    
    if empty_episodes:
        print("\nEpisodes needing signal regeneration:")
        for ep in empty_episodes[:5]:  # Show first 5
            print(f"- {ep['id']}: {ep['title'][:60]}")
        if len(empty_episodes) > 5:
            print(f"... and {len(empty_episodes) - 5} more")

if __name__ == "__main__":
    audit_episodes()