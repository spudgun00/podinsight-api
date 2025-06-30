#!/usr/bin/env python3
"""Check MongoDB connection and data availability"""

import os
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

# List all databases
print("=== MongoDB Databases ===")
db_names = client.list_database_names()
for db_name in db_names:
    print(f"  - {db_name}")

# Check podcast_insight database
print("\n=== Collections in podcast_insight database ===")
db = client['podcast_insight']
collections = db.list_collection_names()
for coll in collections:
    count = db[coll].count_documents({})
    print(f"  - {coll}: {count} documents")

# Try different database names
for db_name in ['podinsight', 'pod_insight', 'podinsight-api', 'pod-insight']:
    if db_name in db_names:
        print(f"\n=== Found database: {db_name} ===")
        db = client[db_name]
        collections = db.list_collection_names()
        for coll in collections:
            count = db[coll].count_documents({})
            print(f"  - {coll}: {count} documents")

            # If episode_metadata exists, show sample
            if coll == 'episode_metadata' and count > 0:
                sample = db[coll].find_one()
                print(f"    Sample fields: {list(sample.keys())}")

client.close()
