# Sprint 3 Architecture Updates

## Purpose
Document all architectural changes and design decisions made during Sprint 3.

---

## Phase 1A: Audio Clip Generation Architecture

### New Components

#### 1. Audio Clip Lambda Function
**Purpose**: Generate 30-second audio clips on demand
**Technology**: Python + FFmpeg Lambda Layer
**Triggers**: API Gateway HTTP request
**Configuration**:
- Memory: 512MB
- Timeout: 300 seconds (5 minutes)
- Environment Variables:
  - `S3_SOURCE_BUCKET`: pod-insights-raw
  - `S3_CLIPS_BUCKET`: pod-insights-clips
  - `MONGODB_URI`: Connection string

#### 2. S3 Bucket Structure
**New Bucket**: `pod-insights-clips`
```
pod-insights-clips/
└── audio_clips/
    └── {episode_id}/
        └── {chunk_index}.mp3
```

**Bucket Policies**:
- Public read access for generated clips
- CloudFront distribution for CDN
- Lifecycle policy: Archive after 90 days

#### 3. API Endpoint
**Path**: `/api/generate-audio-clip`
**Method**: POST
**Request Body**:
```json
{
  "episode_id": "guid-string",
  "chunk_index": 123
}
```
**Response**:
```json
{
  "audio_url": "https://clips.podinsighthq.com/audio_clips/{episode_id}/{chunk_index}.mp3",
  "duration": 30,
  "cached": false
}
```

### Database Schema Updates

#### MongoDB - New Collection: `audio_clips`
```javascript
{
  _id: ObjectId(),
  episode_id: "guid-string",
  chunk_index: 123,
  s3_url: "s3://pod-insights-clips/audio_clips/{episode_id}/{chunk_index}.mp3",
  public_url: "https://clips.podinsighthq.com/...",
  duration_seconds: 30,
  start_time: 145.5,
  end_time: 175.5,
  generated_at: ISODate(),
  file_size_bytes: 480000,
  processing_time_ms: 2340
}
```

### Integration Points

#### 1. Search API Enhancement
Update search results to include audio clip availability:
```javascript
{
  // Existing fields...
  "audio_clip": {
    "available": true,
    "url": "https://clips.podinsighthq.com/...",
    "duration": 30
  }
}
```

#### 2. Caching Strategy
- Check MongoDB `audio_clips` collection first
- If exists and S3 file valid, return cached URL
- If not, generate new clip and store reference

### Security Considerations

1. **API Rate Limiting**:
   - 10 requests per minute per IP
   - 100 requests per hour per user

2. **Authentication**:
   - API key required for clip generation
   - Public read access for generated clips

3. **Input Validation**:
   - Validate episode_id exists in database
   - Validate chunk_index is within episode bounds

### Performance Optimizations

1. **Lambda Layers**:
   - FFmpeg binary as Lambda layer
   - Boto3 and PyMongo pre-installed

2. **S3 Transfer Acceleration**:
   - Enable for faster uploads from Lambda

3. **CloudFront CDN**:
   - Cache clips at edge locations
   - 24-hour TTL for generated clips

### Monitoring & Logging

1. **CloudWatch Metrics**:
   - Lambda invocation count
   - Error rate
   - Average processing time
   - S3 storage usage

2. **Application Logs**:
   - Clip generation requests
   - Cache hit/miss ratio
   - Error details

### Cost Estimates

**Monthly Costs (estimated)**:
- Lambda executions: $5-10
- S3 storage (1TB): $23
- CloudFront CDN: $10-20
- Data transfer: $5-10
- **Total**: ~$43-73/month

### Future Considerations

1. **Batch Pre-generation**:
   - Consider pre-generating popular clips
   - ML model to predict high-demand clips

2. **Alternative Formats**:
   - Support for different durations (15s, 60s)
   - Video clip generation for YouTube podcasts

3. **Advanced Features**:
   - Waveform visualization
   - Transcript overlay on audio player

---

## Architecture Diagrams

### Audio Clip Generation Flow
```
User Request
    ↓
API Gateway → Lambda Function
    ↓           ↓
MongoDB     S3 Source
(Check)     (Download)
    ↓           ↓
[Exists?]   FFmpeg
    ↓           ↓
Return URL  S3 Upload
    ←           ↓
            MongoDB
            (Store)
                ↓
            Return URL
```

---

Last Updated: December 28, 2024
