#!/usr/bin/env python3
"""
Script to check MongoDB collections and their document counts
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from pathlib import Path

# Load environment variables from parent directory
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

def check_mongodb_structure():
    """Check MongoDB database structure and collections"""

    mongo_uri = os.getenv('MONGODB_URI')
    if not mongo_uri:
        print("ERROR: MONGODB_URI not found in environment variables")
        return

    client = MongoClient(mongo_uri)

    # List all databases
    print("=" * 80)
    print("DATABASES")
    print("=" * 80)
    databases = client.list_database_names()
    for db_name in databases:
        print(f"  - {db_name}")

    # Check podinsight database (note: singular, not plural)
    print("\n" + "=" * 80)
    print("PODINSIGHT DATABASE COLLECTIONS")
    print("=" * 80)

    db = client['podinsight']
    collections = db.list_collection_names()

    for collection_name in sorted(collections):
        count = db[collection_name].count_documents({})
        print(f"  {collection_name}: {count:,} documents")

        # Sample a document from each collection
        if count > 0:
            sample = db[collection_name].find_one()
            if sample:
                fields = list(sample.keys())[:10]  # First 10 fields
                print(f"    Sample fields: {', '.join(fields)}")

                # Check for GUID-related fields
                guid_fields = [f for f in sample.keys() if 'guid' in f.lower() or 'id' in f.lower()]
                if guid_fields:
                    print(f"    GUID/ID fields: {', '.join(guid_fields)}")

    # Look for metadata in other collections
    print("\n" + "=" * 80)
    print("SEARCHING FOR EPISODE METADATA")
    print("=" * 80)

    # Search for collections that might contain episode metadata
    for collection_name in collections:
        collection = db[collection_name]

        # Check if collection has episode-related fields
        sample = collection.find_one()
        if sample and any(field in str(sample).lower() for field in ['episode', 'title', 'podcast', 'guid']):
            print(f"\n  Collection '{collection_name}' might contain episode data:")

            # Check for specific GUIDs
            test_guids = [
                "flightcast:qoefujdsy5huurb987mnjpw2",
                "e405359e-ea57-11ef-b8c4-ff74e39a637e"
            ]

            for guid in test_guids:
                # Try different field names
                for field in ['guid', 'GUID', '_id', 'episode_id', 'episodeId']:
                    doc = collection.find_one({field: guid})
                    if doc:
                        print(f"    ✓ Found GUID '{guid}' in field '{field}'")
                        print(f"      Title: {doc.get('title', doc.get('episode_title', 'N/A'))}")
                        break

if __name__ == "__main__":
    check_mongodb_structure()
