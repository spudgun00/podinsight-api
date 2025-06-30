# Dashboard Audio Integration - Quick Reference Guide

## 🚀 Quick Start

### API Endpoint
```
GET https://podinsight-api.vercel.app/api/v1/audio_clips/{episode_id}
```

### Parameters
- `episode_id` (path): MongoDB ObjectId from search results
- `start_time_ms` (query): Start time in milliseconds
- `duration_ms` (query, optional): Duration in milliseconds (default: 30000)

### Example Request
```javascript
const response = await fetch(
  'https://podinsight-api.vercel.app/api/v1/audio_clips/685ba776e4f9ec2f0756267a?start_time_ms=30000'
);
const data = await response.json();
// data.clip_url contains the audio URL
```

### Example Response
```json
{
  "clip_url": "https://pod-insights-clips.s3.amazonaws.com/unchained/022f8502-14c3-11f0-9b7c-bf77561f0071/30000-60000.mp3?X-Amz-Algorithm=...",
  "expires_at": "",
  "cache_hit": true,
  "episode_id": "685ba776e4f9ec2f0756267a",
  "start_time_ms": 30000,
  "duration_ms": 30000,
  "generation_time_ms": 156
}
```

---

## 💡 Key Implementation Points

### 1. Converting Search Results to Audio Requests

```javascript
// Search result contains:
{
  "_id": "507f1f77bcf86cd799439011",        // episode_id
  "start_time": 123.5,                      // in seconds
  "end_time": 153.5,
  "text": "The search result text...",
  "episode_metadata": {
    "episode_title": "AI Breakthroughs",
    "podcast_title": "a16z Podcast"
  }
}

// Convert to audio request:
const episodeId = result._id;
const startTimeMs = Math.floor(result.start_time * 1000);
```

### 2. React Component Example

```jsx
import React, { useState, useEffect } from 'react';

function AudioClipPlayer({ episodeId, startTimeMs, episodeTitle }) {
  const [clipUrl, setClipUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAudioClip = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/v1/audio_clips/${episodeId}?start_time_ms=${startTimeMs}`
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setClipUrl(data.clip_url);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (episodeId && startTimeMs !== undefined) {
      fetchAudioClip();
    }
  }, [episodeId, startTimeMs]);

  const handleAudioError = () => {
    // Pre-signed URL might have expired, refetch
    console.log('Audio playback error, refetching...');
    fetchAudioClip();
  };

  if (loading) {
    return <div className="audio-loading">Generating audio clip...</div>;
  }

  if (error) {
    return (
      <div className="audio-error">
        <p>Error loading audio: {error}</p>
        <button onClick={fetchAudioClip}>Retry</button>
      </div>
    );
  }

  if (!clipUrl) {
    return null;
  }

  return (
    <div className="audio-player">
      <h4>{episodeTitle}</h4>
      <audio
        controls
        src={clipUrl}
        onError={handleAudioError}
      >
        Your browser does not support audio playback.
      </audio>
      <p className="audio-info">30-second clip</p>
    </div>
  );
}
```

### 3. Error Handling

```javascript
// Handle different error scenarios
switch (response.status) {
  case 400:
    // Invalid parameters
    showError('Invalid audio clip parameters');
    break;
  case 404:
    // Episode not found
    showError('Episode not found');
    break;
  case 422:
    // No transcript available
    showError('Audio not available for this episode');
    break;
  case 500:
  case 504:
    // Server error or timeout - retry
    setTimeout(() => fetchAudioClip(), 2000);
    break;
}
```

---

## 🎯 Testing Your Integration

### Working Test Episode
```javascript
// This episode has been verified to work:
const testEpisodeId = "685ba776e4f9ec2f0756267a";  // pragma: allowlist secret
// Episode: Unchained podcast
// GUID: 022f8502-14c3-11f0-9b7c-bf77561f0071
// Duration: ~73 minutes
```

### Step 1: Test the API Directly
```bash
# Working test command:
curl "https://podinsight-api.vercel.app/api/v1/audio_clips/685ba776e4f9ec2f0756267a?start_time_ms=30000"
```

### Step 2: Find More Test Episodes
```javascript
// MongoDB query to find episodes with transcripts:
db.episode_metadata.aggregate([
  {
    $lookup: {
      from: "transcript_chunks_768d",
      localField: "guid",
      foreignField: "episode_id",
      as: "chunks"
    }
  },
  { $match: { chunks: { $ne: [] } } },
  { $limit: 5 },
  { $project: { _id: 1, podcast_title: 1, guid: 1 } }
])
```

### Step 3: Test in Your Component
```jsx
// Test component with verified episode
<AudioClipPlayer
  episodeId="685ba776e4f9ec2f0756267a"  // pragma: allowlist secret
  startTimeMs={30000}
  episodeTitle="Unchained Episode"
/>
```

---

## ⚠️ Important Notes

1. **Pre-signed URLs expire after 24 hours**
   - Don't cache URLs longer than 23 hours
   - Implement retry logic for expired URLs

2. **No authentication required**
   - The API handles authentication internally
   - Just make direct GET requests

3. **Rate limiting**
   - Currently no rate limits
   - Implement client-side throttling if making many requests

4. **Episode availability**
   - Not all episodes have audio clips available
   - Handle 422 errors gracefully

5. **Performance expectations**
   - Cache hits: <200ms
   - New clips: 2-3 seconds
   - Show loading state during generation

---

## 🐛 Troubleshooting

### "Episode not found" (404)
- Verify the episode_id is a valid MongoDB ObjectId
- Check that the episode exists in the database
- Ensure the episode has a `guid` field

### "Episode does not have transcript data" (422)
- This episode has no transcript chunks
- Audio clips require transcript timing data
- Check `transcript_chunks_768d` collection for episode_id matching the guid

### "Forbidden" (403) or "Audio generation failed"
- This is usually a Lambda permission issue
- Ensure Lambda Function URL has public invoke permission:
```bash
aws lambda add-permission \
  --function-name audio-clip-generator-optimized \
  --region eu-west-2 \
  --statement-id FunctionURLAllowPublicAccess \
  --action lambda:InvokeFunctionUrl \
  --principal '*' \
  --function-url-auth-type NONE
```

### Audio won't play
- Check browser console for CORS errors
- Verify the pre-signed URL hasn't expired (24hr expiry)
- Try refetching the clip URL
- Ensure S3 audio file exists at expected path

### Slow response times
- First request to an episode takes 2-3 seconds (cache miss)
- Subsequent requests should be <200ms (cache hit)
- Check if Lambda is cold starting
- Monitor CloudWatch logs for errors

---

## 📞 Support

For issues or questions:
1. Check the full testing plan: `AUDIO_TESTING_PLAN_COMPLETE.md`
2. Review CloudWatch logs for errors
3. Contact the backend team with:
   - Episode ID
   - Error message
   - Time of request

---

## 📊 MongoDB Data Structure

### Collections Used:
1. **episode_metadata**
   - `_id`: ObjectId (used as episode_id in API)
   - `guid`: String (unique episode identifier)
   - `podcast_title`: String

2. **transcript_chunks_768d**
   - `episode_id`: String (contains the guid from episode_metadata)
   - `feed_slug`: String (podcast identifier for S3 path)
   - `start_time`: Number (seconds)
   - `end_time`: Number (seconds)

### Data Flow:
```
Frontend episode_id → episode_metadata._id → guid → transcript_chunks_768d.episode_id → feed_slug
```

---

**Last Updated**: June 30, 2025
**API Version**: 1.0
**Test Episode**: 685ba776e4f9ec2f0756267a
