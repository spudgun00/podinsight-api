# Audio Clip Generation Implementation Log

## Overview
This document tracks the implementation steps for the Lambda-based audio clip generation system.

---

## Lambda Function Development

### December 28, 2024 - Initial Implementation

#### 10:00 AM - Architecture Planning
- Decided on Lambda + FFmpeg approach
- Chose on-demand generation over batch processing
- Defined API endpoint: `GET /api/v1/audio_clips/{episode_id}?start_time_ms={start}&duration_ms={duration}`

#### 11:00 AM - Lambda Handler Implementation
```python
# Created handler.py with:
- API Gateway event parsing
- S3 cache checking (HEAD object)
- MongoDB episode metadata lookup
- FFmpeg clip extraction
- S3 clip upload
- Pre-signed URL generation (24hr expiry)
```

#### 11:30 AM - Configuration Updates
- Changed from chunk_index to start_time_ms approach
- Updated S3 key format: `audio_clips/{episode_id}/{start_ms}-{end_ms}.mp3`
- Set Lambda memory to 1GB (from initial 512MB)
- Set timeout to 30 seconds

---

## FFmpeg Layer Setup

### Layer Configuration

#### Option 1: Public Lambda Layer (Recommended)
```yaml
# Available FFmpeg layers by region:
us-east-1: arn:aws:lambda:us-east-1:1234567890:layer:ffmpeg:1
us-west-2: arn:aws:lambda:us-west-2:1234567890:layer:ffmpeg:1
eu-west-1: arn:aws:lambda:eu-west-1:1234567890:layer:ffmpeg:1
```

#### Option 2: Custom Layer Creation
```bash
# 1. Download FFmpeg static build
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar -xf ffmpeg-release-amd64-static.tar.xz

# 2. Create layer structure
mkdir -p ffmpeg-layer/bin
cp ffmpeg-*-amd64-static/ffmpeg ffmpeg-layer/bin/
cp ffmpeg-*-amd64-static/ffprobe ffmpeg-layer/bin/

# 3. Create layer ZIP
cd ffmpeg-layer
zip -r ../ffmpeg-layer.zip .

# 4. Upload layer
aws lambda publish-layer-version \
    --layer-name ffmpeg \
    --description "FFmpeg binaries for Lambda" \
    --zip-file fileb://../ffmpeg-layer.zip \
    --compatible-runtimes python3.9
```

#### Layer Integration
```yaml
# In SAM template.yaml:
Layers:
  - arn:aws:lambda:us-east-1:000000000000:layer:ffmpeg:1
```

---

## Lambda Deployment Steps

### 1. Environment Setup
```bash
# Set environment variables
export MONGODB_URI="mongodb+srv://podinsight-api:***@podinsight-cluster.bgknvz.mongodb.net/"
export DEPLOYMENT_BUCKET="podinsight-deployment-artifacts"
```

### 2. Create S3 Buckets
```bash
# Create clips bucket
aws s3 mb s3://pod-insights-clips

# Set bucket policy for public read
aws s3api put-bucket-policy \
    --bucket pod-insights-clips \
    --policy file://bucket-policy.json

# Enable CORS
aws s3api put-bucket-cors \
    --bucket pod-insights-clips \
    --cors-configuration file://cors-config.json
```

### 3. Package Lambda Function
```bash
cd lambda_functions/audio_clip_generator

# Install dependencies
pip install -r requirements.txt -t .

# Create deployment package
zip -r function.zip . -x "*.pyc" -x "__pycache__/*" -x "tests/*"
```

### 4. Deploy with SAM
```bash
# Build
sam build

# Package
sam package \
    --s3-bucket $DEPLOYMENT_BUCKET \
    --output-template-file packaged.yaml

# Deploy
sam deploy \
    --template-file packaged.yaml \
    --stack-name podinsight-audio-clip-generator \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides MongoDBUri=$MONGODB_URI
```

### 5. API Gateway Configuration
```bash
# Get API endpoint
aws cloudformation describe-stacks \
    --stack-name podinsight-audio-clip-generator \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
    --output text
```

---

## MongoDB Setup

### Create Audio Clips Collection
```javascript
// Connect to MongoDB
use podinsight

// Create collection with schema validation
db.createCollection("audio_clips", {
   validator: {
      $jsonSchema: {
         bsonType: "object",
         required: ["episode_id", "clip_start_ms", "clip_end_ms", "s3_key"],
         properties: {
            episode_id: { bsonType: "string" },
            clip_start_ms: { bsonType: "int" },
            clip_end_ms: { bsonType: "int" },
            s3_key: { bsonType: "string" },
            generated_at: { bsonType: "date" },
            file_size_bytes: { bsonType: "int" }
         }
      }
   }
})

// Create compound index for fast lookups
db.audio_clips.createIndex({
    "episode_id": 1,
    "clip_start_ms": 1,
    "clip_end_ms": 1
}, {
    unique: true,
    name: "clip_lookup_idx"
})
```

---

## IAM Role Configuration

### Lambda Execution Role
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::pod-insights-raw/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::pod-insights-clips/*"
        }
    ]
}
```

---

## Testing & Validation

### 1. Local Testing
```bash
# Set up environment
export AWS_PROFILE=podinsight-dev
export MONGODB_URI="mongodb://localhost:27017/podinsight"

# Run unit tests
cd tests
pytest test_audio_lambda.py -v

# Run integration tests
pytest test_audio_api.py -v
```

### 2. Lambda Testing
```bash
# Test invoke
aws lambda invoke \
    --function-name audio-clip-generator \
    --payload '{"pathParameters":{"episode_id":"test"},"queryStringParameters":{"start_time_ms":"30000","duration_ms":"30000"}}' \
    response.json

# Check logs
aws logs tail /aws/lambda/audio-clip-generator --follow
```

### 3. API Testing
```bash
# Test endpoint
curl "https://api.podinsighthq.com/api/v1/audio_clips/0e983347-7815-4b62-87a6-84d988a772b7?start_time_ms=30000&duration_ms=30000"

# Expected response:
{
    "clip_url": "https://pod-insights-clips.s3.amazonaws.com/...",
    "cache_hit": false,
    "generation_time_ms": 2340
}
```

---

## Production Deployment Checklist

- [x] Lambda function packaged with dependencies
- [x] FFmpeg layer configured
- [x] S3 buckets created with proper permissions
- [x] MongoDB collection and indexes created
- [x] IAM roles configured with least privilege
- [x] API Gateway endpoints configured
- [x] Environment variables set
- [x] CloudWatch logging enabled
- [x] Monitoring alarms configured
- [x] Performance benchmarks validated

---

## Troubleshooting

### Common Issues

1. **FFmpeg not found**
   - Verify layer is attached to Lambda
   - Check layer compatibility with runtime

2. **S3 Access Denied**
   - Check IAM role permissions
   - Verify bucket policies

3. **MongoDB Connection Timeout**
   - Verify VPC/security group settings
   - Check connection string format

4. **Lambda Timeout**
   - Monitor CloudWatch logs
   - Check file download times
   - Consider increasing timeout

---

## Next Steps

1. Set up CloudFront distribution for clips
2. Implement cache warming for popular clips
3. Add CloudWatch metrics and dashboards
4. Configure auto-scaling based on load

---

Last Updated: December 28, 2024
