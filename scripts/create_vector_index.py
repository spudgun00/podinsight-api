#!/usr/bin/env python3
"""
Script to create the missing vector index in MongoDB Atlas
"""
import os
import sys
import asyncio
import logging
from datetime import datetime

# Add the parent directory to Python path so we can import from api/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def create_vector_index():
    """Create the vector_index_768d index in MongoDB Atlas"""
    
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        print("❌ ERROR: MONGODB_URI not set")
        return False
    
    try:
        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client.podinsight
        collection = db.transcript_chunks_768d
        
        print("Connected to MongoDB")
        
        # Check if the index already exists
        existing_indexes = await collection.list_indexes().to_list(None)
        index_names = [idx['name'] for idx in existing_indexes]
        
        if 'vector_index_768d' in index_names:
            print("✅ Vector index already exists!")
            return True
        
        print("Creating vector index...")
        
        # This is the vector search index definition for MongoDB Atlas
        # Note: This needs to be created via the Atlas UI or Atlas API, not the MongoDB driver
        index_definition = {
            "type": "vectorSearch",
            "name": "vector_index_768d",
            "definition": {
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding_768d",
                        "numDimensions": 768,
                        "similarity": "cosine"
                    }
                ]
            }
        }
        
        print("❌ ERROR: Vector search indexes cannot be created via the MongoDB driver.")
        print("You must create this index via the MongoDB Atlas UI or Atlas Admin API.")
        print("Index definition needed:")
        print(f"{index_definition}")
        print("\nTo create via Atlas UI:")
        print("1. Go to MongoDB Atlas dashboard")
        print("2. Navigate to your cluster")
        print("3. Go to 'Search' -> 'Create Search Index'")
        print("4. Choose 'Atlas Vector Search'")
        print("5. Select database: podinsight")
        print("6. Select collection: transcript_chunks_768d")
        print("7. Use index name: vector_index_768d")
        print("8. Configure field: embedding_768d, type: vector, dimensions: 768, similarity: cosine")
        
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("MongoDB Vector Index Creation Tool")
    print(f"Time: {datetime.now()}")
    
    await create_vector_index()

if __name__ == "__main__":
    asyncio.run(main())