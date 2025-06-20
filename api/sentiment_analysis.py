#!/usr/bin/env python3
"""
Sentiment Analysis API Handler for PodInsightHQ
Analyzes sentiment trends for topics using MongoDB transcripts
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import urllib.parse
from pymongo import MongoClient
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Handle GET request for sentiment analysis"""
        try:
            # Parse query parameters
            parsed_path = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_path.query)
            
            # Get parameters with defaults
            weeks = int(query_params.get('weeks', ['12'])[0])
            topics = query_params.get('topics[]', query_params.get('topics', [
                "AI Agents", "Capital Efficiency", "DePIN", "B2B SaaS", "Crypto/Web3"
            ]))
            
            logger.info(f"Sentiment analysis request: weeks={weeks}, topics={topics}")
            
            # Calculate sentiment data
            sentiment_data = self._calculate_sentiment(weeks, topics)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "success": True,
                "data": sentiment_data,
                "metadata": {
                    "weeks": weeks,
                    "topics": topics,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                "success": False,
                "error": str(e)
            }
            self.wfile.write(json.dumps(error_response).encode())
    
    def _calculate_sentiment(self, weeks: int, topics: List[str]) -> List[Dict[str, Any]]:
        """Calculate sentiment scores based on transcript content from MongoDB"""
        
        # Connect to MongoDB
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not configured")
            
        client = MongoClient(mongodb_uri)
        db = client['podinsight']
        collection = db['transcripts']
        
        try:
            # Get date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(weeks=weeks)
            
            # Sentiment keywords with weights
            sentiment_keywords = {
                # Strong positive
                'amazing': 1.0, 'incredible': 1.0, 'revolutionary': 1.0, 'breakthrough': 1.0,
                'phenomenal': 1.0, 'excellent': 0.8, 'fantastic': 0.8, 'brilliant': 0.8,
                
                # Positive
                'great': 0.7, 'love': 0.7, 'wonderful': 0.7, 'outstanding': 0.7,
                'excited': 0.6, 'impressive': 0.6, 'innovative': 0.6, 'powerful': 0.6,
                'successful': 0.5, 'valuable': 0.5, 'promising': 0.5, 'good': 0.4,
                'interesting': 0.3, 'useful': 0.4, 'helpful': 0.4,
                
                # Negative
                'bad': -0.4, 'poor': -0.5, 'disappointing': -0.6, 'failed': -0.6,
                'useless': -0.7, 'terrible': -0.8, 'horrible': -0.8, 'awful': -0.8,
                'problematic': -0.5, 'concerning': -0.4, 'worried': -0.4, 'difficult': -0.3,
                'challenging': -0.2, 'risky': -0.4, 'dangerous': -0.6, 'threat': -0.5,
                
                # Strong negative
                'disaster': -1.0, 'catastrophe': -1.0, 'failure': -0.8, 'worst': -0.8
            }
            
            sentiment_results = []
            
            # Process each week
            for week_offset in range(weeks):
                week_start = start_date + timedelta(weeks=week_offset)
                week_end = week_start + timedelta(days=7)
                week_label = f"W{week_offset + 1}"
                
                for topic in topics:
                    # Create case-insensitive regex for topic
                    topic_pattern = re.compile(re.escape(topic), re.IGNORECASE)
                    
                    # Find episodes in this date range that mention the topic
                    # Note: MongoDB transcript structure uses 'published_at' not 'published_date'
                    query = {
                        "full_text": {"$regex": topic_pattern},
                        "published_at": {
                            "$gte": week_start,
                            "$lt": week_end
                        }
                    }
                    
                    # Count episodes
                    episode_count = collection.count_documents(query)
                    
                    if episode_count == 0:
                        sentiment_results.append({
                            "topic": topic,
                            "week": week_label,
                            "sentiment": 0.0,
                            "episodeCount": 0
                        })
                        continue
                    
                    # Get sample of episodes (limit to prevent timeout)
                    cursor = collection.find(query, {
                        "full_text": 1,
                        "episode_title": 1,
                        "_id": 0
                    }).limit(20)  # Analyze up to 20 episodes per topic/week
                    
                    transcripts = list(cursor)
                    
                    # Calculate sentiment for sampled transcripts
                    total_sentiment_score = 0
                    analyzed_count = 0
                    
                    for transcript in transcripts:
                        content = transcript.get('full_text', '').lower()
                        
                        # Find context around topic mentions (±200 characters)
                        contexts = []
                        for match in topic_pattern.finditer(content, re.IGNORECASE):
                            start = max(0, match.start() - 200)
                            end = min(len(content), match.end() + 200)
                            contexts.append(content[start:end])
                        
                        if not contexts:
                            continue
                            
                        # Calculate sentiment for contexts
                        context_sentiments = []
                        
                        for context in contexts[:5]:  # Limit contexts per transcript
                            sentiment_score = 0
                            keyword_hits = 0
                            
                            # Check for sentiment keywords
                            for keyword, weight in sentiment_keywords.items():
                                if keyword in context:
                                    sentiment_score += weight
                                    keyword_hits += 1
                            
                            # Only count if we found sentiment keywords
                            if keyword_hits > 0:
                                context_sentiments.append(sentiment_score / keyword_hits)
                        
                        # Average sentiment across contexts
                        if context_sentiments:
                            transcript_sentiment = sum(context_sentiments) / len(context_sentiments)
                            total_sentiment_score += transcript_sentiment
                            analyzed_count += 1
                    
                    # Calculate average sentiment
                    if analyzed_count > 0:
                        avg_sentiment = total_sentiment_score / analyzed_count
                    else:
                        avg_sentiment = 0.0
                    
                    # Clamp to [-1, 1] range
                    avg_sentiment = max(-1, min(1, avg_sentiment))
                    
                    sentiment_results.append({
                        "topic": topic,
                        "week": week_label,
                        "sentiment": round(avg_sentiment, 2),
                        "episodeCount": episode_count
                    })
                    
                    logger.info(f"Topic: {topic}, Week: {week_label}, Sentiment: {avg_sentiment:.2f}, Episodes: {episode_count}")
            
            return sentiment_results
            
        finally:
            client.close()