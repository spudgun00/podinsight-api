# MongoDB Migration Plan - Transcripts & Search

## Architecture Overview

### Keep in Supabase (using $300 credit):
- Episodes metadata table (lightweight)
- User authentication (when added)
- Topic mentions (small data)
- KPIs and entities (structured data)

### Move to MongoDB Atlas (using $5,000 credit):
- Full transcript text (527MB+)
- Segments data (2.3GB)
- Embeddings vectors
- Search indexes

## Implementation Plan (4-6 hours total)

### Phase 1: MongoDB Setup (30 minutes)

1. **Create MongoDB Atlas Account**
   ```bash
   # Sign up at mongodb.com/atlas
   # Apply your $5,000 credit
   # Create M10 cluster (covers everything)
   ```

2. **Create Collections**
   ```javascript
   // transcripts collection
   {
     _id: ObjectId(),
     episode_id: "uuid-from-supabase",
     podcast_name: "The Twenty Minute VC",
     episode_title: "...",
     published_at: ISODate(),
     full_text: "Complete transcript text...",
     segments: [...],
     topics: ["AI Agents", "B2B SaaS"],
     s3_path: "pod-insights-stage/..."
   }

   // embeddings collection (optional - for vector search)
   {
     _id: ObjectId(),
     episode_id: "uuid",
     embedding: [0.123, 0.456, ...], // 1536 dimensions
     chunk_text: "relevant excerpt",
     chunk_index: 0
   }
   ```

### Phase 2: Data Migration Script (2 hours)

Create `migrate_to_mongodb.py`:

```python
import os
import boto3
import json
from pymongo import MongoClient
from supabase import create_client, Client
from typing import Dict, List
import asyncio
from tqdm import tqdm

class TranscriptMigrator:
    def __init__(self):
        # MongoDB connection
        self.mongo_client = MongoClient(os.getenv('MONGODB_URI'))
        self.db = self.mongo_client['podinsight']
        self.transcripts = self.db['transcripts']

        # Supabase connection
        self.supabase: Client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_KEY')
        )

        # S3 connection
        self.s3 = boto3.client('s3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

    async def migrate_all_transcripts(self):
        """Migrate all transcripts from S3 to MongoDB"""

        # Get all episodes from Supabase
        episodes = self.supabase.table('episodes').select('*').execute()

        print(f"Found {len(episodes.data)} episodes to migrate")

        for episode in tqdm(episodes.data):
            try:
                # Get S3 path from episode
                s3_prefix = episode['s3_stage_prefix']

                # Fetch transcript from S3
                transcript_data = await self.fetch_transcript_from_s3(s3_prefix)

                if transcript_data:
                    # Prepare MongoDB document
                    doc = {
                        'episode_id': episode['id'],
                        'podcast_name': episode['podcast_name'],
                        'episode_title': episode['episode_title'],
                        'published_at': episode['published_at'],
                        'full_text': self.extract_full_text(transcript_data),
                        'segments': transcript_data.get('segments', []),
                        'topics': await self.get_episode_topics(episode['id']),
                        's3_path': s3_prefix,
                        'word_count': episode.get('word_count', 0),
                        'duration_seconds': episode.get('duration_seconds', 0)
                    }

                    # Insert into MongoDB
                    self.transcripts.update_one(
                        {'episode_id': episode['id']},
                        {'$set': doc},
                        upsert=True
                    )

            except Exception as e:
                print(f"Error migrating episode {episode['id']}: {e}")
                continue

    def extract_full_text(self, transcript_data: Dict) -> str:
        """Combine all segments into full text"""
        segments = transcript_data.get('segments', [])
        return " ".join([seg.get('text', '') for seg in segments])

    async def get_episode_topics(self, episode_id: str) -> List[str]:
        """Get topics for an episode from Supabase"""
        topics = self.supabase.table('topic_mentions')\
            .select('topic_name')\
            .eq('episode_id', episode_id)\
            .execute()
        return [t['topic_name'] for t in topics.data]

# Run migration
if __name__ == "__main__":
    migrator = TranscriptMigrator()
    asyncio.run(migrator.migrate_all_transcripts())
```

### Phase 3: Update Search API (1-2 hours)

Update `search_lightweight.py` to use MongoDB:

