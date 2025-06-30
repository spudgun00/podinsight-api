# Audio Clip Lambda Implementation - Clean Start

## 🧹 CLEANUP FIRST: Remove Failed Implementation

### What Went Wrong (Original Prompt Issues)

The original prompt was too vague:
```
"Add API endpoint for clip requests"  # WHERE? This led to modifying topic_velocity.py
"Create Lambda function"               # WHICH REGION? Created in wrong region
"Repository: podinsight-api"          # NO FILE SEPARATION specified
```

Result: Audio code mixed into topic_velocity.py, Lambda in wrong region, total mess.


## ⚠️ CRITICAL: File Separation

**DO NOT MODIFY**: `api/topic_velocity.py` - This is for Supabase charts, completely unrelated to audio clips!

**CREATE NEW FILE**: `api/audio_clips.py` - This will handle ONLY audio clip generation

---

## Claude Code Prompt for Audio Clip Lambda

```
I need to implement an optimized Lambda function for on-demand audio clip generation.

CRITICAL CONTEXT:
- Previous attempt incorrectly modified topic_velocity.py (Supabase feature)
- This audio feature is COMPLETELY SEPARATE
- Create NEW files, don't modify existing unrelated endpoints

PROJECT CONTEXT:
- Sprint 3, Phase 1A.2 - Audio clip generation ONLY
- Implementing "Option 3" (byte-range optimization)
- This is a standalone feature for the command bar search results

FILE STRUCTURE:
Create these NEW files:
1. api/audio_clips.py - FastAPI endpoint for audio clips
2. lambda_functions/audio_clip_generator/ - Lambda function code
3. tests/test_audio_clips.py - Tests for the new endpoint

DO NOT TOUCH:
- api/topic_velocity.py (Supabase charts)
- Any MongoDB search endpoints
- Any existing dashboard features

AWS CONFIGURATION:
- Region: eu-west-2 (London)
- Source bucket: pod-insights-raw
- Clips bucket: pod-insights-clips
- Lambda: Public (not in VPC)
- API: Lambda Function URL (called from Vercel)
- IAM User: dev-podinsights

S3 SOURCE STRUCTURE:
s3://pod-insights-raw/{feed_slug}/{guid}/audio/{filename}.mp3

CRITICAL: The audio filename includes first 8 chars of GUID:
Example:
s3://pod-insights-raw/a16z-podcast/0e983347-7815-4b62-87a6-84d988a772b7/audio/a16z-podcast-2025-06-09-chris-dixon-stablecoins-startups-and-the-crypto-stack_0e983347_audio.mp3

Note: "0e983347" in filename is first 8 chars of GUID "0e983347-7815-4b62-87a6-84d988a772b7"

MONGODB DATA STRUCTURE:
- Collection: transcript_chunks_768d
  - Field: episode_id contains the GUID (e.g., "1216c2e7-42b8-42ca-92d7-bad784f80af2")
  - Field: feed_slug contains podcast name (e.g., "a16z-podcast")
  - Field: start_time and end_time for chunk timing

- Collection: episode_metadata
  - Field: guid contains the GUID
  - Field: podcast_title contains the podcast name

IMPORTANT: Frontend sends episode_id from transcript_chunks, which IS the GUID.

REQUIREMENTS:

1. NEW API Endpoint (api/audio_clips.py):
   ```python
   from fastapi import APIRouter, HTTPException, Query
   import httpx
   import os

   router = APIRouter(prefix="/api/v1/audio_clips", tags=["audio"])

   LAMBDA_FUNCTION_URL = os.environ.get("AUDIO_LAMBDA_URL")

   @router.get("/{episode_id}")
   async def get_audio_clip(
       episode_id: str,
       start_time_ms: int = Query(...),
       duration_ms: int = Query(30000)
   ):
       # Parse episode_id to extract feed_slug and guid
       # Call Lambda Function URL
       # Return clip URL
   ```

2. Lambda Function (audio-clip-generator):
   - Python 3.11 runtime
   - 512MB memory
   - 60s timeout
   - Environment variables:
     - SOURCE_BUCKET=pod-insights-raw
     - CLIPS_BUCKET=pod-insights-clips
   - Function URL enabled with CORS

3. Optimized FFmpeg Command:
   ```bash
   # Key: -ss BEFORE -i for byte-range seeking
   ffmpeg -ss {start_seconds} -i {s3_signed_url} -t 30 -acodec copy output.mp3
   ```

4. Lambda Handler Logic:
   - Input: feed_slug, guid, start_time_ms
   - Check cache: clips/{feed_slug}/{guid}/{start_ms}-{end_ms}.mp3
   - If missing: generate with byte-range FFmpeg
   - Return 24hr pre-signed URL

5. Main App Integration (main.py or app.py):
   ```python
   from api import audio_clips

   # Add to your FastAPI app
   app.include_router(audio_clips.router)
   ```

6. Environment Variables for Vercel:
   - AUDIO_LAMBDA_URL=https://[your-lambda-url].lambda-url.eu-west-2.on.aws/

DELIVERABLES:
1. api/audio_clips.py - NEW endpoint file
2. lambda_functions/audio_clip_generator/handler.py
3. lambda_functions/audio_clip_generator/requirements.txt
4. lambda_functions/audio_clip_generator/deploy.sh
5. tests/test_audio_clips.py
6. IAM policy JSON for dev-podinsights
7. Updated main.py to include new router

IMPORTANT NOTES:
- This is a STANDALONE feature for audio clips
- Has NOTHING to do with topic_velocity or Supabase
- Keep all audio logic in dedicated files
- Don't mix MongoDB search with audio generation
- Test Lambda independently before API integration

ERROR TO AVOID:
Do NOT add audio code to:
- topic_velocity.py (Supabase charts)
- search endpoints (MongoDB)
- Any existing feature files

Please implement this as a clean, separate feature with proper file organization.
```

