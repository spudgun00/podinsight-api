#!/usr/bin/env python3
"""
Fast Sentiment Analysis API v2 (Batch-powered)

Returns pre-computed sentiment data from nightly batch processing.
This API is designed for instant response (<100ms) by reading from
the sentiment_results collection instead of computing on-demand.
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
import urllib.parse
from pymongo import MongoClient

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
        """Handle GET request for pre-computed sentiment data"""
        try:
            # Parse query parameters
            parsed_path = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_path.query)

            # Get parameters with defaults
            weeks = int(query_params.get('weeks', ['12'])[0])
            topics = query_params.get('topics[]', query_params.get('topics', [
                "AI Agents", "Capital Efficiency", "DePIN", "B2B SaaS", "Crypto/Web3"
            ]))

            logger.info(f"Fast sentiment lookup: weeks={weeks}, topics={topics}")

            # Get pre-computed sentiment data
            sentiment_data = self._get_precomputed_sentiment(weeks, topics)

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
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "source": "pre_computed_batch",
                    "api_version": "v2"
                }
            }

            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            logger.error(f"Error in fast sentiment API: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            error_response = {
                "success": False,
                "error": str(e),
                "api_version": "v2"
            }
            self.wfile.write(json.dumps(error_response).encode())

    def _get_precomputed_sentiment(self, weeks: int, topics: List[str]) -> List[Dict[str, Any]]:
        """Get pre-computed sentiment data from MongoDB"""

        # Connect to MongoDB
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not configured")

        client = MongoClient(mongodb_uri)
        db = client['podinsight']
        results_collection = db['sentiment_results']

        try:
            # Build query for requested topics and weeks
            query = {
                "topic": {"$in": topics}
            }

            # Get results sorted by year and week
            cursor = results_collection.find(query).sort([
                ("year", 1),
                ("week", 1),
                ("topic", 1)
            ])

            all_results = list(cursor)
            logger.info(f"Found {len(all_results)} pre-computed results")

            # Filter to requested number of weeks (get most recent)
            if all_results:
                # Group by week to get all topics for the most recent weeks
                weeks_data = {}
                for result in all_results:
                    week_key = f"{result['year']}-{result['week']}"
                    if week_key not in weeks_data:
                        weeks_data[week_key] = []
                    weeks_data[week_key].append(result)

                # Sort weeks and take the most recent ones
                sorted_weeks = sorted(weeks_data.keys(), reverse=True)
                recent_weeks = sorted_weeks[:weeks]

                # Flatten results from recent weeks
                filtered_results = []
                for week_key in reversed(recent_weeks):  # Reverse to show oldest first
                    filtered_results.extend(weeks_data[week_key])

                all_results = filtered_results

            # Convert to API format
            sentiment_data = []
            for result in all_results:
                # Only include requested topics
                if result['topic'] in topics:
                    sentiment_data.append({
                        "topic": result['topic'],
                        "week": result['week'],
                        "sentiment": result['sentiment_score'],
                        "episodeCount": result['episode_count'],
                        "chunkCount": result.get('chunk_count', 0),
                        "confidence": result.get('confidence', 0.0),
                        "keywordsFound": result.get('keywords_found', []),
                        "computedAt": result['computed_at'].isoformat() if result.get('computed_at') else None,
                        "metadata": result.get('metadata', {})
                    })

            # If no pre-computed data found, return empty structure
            if not sentiment_data:
                logger.warning("No pre-computed sentiment data found, returning empty structure")
                sentiment_data = self._generate_empty_structure(weeks, topics)

            # Ensure we have data for all requested topics and weeks
            sentiment_data = self._fill_missing_data(sentiment_data, weeks, topics)

            return sentiment_data

        finally:
            client.close()

    def _generate_empty_structure(self, weeks: int, topics: List[str]) -> List[Dict[str, Any]]:
        """Generate empty sentiment structure when no data is available"""
        logger.info("Generating empty sentiment structure (batch not run yet)")

        empty_data = []
        for week_num in range(1, weeks + 1):
            for topic in topics:
                empty_data.append({
                    "topic": topic,
                    "week": f"W{week_num}",
                    "sentiment": 0.0,
                    "episodeCount": 0,
                    "chunkCount": 0,
                    "confidence": 0.0,
                    "keywordsFound": [],
                    "computedAt": None,
                    "metadata": {
                        "status": "no_batch_data",
                        "message": "Run batch processor to generate data"
                    }
                })

        return empty_data

    def _fill_missing_data(self, sentiment_data: List[Dict], weeks: int, topics: List[str]) -> List[Dict[str, Any]]:
        """Fill in missing combinations of topics and weeks with zeros"""

        # Create a set of existing combinations
        existing = set()
        for item in sentiment_data:
            existing.add((item['topic'], item['week']))

        # Add missing combinations
        for week_num in range(1, weeks + 1):
            week_label = f"W{week_num}"
            for topic in topics:
                if (topic, week_label) not in existing:
                    sentiment_data.append({
                        "topic": topic,
                        "week": week_label,
                        "sentiment": 0.0,
                        "episodeCount": 0,
                        "chunkCount": 0,
                        "confidence": 0.0,
                        "keywordsFound": [],
                        "computedAt": None,
                        "metadata": {
                            "status": "missing_data",
                            "message": "No data for this topic/week combination"
                        }
                    })

        # Sort by week and topic for consistent output
        sentiment_data.sort(key=lambda x: (x['week'], x['topic']))

        return sentiment_data
