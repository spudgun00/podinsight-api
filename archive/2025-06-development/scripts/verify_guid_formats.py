#!/usr/bin/env python3
"""
Script to verify GUID formats in MongoDB episode_metadata collection
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
import json
from collections import Counter

# Load environment variables from parent directory
from pathlib import Path
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

def connect_to_mongodb():
    """Connect to MongoDB using environment variables"""
    mongo_uri = os.getenv('MONGODB_URI')
    if not mongo_uri:
        raise ValueError("MONGODB_URI not found in environment variables")

    client = MongoClient(mongo_uri)
    db = client['podinsights']
    return db

def check_specific_guids(db):
    """Check for specific GUIDs in the episode_metadata collection"""
    print("=" * 80)
    print("CHECKING SPECIFIC GUIDs")
    print("=" * 80)

    specific_guids = [
        "flightcast:qoefujdsy5huurb987mnjpw2",
        "e405359e-ea57-11ef-b8c4-ff74e39a637e"
    ]

    collection = db['episode_metadata']

    for guid in specific_guids:
        print(f"\nSearching for GUID: {guid}")

        # Try exact match
        doc = collection.find_one({"guid": guid})
        if doc:
            print(f"  ✓ Found with exact match (guid field)")
            print(f"    Title: {doc.get('title', 'N/A')}")
            print(f"    Podcast: {doc.get('podcast_title', 'N/A')}")
        else:
            print(f"  ✗ Not found with exact match")

        # Try case-insensitive search
        doc = collection.find_one({"guid": {"$regex": f"^{guid}$", "$options": "i"}})
        if doc:
            print(f"  ✓ Found with case-insensitive match")
            print(f"    Actual GUID in DB: {doc.get('guid')}")
            print(f"    Title: {doc.get('title', 'N/A')}")

        # Try searching in other fields
        doc = collection.find_one({"GUID": guid})
        if doc:
            print(f"  ✓ Found in 'GUID' field (uppercase)")
            print(f"    Title: {doc.get('title', 'N/A')}")

        # Try searching in _id field
        doc = collection.find_one({"_id": guid})
        if doc:
            print(f"  ✓ Found as _id")
            print(f"    Title: {doc.get('title', 'N/A')}")

def sample_guid_formats(db):
    """Sample GUIDs from the collection to see their formats"""
    print("\n" + "=" * 80)
    print("SAMPLING GUID FORMATS")
    print("=" * 80)

    collection = db['episode_metadata']

    # Get total count
    total_count = collection.count_documents({})
    print(f"\nTotal documents in episode_metadata: {total_count}")

    # Sample some documents
    sample_size = min(100, total_count)
    sample_docs = list(collection.find({}, {"guid": 1, "GUID": 1, "_id": 1, "title": 1}).limit(sample_size))

    print(f"\nSampling {len(sample_docs)} documents...")

    # Analyze GUID formats
    guid_formats = Counter()
    field_names = Counter()

    for doc in sample_docs:
        # Check which field contains the GUID
        if "guid" in doc:
            field_names["guid"] += 1
            guid = doc["guid"]
        elif "GUID" in doc:
            field_names["GUID"] += 1
            guid = doc["GUID"]
        else:
            field_names["no_guid_field"] += 1
            guid = str(doc.get("_id", ""))

        # Categorize GUID format
        if guid.startswith("flightcast:"):
            guid_formats["flightcast_format"] += 1
        elif len(guid) == 36 and guid.count('-') == 4:
            guid_formats["standard_uuid"] += 1
        elif guid.startswith("http"):
            guid_formats["url_format"] += 1
        else:
            guid_formats["other_format"] += 1

    print("\nField name distribution:")
    for field, count in field_names.items():
        print(f"  {field}: {count}")

    print("\nGUID format distribution:")
    for format_type, count in guid_formats.items():
        print(f"  {format_type}: {count}")

    # Show examples of each format
    print("\nExamples of each GUID format:")
    shown_formats = set()

    for doc in sample_docs:
        guid = doc.get("guid") or doc.get("GUID") or str(doc.get("_id", ""))
        title = doc.get("title", "N/A")

        format_type = None
        if guid.startswith("flightcast:"):
            format_type = "flightcast_format"
        elif len(guid) == 36 and guid.count('-') == 4:
            format_type = "standard_uuid"
        elif guid.startswith("http"):
            format_type = "url_format"
        else:
            format_type = "other_format"

        if format_type and format_type not in shown_formats:
            shown_formats.add(format_type)
            print(f"\n  {format_type}:")
            print(f"    GUID: {guid}")
            print(f"    Title: {title[:50]}...")

def check_field_variations(db):
    """Check for variations in field names"""
    print("\n" + "=" * 80)
    print("CHECKING FIELD NAME VARIATIONS")
    print("=" * 80)

    collection = db['episode_metadata']

    # Get a sample document to see all fields
    sample_doc = collection.find_one()
    if sample_doc:
        print("\nSample document fields:")
        for key in sorted(sample_doc.keys()):
            if 'guid' in key.lower() or 'id' in key.lower():
                print(f"  {key}: {type(sample_doc[key]).__name__}")
                if isinstance(sample_doc[key], str):
                    print(f"    Value: {sample_doc[key][:50]}...")

def search_by_partial_guid(db):
    """Search for documents containing parts of the specific GUIDs"""
    print("\n" + "=" * 80)
    print("SEARCHING BY PARTIAL GUID")
    print("=" * 80)

    collection = db['episode_metadata']

    # Search for documents containing parts of the flightcast GUID
    partial_search = "qoefujdsy5huurb987mnjpw2"
    print(f"\nSearching for documents containing: {partial_search}")

    # Search in all possible fields
    docs = collection.find({
        "$or": [
            {"guid": {"$regex": partial_search, "$options": "i"}},
            {"GUID": {"$regex": partial_search, "$options": "i"}},
            {"_id": {"$regex": partial_search, "$options": "i"}}
        ]
    }).limit(5)

    count = 0
    for doc in docs:
        count += 1
        print(f"\n  Found document {count}:")
        print(f"    _id: {doc.get('_id')}")
        print(f"    guid: {doc.get('guid', 'N/A')}")
        print(f"    GUID: {doc.get('GUID', 'N/A')}")
        print(f"    Title: {doc.get('title', 'N/A')[:50]}...")

    if count == 0:
        print("  No documents found containing this partial GUID")

def main():
    try:
        db = connect_to_mongodb()

        # Run all checks
        check_specific_guids(db)
        sample_guid_formats(db)
        check_field_variations(db)
        search_by_partial_guid(db)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
