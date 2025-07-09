#!/usr/bin/env python3
"""
Generate complete episode intelligence report with all signal details
"""
import requests
import json
from datetime import datetime

def generate_report():
    """Generate complete report of all episodes and their signals"""

    # Fetch audit data
    print("Fetching episode intelligence data...")
    response = requests.get("https://podinsight-api.vercel.app/api/intelligence/audit-empty-signals")
    data = response.json()

    # Extract populated episodes (all of them, not just sample)
    print("\nFetching complete episode list...")
    all_episodes_response = requests.get("https://podinsight-api.vercel.app/api/intelligence/find-episodes-with-intelligence")
    all_episodes_data = all_episodes_response.json()

    # Get detailed signal data for each episode
    detailed_episodes = []

    print(f"\nFetching detailed data for {data['total_documents']} episodes...")

    # First, get all episode IDs from the audit
    audit_response = requests.get("https://podinsight-api.vercel.app/api/intelligence/audit-empty-signals")
    audit_data = audit_response.json()

    # Combine populated and empty episodes
    all_episode_ids = []

    # Add populated episodes
    for ep in audit_data.get('populated_episodes_sample', []):
        all_episode_ids.append(ep['episode_id'])

    # Add empty episodes
    for ep in audit_data.get('empty_episodes', []):
        all_episode_ids.append(ep['episode_id'])

    print(f"Processing {len(all_episode_ids)} episodes...")

    # Create detailed report
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_episodes": data['total_documents'],
        "episodes_with_signals": data['documents_with_signals'],
        "episodes_empty": data['documents_empty'],
        "success_rate": data['success_rate'],
        "signal_distribution": data['signal_distribution'],
        "episodes": []
    }

    # Add populated episodes
    populated = sorted(audit_data.get('populated_episodes_sample', []),
                      key=lambda x: x['total_signals'],
                      reverse=True)

    for ep in populated:
        report['episodes'].append({
            "episode_id": ep['episode_id'],
            "title": ep.get('title', 'Unknown'),
            "total_signals": ep['total_signals'],
            "signals": {
                "investable": ep['breakdown']['investable'],
                "competitive": ep['breakdown']['competitive'],
                "portfolio": ep['breakdown']['portfolio'],
                "soundbites": ep['breakdown']['soundbites']
            },
            "has_signals": True
        })

    # Add empty episodes
    for ep in audit_data.get('empty_episodes', []):
        report['episodes'].append({
            "episode_id": ep['episode_id'],
            "title": ep.get('title', 'Unknown'),
            "total_signals": 0,
            "signals": {
                "investable": 0,
                "competitive": 0,
                "portfolio": 0,
                "soundbites": 0
            },
            "has_signals": False
        })

    # Save to file
    with open('episode_intelligence_full_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to episode_intelligence_full_report.json")
    print(f"Total episodes: {report['total_episodes']}")
    print(f"With signals: {report['episodes_with_signals']} ({report['success_rate']})")
    print(f"Empty: {report['episodes_empty']}")

    # Print summary
    print("\nTop 5 episodes by signal count:")
    for i, ep in enumerate(report['episodes'][:5], 1):
        print(f"{i}. {ep['episode_id']}: {ep['total_signals']} signals")

if __name__ == "__main__":
    generate_report()
