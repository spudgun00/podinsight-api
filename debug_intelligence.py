#!/usr/bin/env python3
"""Debug Episode Intelligence data structure"""

import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

mongodb_uri = os.getenv('MONGODB_URI')
if not mongodb_uri:
    print("Error: MONGODB_URI not found in .env file")
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
    print(f"Document keys: {list(doc.keys())}")
    
    if 'signals' in doc:
        print(f"\nSignals structure:")
        print(f"  Type: {type(doc['signals'])}")
        
        if isinstance(doc['signals'], dict):
            print(f"  Signal categories: {list(doc['signals'].keys())}")
            
            # Check each signal category
            for category in doc['signals']:
                signals_list = doc['signals'][category]
                print(f"\n  {category}:")
                print(f"    Count: {len(signals_list) if isinstance(signals_list, list) else 'Not a list'}")
                
                if isinstance(signals_list, list) and len(signals_list) > 0:
                    first_signal = signals_list[0]
                    print(f"    First signal keys: {list(first_signal.keys()) if isinstance(first_signal, dict) else 'Not a dict'}")
                    print(f"    First signal: {json.dumps(first_signal, indent=6)}")
else:
    print(f"\nNo document found for episode {episode_id}")
    
    # Try to find any document with signals
    print("\nLooking for any document with signals...")
    sample = collection.find_one({"signals": {"$exists": True}})
    if sample:
        print(f"Found a document with signals: {sample['episode_id']}")
        print(f"Signals structure: {json.dumps(sample['signals'], indent=2)}")

client.close()