```python
from motor.motor_asyncio import AsyncIOMotorClient
import os

class MongoSearchHandler:
    def __init__(self):
        self.client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
        self.db = self.client['podinsight']
        self.transcripts = self.db['transcripts']

        # Create text index for search
        self.transcripts.create_index([("full_text", "text")])

    async def search_transcripts(self, query: str, limit: int = 10):
        """Search transcripts using MongoDB full-text search"""

        # MongoDB text search
        results = await self.transcripts.find(
            {"$text": {"$search": query}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(limit).to_list(length=limit)

        # Format results with real excerpts
        formatted_results = []
        for doc in results:
            # Extract relevant excerpt around the match
            excerpt = self.extract_excerpt(doc['full_text'], query, 200)

            formatted_results.append({
                'episode_id': doc['episode_id'],
                'podcast_name': doc['podcast_name'],
                'episode_title': doc['episode_title'],
                'published_at': doc['published_at'],
                'similarity_score': doc['score'] / 10,  # Normalize score
                'excerpt': excerpt,  # REAL EXCERPT!
                'topics': doc.get('topics', [])
            })

        return formatted_results

    def extract_excerpt(self, text: str, query: str, max_words: int = 200):
        """Extract relevant excerpt from full text"""
        # Find query terms in text (case-insensitive)
        query_words = query.lower().split()
        text_lower = text.lower()

        # Find best matching position
        best_pos = 0
        for word in query_words:
            pos = text_lower.find(word)
            if pos > 0:
                best_pos = pos
                break

        # Extract excerpt around match
        words = text.split()
        word_pos = len(text[:best_pos].split())

        start = max(0, word_pos - max_words // 2)
        end = min(len(words), word_pos + max_words // 2)

        excerpt = ' '.join(words[start:end])

        # Add ellipsis if truncated
        if start > 0:
            excerpt = '...' + excerpt
        if end < len(words):
            excerpt = excerpt + '...'

        return excerpt
```

### Phase 4: Enhanced Vector Search (Optional - 1 hour)

MongoDB Atlas also supports vector search:

```python
# Create vector search index in MongoDB Atlas UI
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "embedding": {
        "dimensions": 1536,
        "similarity": "cosine",
        "type": "knnVector"
      }
    }
  }
}

# Search using vectors
async def vector_search(self, query_embedding: List[float], limit: int = 10):
    pipeline = [
        {
            "$search": {
                "index": "vector_index",
                "knn": {
                    "vector": query_embedding,
                    "path": "embedding",
                    "k": limit
                }
            }
        },
        {
            "$project": {
                "episode_id": 1,
                "podcast_name": 1,
                "excerpt": "$chunk_text",
                "score": {"$meta": "searchScore"}
            }
        }
    ]

    results = await self.transcripts.aggregate(pipeline).to_list(length=limit)
    return results
```

## Testing the New Architecture

1. **Test MongoDB Connection**
   ```python
   # Quick test script
   from pymongo import MongoClient
   client = MongoClient(MONGODB_URI)
   db = client['podinsight']
   print(f"Collections: {db.list_collection_names()}")
   print(f"Transcript count: {db.transcripts.count_documents({})}")
   ```

2. **Test Search Performance**
   ```bash
   # Before: Mock excerpts, 4% relevance
   # After: Real excerpts, 70%+ relevance
   curl -X POST https://podinsight-api.vercel.app/api/search \
     -H "Content-Type: application/json" \
     -d '{"query": "AI agents", "limit": 5}'
   ```

## Environment Variables to Add

```bash
# .env.local (API)
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/podinsight?retryWrites=true&w=majority

# Vercel Dashboard
# Add MONGODB_URI to environment variables
```

## Benefits of This Architecture

1. **Scalability**: MongoDB handles 100GB+ easily on your credit
2. **Performance**: Native full-text and vector search
3. **Flexibility**: Can store segments, embeddings, anything
4. **Cost**: FREE for 12+ months with your credits
5. **Simplicity**: Less complex than managing everything in Supabase

## Timeline

- **Today (2 hours)**: Set up MongoDB + migrate 100 episodes as test
- **Tomorrow (2 hours)**: Complete migration + update search API
- **Day 3 (1 hour)**: Test and optimize search relevance

Your advisor is 100% right - this solves your immediate problem AND sets you up for scale!
