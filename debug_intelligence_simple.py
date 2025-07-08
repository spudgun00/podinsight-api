#!/usr/bin/env python3
"""Simple debug for Episode Intelligence - no dotenv"""

import os
import json
from pymongo import MongoClient

# Get MongoDB URI from environment
mongodb_uri = os.environ.get('MONGODB_URI')
if not mongodb_uri:
    print("Error: MONGODB_URI not found in environment")
    print("Please set it or run: export MONGODB_URI='your_connection_string'")
    exit(1)

# Connect to MongoDB
client = MongoClient(mongodb_uri)
db = client['podinsight']  # Based on the API code

# Check episode_intelligence collection
collection = db['episode_intelligence']
print(f"Total documents in episode_intelligence: {collection.count_documents({})}")

# Find the specific episode
episode_id = "02fc268c-61dc-4074-b7ec-882615bc6d85"
doc = collection.find_one({"episode_id": episode_id})

if doc:
    print(f"\nFound document for episode {episode_id}")
    
    # Remove the _id field for cleaner JSON output
    doc_copy = dict(doc)
    doc_copy.pop('_id', None)
    
    print("\nFull document structure:")
    print(json.dumps(doc_copy, indent=2, default=str))
else:
    print(f"\nNo document found for episode {episode_id}")

client.close()