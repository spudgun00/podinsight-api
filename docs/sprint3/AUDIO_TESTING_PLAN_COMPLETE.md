# PodInsight Audio Clip Service - Comprehensive Testing Plan

**Version**: 1.0
**Date**: December 30, 2024
**Authors**: PodInsightHQ Engineering Team (with AI assistance)

---

## Executive Summary

This document provides a complete testing plan for the Sprint 3 audio clip generation service. It covers API testing, integration testing, performance validation, dashboard integration requirements, and production monitoring setup.

## System Under Test

### Infrastructure
- **API Endpoint**: `/api/v1/audio_clips/{episode_id}`
- **Vercel Base URL**: `https://podinsight-api.vercel.app`
- **Lambda Function URL**: `https://zxhnx2lugw3pprozjzvn3275ee0ypqpw.lambda-url.eu-west-2.on.aws/`
- **Lambda API Key**: `<AUDIO_LAMBDA_API_KEY>` (stored in environment variables)
- **AWS Region**: `eu-west-2`

### Storage
- **Source Bucket**: `pod-insights-raw`
- **Clips Bucket**: `pod-insights-clips`
- **Pre-signed URL Lifetime**: 24 hours (86400 seconds)

### Database Collections
- **episode_metadata**: Contains episode information
- **transcript_chunks_768d**: Contains transcript chunks with timing

---

## Part 1: Test Data Preparation

### 1.1 MongoDB Schema Reference

**episode_metadata collection:**
```javascript
{
  "_id": ObjectId("..."),          // This is the episode_id used in API
  "guid": "0e983347-7815-4b62-87a6-84d988a772b7",
  "episode_title": "AI Research Breakthroughs",
  "podcast_title": "a16z Podcast",
  "pubDate": ISODate("2024-03-15"),
  "audio_duration_sec": 3600      // Duration in seconds
}
```

**transcript_chunks_768d collection:**
```javascript
{
  "episode_id": "0e983347-7815-4b62-87a6-84d988a772b7", // Maps to guid
  "feed_slug": "a16z-podcast",
  "chunk_index": 42,
  "start_time": 1230.5,           // Start time in seconds
  "end_time": 1260.5,             // End time in seconds
  "text": "The breakthrough in AI research..."
}
```

### 1.2 Finding Test Episodes

**Find a valid long-duration episode:**
```javascript
// Connect to MongoDB and run:
db.episode_metadata.findOne(
  { "audio_duration_sec": { $gt: 120 } }, // Episode > 2 minutes
  { "_id": 1, "guid": 1, "episode_title": 1, "audio_duration_sec": 1 }
)
```

**Find episodes with transcripts:**
```javascript
// First find episode with transcript chunks
db.transcript_chunks_768d.aggregate([
  { $group: { _id: "$episode_id", count: { $sum: 1 } } },
  { $sort: { count: -1 } },
  { $limit: 5 }
])

// Then lookup the episode metadata
db.episode_metadata.findOne({ "guid": "<episode_id_from_above>" })
```

**Test Data Examples:**
- Valid episode_id: `<REPLACE_WITH_ACTUAL_ID>` (24 character hex string)
- Invalid episode_id: `ffffffffffffffffffffffff`

---

## Part 2: API Functional Testing

### Test Case 2.1: Standard Request (Happy Path)

**Objective**: Verify standard 30-second clip generation

**Request**:
```bash
EPISODE_ID="<YOUR_TEST_EPISODE_ID>"
START_TIME_MS=30000  # 30 seconds

curl -X GET "https://podinsight-api.vercel.app/api/v1/audio_clips/${EPISODE_ID}?start_time_ms=${START_TIME_MS}" \
  -H "Accept: application/json"
```

**Expected Response (200 OK)**:
```json
{
  "clip_url": "https://pod-insights-clips.s3.eu-west-2.amazonaws.com/...",
  "expires_at": "2024-12-31T12:00:00Z",
  "cache_hit": false,
  "episode_id": "<YOUR_TEST_EPISODE_ID>",
  "start_time_ms": 30000,
  "duration_ms": 30000,
  "generation_time_ms": 2500
}
```

