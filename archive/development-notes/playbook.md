# PodInsightHQ: The Genesis Sprint Playbook

*This document is the single source of truth for building the first functional version of the PodInsightHQ application. It combines a lean, rapid development strategy with detailed, step-by-step technical guidance.*

---

## Part 1: Sprint Definition & Product Decisions

### Sprint Goal (The Mission)
Build the minimal viable infrastructure to transform our S3-stored podcast data into a live, authenticated web dashboard displaying our Topic Velocity chart with real podcast insights—focusing on speed and proving core value.

### Definition of Success (How We Know We've Won)
- ✅ **Data is Live**: All 1,171 processed episodes are loaded into Supabase
- ✅ **API is Functional**: A live API endpoint fetches real data and responds in under 1 second
- ✅ **Dashboard is Functional**: The Topic Velocity chart displays real trends from our podcast data
- ✅ **Application is Deployed**: Dashboard accessible via password-protected staging URL on Vercel
- ✅ **Performance Target**: Page loads in under 2 seconds

### Core Product & Technical Decisions

| Theme | Question | Decision | Strategic Rationale |
|-------|----------|----------|-------------------|
| **Data Scope** | Support full-text search now? | **No. Topic tracking only.** | Full-text search is a much larger engineering effort. The "Topic Velocity" chart is our core "wow" feature. We must nail that first. |
| **Data Scope** | Expected query volume? | **Assume very low (<100/day).** | We're building for alpha testers. This allows us to use free/cheap service tiers and focus on features, not infrastructure. |
| **Data Scope** | Plan for multi-tenancy? | **No. Single-tenant model.** | Since we've deferred user accounts, there's only one "tenant": us. Multi-tenancy would slow us down significantly. |
| **Infrastructure** | Budget for this sprint? | **Target < $50/month.** | Using free tiers of Supabase and Vercel, costs should be near zero. This preserves capital for scaling. |
| **Infrastructure** | Dev and Production databases? | **No. Single Supabase project.** | For a fast-moving sprint, managing separate environments is unnecessary overhead. Simplicity equals speed. |
| **Infrastructure** | Compliance requirements? | **None for now.** | We're not handling sensitive user data yet. Compliance is a heavy lift for public launch only. |
| **Analytics** | Which topics to track initially? | **AI Agents, Capital Efficiency, DePIN, B2B SaaS, Crypto/Web3** | Balanced mix of hot trends, strategic shifts, emerging niches, and core categories. |
| **Analytics** | How to count multiple mentions? | **Count 1 mention per episode/week.** | We want breadth (how many podcasts discuss it), not depth. Prevents one long episode from skewing trends. |
| **Analytics** | Backfill all historical data? | **Yes. Absolutely critical.** | A trend chart without history is useless. Must process all 1,171 episodes from Jan-Jun 2025. |
| **Frontend UI** | Use specific design system? | **Yes. Dark theme from prototypes.** | We already have professional designs. Consistency saves time and builds cohesive brand. |
| **Frontend UI** | Support mobile responsiveness? | **No. Defer to Sprint 1.** | Target users (VCs, analysts) primarily use desktop. Mobile is significant extra effort. |
| **Frontend UI** | Light or dark mode? | **Dark mode only.** | Faster to build one mode. Dark is standard for "pro" tools and makes visualizations pop. |
| **Frontend UI** | Loading/splash screen? | **No splash. Use skeleton loaders.** | Skeleton loaders make app feel faster and more responsive than static loading screens. |
| **Chart Config** | Default time range? | **"Last 3 Months."** | Standard, intuitive default. Recent enough to feel current but shows meaningful trends. |
| **Chart Config** | How many topics to compare? | **Maximum of 4.** | More than 4 lines becomes visually cluttered. Forces focus on important comparisons. |
| **Chart Config** | Raw counts or percentages? | **Raw counts.** | "Mentioned in 45 episodes" is more concrete than abstract percentages. |
| **Chart Config** | Default topics on chart? | **AI Agents, Capital Efficiency, DePIN, B2B SaaS** | Gives every user immediate, compelling view of market on landing. |
| **Chart Config** | Allow users to change topics? | **No. Defer to Sprint 1.** | Dynamic topic selector is complex. First prove we can deliver valuable, data-driven chart. |

---

## Part 2: Phase 1 - Foundational Data Architecture
*(Goal: Get our S3 data into a queryable Supabase database)*

### 🎯 Critical Context About Our Data

