# Transcript Integration Plan for Real Search

## The Problem
- Current search returns mock excerpts, not real transcript content
- Low similarity scores (4%) because we're matching whole episodes
- Users can't see WHY something matched their query

## Proposed Solution: S3 + Smart Caching

### Architecture
1. **Keep transcripts in S3** (already there, already paid for)
2. **Fetch on-demand** when search results need excerpts
3. **Cache popular transcripts** in memory/Redis
4. **Extract relevant segments** around the matching content

### Implementation Steps

#### Step 1: Update Search Response
```python
# In search_lightweight.py, after getting search results:
async def fetch_transcript_excerpt(episode_id: str, s3_prefix: str) -> str:
    """Fetch real transcript from S3 and extract relevant excerpt"""
    # 1. Get transcript path from episode
    # 2. Fetch from S3 (already have boto3 setup)
    # 3. Find most relevant segment
    # 4. Return 200-word excerpt around match
```

#### Step 2: S3 Transcript Fetcher
```python
class TranscriptFetcher:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.cache = {}  # Simple in-memory cache

    async def get_transcript(self, s3_path: str) -> dict:
        # Check cache first
        if s3_path in self.cache:
            return self.cache[s3_path]

        # Fetch from S3
        response = self.s3_client.get_object(
            Bucket='pod-insights-stage',
            Key=s3_path
        )

        transcript = json.loads(response['Body'].read())

        # Cache if under 1MB
        if len(response['Body']) < 1_000_000:
            self.cache[s3_path] = transcript

        return transcript
```

#### Step 3: Excerpt Extraction
```python
def extract_relevant_excerpt(transcript: dict, query: str, max_words: int = 200) -> str:
    """Extract the most relevant excerpt from transcript"""
    # Combine all segments
    full_text = " ".join([seg["text"] for seg in transcript["segments"]])

    # Find best matching section (simple keyword matching for now)
    # In future: use embeddings for semantic matching

    # Return excerpt with context
    return excerpt
```

### Benefits
- **No database upgrade needed** - Stay on free tier
- **Real excerpts** - Users see actual transcript content
- **Better relevance** - Can show the exact matching section
- **Scalable** - Can add Redis cache later if needed

### Quick Test Implementation

For immediate improvement, even without the full implementation:

```python
# In search_lightweight.py, replace the mock excerpt with:
excerpt = (
    f"This episode discusses {topics_str} in depth. "
    f"The conversation covers how {topics_str.lower()} "
    f"are transforming the technology landscape, with insights from "
    f"industry leaders on implementation strategies and market trends. "
    f"Published on {result['published_at'][:10]}."
)
```

This at least gives more context than the current placeholder.

### Cost Analysis
- **Current**: ~$5/month S3 storage
- **With this approach**: ~$5-10/month (S3 storage + minimal transfer)
- **With database storage**: $25+/month (Supabase Pro required)

### Timeline
- **2 hours**: Basic S3 fetching for search results
- **4 hours**: Full implementation with caching
- **1 day**: Add segment-level search with better relevance

## Decision Point

Do you want to:
1. **Keep current approach** (fast, cheap, but poor search quality)
2. **Implement S3 fetching** (best of both worlds - real data, low cost)
3. **Store in database** (simplest but requires immediate $25/month upgrade)

The S3 approach gives you real excerpts without breaking the budget!