## Testing Strategy

### 1. Test Lambda Independently First
```bash
# Deploy Lambda
cd lambda_functions/audio_clip_generator
./deploy.sh

# Test via AWS Console or CLI
aws lambda invoke --function-url [URL] --payload '{"feed_slug":"a16z-podcast","guid":"0e983347-7815-4b62-87a6-84d988a772b7","start_time_ms":30000}'
```

### 2. Test API Endpoint Separately
```bash
# Test new endpoint
curl http://localhost:8000/api/v1/audio_clips/a16z-podcast:0e983347-7815-4b62-87a6-84d988a772b7?start_time_ms=30000
```

### 3. Integration with Frontend
- Frontend calls ONLY `/api/v1/audio_clips/{episode_id}`
- This endpoint ONLY handles audio clips
- Search results come from different endpoint

## File Organization Summary

```
podinsight-api/
├── api/
│   ├── topic_velocity.py      # DON'T TOUCH - Supabase charts
│   ├── search_lightweight.py   # DON'T TOUCH - MongoDB search
│   └── audio_clips.py         # NEW FILE - Audio clips ONLY
├── lambda_functions/
│   └── audio_clip_generator/  # NEW FOLDER - Lambda code
├── tests/
│   └── test_audio_clips.py    # NEW FILE - Audio tests
└── main.py                    # UPDATE - Add audio router
```

## Key Success Criteria

1. ✅ Audio endpoint is completely separate from other features
2. ✅ No modifications to topic_velocity.py
3. ✅ Lambda generates clips in <1s using byte-range
4. ✅ Clean separation of concerns
5. ✅ Easy to test and deploy independently

---

## Cleanup Decision Tree

### Option A: Clean Everything Now (Recommended)
- **When**: If the previous implementation is completely broken
- **Benefit**: Fresh start, no confusion
- **Process**: Follow cleanup steps above before starting

### Option B: Keep for Reference
- **When**: If you want to reference previous work
- **How**: Rename old Lambda to `audio-clip-generator-old`
- **Risk**: Might cause confusion or accidental usage

### Option C: Incremental Migration
- **When**: If some parts are working
- **How**: Build new solution alongside, migrate, then cleanup
- **Risk**: More complex, higher chance of mixing concerns

**Recommendation**: Since the previous attempt mixed concerns badly, do a full cleanup first (Option A). Document any useful learnings, then start fresh.
