# PodInsightHQ API

FastAPI backend for PodInsightHQ - Track emerging topics in startup and VC podcasts.

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Vercel CLI (for local development)
- Supabase account with configured database

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/spudgun00/podinsight-api.git
   cd podinsight-api
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

4. **Run locally with Vercel CLI**
   ```bash
   vercel dev
   ```
   The API will be available at `http://localhost:3000`

### Deployment

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Deploy to Vercel**
   ```bash
   vercel
   ```

3. **Set environment variables in Vercel**
   ```bash
   vercel env add SUPABASE_URL
   vercel env add SUPABASE_ANON_KEY
   ```

## 📡 API Endpoints

### Health Check
```
GET /
```
Returns API health status and version.

### Topic Velocity
```
GET /api/topic-velocity?days=30&topics=AI%20Agents,B2B%20SaaS
```

**Parameters:**
- `days` (optional): Number of days to look back (default: 30)
- `topics` (optional): Comma-separated list of topics to track

**Response:**
```json
{
  "success": true,
  "date_range": {
    "start": "2025-05-16T00:00:00",
    "end": "2025-06-15T00:00:00",
    "days": 30
  },
  "topics": {
    "AI Agents": {
      "total_mentions": 245,
      "velocity": 35.5,
      "trending": true,
      "weekly_counts": {...}
    }
  },
  "top_trending": [...]
}
```

### Available Topics
```
GET /api/topics
```
Returns all available topics being tracked in the database.

### Sentiment Analysis (v2 - Batch Powered)
```
GET /api/sentiment_analysis_v2?weeks=12&topics[]=AI%20Agents&topics[]=Crypto/Web3
```

**Parameters:**
- `weeks` (optional): Number of weeks to analyze (default: 12)
- `topics[]` (optional): Array of topics to analyze (default: AI Agents, Capital Efficiency, DePIN, B2B SaaS, Crypto/Web3)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "topic": "AI Agents",
      "week": "W1",
      "sentiment": 0.65,
      "episodeCount": 12,
      "chunkCount": 340,
      "confidence": 0.89,
      "keywordsFound": ["great", "amazing", "innovative"],
      "computedAt": "2025-06-26T02:15:30Z",
      "metadata": {...}
    }
  ],
  "metadata": {
    "weeks": 12,
    "topics": [...],
    "source": "pre_computed_batch",
    "api_version": "v2"
  }
}
```

**Performance**: Returns pre-computed results in <100ms vs 300+ second timeouts of the original API.

> **📖 See [Batch Sentiment Processing Documentation](./docs/BATCH_SENTIMENT_PROCESSING.md)** for complete implementation details, troubleshooting, and architecture overview.

## 🏗️ Architecture

### API Layer
- **Framework**: FastAPI with Uvicorn ASGI server
- **Deployment**: Vercel Serverless Functions
- **Region**: London (lhr1) for low latency
- **Memory**: 512MB per function
- **Timeout**: 10 seconds max (API calls), 30 minutes (batch processing)

### Data Layer
- **Primary Database**: MongoDB Atlas (transcript data, sentiment results)
- **Secondary Database**: Supabase (PostgreSQL) (topic mentions, metadata)
- **Vector Search**: MongoDB Atlas Vector Search (768D embeddings)

### Batch Processing
- **Sentiment Analysis**: Nightly batch processing via GitHub Actions
- **Schedule**: 2 AM UTC daily
- **Processing**: 800,000+ transcript chunks → pre-computed sentiment results
- **Performance**: Transforms 300s timeout → <100ms response time

## 🔧 Development

### Local Development
```bash
# Run with hot reload
uvicorn api.topic_velocity:app --reload --port 8000
```

### Testing
```bash
# Test the endpoints
curl http://localhost:8000/api/topic-velocity
curl http://localhost:8000/api/topics
```

## 📊 Database Schema

### MongoDB Collections (Primary)

#### transcript_chunks_768d
```javascript
{
  _id: ObjectId,
  chunk_index: 156,
  episode_id: "uuid",
  text: "The AI agents market is really exciting...",
  created_at: ISODate,
  start_time: 45.2,
  end_time: 48.9,
  speaker: "host",
  feed_slug: "a16z-podcast",
  embedding_768d: [0.1, 0.2, ...] // 768-dimensional vector
}
```

#### sentiment_results (Pre-computed)
```javascript
{
  _id: ObjectId,
  topic: "AI Agents",
  week: "W1",
  year: 2025,
  sentiment_score: 0.65,
  episode_count: 12,
  chunk_count: 340,
  confidence: 0.89,
  keywords_found: ["great", "amazing", "innovative"],
  computed_at: ISODate,
  metadata: {
    date_range: "2025-06-01 to 2025-06-08",
    analyzed_chunks: 156
  }
}
```

### Supabase Tables (Secondary)

#### topic_mentions
```sql
CREATE TABLE topic_mentions (
  id SERIAL PRIMARY KEY,
  episode_id TEXT NOT NULL,
  topic TEXT NOT NULL,
  mention_count INTEGER DEFAULT 1,
  published_date TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

## 🛡️ Security

- CORS is configured for production use
- Environment variables for sensitive data
- Anon key used for public read access
- Service role key available for admin operations

## 📈 Performance Optimizations

- Cold start optimization with minimal dependencies
- 512MB memory allocation for consistent performance
- Response streaming enabled for large datasets
- Pinned to London region for target audience

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📝 License

MIT License - see LICENSE file for details

## 🔗 Related Projects

- [podinsight-etl](https://github.com/spudgun00/podinsight-etl) - ETL pipeline for processing podcast data
- [podinsight-frontend](https://github.com/spudgun00/podinsight-frontend) - React frontend (coming soon)
# Trigger deployment