**Validation Steps**:
1. Verify HTTP status is 200
2. Download and verify the audio clip:
   ```bash
   curl -o test_clip.mp3 "<clip_url_from_response>"
   ffprobe test_clip.mp3  # Should show ~30 seconds duration
   ```
3. Play the clip to verify audio quality

### Test Case 2.2: Custom Duration Request

**Request**:
```bash
curl -X GET "https://podinsight-api.vercel.app/api/v1/audio_clips/${EPISODE_ID}?start_time_ms=60000&duration_ms=15000"
```

**Expected**: 15-second clip starting at 1 minute

### Test Case 2.3: Cache Hit Performance

**Procedure**:
1. Make the same request as 2.1
2. Note the `generation_time_ms` (should be <200ms)
3. Verify `cache_hit: true` in response

---

## Part 3: Error Handling Tests

### Test Case 3.1: Invalid Episode ID

**Request**:
```bash
curl -X GET "https://podinsight-api.vercel.app/api/v1/audio_clips/invalid-id?start_time_ms=30000"
```

**Expected**: 400 Bad Request - "Invalid episode ID format"

### Test Case 3.2: Non-existent Episode

**Request**:
```bash
curl -X GET "https://podinsight-api.vercel.app/api/v1/audio_clips/ffffffffffffffffffffffff?start_time_ms=30000"
```

**Expected**: 404 Not Found - "Episode not found"

### Test Case 3.3: Invalid Parameters

**Negative start time**:
```bash
curl -X GET "https://podinsight-api.vercel.app/api/v1/audio_clips/${EPISODE_ID}?start_time_ms=-1000"
```

**Expected**: 400 Bad Request - "Start time must be non-negative"

**Invalid duration**:
```bash
curl -X GET "https://podinsight-api.vercel.app/api/v1/audio_clips/${EPISODE_ID}?start_time_ms=0&duration_ms=70000"
```

**Expected**: 400 Bad Request - "Duration must be between 1 and 60000 milliseconds"

### Test Case 3.4: Episode Without Transcript

**Find an episode without transcript chunks**:
```javascript
// Find episodes not in transcript_chunks
db.episode_metadata.aggregate([
  {
    $lookup: {
      from: "transcript_chunks_768d",
      localField: "guid",
      foreignField: "episode_id",
      as: "chunks"
    }
  },
  { $match: { chunks: { $size: 0 } } },
  { $limit: 1 }
])
```

**Expected**: 422 Unprocessable Entity - "Episode does not have transcript data available"

---

## Part 4: Performance Testing

### 4.1 Cold Start Measurement

**Wait 15+ minutes, then**:
```bash
time curl -o /dev/null -s \
  "https://podinsight-api.vercel.app/api/v1/audio_clips/${EPISODE_ID}?start_time_ms=90000"
```

**Expected**: 2-4 seconds total time

### 4.2 Warm Start Measurement

**Immediately repeat the above command**

**Expected**: <1 second total time

### 4.3 Load Testing Script

**Using Apache Bench**:
```bash
# Test cache hits (100 requests, 10 concurrent)
ab -n 100 -c 10 \
  "https://podinsight-api.vercel.app/api/v1/audio_clips/${EPISODE_ID}?start_time_ms=30000"
```

**Success Criteria**:
- P95 Latency (Cache Miss): <3000ms
- P95 Latency (Cache Hit): <300ms
- Error rate: <1%

---

## Part 5: Dashboard Integration Guide

### 5.1 API Contract for Frontend

**Request Format**:
```javascript
// Using fetch API
const response = await fetch(
  `https://podinsight-api.vercel.app/api/v1/audio_clips/${episodeId}?start_time_ms=${startTimeMs}`,
  {
    method: 'GET',
    headers: {
      'Accept': 'application/json'
    }
  }
);

const data = await response.json();
// data.clip_url contains the audio URL
```

### 5.2 Audio Player Implementation

**Basic HTML5 Audio Player**:
```html
<audio controls>
  <source src="${clip_url}" type="audio/mpeg">
  Your browser does not support the audio element.
