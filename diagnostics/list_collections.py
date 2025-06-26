#!/usr/bin/env python3
"""
List all MongoDB collections and their sample documents
"""

import os
from pymongo import MongoClient

def list_collections():
    """List all collections and their structure"""

    mongodb_uri = os.getenv('MONGODB_URI')
    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client['podinsight']

    print("📋 MongoDB Collections in 'podinsight' database:")
    print("=" * 50)

    collections = db.list_collection_names()
    print(f"Total collections: {len(collections)}")

    for collection_name in collections:
        collection = db[collection_name]
        count = collection.estimated_document_count()

        print(f"\n📄 {collection_name}")
        print(f"   Count: {count:,} documents")

        if count > 0:
            sample = collection.find_one()
            fields = list(sample.keys())
            print(f"   Fields: {fields}")

            # Look for date/published fields
            date_fields = [f for f in fields if any(keyword in f.lower()
                          for keyword in ['date', 'published', 'created', 'updated', 'time'])]
            if date_fields:
                print(f"   Date fields: {date_fields}")
                for field in date_fields:
                    value = sample[field]
                    print(f"     {field}: {type(value)} = {value}")

    client.close()

if __name__ == "__main__":
    list_collections()