- **All 1,171 episodes are already transcribed and processed**
- **Two S3 buckets exist:**
  - `pod-insights-raw`: Audio files only (we DON'T need this)
  - `pod-insights-stage`: Transcripts, metadata, KPIs (we WILL use this)
- **Data structure**: `<feed_slug>/<guid>/<type>/<filename>`
  - Example: `the-twenty-minute-vc-20vc.../3741fdcc-f8e2.../transcripts/transcript.json`

> ⚠️ **CRITICAL UPDATE (June 14, 2025):** Production file naming differs significantly from documentation. Files use complex naming patterns. See updated file discovery logic below.

### 📊 Data Loading Strategy

| Data Type | Load Now? | Why | Future Use |
|-----------|-----------|-----|------------|
| **Transcripts** | ✅ Yes | Core feature - topic detection | Topic Velocity (now) |
| **Metadata** | ✅ Yes | Episode info, dates, titles | All features |
| **KPIs** | ✅ Yes | Financial metrics tracking | KPI dashboard |
| **Entities** | ✅ Yes | People/company mentions | "Track Sequoia mentions" |
| **Embeddings Path** | ✅ Yes (path only) | Don't download 500KB files | Natural language search |
| **Audio Path** | ✅ Yes (path only) | For streaming | Audio playback |
| **Segments** | ❌ No | 2MB files, only for UI | Defer to transcript UI sprint |

### 🎵 Audio Streaming Strategy
- **Store**: S3 path reference only
- **Playback**: Generate pre-signed URLs (1-hour expiration)
- **Benefits**: No database bloat, secure, cost-effective
- **Implementation**: Sprint 3 or 4

### 🏠 Repository Setup

**Repository: Work in `podinsight-etl` (local folder)**

#### First: Create Your ETL Repository

```bash
# In your development directory
mkdir podinsight-etl
cd podinsight-etl

# Copy the playbook and business overview
# (Copy playbook.md and business_overview.md from wherever you saved them)
# Create project.md with content from Appendix C
```

#### Initial Folder Structure for ETL:

```
podinsight-etl/
├── playbook.md          # This Genesis Sprint Playbook
├── business_overview.md # Business context and objectives
├── project.md           # ETL-specific context (from Appendix C)
├── .env                 # Credentials (create this)
├── .env.example         # Template for credentials
├── requirements.txt     # Python dependencies
├── main.py             # Main ETL script
└── modules/            # Organized code modules
    ├── __init__.py
    ├── s3_reader.py
    ├── topic_detector.py
    └── supabase_loader.py
```

### Step 1.1: Database Setup with Supabase

**🏠 Repository: Work in `podinsight-etl` (local folder)**

**The Goal:** Create a production-ready PostgreSQL database in under 5 minutes.

**The "Why":** Supabase provides instant PostgreSQL with built-in APIs, authentication, and a web interface. It's like getting a fully-furnished apartment instead of building a house—move in today, not next month.

#### Detailed Actions:

1. **Create Supabase Project**
   - Go to [supabase.com](https://supabase.com)
   - Sign up/login and click "New Project"
   - Name: `podhq-staging`
   - Password: Generate a strong one (save it!)
   - Region: Choose closest to you
   - Wait ~2 minutes for provisioning

2. **Enable pgvector Extension**
   ```sql
   -- Run this in Supabase SQL Editor
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. **Create Database Schema**

   **Your First Prompt to Claude Code:**
   ```
   I need to create a database schema in Supabase for a podcast analytics application.

   Requirements:
   - Table: episodes (id, guid, podcast_name, episode_title, published_at, duration_seconds,
                      s3_stage_prefix, s3_audio_path, s3_embeddings_path, word_count)
   - Table: topic_mentions (id, episode_id, topic_name, mention_date, week_number)
   - Table: extracted_kpis (id, episode_id, kpi_type, kpi_value, context, confidence, timestamp)
   - Table: extracted_entities (id, episode_id, entity_name, entity_type, normalized_name,
                                confidence, role, organization)

   Generate the complete SQL DDL with:
   - Proper primary keys and foreign keys
   - Unique constraint on episodes.guid
   - Indexes on commonly queried fields (published_at, topic_name, entity_name, entity_type)
   - RLS (Row Level Security) disabled for now
   - Comments explaining each table's purpose

   The output must be two separate files:
   - 001_initial_schema.up.sql (with the CREATE TABLE statements)
   - 001_initial_schema.down.sql (with the corresponding DROP TABLE statements)

   Notes:
   - s3_stage_prefix: Base path like "pod-insights-stage/<feed_slug>/<guid>/"
   - s3_audio_path: Full path to MP3 in raw bucket for future streaming
   - s3_embeddings_path: Path to .npy file for semantic search (Sprint 2)
   - extracted_entities: Store cleaned entities for future person/company tracking
   ```

   **Rationale for migration files:** This is a professional database management practice called migration scripting. It provides a safe, version-controlled way to apply and, more importantly, revert database schema changes, preventing a bad migration from blocking development.

4. **Save Connection Details**
   - Project URL: `https://[your-project].supabase.co`
   - Anon Key: Found in Settings > API
   - Service Role Key: For backend operations
   - Store these in a `.env` file

**Testing Checkpoint:**
- Run `SELECT COUNT(*) FROM episodes` in Supabase SQL Editor - should return exactly 0 (empty table)
- Run `SELECT * FROM pg_extension WHERE extname = 'vector'` - should return 1 row confirming pgvector is installed
- Run `\dt` in SQL editor - should show all 4 tables: episodes, topic_mentions, extracted_kpis, extracted_entities
- Run `\d topic_mentions` - should show foreign key constraint to episodes table

### Step 1.2: The Data Loading Script (ETL)

**🏠 Repository: Continue in `podinsight-etl` (local folder)**

**The Goal:** Write a Python script that reads our 1,171 processed episodes from S3 and populates our Supabase tables.

**The "Why":** This script transforms a collection of already-processed JSON files into structured, queryable intelligence. It's the bridge between our existing processed data and the new database.

> ⚠️ **CRITICAL UPDATE:** Production file naming differs significantly from documentation. We must use dynamic file discovery.

**Important Context:**
- All 1,171 episodes have already been transcribed and processed
- Data is in the `pod-insights-stage` bucket (NOT the raw bucket)
- Each episode has transcript, enriched metadata, KPIs, embeddings, and entities ready to use
- We'll load most data now for future features, but defer large segment files

**Data We'll Load:**
- ✅ Transcripts (for topic detection)
- ✅ Metadata (episode info)
- ✅ KPIs (financial metrics)
- ✅ Entities (people/company mentions - for future features)
- ✅ S3 paths for embeddings and audio (for Sprint 2 features)
- ❌ Segments (large files, only needed for transcript UI - defer to later sprint)

#### Local Development

**🏠 Repository: Continue in `podinsight-etl` (local folder)**

For faster, offline iteration, use the Supabase CLI. Run 'supabase start' to spin up a local Docker-based database. The ETL script should first be tested against this local instance before running against the live database.

**Rationale:** This is critical for development speed. It allows for rapid testing of the ETL script without using cloud resources or quotas, which makes debugging much faster and more efficient.

#### Environment Setup

**🏠 Repository: Continue in `podinsight-etl` (local folder)**

**Prompt for Claude Code:**
```
Create a Python project structure for an ETL script that:
1. Connects to AWS S3 to read podcast data from 'pod-insights-stage' bucket
2. Connects to Supabase to insert processed data
3. Uses environment variables for all credentials

Show me:
- requirements.txt with necessary packages (boto3, supabase-py, python-dotenv)
- .env.example file structure (including AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_STAGE)
- Basic project folder structure
- Initial connection test script that lists folders in pod-insights-stage
```

#### S3 Data Reader (UPDATED FOR PRODUCTION)

**🏠 Repository: Continue in `podinsight-etl` (local folder)**

**Important Context**: Our data uses complex file naming patterns that differ from documentation:
- Transcripts have descriptive filenames with dates and titles
- Meta files include the GUID in the filename
- Entities are in `cleaned_entities/` folder, not `entities/`

**Updated Prompt for Claude Code:**
```
Write a Python module called s3_reader.py that:

1. Lists all feed_slug folders in the S3 bucket 'pod-insights-stage'
2. For each episode (feed_slug/guid combination), dynamically discovers and reads files:
   - Transcript: Find JSON file in transcripts/ folder (complex naming pattern)
   - Meta: Find file matching pattern meta_<guid>_details.json in meta/ folder
   - KPIs: Find file matching pattern kpis_<guid>.json in kpis/ folder
   - Entities: Find file matching pattern <guid>_clean.json in cleaned_entities/ folder

3. Also captures these S3 paths for future use (don't download the files):
   - Embeddings: embeddings/<guid>.npy (path only - for semantic search in Sprint 2)
   - Audio path from pod-insights-raw bucket (construct from feed_slug/guid)

4. IMPORTANT: Use dynamic file discovery instead of hardcoded paths:
   - List all files in each episode folder
   - Match by pattern, not exact filename
   - For transcripts: any .json file in transcripts/ folder
   - For meta: files containing 'meta_' and the guid
   - For kpis: files starting with 'kpis_' and containing the guid
   - For entities: files in cleaned_entities/ ending with '_clean.json'

5. Include this discovery function:
```

```python
def discover_episode_files(s3_client, bucket, feed_slug, guid):
    """Dynamically discover files for an episode"""
    prefix = f"{feed_slug}/{guid}/"
    files = {}

    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    if 'Contents' not in response:
        return files

    for obj in response['Contents']:
        key = obj['Key']
        parts = key.split('/')
        if len(parts) < 4:
            continue

        folder = parts[-2]
        filename = parts[-1]

        # Pattern matching for each file type
        if folder == 'transcripts' and filename.endswith('.json'):
            files['transcript'] = key
        elif folder == 'meta' and 'meta_' in filename and guid in filename:
            files['meta'] = key
        elif folder == 'kpis' and filename.startswith('kpis_') and guid in filename:
            files['kpis'] = key
        elif folder == 'cleaned_entities' and filename.endswith('_clean.json'):
            files['entities'] = key
        elif folder == 'embeddings' and filename.endswith('.npy'):
            files['embeddings'] = key
        elif folder == 'segments' and filename.endswith('.json'):
            files['segments'] = key

    return files
```

```
6. Handles missing files gracefully with logging
7. Returns a generator that yields processed episode data
8. Include progress tracking that shows "Processing episode X of 1,171"

Example discovery output:
- Transcript: a16z-podcast-2025-01-22-rip-to-rpa-how-ai-makes-operations-work_1216c2e7_raw_transcript.json
- Meta: meta_1216c2e7-42b8-42ca-92d7-bad784f80af2_details.json
- KPIs: kpis_1216c2e7-42b8-42ca-92d7-bad784f80af2.json
- Entities: 1216c2e7-42b8-42ca-92d7-bad784f80af2_clean.json (in cleaned_entities/)
```

#### Topic Detection Logic

**🏠 Repository: Continue in `podinsight-etl` (local folder)**

**Prompt for Claude Code:**
```
Create a topic detection module that:

1. Takes transcript data as input (from transcript.json files)
   - Input format: {"segments": [{"text": "...", "speaker": "SPEAKER_01", ...}], ...}
   - Combine all segment texts into full transcript text

2. Searches for these topics (case-insensitive):
   - "AI Agents" (also match: AI agent, artificial intelligence agents)
   - "Capital Efficiency" (also match: burn rate, runway, cash efficiency)
   - "DePIN" (also match: decentralized physical infrastructure)
   - "B2B SaaS" (also match: B2B software, enterprise SaaS)
   - "Crypto / Web3" (also match: cryptocurrency, blockchain, web3)

3. Returns True/False for each topic's presence
4. Extracts the week number from the episode date (from meta.json)

Important: Count each topic maximum ONCE per episode, even if mentioned multiple times.

Note: The transcripts are already processed with speaker diarization from WhisperX.
```

#### Database Insertion (UPDATED FOR DISCOVERED PATHS)

**🏠 Repository: Continue in `podinsight-etl` (local folder)**

**Prompt for Claude Code:**
```
Write the Supabase insertion logic that:

1. For each episode from S3 (using dynamically discovered file paths):
   - Inserts episode metadata into 'episodes' table (from discovered meta file)
   - For each detected topic, inserts ONE row into 'topic_mentions'
   - Inserts KPIs into 'extracted_kpis' table (if file exists)
   - Inserts entities into 'extracted_entities' table (from cleaned_entities folder)
   - Stores ACTUAL S3 path references (not hardcoded paths)
   - Uses upsert to handle duplicates (based on guid)

2. Key fields to extract:
   - From meta file: guid, podcast_title, episode_title, published date, duration_seconds, word_count
   - S3 paths: Store ACTUAL discovered paths, not assumed paths
   - From entities: entity_name, type, normalized_name, confidence, role

3. Implements batch processing (insert 50 episodes at a time)
4. Includes error handling with detailed logging
5. Shows running count: "Inserted X of 1,171 episodes"

6. Final validation query that prints:
   - Total episodes in database
   - Mention count per topic
   - Total entities by type (PERSON, ORG)
   - Date range of data

Important: Store the actual S3 paths discovered, not idealized paths from documentation
```

#### Complete ETL Script

**🏠 Repository: Continue in `podinsight-etl` (local folder)**

**Prompt for Claude Code:**
```
Combine the above modules into a main.py script that:

1. Loads environment variables
2. Connects to S3 (pod-insights-stage bucket) and Supabase
3. Processes all episodes with progress bar
4. Handles interruptions gracefully (can resume based on existing GUIDs)
5. Logs everything to etl_run.log
6. Ends with summary statistics

Important notes for the script:
- Read from 'pod-insights-stage' bucket (not 'pod-insights-raw')
- Episodes are organized as <feed_slug>/<guid>/ folders
- Each episode has files in subfolders with COMPLEX NAMING:
  - transcripts/ (descriptive filenames)
  - meta/ (includes guid in filename)
  - kpis/ (includes guid in filename)
  - cleaned_entities/ (NOT entities/)
  - embeddings/ (standard naming)
- Use the file discovery function for each episode
- Store actual S3 paths found, not idealized paths
- Skip segments/ folder entirely (defer to future sprint)
- Total expected: 1,171 processed episodes

Summary should show:
- Episodes loaded
- Topics detected (with counts)
- Entities extracted (by type)
- KPIs found
- Any errors encountered
- Files not found (missing data)

The script should be runnable with: python main.py
```

**Testing Checkpoints:**
1. **File discovery test**: Test discovery on known episode - should find 5-6 file types
2. **Pattern matching test**: Verify transcript found despite complex naming
3. **Entity folder test**: Confirm looking in 'cleaned_entities/' not 'entities/'
4. **Dry run test**: `python main.py --dry-run` - should process without errors
5. **Limited test**: `python main.py --limit 10` - should complete in <30 seconds
6. **Verify test data**:
   - Run `SELECT COUNT(*) FROM episodes` - should return exactly 10
   - Run `SELECT COUNT(*) FROM extracted_entities WHERE entity_type = 'PERSON'` - should return some people
   - Run `SELECT COUNT(*) FROM extracted_entities WHERE entity_type = 'ORG'` - should return some companies
7. **Check topics**: Run `SELECT topic_name, COUNT(*) FROM topic_mentions GROUP BY topic_name` - each detected topic returns ≥1 row
8. **Full load**: `python main.py` - should show progress bar reaching 1,171
9. **Final verification**:
   - `SELECT COUNT(*) FROM episodes` returns exactly 1,171
   - `SELECT COUNT(DISTINCT topic_name) FROM topic_mentions` returns exactly 5
   - `SELECT entity_type, COUNT(*) FROM extracted_entities GROUP BY entity_type` shows ~100-150k entities (not millions)

**⚠️ IMPORTANT DATA INTERPRETATION CONTEXT:**
After running the full ETL, expect these patterns:
- **Topic Distribution Bias**: Statistics will reflect podcast selection (e.g., crypto podcasts mention crypto heavily)
- **Missing Topics Normal**: ~30-40% of episodes may have no topic mentions - not all podcasts discuss our 5 tracked topics
- **Entity Counts**: Expect ~100-150k meaningful entities after filtering (PERSON, ORG, GPE, MONEY only)
- **KPI Extraction**: Expect ~40-60k financial metrics - not all episodes contain business metrics
- **Processing Time**: Full 1,171 episode run takes ~20-30 minutes with proper date retrieval

---

## Part 3: Phase 2 - Backend API
*(Goal: Create a single, high-performance API endpoint)*

### 🏠 Repository Setup

**Repository: Create and work in `podinsight-api` (GitHub repo)**

#### First: Create Your API Repository

```bash
# Create new GitHub repository named 'podinsight-api'
# Then clone it locally:
git clone https://github.com/YOUR_USERNAME/podinsight-api.git
cd podinsight-api

# Copy the playbook and business overview
cp ../podinsight-etl/playbook.md .
cp ../podinsight-etl/business_overview.md .
# Create project.md with API-specific content from Appendix C
```

#### Initial Folder Structure for API:

```
podinsight-api/
├── playbook.md          # This Genesis Sprint Playbook
├── business_overview.md # Business context and objectives
├── project.md           # API-specific context (from Appendix C)
├── api/
│   └── topic_velocity.py # Main endpoint handler
├── requirements.txt     # FastAPI + dependencies
├── vercel.json         # Deployment configuration
├── .env.example        # Environment template
├── .gitignore          # Ignore .env and __pycache__
└── README.md           # API documentation
```

### Step 2.1: FastAPI Serverless Setup

**The Goal:** Deploy a Python API without managing servers.

**The "Why":** Vercel runs our Python code as "serverless functions"—automatic scaling, zero maintenance, instant deployments from GitHub.

#### Repository Setup

**🏠 Repository: Continue in `podinsight-api` (GitHub repo)**

**Prompt for Claude Code:**
```
Create a new project structure for a FastAPI app deployed on Vercel:

1. Create these files:
   - api/topic_velocity.py (main endpoint)
   - requirements.txt
   - vercel.json (deployment config with cold start optimization)
   - .env.example
   - README.md with setup instructions

2. The vercel.json must include:
   - Function memory set to 512MB
   - Max duration set to 10 seconds
   - Proper Python runtime configuration
   - Pin the deployment region to ["lhr1"] for London
   - Include the flag "supportsResponseStreaming": true

3. The structure should support Vercel's Python runtime
4. Include CORS configuration for frontend access
5. Add basic error handling and logging
```

**Rationale for region pinning:** This is a performance optimization to mitigate "cold starts" on Vercel's serverless functions. By pinning the region closest to our initial users, we reduce network latency and ensure the first API call is as fast as possible, which is critical for a good first impression.

**Rationale for response streaming:** This enables support for streaming data in the future at no extra cost, which will be valuable for more advanced real-time features.

#### Topic Velocity Endpoint

**Prompt for Claude Code:**
```
Write the FastAPI endpoint for GET /api/topic-velocity that:

1. Connects to Supabase using environment variables
2. Accepts optional query parameters:
   - weeks: number of weeks to return (default: 12)
   - topics: comma-separated list (default: our 4 main topics)

3. Executes this logic:
   - Query topic_mentions grouped by week_number and topic_name
   - Count mentions per topic per week
   - Format for Recharts line chart

4. Returns JSON like:
{
  "data": {
    "AI Agents": [
      {"week": "2025-W01", "mentions": 45, "date": "Jan 1-7"},
      {"week": "2025-W02", "mentions": 67, "date": "Jan 8-14"}
    ],
    "Capital Efficiency": [...],
    "DePIN": [...],
    "B2B SaaS": [...]
  },
  "metadata": {
    "total_episodes": 1171,
    "date_range": "2025-01-01 to 2025-06-14",
    "data_completeness": "topics_only"  // Note: entities available in v2
  }
}

5. Optimize query with proper indexes
6. Add response caching headers (1 hour)

Note: We have entity data loaded but not exposed in v1 API - future feature
```

#### Deployment & Testing

**🏠 Repository: Continue in `podinsight-api` (GitHub repo)**

**Prompt for Claude Code:**
```
Create deployment instructions that:

1. Show how to connect GitHub repo to Vercel
2. Set environment variables in Vercel dashboard
3. Test the deployed endpoint with curl commands
4. Measure response time (target: <500ms)
5. Add basic monitoring with Vercel Analytics
```

**Testing Checkpoints:**
1. **Local test**: `uvicorn api.topic_velocity:app --reload` (in `podinsight-api`) - should start without errors on port 8000
2. **Response format**: `curl http://localhost:8000/api/topic-velocity` - should return JSON with 4 topics
3. **Performance test**: `curl -w "\nResponse time: %{time_total}s\n" -o /dev/null -s http://localhost:8000/api/topic-velocity` - should show <500ms
4. **Deploy to Vercel**: `vercel --prod` - should complete without errors
5. **Production test**:
   - `curl https://your-api.vercel.app/api/topic-velocity` returns HTTP 200
   - Response includes all 4 default topics
   - Each topic has 12+ data points
   - Response time <500ms (use curl -w flag)
6. **CORS verification**: Check response headers include `Access-Control-Allow-Origin: *`

---

## Part 4: Phase 3 - Frontend Dashboard
*(Goal: Build the user-facing dashboard using v0.dev for speed)*

### 🏠 Repository Setup

**Repository: Create and work in `podinsight-dashboard` (GitHub repo)**

#### First: Create Your Dashboard Repository

```bash
# Create new GitHub repository named 'podinsight-dashboard'
# Then clone it locally:
git clone https://github.com/YOUR_USERNAME/podinsight-dashboard.git
cd podinsight-dashboard

# Copy the playbook and business overview
cp ../podinsight-etl/playbook.md .
cp ../podinsight-etl/business_overview.md .
# Create project.md with dashboard-specific content from Appendix C
```

#### Initial Folder Structure for Dashboard:

```
podinsight-dashboard/
├── playbook.md              # This Genesis Sprint Playbook
├── business_overview.md     # Business context and objectives
├── project.md               # Dashboard-specific context (from Appendix C)
├── app/
│   ├── layout.tsx          # Root layout with dark theme
│   ├── page.tsx            # Main dashboard page
│   └── globals.css         # Tailwind styles
├── components/
│   ├── TopicVelocityChart.tsx  # Main chart component
│   └── LoadingSkeleton.tsx     # Loading state
├── lib/
│   ├── api.ts              # API client functions
│   └── utils.ts            # Helper functions
├── types/
│   └── analytics.ts        # TypeScript interfaces
├── public/                 # Static assets
├── .env.local             # Local environment vars
├── .env.example           # Environment template
├── next.config.js         # Next.js configuration
├── tailwind.config.ts     # Tailwind configuration
├── tsconfig.json          # TypeScript config
├── package.json           # Dependencies
└── README.md              # Dashboard documentation
```

### Step 3.1: v0.dev Rapid UI Generation

**The Goal:** Generate 80% of our dashboard UI in 10 minutes using AI.

**The "Why":** v0.dev generates production-ready React/Next.js code instantly. It's like having a senior frontend developer build your UI scaffolding while you focus on the data integration.

#### The v0.dev Strategy

**🏠 Repository: You'll paste the generated code into `podinsight-dashboard`**

**Option 1: Standard Professional Dashboard (paste this exactly):**
```
Create a dark-mode data analytics dashboard for PodInsightHQ using Next.js 14, TypeScript, and Tailwind CSS.

Layout:
- Full-width header with "PodInsightHQ" logo (gradient text: purple to blue)
- Centered main content area (max-width: 1400px)
- Dark background (#0A0A0A) with subtle purple/blue gradient accents

Main Component:
- Large "Topic Velocity Tracker" card taking 80% of screen
- Card has glass morphism effect (semi-transparent with backdrop blur)
- Contains a Recharts LineChart with:
  - 4 lines for different topics (use these colors: #10B981, #6B46C1, #3B82F6, #EF4444)
  - Smooth curves
  - X-axis: weeks, Y-axis: mention count
  - Interactive tooltips showing exact values
  - Legend below chart with clickable items

Loading State:
- Skeleton loader that mimics the chart shape
- Pulsing animation on the skeleton
- "Analyzing podcast intelligence..." text

No mobile responsiveness needed. Include mock data for 12 weeks of 4 topics.
```

**Option 2: Premium "Bloomberg Terminal" Style (Enhanced - paste this for maximum impact):**
```
Create a premium dark-mode analytics dashboard for PodInsightHQ using Next.js 14, TypeScript, Tailwind CSS, and Framer Motion.

Visual Design:
- Deep black background (#0A0A0A) with animated gradient mesh overlay (purple/blue/teal)
- Subtle noise texture overlay for depth
- Full-width header with "PodInsightHQ" in bold gradient text (animated gradient shift on hover)
- Add subtle tagline under logo: "1,000 hours of podcast intelligence, visualized"
- Ambient glow effects behind cards

Main Dashboard Layout:
- Hero metric cards above chart (mini cards with live-updating animations):
  - "📈 Trending Now" with top rising topic
  - "🎙️ Episodes Analyzed: 1,171" with subtle count-up animation
  - "⚡ Insights Generated: Real-time" with pulsing dot
  - "📊 Data Freshness: Live" with green indicator

Topic Velocity Tracker Card:
- Glass morphism with multi-layer depth (backdrop-blur-xl, gradient borders)
- Subtle inner glow on hover
- Contains an enhanced Recharts LineChart:
  - Animated line drawing on load (staggered by topic)
  - Gradient fills under each line (semi-transparent)
  - Custom dot indicators that pulse on data points
  - Interactive tooltips with glass morphism effect showing:
    - Topic name with color indicator
    - Exact mention count
    - Week date range
    - Percentage change from previous week (↑↓)
  - Y-axis with subtle grid lines (opacity 10%)
  - X-axis with formatted week labels
  - Smooth curve interpolation with tension

Enhanced Interactions:
- Topic lines highlight on hover (others fade to 30% opacity)
- Click legend items to toggle lines with smooth transitions
- Hover effects on all interactive elements
- Cursor changes to pointer with custom glow
- Add velocity indicators: small arrows showing trend direction at line ends

Loading State:
- Sophisticated skeleton with:
  - Animated gradient shimmer effect
  - Chart skeleton that draws the axis first, then animated placeholder lines
  - "Analyzing 1,000+ hours of podcast intelligence..." with typewriter effect
  - Subtle particle effects in background

Modern Touches:
- Use Inter font for UI, SF Mono for numbers
- Add kbd shortcuts hint in corner: "Press / for search"
- Subtle CSS animations: floating gradient orbs in background
- Premium color palette:
  - Emerald: #10B981
  - Purple: #8B5CF6 (softer than #6B46C1)
  - Blue: #3B82F6
  - Coral: #F59E0B (warmer than red)
- Add micro-animations:
  - Numbers tick up when they change
  - Smooth color transitions
  - Hover states with scale(1.02)
  - Active states with subtle depression effect

Footer Details:
- "Last updated: X seconds ago" with live timer
- Subtle metadata: "Tracking 5 topics across 29 podcasts"

CSS Features to Include:
- CSS custom properties for theming
- Mix-blend-mode for interesting overlaps
- CSS Grid for precise layouts
- Container queries for component responsiveness
- :has() selector for contextual styling

Include these Tailwind classes for premium feel:
- backdrop-blur-2xl
- bg-gradient-to-br
- shadow-2xl shadow-purple-500/20
- ring-1 ring-white/10
- transition-all duration-300 ease-out

Mock data: 12 weeks for topics "AI Agents", "Capital Efficiency", "DePIN", "B2B SaaS"

Make it feel like a $10k/month enterprise dashboard, not a free tool.
```

**💡 Recommendation:** Use Option 2 for maximum impact with VCs and founders who expect premium tools.

#### Setting Up the Next.js Project

**🏠 Repository: Continue in `podinsight-dashboard` (GitHub repo)**

**Prompt for Claude Code after getting v0.dev code:**
```
I have this dashboard component from v0.dev. Help me:

1. Create a new Next.js 14 project with TypeScript
2. Install all necessary dependencies (including recharts, @tanstack/react-query)
3. Set up the project structure with:
   - app/page.tsx (main dashboard)
   - components/TopicVelocityChart.tsx (from v0)
   - lib/api.ts (for data fetching)
   - types/analytics.ts (TypeScript types)

4. Configure Tailwind with the dark theme colors
5. Add Inter font from Google Fonts
```

### Step 3.2: Data Integration

**🏠 Repository: Continue in `podinsight-dashboard` (GitHub repo)**

**The Goal:** Connect our beautiful UI to real API data.

**The "Why":** This is where static design becomes living intelligence—the moment our dashboard transforms from mockup to valuable product.

#### API Integration with React Query

**🏠 Repository: Continue in `podinsight-dashboard` (GitHub repo)**

**Prompt for Claude Code:**
```
Integrate the Topic Velocity chart with our real API:

1. Create a custom hook using React Query:
   - Fetches from process.env.NEXT_PUBLIC_API_URL + '/api/topic-velocity'
   - Handles loading, error, and success states
   - Refreshes data every 5 minutes
   - Shows skeleton loader during fetch

2. Transform API response to Recharts format:
   - Map week numbers to readable dates
   - Ensure all topics have data for all weeks (fill missing with 0)
   - Sort by date ascending

3. Update the chart component to:
   - Use real data from the hook
   - Show error state if API fails
   - Display metadata (total episodes, date range) below chart
```

#### Basic Authentication

**🏠 Repository: Continue in `podinsight-dashboard` (GitHub repo)**

**Prompt for Claude Code:**
```
Add password protection using Vercel's built-in features:

1. Create middleware.ts that:
   - Checks for basic auth header
   - Uses environment variable for password
   - Shows browser's built-in auth prompt
   - Allows access once authenticated

2. Set up environment variables:
   - BASIC_AUTH_PASSWORD in .env.local
   - Instructions for setting in Vercel dashboard

This gives us staging protection without building a full auth system.
```

**Testing Checkpoints:**
1. **Local development**: `npm run dev` - should start on http://localhost:3000 (in `podinsight-dashboard`)
2. **Data fetching**: Open Network tab - should see request to API endpoint returning 200
3. **Chart validation**:
   - Chart displays 4 lines with correct colors (#10B981, #6B46C1, #3B82F6, #EF4444)
   - Hovering any data point shows tooltip with topic name and count
   - X-axis labels show week dates, Y-axis shows mention counts
4. **Build test**: `npm run build` - completes without TypeScript errors
5. **Deployment**: Push to GitHub - Vercel auto-deploys within 2 minutes

### Step 3.3: Deployment

**🏠 Repository: Continue in `podinsight-dashboard` (GitHub repo)**

**The Goal:** Deploy the working dashboard to Vercel with password protection.

**The "Why":** We need a live, accessible URL to demonstrate our progress and gather feedback from stakeholders.

#### Deployment Steps

**Prompt for Claude Code:**
```
Create a deployment checklist:

1. Environment setup:
   - List all required environment variables
   - Show how to add them in Vercel dashboard
   - Include example values

2. Vercel deployment:
   - Connect GitHub repository
   - Configure build settings
   - Enable password protection using Vercel's feature

3. Post-deployment testing:
   - Verify chart loads with real data in <2 seconds
   - Test basic auth works with correct "access code"
   - Measure API response time is <500ms
```

**Testing Checkpoints:**
1. **Deployment verification**: Visit Vercel dashboard - should show "Ready" status with green checkmark for `podinsight-dashboard`
2. **Environment variables**: Verify `NEXT_PUBLIC_API_URL` is set to your API endpoint
3. **Auth test**:
   - Open staging URL in incognito - should prompt for "access code"
   - Enter wrong code - should be denied
   - Enter correct code from `BASIC_AUTH_PASSWORD` - dashboard loads
4. **Full integration test**:
   - Chart loads within 2 seconds (measure in Network tab)
   - Shows 4 topic lines with 12+ weeks of data each
   - Hover tooltips work on all data points
   - No console errors in browser DevTools
5. **Cross-browser check**: Test in Chrome and Safari - both should render identically

---

## Part 5: Testing & Validation Checkpoints

### Phase 1 (Data) Success Criteria
- [ ] The 'episodes' table contains exactly 1,171 rows
- [ ] Each episode has a unique GUID identifier
- [ ] Query `SELECT topic_name, COUNT(*) FROM topic_mentions GROUP BY topic_name` returns 5 rows with ~1,200-1,400 total mentions
- [ ] Query `SELECT MIN(published_at), MAX(published_at) FROM episodes` returns dates spanning Jan 1 - Jun 14, 2025
- [ ] All episodes have s3_stage_prefix pointing to pod-insights-stage bucket paths
- [ ] Query `SELECT entity_type, COUNT(*) FROM extracted_entities GROUP BY entity_type` shows ~100-150k total entities
- [ ] Query `SELECT COUNT(*) FROM extracted_kpis` shows ~40-60k financial metrics
- [ ] All episodes have s3_embeddings_path and s3_audio_path populated for future features
- [ ] All tables have proper foreign key relationships verified by `\d topic_mentions` in SQL editor

### Phase 2 (API) Success Criteria
- [ ] Endpoint responds with HTTP 200 and valid JSON body
- [ ] Response time measured with `curl -w "\n%{time_total}s\n"` is < 500ms
- [ ] JSON response contains all 4 default topics with 12+ weeks of data each
- [ ] CORS headers present: `Access-Control-Allow-Origin: *` in response

### Phase 3 (Frontend) Success Criteria
- [ ] Chart renders with 4 colored lines matching our topic colors
- [ ] Hovering over any data point shows tooltip with exact value
- [ ] Browser Network tab shows total page load time < 2 seconds
- [ ] Accessing URL without password shows browser auth prompt
- [ ] Chart displays "Topic Velocity Tracker" title and axis labels

---

## Part 6: Sprint Review & Demo Script

### Demo Flow (5 minutes)

**🏠 Demo from:** All three repositories should be complete; run demo from browser

1. **Show the Data Foundation (1 min)**
   - Open Supabase dashboard
   - Show episodes table with 1,171 rows
   - Run query: "SELECT topic_name, COUNT(*) as mentions FROM topic_mentions GROUP BY topic_name ORDER BY mentions DESC"
   - Show bonus: "SELECT entity_type, COUNT(*) FROM extracted_entities GROUP BY entity_type"
   - "We've successfully loaded 6 months of podcast intelligence, including 5,000+ company and person mentions ready for Sprint 2 features"

2. **Demonstrate the API (1 min)**
   - Open browser to API endpoint
   - Show JSON response with real data
   - "Our API responds in 247ms with trend data"

3. **Reveal the Dashboard (3 min)**
   - Navigate to staging URL
   - Enter the staging "access code" when prompted
   - Watch chart load with data
   - Hover over data points
   - "This is 1,000+ hours of podcast intelligence, visualized"

### Measuring Success

Run through our original success criteria:
- ✅ Data is Live: 1,171 episodes in Supabase
- ✅ API is Functional: <500ms response time achieved
- ✅ Dashboard is Functional: Topic Velocity chart working
- ✅ Application is Deployed: Live at [staging-url]
- ✅ Performance: Page loads in 1.8 seconds

### Next Sprint Preview

"Now that we've proven we can transform raw podcast data into valuable insights, Sprint 2 will add:
1. Natural language search across all transcripts (using the embeddings we stored)
2. User authentication for our first alpha testers
3. The Sentiment Heatmap visualization
4. Visual polish: animations, metric cards, and premium effects
5. Ability to customize which topics appear on the chart
6. Entity tracking: "Show me all mentions of Sequoia Capital"
7. Audio playback with streaming from S3 (using pre-signed URLs)

Note: We'll load segments.json data when we build the transcript reading UI with synchronized audio playback."

**Additional Available Data for Future Features:**
The S3 data contains rich metadata we haven't extracted yet:
- Guest/Host information (speaker profiles and roles)
- Categories array (content classification beyond our 5 topics)
- Keywords from transcripts (for enhanced search)
- Entity character positions (for in-transcript highlighting)
- Processing quality metrics (confidence scores, speech-to-music ratios)

---

## Appendix A: Troubleshooting Guide

### Common Issues & Solutions

| Problem | Likely Cause | Solution |
|---------|--------------|----------|
| ETL script fails midway | S3 connection timeout | Add retry logic with exponential backoff |
| Supabase connection errors | Wrong credentials | Double-check service role key, not anon key |
| Chart not showing data | CORS issue | Ensure API allows frontend origin |
| Slow API response | Missing database indexes | Run CREATE INDEX on topic_name, week_number |
| Vercel deployment fails | Missing env variables | Check all variables set in dashboard |
| Database migration fails | Error in schema.sql | Run 'supabase db reset' to restore a clean local database, fix the SQL, and push again |
| **File not found errors** | **Hardcoded paths** | **Use dynamic file discovery function** |
| **Missing entities** | **Wrong folder name** | **Look in cleaned_entities/ not entities/** |
| **Zero KPIs extracted** | **Data format mismatch** | **KPIs may be direct array [], not wrapped {"kpis": []}** |
| **Entity type issues** | **Field name mismatch** | **Use 'label' field for entity type, not 'type'** |

**Rationale for migration troubleshooting:** This provides a critical emergency procedure for the most common and blocking type of development error, making our process safer.

### Emergency Contacts
- Supabase Support: support.supabase.com
- Vercel Support: vercel.com/support
- AWS S3 Issues: Check AWS Status page first

---

## Appendix B: Cost Tracking

### Current Monthly Costs
- Supabase: $0 (free tier)
- Vercel: $0 (hobby tier)
- AWS S3: ~$5 (existing storage)
- **Total: <$10/month**

### When We'll Need to Upgrade
- Supabase: At 500MB data or 2GB transfer
- Vercel: At 100GB bandwidth or need team features
- Monitor usage weekly in both dashboards
- Monitor storage in the Supabase dashboard weekly. We will plan to upgrade to the Pro tier when usage exceeds 400MB.
  - **Rationale:** This is a proactive measure to avoid unexpected costs and service interruptions as we add more data. It establishes a clear trigger for when we need to scale our plan.
- Monitor data egress in the Supabase dashboard. We will plan to upgrade when monthly bandwidth exceeds 1.5GB to avoid hitting the 2GB free-tier cap.
  - **Rationale:** This adds another layer of proactive cost management to prevent unexpected service interruptions from bandwidth limits.
- Upgrade Vercel plan when monthly bandwidth egress exceeds 80GB.

---

*This playbook is your single source of truth. Follow it step by step, test at each checkpoint, and you'll have a working product in 8 days.*

---

## Final Note: What Makes This a True "Genesis Sprint"

This playbook exemplifies exactly what a "Genesis Sprint" should be: proving core value with minimal complexity while laying a foundation for rapid iteration. By focusing on one compelling visualization (Topic Velocity) with real data, we validate the entire concept before building authentication, search, or mobile features.

Every decision—from using Supabase over AWS RDS to deferring user auth—optimizes for speed to value. The result is a lean, mean, insight-generating machine that will wow stakeholders and justify further investment.

**Let's build! 🚀**

---

## Appendix C: Working with Claude Code - Context Management

### Repository Structure

This sprint will create three separate code repositories:

1. **`podinsight-etl`** - Python ETL scripts for data loading
   - Location: Local only (not deployed)
   - Purpose: One-time data migration from S3 to Supabase

2. **`podinsight-api`** - FastAPI backend
   - Location: GitHub → Vercel deployment
   - Purpose: Serves the /api/topic-velocity endpoint

3. **`podinsight-dashboard`** - Next.js frontend
   - Location: GitHub → Vercel deployment
   - Purpose: The user-facing dashboard with Topic Velocity chart

### Creating Context Documents

Each repository should contain both a `PROJECT.md` file and the `business_overview.md` file that Claude Code can reference:

**Note:** Copy the `business_overview.md` file into each repository to provide business context alongside technical instructions.

#### For `podinsight-etl/PROJECT.md`:

```markdown
# PodInsightHQ ETL Script

## Purpose
Load 1,171 podcast episodes from S3 into Supabase for the Genesis Sprint.

## Key Decisions
- One-time script (not a continuous pipeline)
- Topics to track: AI Agents, Capital Efficiency, DePIN, B2B SaaS, Crypto/Web3
- Count each topic ONCE per episode maximum
- S3 bucket: pod-insights-stage (contains processed transcripts and metadata)
- Target database: Supabase (connection via env vars)
- Data structure: <feed_slug>/<guid>/<type>/<filename>

## Data Loading Strategy
- Load: transcripts, metadata, KPIs, entities
- Store paths only: embeddings, audio files
- Defer: segments (large files for future transcript UI)

## Critical Update (June 14, 2025)
Production file naming differs from documentation:
- Transcripts have complex descriptive filenames
- Meta files include GUID in filename
- Entities are in cleaned_entities/ folder
- Must use dynamic file discovery

## Success Criteria
- All 1,171 episodes loaded with unique GUIDs
- 5 topics tracked with mention counts
- Entities extracted (people, companies)
- Date range: Jan-Jun 2025
- S3 paths stored for future audio/search features
```

#### For `podinsight-api/PROJECT.md`:

```markdown
# PodInsightHQ API

## Purpose
Serve topic velocity data for the dashboard via a single endpoint.

## Key Decisions
- Framework: FastAPI on Vercel serverless
- Single endpoint: GET /api/topic-velocity
- Response format: JSON optimized for Recharts
- Performance target: <500ms response time
- Region: London (lhr1)

## Success Criteria
- Returns data for 4 default topics
- 12 weeks of historical data
- CORS enabled for frontend access
```

#### For `podinsight-dashboard/PROJECT.md`:

```markdown
# PodInsightHQ Dashboard

## Purpose
Display Topic Velocity chart with real podcast intelligence data.

## Key Decisions
- Framework: Next.js 14 + TypeScript + Tailwind
- Chart library: Recharts
- Auth: Basic auth via Vercel (no user accounts)
- Topics: AI Agents, Capital Efficiency, DePIN, B2B SaaS (hardcoded)
- Dark mode only, desktop only

## Success Criteria
- Chart loads in <2 seconds
- Displays 4 topic trend lines
- Interactive tooltips on hover
```

### Working with Claude Code - Best Practices

#### 1. Start Each Session with Context

```
I'm working on PodInsightHQ, a podcast intelligence SaaS for VCs and founders. Here's the current context:

[Paste the relevant PROJECT.md]
[The business_overview.md is also available for reference]

We're on [Phase X] of our Genesis Sprint. Today's task:
[Paste specific step from playbook]
```

#### 2. Using Windsurf/Cursor with @-mentions

**✅ DO This (Best Practice):**
```
@playbook.md (so it's available for reference)
@business_overview.md (for understanding the "why")
@project.md (current context)

"I'm starting Phase 2 (ETL development). The playbook is available for your reference, but let's focus on the ETL section specifically. Here's what we need to accomplish today: [paste current step]"
```

**Why This Works:**
- The @playbook gives Claude Code the ability to **look up** information when needed
- The @business_overview provides the business context and target audience understanding
- You're explicitly telling it which section to focus on
- It can reference back to earlier decisions if questions arise
- But it won't get lost trying to process 30 pages upfront

**❌ DON'T Do This:**
```
"Read this entire 30-page playbook first and understand everything before we start coding"
```

**The Key Difference:** Reference vs Read Everything First. Think of it like giving someone a manual - they should have it on their desk, but focus on the current chapter.

#### 3. Progressive Disclosure Strategy

**Don't do this:**
- Dump the entire 30-page playbook into Claude Code
- Start coding without context
- Jump between phases randomly

**Do this:**
- Share PROJECT.md + current phase only
- Reference previous work when building on it
- Keep Claude Code focused on one task at a time

#### 4. Reference Chain for Each Phase

**Phase 1 (Database):**
- Share: PROJECT.md + Step 1.1 + Product decisions table

**Phase 2 (ETL):**
- Share: PROJECT.md + Step 1.2 + Database schema from Phase 1

**Phase 3 (API):**
- Share: PROJECT.md + Step 2.1 + Expected data structure

**Phase 4 (Frontend):**
- Share: PROJECT.md + Step 3.1 + API response format

### Example Session Starters

#### Important Context Management Note:
Include `@business_overview.md` along with other documents to provide the "why" behind technical decisions. The business overview is concise and helps Claude Code understand the target audience (VCs/founders) and business goals.

#### For Database Setup (Windsurf - in `podinsight-etl`):

```
@playbook.md
@business_overview.md
@project.md

I need to set up the database for PodInsightHQ.

Repository: podinsight-etl (local)
Current focus: Phase 1, Step 1.1 - Database Setup with Supabase

The playbook has the technical steps, and business_overview provides context on why we're building this (for a VC/startup audience).

Please help me create the schema with proper migration files.
```

#### For ETL Development (Windsurf - in `podinsight-etl`):

```
@playbook.md
@business_overview.md
@project.md

I'm building the ETL script for PodInsightHQ.

Repository: podinsight-etl (local)
Current focus: Phase 2, Step 1.2 - Data Loading Script
- 1,171 podcast episodes in S3 bucket: pod-insights-stage (already processed)
- Files organized as: <feed_slug>/<guid>/<type>/<filename>
- Target: Supabase database (schema already created)
- Track 5 topics, count once per episode max

CRITICAL: Production uses complex file naming, not simple paths. Must use dynamic discovery.

The business_overview explains why these specific topics matter to our VC/founder audience.

Let's start with the S3 reader module.
```

#### For API Development (Windsurf - in `podinsight-api`):

```
@playbook.md
@business_overview.md
@project.md

I'm creating the API for PodInsightHQ using FastAPI on Vercel.

Repository: podinsight-api (GitHub)
Current focus: Phase 3, Step 2.1 - FastAPI Serverless Setup
Required endpoint: GET /api/topic-velocity

The API will serve trend data to help VCs/founders track emerging topics in podcasts.

Please create the initial project structure with the vercel.json configuration.
```

#### For Frontend Development (Windsurf - in `podinsight-dashboard`):

```
@playbook.md
@business_overview.md
@project.md

I'm building the dashboard for PodInsightHQ using Next.js.

Repository: podinsight-dashboard (GitHub)
Current focus: Phase 4, Step 3.1 - Frontend Dashboard
Starting with v0.dev generated components

The dashboard needs to feel premium for our VC/founder users - dark mode, data-rich visualizations.

Please help me integrate the TopicVelocityChart with real API data.
```

### Quick Reference Card

Save this for easy copy-paste during development:

```
=== PODINSIGHTHQ QUICK CONTEXT ===
What: SaaS turning podcast transcripts into VC/founder intelligence
Goal: Display Topic Velocity chart with real data
Stack: Supabase + FastAPI + Next.js on Vercel
Topics: AI Agents, Capital Efficiency, DePIN, B2B SaaS, Crypto/Web3
Timeline: 8-day Genesis Sprint
Current Phase: [INSERT HERE]
CRITICAL: Production uses complex file naming - must use dynamic discovery
===================================
```

### Repository Quick Reference

| Phase | Repository | Type | Purpose |
|-------|------------|------|---------|
| **Phase 1: Database + ETL** | `podinsight-etl` | Local only | One-time data migration scripts |
| **Phase 2: API** | `podinsight-api` | GitHub → Vercel | FastAPI endpoint deployment |
| **Phase 3: Frontend** | `podinsight-dashboard` | GitHub → Vercel | Next.js dashboard deployment |

### Work Location Summary

- **Part 2 (Database & ETL)**: Work entirely in `podinsight-etl` (local)
- **Part 3 (API)**: Create and work in `podinsight-api` (GitHub)
- **Part 4 (Frontend)**: Create and work in `podinsight-dashboard` (GitHub)

This approach ensures Claude Code always has the right context without being overwhelmed, while maintaining our playbook as the single source of truth.