</audio>
```

**React Component Example**:
```jsx
function AudioClipPlayer({ episodeId, startTimeMs }) {
  const [clipUrl, setClipUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchClip = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/v1/audio_clips/${episodeId}?start_time_ms=${startTimeMs}`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setClipUrl(data.clip_url);
    } catch (err) {
      setError(err.message);
      // Implement retry logic here
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClip();
  }, [episodeId, startTimeMs]);

  if (loading) return <div>Loading audio...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!clipUrl) return null;

  return (
    <audio
      controls
      src={clipUrl}
      onError={() => {
        // Pre-signed URL expired, refetch
        fetchClip();
      }}
    />
  );
}
```

### 5.3 CORS Configuration

**Current Setting**: Allow all origins (`*`)

**Production Configuration** (to be updated):
```json
{
  "AllowOrigins": ["https://podinsighthq.com", "http://localhost:3000"],
  "AllowMethods": ["GET", "OPTIONS"],
  "AllowHeaders": ["Content-Type", "Accept"]
}
```

### 5.4 Error Handling Guide

| Status Code | Error Type | Frontend Action |
|-------------|------------|-----------------|
| 400 | Invalid parameters | Show user error message |
| 404 | Episode not found | Hide audio player |
| 422 | No transcript available | Show "Audio not available" |
| 500 | Server error | Retry with exponential backoff |
| 504 | Timeout | Retry once after 2 seconds |

### 5.5 Integration with Search Results

**Search Result Enhancement**:
```javascript
// When displaying search results
searchResults.forEach(result => {
  // Each result should have:
  // - episode_id (MongoDB ObjectId)
  // - start_time (in seconds from chunk)

  result.audioClipParams = {
    episodeId: result.episode_id,
    startTimeMs: Math.floor(result.start_time * 1000)
  };
});
```

---

## Part 6: End-to-End Testing Scenarios

### Scenario 1: Search to Audio Playback

1. **User searches** for "AI valuations"
2. **Search API returns** results with episode_id and start_time
3. **Dashboard displays** results with audio player buttons
4. **User clicks** play button
5. **Dashboard calls** `/api/v1/audio_clips/{episode_id}?start_time_ms={time}`
6. **API returns** pre-signed URL
7. **Audio plays** in browser

### Scenario 2: Expired URL Handling

1. User leaves page open for 24+ hours
2. User attempts to play audio
3. S3 returns 403 Forbidden
4. Frontend catches error
5. Frontend re-requests clip URL
6. New URL loads and plays

### Scenario 3: Multiple Concurrent Requests

1. User rapidly clicks multiple audio clips
2. Dashboard makes parallel API requests
3. All clips load without errors
4. No rate limiting issues

---

## Part 7: Production Monitoring Setup

### 7.1 CloudWatch Metrics

**Lambda Metrics**:
- Invocations
- Errors
- Duration (P50, P90, P99)
- Concurrent Executions
- Throttles

**Custom Metrics** (to implement):
```python
# In Lambda handler
cloudwatch.put_metric_data(
    Namespace='PodInsight/AudioClips',
    MetricData=[
        {
            'MetricName': 'CacheHit' if cache_hit else 'CacheMiss',
            'Value': 1,
            'Unit': 'Count'
        },
        {
            'MetricName': 'GenerationTime',
            'Value': generation_time_ms,
            'Unit': 'Milliseconds'
        }
    ]
)
```

### 7.2 CloudWatch Alarms

| Alarm Name | Condition | Action |
|------------|-----------|--------|
| HighErrorRate | Errors > 5% over 5 min | PagerDuty alert |
| HighLatency | P99 > 5000ms for 10 min | Email notification |
| LowCacheHitRate | Hit rate < 50% over 1 hour | Review S3 lifecycle |
| HighConcurrency | Concurrent > 900 | Scale Lambda limits |

### 7.3 Monitoring Dashboard

Create CloudWatch dashboard with:
1. Request rate graph
2. Error rate percentage
3. Latency percentiles (P50, P90, P99)
4. Cache hit ratio
5. S3 storage usage
6. Lambda cold starts

### 7.4 Log Queries

**Find slow requests**:
```
fields @timestamp, episode_id, generation_time_ms
| filter generation_time_ms > 3000
| sort @timestamp desc
| limit 20
```

**Track cache effectiveness**:
```
fields @timestamp, cache_hit
| stats count() by cache_hit
```

---

## Part 8: Security Audit Checklist

- [ ] Lambda API key is not exposed in client code
- [ ] Pre-signed URLs use HTTPS only
- [ ] S3 bucket has proper access policies
- [ ] Lambda has minimum required permissions
- [ ] No sensitive data in CloudWatch logs
- [ ] CORS restricted to production domains
- [ ] Input validation prevents injection attacks
- [ ] Rate limiting implemented (future)

---

## Part 9: Handoff Checklist for Dashboard Team

### Technical Requirements
- [ ] **Episode ID Format**: MongoDB ObjectId (24 character hex string)
- [ ] **Start Time**: In milliseconds (multiply seconds by 1000)
- [ ] **Duration**: Optional, defaults to 30000ms (30 seconds)
- [ ] **Max Duration**: 60000ms (60 seconds)

### API Details
- [ ] **Endpoint**: `GET /api/v1/audio_clips/{episode_id}`
- [ ] **Base URL**: `https://podinsight-api.vercel.app`
- [ ] **Authentication**: None required (handled by API Gateway)
- [ ] **Rate Limits**: Currently none (implement client-side throttling)

### Implementation Notes
- [ ] Cache clip URLs for max 23 hours (leave 1 hour buffer)
- [ ] Implement exponential backoff for retries
- [ ] Show loading state during clip generation
- [ ] Handle all error states gracefully
- [ ] Test with episodes both with and without transcripts

### Test Data
```javascript
// Valid test episode (replace with actual from your DB)
const testEpisode = {
  episodeId: "<YOUR_TEST_EPISODE_ID>",
  title: "AI Research Breakthroughs",
  validStartTimes: [30000, 60000, 90000, 120000]
};
```

---

## Part 10: Performance Benchmarks

### Expected Performance Metrics

| Scenario | Target | Acceptable | Critical |
|----------|--------|------------|----------|
| Cache Hit Latency | <200ms | <500ms | >1000ms |
| Cache Miss Latency | <2500ms | <4000ms | >6000ms |
| Cold Start | <3000ms | <5000ms | >8000ms |
| Error Rate | <0.1% | <1% | >5% |
| Availability | 99.9% | 99.5% | <99% |

### Load Test Results (to be filled)

```
Date: ___________
Tool: Apache Bench / k6
Concurrent Users: 10
Total Requests: 1000
Results:
- Requests/sec: _____
- P50 Latency: _____ms
- P90 Latency: _____ms
- P99 Latency: _____ms
- Error Rate: _____%
```

---

## Appendix A: Troubleshooting Guide

### Common Issues and Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Episode not found | 404 error | Verify episode exists in MongoDB |
| No feed_slug | 500 error | Check transcript_chunks for episode |
| Lambda timeout | 504 error | Check source audio file size |
| CORS error | Browser console error | Update Lambda CORS config |
| Expired URL | 403 from S3 | Implement retry in frontend |

### Debug Commands

**Check if episode exists**:
```javascript
db.episode_metadata.findOne({ "_id": ObjectId("...") })
```

**Find feed_slug**:
```javascript
db.transcript_chunks_768d.findOne(
  { "episode_id": "<guid>" },
  { "feed_slug": 1 }
)
```

**Verify S3 source file**:
```bash
aws s3 ls s3://pod-insights-raw/<feed_slug>/<guid>/audio/
```

---

## Appendix B: Future Enhancements

1. **Reduce Pre-signed URL TTL**: From 24 hours to 15 minutes for better security
2. **Add Rate Limiting**: Implement per-IP or per-user limits
3. **Support Multiple Formats**: Add WebM/Opus for smaller files
4. **Implement Warmup**: Reduce cold starts with scheduled pings
5. **Add Request Signing**: Additional security layer
6. **Cache MongoDB Lookups**: Redis layer for episode metadata

---

**Document Version**: 1.0
**Last Updated**: December 30, 2024
**Next Review**: January 15, 2025

**Sign-off**:
- [ ] Backend Team
- [ ] Frontend Team
- [ ] DevOps Team
- [ ] QA Team
