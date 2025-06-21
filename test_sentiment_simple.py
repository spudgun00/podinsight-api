#!/usr/bin/env python3
"""
Simple test for sentiment calculation logic
"""

import os
import sys
import json
from datetime import datetime, timedelta, timezone

# Add the api directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

def test_sentiment_calculation():
    """Test the sentiment calculation directly"""
    print("Testing sentiment calculation logic...\n")
    
    # Set a test MongoDB URI if not set
    if not os.getenv('MONGODB_URI'):
        print("WARNING: MONGODB_URI not set. This test will fail when trying to connect.")
        print("For real testing, set MONGODB_URI environment variable.\n")
        return
    
    try:
        # Import the handler
        from sentiment_analysis import handler
        
        # Create an instance
        h = handler(None, None, None)
        
        # Test parameters
        weeks = 4
        topics = ["AI Agents", "B2B SaaS"]
        
        print(f"Testing with: weeks={weeks}, topics={topics}")
        print("Connecting to MongoDB...")
        
        # Call the calculation method directly
        results = h._calculate_sentiment(weeks, topics)
        
        print(f"\nGot {len(results)} sentiment data points:")
        
        # Group by topic
        by_topic = {}
        for result in results:
            topic = result['topic']
            if topic not in by_topic:
                by_topic[topic] = []
            by_topic[topic].append(result)
        
        # Display results
        for topic, data_points in by_topic.items():
            print(f"\n{topic}:")
            total_episodes = sum(dp['episodeCount'] for dp in data_points)
            avg_sentiment = sum(dp['sentiment'] * dp['episodeCount'] for dp in data_points) / max(total_episodes, 1)
            
            print(f"  Total episodes analyzed: {total_episodes}")
            print(f"  Average sentiment: {avg_sentiment:.3f}")
            print(f"  Weekly breakdown:")
            
            for dp in sorted(data_points, key=lambda x: x['week']):
                sentiment_desc = "positive" if dp['sentiment'] > 0.1 else "negative" if dp['sentiment'] < -0.1 else "neutral"
                print(f"    {dp['week']}: {dp['sentiment']:+.2f} ({sentiment_desc}) from {dp['episodeCount']} episodes")
        
        return True
        
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("MongoDB Sentiment Analysis Test")
    print("=" * 50)
    print(f"Timestamp: {datetime.now()}")
    print()
    
    # Check environment
    if os.getenv('MONGODB_URI'):
        print("✓ MONGODB_URI is set")
    else:
        print("✗ MONGODB_URI is NOT set")
        print("\nTo run this test with real data:")
        print("export MONGODB_URI='your_mongodb_connection_string'")
    
    print("\n" + "-" * 50 + "\n")
    
    # Run test
    success = test_sentiment_calculation()
    
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")