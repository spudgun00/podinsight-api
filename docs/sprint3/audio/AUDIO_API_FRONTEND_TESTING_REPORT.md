# Audio API Frontend Testing Report

**Date:** June 30, 2025
**Tested By:** Frontend Team
**Purpose:** Comprehensive testing of audio functionality integration with dashboard

## Executive Summary

The frontend implementation is complete and working correctly. The audio functionality is failing due to backend API issues, not frontend problems.

## Testing Environment

- **Local Development:** http://localhost:3000
- **Node Version:** Latest
- **Browser:** Chrome with DevTools
- **API Endpoints:**
  - Search: https://podinsight-api.vercel.app/api/search
  - Audio: https://podinsight-api.vercel.app/api/v1/audio_clips/{episode_id}

## Test Results

### 1. Search API Integration ✅ PASS

**Test Query:** "AI valuations"

**Console Output:**
```javascript
[Search] First citation episode_id: 673b06c4-cf90-11ef-b9e1-0b761165641d
[Search] ID format check: {
  is_guid: true,
  is_objectid: false,
  length: 36,
  sample_id: "673b06c4-cf90-11ef-b9e1-0b761165641d"
}
```

**Findings:**
- Search API correctly returns episode IDs in GUID format
- IDs are valid UUIDs (8-4-4-4-12 format)
- Frontend correctly extracts and passes these IDs

### 2. Audio API Calls ❌ FAIL (Backend Issue)

**Test Requests Made:**
1. `/api/v1/audio_clips/673b06c4-cf90-11ef-b9e1-0b761165641d?start_time_ms=556789`
2. `/api/v1/audio_clips/9497d063-69c2-4701-9951-931c1599b170?start_time_ms=3114541`

**Response:** 500 Internal Server Error

**Error Message:**
```json
{
  "error": "Failed to fetch audio clip"
}
```

### 3. ID Format Analysis

**Initial Assumption:** Audio API expected MongoDB ObjectIds (24 hex characters)

**Discovery:** Audio API actually needs GUIDs to match S3 file paths

**Current Status:**
- Frontend sends: ✅ GUIDs (e.g., `673b06c4-cf90-11ef-b9e1-0b761165641d`)
- Backend expects: ✅ GUIDs
- Backend response: ❌ 500 errors

## Frontend Implementation Details

### 1. Audio Proxy Route (`/app/api/v1/audio_clips/[episode_id]/route.ts`)

**Updated Validation:**
```typescript
// Regex to validate a GUID format (8-4-4-4-12 hex pattern)
const guidRegex = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/
```

**Error Handling:**
- Validates GUID format before proxying
- Provides clear error messages for invalid formats
- Distinguishes between ObjectIds and GUIDs in error responses
- 10-second timeout to prevent hanging

### 2. Search Component (`search-command-bar-fixed.tsx`)

**Debug Logging Added:**
```typescript
console.log('[Search] First citation episode_id:', citations[0]?.episode_id)
console.log('[Search] ID format check:', {
  sample_id: citations[0]?.episode_id,
  is_objectid: /^[0-9a-fA-F]{24}$/.test(citations[0]?.episode_id || ''),
  is_guid: /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/.test(citations[0]?.episode_id || ''),
  length: citations[0]?.episode_id?.length
})
```

**Audio Integration:**
- Correctly passes `episode_id` and `start_seconds` to audio player
- Handles audio errors gracefully with user feedback

## MongoDB Structure Clarification

Based on investigation and user clarification:

**episode_metadata collection:**
- `_id`: MongoDB auto-generated ObjectId (NOT used for S3)
- `guid`: The actual episode GUID that matches S3 files

**transcript_chunks_768d collection:**
- `episode_id`: Contains the GUID (not ObjectId)

**Key Finding:** The MongoDB `_id` field has no relationship to S3 file paths. The system uses the `guid` field.

## Backend Issues Identified

From `AUDIO_API_BACKEND_ISSUES.md`:

1. **Lambda Function Issues:**
   - May not be deployed
   - May lack S3 permissions
   - FFmpeg layer might be missing

2. **Episode Data Issues:**
   - Episodes might not exist in S3
   - Path construction might be failing

## Recommendations for API Team

### 1. Immediate Actions

**Verify Lambda Deployment:**
```bash
aws lambda get-function --function-name audio-clip-generator
```

**Check Lambda Logs:**
```bash
aws logs tail /aws/lambda/audio-clip-generator --follow
```

**Test with Known Good Episode:**
```bash
curl 'https://podinsight-api.vercel.app/api/v1/audio_clips/022f8502-14c3-11f0-9b7c-bf77561f0071?start_time_ms=30000'
```

### 2. Debug the 500 Errors

The frontend is sending valid requests:
- Episode ID: Valid GUID format ✅
- start_time_ms: Present and valid ✅
- duration_ms: Defaults to 30000 ✅

The backend should:
1. Log the incoming request details
2. Log MongoDB query attempts
3. Log S3 path construction
4. Return specific error messages (not generic 500)

### 3. Expected Backend Flow

According to architecture docs:
1. Receive GUID in episode_id parameter
2. Query MongoDB (but architecture shows querying by ObjectId?)
3. Extract guid and feed_slug
4. Construct S3 path
5. Generate or retrieve audio clip
6. Return pre-signed URL

**Note:** There may be confusion about whether to query MongoDB by `_id` or by `guid`.

## Test Data for API Team

**Working Search Response:**
```json
{
  "answer": {
    "text": "AI valuations are experiencing significant volatility...",
    "citations": [
      {
        "episode_id": "673b06c4-cf90-11ef-b9e1-0b761165641d",
        "episode_title": "AI Market Analysis",
        "podcast_name": "All-In",
        "timestamp": "09:16",
        "start_seconds": 556.789
      }
    ]
  }
}
```

**Failed Audio Request:**
```
GET /api/v1/audio_clips/673b06c4-cf90-11ef-b9e1-0b761165641d?start_time_ms=556789
Response: 500 Internal Server Error
Body: {"error": "Failed to fetch audio clip"}
```

## Frontend Status

✅ **Ready for Production:**
- ID validation implemented
- Error handling in place
- User feedback for failures
- Debug logging available

⏳ **Waiting on Backend:**
- Audio clip generation endpoint
- Proper error messages
- MongoDB query clarification

## Contact

Frontend implementation is complete. Audio functionality will work as soon as backend issues are resolved.
