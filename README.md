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

## 🏗️ Architecture

- **Framework**: FastAPI with Uvicorn ASGI server
- **Database**: Supabase (PostgreSQL)
- **Deployment**: Vercel Serverless Functions
- **Region**: London (lhr1) for low latency
- **Memory**: 512MB per function
- **Timeout**: 10 seconds max

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

The API expects the following table structure in Supabase:

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