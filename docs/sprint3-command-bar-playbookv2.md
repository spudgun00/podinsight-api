# Sprint 3: Instant-Answer Command Bar Playbook

## 🚨 CRITICAL UPDATE: Audio Architecture Pivot

**Major Discovery**: Pre-generating 823,763 audio clips would create 60-80% duplicates and waste ~$10,000/year!

**Solution**: **On-demand clip generation** - Only create clips when users click play:
- Lambda + FFmpeg extracts clips in real-time (2-3s first play)
- Saves 85-95% on storage costs
- Better UX - no upfront loading
- Natural caching for popular content

**Impact on Sprint 3**:
- Phase 1A changed from batch processing to Lambda function
- Frontend handles loading states for first-play
- Overall timeline unchanged, complexity reduced

---

## 🎯 Sprint Overview

**Sprint Duration:** 5-6 working days
**Theme:** "Ask, listen, decide"
**Core Feature:** Conversational intelligence via command bar
**Success Metric:** "This feels like Perplexity but just for podcasts"

### 💡 Advisor-Recommended Enhancements (+2 hours)
Based on advisor feedback, we're adding three simple improvements that deliver 80% of the quality gain:

| Enhancement | Change | Impact |
|------------|--------|---------|
| **Better Recall** | numCandidates: 20 → 100 | Finds more relevant chunks (+10ms) |
| **More Context** | 6 chunks → 10 chunks (~1000 tokens) | Richer answers, better citations |
| **Cleaner UI** | Show 2 sources + "more" toggle | Less overwhelming, cleaner UX |

### Sprint Details
| Aspect | Details |
|--------|---------|
| **Target Users** | Time-poor VCs & founders needing instant insights |
| **Repositories** | `podinsight-etl`, `podinsight-api`, `podinsight-dashboard` |
| **Infrastructure** | MongoDB Atlas (vector search), Modal GPU (embeddings), AWS Lambda (audio) |
| **Definition of Done** | `/` or `⌘K` → ask question → 2-sentence answer with citations → 30s audio plays on-demand (p95 < 2s search, < 3s audio) |

---

## ✅ Prerequisites Checklist

| Component | Requirement | Verification |
|-----------|-------------|--------------|
| **Semantic Chunks** | 823,763 chunks with 768-d embeddings in MongoDB | ✅ DONE - `db.transcript_chunks_768d.count()` |
| **Atlas Search Index** | `vector_index_768d` configured | ✅ DONE - Dimensions: 768, Similarity: cosine |
| **Modal Embedding Service** | Instructor-XL model deployed | ✅ DONE - `modal_web_endpoint_simple.py` |
| **Search API** | `/api/search` endpoint operational | ✅ DONE - 85-95% relevance achieved |
| **Audio Architecture** | On-demand generation strategy | ✅ DECIDED - Lambda + FFmpeg approach |
| **Audio Implementation** | Lambda function for clip extraction | 🔲 TODO - Build in Phase 1A |
| **UI Components** | Radix UI / shadcn installed | 🔲 TODO - `pnpm install @radix-ui/react-dialog cmdk` |

### What's Already Built:
- ✅ **Modal.com GPU Infrastructure**: 2.1GB Instructor-XL model running on A10G
- ✅ **MongoDB Vector Search**: Operational with 768D embeddings
- ✅ **Search API**: `/api/search` endpoint returning relevant chunks with metadata
- ✅ **Performance**: 3-5s warm responses, 14s cold start (physics limit)
- ✅ **Security**: MongoDB credentials rotated, git history cleaned

### What Sprint 3 Adds:
- 🎯 **Command Bar UI**: Slash-key activated search interface
- 🎯 **Answer Synthesis**: LLM generates 2-sentence summaries with citations
- 🎯 **Audio Integration**: 30-second proof clips generated on-demand
- 🎯 **Polished UX**: Glassmorphism, smooth animations, keyboard navigation

### Key Architectural Insight:
**Why On-Demand Audio Is Superior**:
- **No Duplicates**: Chunks at 1s, 3s, 5s would all generate identical 0-30s clips
- **User-Driven**: Only ~2-3 clips played per search (not all 6)
- **Smart Caching**: Popular clips cached, unpopular ones never generated
- **Cost Alignment**: Pay for value delivered, not theoretical coverage

### Sprint 3 Enhancements (Based on Advisor Feedback):
- 📈 **Better Recall**: Increased numCandidates from 20 → 100 (+10ms latency)
- 📈 **More Context**: Pass 10 chunks (~1000 tokens) instead of 6 to LLM
- 📈 **Cleaner UI**: Show 2 citations by default, rest behind "+ more" toggle
- 📈 **Total Time**: +2 hours for 80% quality improvement

---

## 🔧 Phase 1: Backend Infrastructure

### Phase 1 Setup Prompt for Claude Code:
```
I'm starting Sprint 3 Phase 1 (Backend Infrastructure) for PodInsightHQ.

Please read these essential context files:
@sprint3_command_bar_playbook.md - Complete sprint guide
@podinsight-business-overview.md - Business context
@PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md - Current system architecture
@AUDIO_CLIP_ARCHITECTURE_ANALYSIS.md - Critical on-demand audio pivot

Before we begin coding, please:
1. Review the "Documentation Best Practices" section in the playbook appendix
2. Create the following documentation structure in this repository:
   docs/
   └── sprint3/
       ├── README.md (Sprint overview & current status)
       ├── implementation_log.md (Daily progress tracking)
       ├── test_results.md (Running test log)
       ├── issues_and_fixes.md (Problems & solutions)
       └── architecture_updates.md (System design changes)

3. Note the Sprint Documentation Requirements for each phase
4. Review what's already built vs what needs implementation

Current Phase: 1A (Audio Clip Generation) and 1B (Answer Synthesis)
Repository: podinsight-api (for both - Lambda + API enhancement)

Let's start with creating the documentation structure, then proceed with implementation.
```

### 1A. Query Embedding Microservice (`podinsight-etl`)

**Status: ✅ ALREADY BUILT**

**What Exists:**
- Modal endpoint: `https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run`
- Uses Instructor-XL with same instruction prefix as chunks
- Returns 768-dim embeddings
- Performance: ~415ms warm, 14s cold start

**No Action Needed** - The existing Modal endpoint already handles query embedding!

### 1A-Alternative. Audio Clip Generation (PIVOTED TO ON-DEMAND)

### ⚠️ CRITICAL ARCHITECTURAL PIVOT
**Discovery**: Pre-generating clips for all 823,763 chunks would create 60-80% duplicate files and cost ~$10,000/year. All chunks with start_time < 15s generate identical clips!

**New Approach**: On-demand clip generation via AWS Lambda - only create clips when users actually click play.

### Phase 1A Setup Prompt for Claude Code:
```
I'm implementing on-demand audio clip generation (Phase 1A) for Sprint 3.

Repository: podinsight-api (NOT etl - this is now an API feature)
Task: Create Lambda function for real-time audio clip extraction

Please:
1. Create/update docs/sprint3/implementation_log.md documenting the pivot
2. Note the massive cost savings from on-demand approach
3. Create Lambda function with FFmpeg layer
4. Add API endpoint for clip requests

Ready to implement the on-demand architecture.
```

**Context:** Users only play 2-3 clips per search, not all 6 results.

**Architecture Clarification**:
- **2-3s chunks**: For precise semantic search (finding exact moments)
- **30s clips**: For human context when verifying claims
- **On-demand**: Bridge between precision search and listening experience

**Why On-Demand Is Better:**
- Saves 85-95% on storage costs
- No duplicate clips (each has unique timestamp range)
- Scales with actual usage, not data volume
- 2-3s generation time acceptable for verification use case

**Definition of Done:**
✅ Lambda function extracts 30s clips on-demand
✅ API endpoint: `/api/v1/audio_clips/{episode_id}?start_time_ms={start}`
✅ S3 structure: `/audio_clips/{episode_id}/{start_ms}-{end_ms}.mp3`
✅ Cache hit: ~200ms, Cache miss: ~2-3s
✅ No pre-generation batch job needed!

**Copy-Paste Prompt for Claude Code:**
```
I need to implement on-demand audio clip generation for PodInsightHQ.

Context from critical analysis:
- Pre-generating 823K clips would create 60-80% duplicates
- Clips in first 15s of episodes are all identical (0-30s)
- On-demand saves ~$10K/year and delivers better UX
- Users only play 2-3 clips, not all search results

Requirements:
1. Create Lambda function (audio_clip_generator.py):
   - Accepts: episode_id, start_time_ms, duration_ms (default 30000)
   - Downloads source MP3 from S3 pod-insights-raw bucket
   - Uses FFmpeg to extract segment
   - Uploads to: s3://pod-insights-clips/audio_clips/{episode_id}/{start_ms}-{end_ms}.mp3
   - Returns pre-signed URL (24hr expiry)

2. FFmpeg extraction command:
   ffmpeg -i input.mp3 -ss {start_s} -t 30 -c copy output.mp3

3. API endpoint in podinsight-api:
   GET /api/v1/audio_clips/{episode_id}?start_time_ms={start}&duration_ms=30000

   Response:
   {
     "clip_url": "https://...",
     "cache_hit": true/false,
     "generation_time_ms": 150
   }

4. Lambda optimizations:
   - Check S3 for existing clip before generating
   - Use Lambda layers for FFmpeg binary
   - Set memory to 1GB for faster processing
   - 30s timeout sufficient

Please implement with proper error handling and CloudWatch logging.
```

**Testing Prompt for Claude Code:**
```
Create tests for on-demand audio clip generation.

Test Requirements:
1. Lambda unit tests (test_audio_lambda.py):
   - Mock S3 operations (boto3)
   - Test cache hit/miss logic
   - Test clip naming: "12500-42500.mp3"
   - Test error cases (missing episode)
   - Verify FFmpeg command construction

2. API integration tests (test_audio_api.py):
   - Test endpoint with valid episode_id
   - Test response format and timing
   - Test concurrent requests (5 parallel)
   - Verify pre-signed URL works
   - Test missing episode returns 404

3. Performance benchmarks:
   - Measure cold start latency
   - Cache hit should be <500ms
   - Cache miss should be <4s
   - Monitor Lambda memory usage

Include moto for S3 mocking and track metrics.
```

**Required Documentation:**
1. **Architecture Decision Record**: `docs/sprint3/adr_001_on_demand_audio.md`
   - Document why we pivoted from batch processing
   - Cost analysis showing $10K savings
2. **Implementation Log**: `docs/sprint3/audio_generation_log.md`
   - Track Lambda deployment steps
   - Document FFmpeg layer setup
3. **Performance Metrics**: `docs/sprint3/audio_performance.md`
   - Cache hit rates, generation times

### 1B. Answer Pipeline Enhancement (`podinsight-api`)

### Phase 1B Setup Prompt for Claude Code:
```
I'm implementing answer synthesis enhancement (Phase 1B) for Sprint 3.

Repository: podinsight-api
Task: Add LLM synthesis to existing /api/search endpoint

Please:
1. Update docs/sprint3/implementation_log.md with Phase 1B start
2. Review current search implementation in the codebase
3. Add OpenAI integration following the playbook specs
4. Create test mocks for deterministic testing

Ready to enhance the search endpoint with answer generation.
```

**Status: ⚙️ PARTIALLY BUILT**

**What Exists:**
- ✅ `/api/search` endpoint returns relevant chunks
- ✅ MongoDB vector search with metadata join
- ✅ 85-95% search relevance

**What's Missing:**
- ❌ LLM answer synthesis (2-sentence summary)
- ❌ Citation extraction and formatting
- ❌ Audio clip URLs in response

**Definition of Done:**
✅ Enhance `/api/search` to generate synthesized answers
✅ Add OpenAI integration for answer generation
✅ Format citations with superscripts
✅ Include audio URLs in response

**Copy-Paste Prompt for Claude Code:**
```
I need to enhance the existing /api/search endpoint to add answer synthesis.

Current State:
- /api/search returns raw chunks from MongoDB vector search
- Each chunk has: text, episode_id, chunk_index, start_time, score
- Metadata includes: episode_title, podcast_name, published_date

New Requirements:
1. After getting search results, pass top 10 chunks to OpenAI:
   - Model: gpt-3.5-turbo-0125
   - Context: ~1000 tokens (10 chunks × ~100 tokens each)
   - System prompt: "You are a podcast intelligence assistant. Given search results, provide a 2-sentence synthesis (max 60 words) that directly answers the question. Cite sources with superscript numbers ¹²³."
   - Include chunk text and metadata in prompt

2. Parse LLM response to:
   - Extract which chunks were cited (by number)
   - Build citation objects with full metadata
   - Generate S3 signed URLs for audio clips

3. Enhanced response format:
   {
     "answer": "VCs are concerned that AI agent valuations...",
     "citations": [
       {
         "index": 1,
         "episode_id": "abc123",
         "episode_title": "AI Bubble Discussion",
         "podcast_name": "All-In",
         "timestamp": "27:04",
         "start_seconds": 1624,
         "chunk_index": 45
         // Note: audio_url removed - generated on-demand
       }
     ],
     "raw_chunks": [...existing format...],
     "processing_time_ms": 2150
   }

4. Add OPENAI_API_KEY to environment variables
5. Handle errors with user-friendly messages:
   - OpenAI timeout: "Taking a bit longer than usual..."
   - No results: "No relevant discussions found. Try rephrasing?"
   - API error: "Something went wrong. Please try again."

Keep existing search functionality intact - add synthesis as enhancement.
```

**Testing Prompt for Claude Code:**
```
Create comprehensive tests for the enhanced answer synthesis feature.

Test Requirements:
1. Unit tests (test_answer_synthesis.py):
   - Mock OpenAI responses for deterministic testing
   - Test citation extraction (superscript parsing)
   - Test error handling (OpenAI timeout/failure)
   - Test response formatting
   - Verify audio URL generation

2. Integration tests (test_search_e2e.py):
   - Test 10 common VC queries:
     * "AI agent valuations"
     * "seed stage pricing"
     * "founder market fit"
     * "B2B SaaS metrics"
   - Verify each returns 2-sentence answer
   - Check citation count matches superscripts
   - Validate audio URLs are accessible
   - Test "+ more sources" expansion works
   - Verify 10 chunks passed to LLM (check logs)

3. Performance tests:
   - Measure latency with/without synthesis
   - Test concurrent requests (10 parallel)
   - Verify timeout handling at 5s

Include fixtures for common query patterns and expected outputs.
```

**Required Documentation:**
1. **Implementation Log**: `docs/sprint3/answer_synthesis_log.md`
   - OpenAI prompt engineering iterations
   - Citation parsing approach
2. **API Documentation**: `docs/sprint3/api_enhancements.md`
   - Updated endpoint specs with examples
   - Error response formats
3. **Test Results**: `docs/sprint3/synthesis_test_results.md`
   - Query quality scores
   - Performance benchmarks

**MongoDB Aggregation Pipeline (Detailed):**

```javascript
// Enhanced pipeline with better recall
[
  // 1. Vector Search with improved candidate pool
  {
    $vectorSearch: {
      index: "vector_index_768d",
      path: "embedding_768d",
      queryVector: embedding,
      numCandidates: 100,    // ← INCREASED from 20 for better recall
      limit: 20              // Still return manageable number
    }
  },

  // 2. Keyword Boost (unchanged)
  {
    $search: {
      text: {
        query: user_terms,
        path: ["text", "episode_title"],
        score: { boost: { value: 5 } }
      }
    }
  },

  // 3. Composite Scoring (unchanged)
  {
    $addFields: {
      composite_score: {
        $add: [
          { $multiply: ["$score", 0.7] },
          { $multiply: ["$search_score", 0.3] }
        ]
      }
    }
  },

  // 4. Diversity - Max 2 chunks per episode (already implemented)
  {
    $group: {
      _id: "$episode_id",
      chunks: { $push: "$$ROOT" },
      max_score: { $max: "$composite_score" }
    }
  },
  { $unwind: { path: "$chunks", includeArrayIndex: "rank" } },
  { $match: { rank: { $lt: 2 } } },

  // 5. Final selection - take top 10 for ~1000 tokens
  { $sort: { "chunks.composite_score": -1 } },
  { $limit: 10 }  // ← INCREASED from 6 for more context
]
```

**Answer Generator Module:**

```python
# File: services/answer_generator.py

class AnswerGenerator:
    """Generate concise, cited answers from podcast chunks"""

    SYSTEM_PROMPT = """
    You are a podcast intelligence assistant. Given search results,
    provide a 2-sentence synthesis (max 60 words) that directly
    answers the question. Cite sources with superscript numbers ¹².

    Rules:
    - Be specific and actionable
    - Use exact quotes when impactful
    - Require ≥2 distinct episodes as sources
    - Format: "Key insight from podcasts. Supporting detail."
    """

    async def generate(self, question: str, chunks: List[Chunk]) -> AnswerResponse:
        # Implementation details...
```

**API Endpoint:**

```python
@app.post("/api/ask")
async def ask_question(request: AskRequest):
    """
    Main command bar endpoint

    Request:
    {
        "q": "What are VCs saying about AI agent valuations?",
        "filters": {"feed_slug": ["acquired", "all-in"]},
        "k": 6
    }

    Response:
    {
        "answer": "VCs express concern that AI agent valuations are outpacing actual capital efficiency¹². Recent rounds show 50-100x revenue multiples despite unclear moats².",
        "citations": [
            {
                "episode_id": "abc123",
                "episode_title": "AI Bubble or Breakthrough?",
                "podcast_name": "All-In",
                "timestamp": "27:04",
                "start_seconds": 1624,
                "audio_url": "https://..."
            }
        ],
        "processing_time_ms": 1847
    }
    """
```

---

## 🎨 Phase 2: Frontend Implementation

### Phase 2 Setup Prompt for Claude Code:
```
I'm starting Sprint 3 Phase 2 (Frontend Implementation) for PodInsightHQ.

Please read these essential context files:
@sprint3_command_bar_playbook.md - Complete sprint guide
@podinsight-business-overview.md - Business context
@PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md - Current system architecture

Before we begin coding, please:
1. Review the "Documentation Best Practices" section in the playbook appendix
2. Create/verify the documentation structure exists:
   docs/
   └── sprint3/
       ├── README.md (Update with Phase 2 status)
       ├── implementation_log.md (Continue from Phase 1)
       ├── test_results.md (Add frontend test results)
       ├── issues_and_fixes.md (Track UI/UX issues)
       └── architecture_updates.md (Document component architecture)

3. Note the Sprint Documentation Requirements for frontend work
4. Review the UI/UX specifications and mockups

Current Phase: 2A (Command Bar) and 2B (Answer Card)
Repository: podinsight-dashboard
Previous Phase Status: [summarize Phase 1 completion]

Let's update the sprint documentation, then build the UI components.
```

### User Flow: Before → After

#### 📸 "Before Search" State
| Zone | Purpose | Interaction Details |
|------|---------|-------------------|
| **Logo Bar** | Brand & navigation | Command bar sits 56px below, never collides |
| **Command Bar** | First-focus element | Placeholder: "Ask anything... (/)"<br>Auto-expands on focus |
| **Dashboard Charts** | Keep dashboard alive | Blur to 20% opacity when bar focused |

#### ✨ "After Search" State
```
╭───────────── Answer Card ─────────────╮
│  VCs express concern that AI agent    │
│  valuations outpace fundamentals¹².   │
│                                       │
│  Sources (2)                          │
│  1 • Acquired – Feb 24      ▶ 47:13  │ ← 30s clip
│  2 • All-In – E185         ▶ 36:04  │ ← 30s clip
│                                       │
│  [Open full episode]                  │
╰───────────────────────────────────────╯
```

**Key UX Decisions:**
- Answer synthesis from top-k chunks (k=10 default)
- Show only 2-5 best citations (hide rest behind "+More")
- 30-second audio previews load but don't auto-play
- ESC or outside-click dismisses overlay
- Background charts become `pointer-events-none`

### 2A. Global Command Bar Component

### Phase 2A Setup Prompt for Claude Code:
```
I'm implementing the command bar UI (Phase 2A) for Sprint 3.

Repository: podinsight-dashboard
Task: Create global command bar with keyboard shortcuts

Please:
1. Update docs/sprint3/implementation_log.md with Phase 2A start
2. Install required dependencies: @radix-ui/react-dialog, cmdk
3. Review the UI specifications and user flow in the playbook
4. Set up component test structure with data-testid attributes

Ready to build CommandBar.tsx following the glassmorphism design.
```

### v0 Component Generation Prompts:

**v0 Prompt 1 - Search Trigger (Before State):**
```
Create a search command bar component for a dark-themed podcast intelligence dashboard.

Visual Requirements:
- Fixed position below header (56px from top), horizontally centered
- Max width 720px on desktop, 90vw on mobile
- Glassmorphism effect: semi-transparent black background (bg-black/80) with backdrop blur
- White/10 border with rounded corners (rounded-2xl)
- Smooth shadow for depth (shadow-2xl)

Functionality:
- Placeholder text: "Ask anything..." with "/" keyboard hint styled smaller and dimmer
- Opens on "/" key press or click
- Also opens with Cmd+K (Mac) or Ctrl+K (Windows)
- Auto-hides when scrolling down, reappears when scrolling up
- When focused, blur background content to 20% opacity

Component Structure:
- Use Radix UI Dialog for accessibility
- Use cmdk library for command palette functionality
- Include loading spinner during search
- Smooth transitions (200ms) for all interactions

The component should feel premium and responsive, like Raycast or Linear's command bars.
```

**v0 Prompt 2 - Complete Command Bar with Answer Card (After State):**
```
Create a command bar with AI-powered answer card for a podcast intelligence platform.

Layout:
- Command bar fixed 56px from top, centered, max-width 720px
- Answer card appears below search input within the same dialog
- Glassmorphism throughout: bg-black/80, backdrop-blur-xl, border-white/10

Command Input:
- Large text input (text-lg) with generous padding (px-6 py-4)
- Placeholder: "Ask anything about venture capital, startups, or tech..."
- Loading spinner on right side during processing

Answer Card Design:
- 2-sentence answer with superscript citations (¹²³)
- "Sources" section below with citation chips
- Each citation chip shows:
  - Index number (matches superscript)
  - Podcast name (bold)
  - Episode title (truncated with ellipsis)
  - Timestamp (e.g., "47:13")
  - Mini audio player button (play/pause icon)
- Active audio chip gets blue glow effect (ring-2 ring-blue-500/50)

Interactions:
- "/" or Cmd+K to open
- Enter to search
- ESC to close
- Click outside to close
- Audio plays inline (30-second clips)
- "Open full episode" link at bottom

Style Details:
- Dark theme with high contrast for readability
- Smooth animations (200ms transitions)
- Hover states on all interactive elements
- Mobile responsive with proper touch targets

Example Answer:
"VCs express concern that AI agent valuations are outpacing actual capital efficiency and business fundamentals¹². Recent seed rounds show 50-100x revenue multiples despite unclear moats²."

Include TypeScript interfaces for the data structure.
```

**v0 Prompt 3 - Mini Audio Player Component:**
```
Create a minimal audio player component for 30-second podcast clips.

Design:
- Compact circular button (40x40px) with play/pause icon
- Progress ring around button showing playback progress
- Smooth transitions between play/pause states
- Optional waveform visualization (simplified, 3-5 bars)

Functionality:
- Load audio from provided URL (30-second MP3 clips)
- Play/pause on click
- Update progress ring during playback
- Auto-reset when finished
- Emit onPlay/onPause events for parent component

Visual States:
- Default: Gray play icon, no ring
- Loading: Subtle pulse animation
- Playing: Blue pause icon, animated progress ring
- Paused: Blue play icon, static progress ring
- Hover: Slight scale increase (1.05)

Integration:
- Accept src prop for audio URL
- Expose playing state to parent
- Handle loading errors gracefully
- Preload audio on component mount

Use HTML5 audio element with React hooks for state management.
```

**Design Specifications:**

| Property | Value |
|----------|-------|
| **Trigger Keys** | `/` (slash) and `⌘K` (Cmd+K) |
| **Position** | 56px below logo, centered |
| **Width** | 640px max (desktop), 90vw (mobile) |
| **Style** | Glassmorphism with dark theme |
| **Animation** | Smooth slide + fade (200ms) |
| **Scroll Behavior** | Auto-hide on scroll down, reappear on scroll up |
| **Background Effect** | Charts blur to 20% opacity when focused |

**Component Structure:**

```tsx
// components/CommandBar.tsx
import { useState, useEffect, useMemo } from 'react';
import { Command } from 'cmdk';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { useHotkeys } from '@/hooks/use-hotkeys';
import { useScrollDirection } from '@/hooks/use-scroll-direction';
import { debounce } from 'lodash';

export function CommandBar() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState<AnswerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const scrollDirection = useScrollDirection();

  // Auto-hide on scroll down
  const isVisible = scrollDirection !== 'down' || open;

  // Keyboard shortcuts
  useHotkeys('/', () => setOpen(true));
  useHotkeys('cmd+k', () => setOpen(true));
  useHotkeys('escape', () => {
    setOpen(false);
    setAnswer(null);
    setError(null);
  });

  // Debounce search to prevent rapid API calls
  const handleSearch = async (searchQuery: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, limit: 10 })
      });

      if (!response.ok) throw new Error('Search failed');

      const data = await response.json();
      setAnswer(data);
    } catch (err) {
      setError('Search error occurred');
    } finally {
      setLoading(false);
    }
  };

  const debouncedSearch = useMemo(
    () => debounce(handleSearch, 300),
    []
  );

  // Blur background charts when focused
  useEffect(() => {
    const charts = document.querySelector('[data-charts-container]');
    if (charts) {
      charts.style.opacity = open ? '0.2' : '1';
      charts.style.transition = 'opacity 200ms';
      charts.style.pointerEvents = open ? 'none' : 'auto';
    }
  }, [open]);

  return (
    <>
      {/* Persistent search trigger */}
      <div
        className={`fixed top-[56px] left-1/2 -translate-x-1/2 w-full max-w-[720px] mx-auto z-50 transition-transform duration-200 ${
          isVisible ? 'translate-y-0' : '-translate-y-full'
        }`}
      >
        <button
          onClick={() => setOpen(true)}
          className="w-full px-6 py-4 bg-black/80 backdrop-blur-xl border border-white/10 rounded-2xl text-left text-gray-500 hover:text-gray-300 transition-colors"
        >
          Ask anything... <span className="text-xs ml-2 opacity-50">(/)</span>
        </button>
      </div>

      {/* Command Dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="fixed top-[56px] left-1/2 -translate-x-1/2 w-full max-w-[720px] p-0 bg-black/80 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl">
          <Command className="overflow-hidden rounded-2xl">
            <div className="relative">
              <input
                className="w-full px-6 py-4 text-lg bg-transparent border-0 outline-none placeholder:text-gray-500"
                placeholder="Ask anything about venture capital, startups, or tech..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={async (e) => {
                  if (e.key === 'Enter' && query.trim()) {
                    await debouncedSearch(query);
                  }
                }}
                autoFocus
              />
              {loading && <LoadingSpinner />}
            </div>

            {answer && (
              <AnswerCard
                answer={answer}
                onClose={() => {
                  setOpen(false);
                  setAnswer(null);
                }}
              />
            )}

            {/* User-friendly error state */}
            {error && !loading && (
              <div className="px-6 py-4 text-center">
                <p className="text-gray-400">
                  Hmm, couldn't find anything. Try another question?
                </p>
                <p className="text-xs text-gray-500 mt-2">
                  Tip: Ask about topics like "AI valuations" or "seed funding"
                </p>
              </div>
            )}
          </Command>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

### 2B. Answer Card Component

### Phase 2B Setup Prompt for Claude Code:
```
I'm implementing the answer card component (Phase 2B) for Sprint 3.

Repository: podinsight-dashboard
Task: Create answer display with citations and audio players

Please:
1. Continue docs/sprint3/implementation_log.md with Phase 2B
2. Review the answer card mockup and specifications
3. Create AnswerCard and SourceChip components
4. Implement MiniAudioPlayer with proper state management

Ready to build the answer visualization components.
```

**Visual Design:**
- Clean, scannable layout with clear hierarchy
- Answer text with inline superscript citations
- Source chips showing podcast + timestamp
- Inline audio player with waveform visualization
- "Open full episode" CTA

```tsx
// components/AnswerCard.tsx
interface AnswerCardProps {
  answer: AnswerResponse;
  onClose: () => void;
}

export function AnswerCard({ answer, onClose }: AnswerCardProps) {
  const [showAllSources, setShowAllSources] = useState(false);

  // Show 2 citations by default, rest behind "more"
  const visibleCitations = showAllSources
    ? answer.citations
    : answer.citations.slice(0, 2);
  const hiddenCount = answer.citations.length - 2;

  return (
    <div className="border-t border-white/10">
      {/* Answer Section */}
      <div className="px-6 py-4">
        <p className="text-white text-base leading-relaxed">
          {answer.answer}
        </p>
      </div>

      {/* Sources Section */}
      <div className="px-6 pb-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">
          Sources ({answer.citations.length})
        </h3>

        <div className="space-y-3">
          {visibleCitations.map((citation, idx) => (
            <SourceChip
              key={citation.episode_id}
              citation={citation}
              index={idx + 1}
            />
          ))}

          {/* Show More Button */}
          {hiddenCount > 0 && !showAllSources && (
            <button
              onClick={() => setShowAllSources(true)}
              className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              + {hiddenCount} more source{hiddenCount > 1 ? 's' : ''}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
```

**Source Chip with Audio Player:**

```tsx
// components/SourceChip.tsx
export function SourceChip({ citation, index }) {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  // On-demand audio clip generation
  const handlePlayClick = async () => {
    if (!audioUrl) {
      setLoading(true);
      try {
        // Request clip generation (may take 2-3s on first play)
        const response = await fetch(
          `/api/v1/audio_clips/${citation.episode_id}?start_time_ms=${citation.start_seconds * 1000}`
        );
        const data = await response.json();
        setAudioUrl(data.clip_url);
        setPlaying(true);
      } catch (error) {
        console.error('Failed to generate audio clip:', error);
      } finally {
        setLoading(false);
      }
    } else {
      setPlaying(!playing);
    }
  };

  return (
    <div className={`
      flex items-center gap-3 p-3 rounded-lg bg-white/5
      transition-all duration-200
      ${playing ? 'ring-2 ring-blue-500/50 bg-white/10' : 'hover:bg-white/10'}
    `}>
      <span className="text-xs font-mono text-gray-500">
        {index}
      </span>

      <div className="flex-1">
        <p className="text-sm font-medium text-white">
          {citation.podcast_name}
        </p>
        <p className="text-xs text-gray-400 truncate">
          {citation.episode_title}
        </p>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500">
          {citation.timestamp}
        </span>

        {loading ? (
          <div className="w-10 h-10 flex items-center justify-center">
            <LoadingSpinner className="w-5 h-5" />
          </div>
        ) : (
          <MiniAudioPlayer
            src={audioUrl}
            onPlayClick={handlePlayClick}
            playing={playing}
            onPause={() => setPlaying(false)}
          />
        )}
      </div>
    </div>
  );
}
```

**Testing Prompt for Claude Code:**
```
Create comprehensive UI tests for the command bar components.

Test Requirements:
1. Component tests (CommandBar.test.tsx):
   - Test keyboard shortcuts (/, ⌘K, ESC)
   - Test scroll hide/show behavior
   - Test background blur effect
   - Mock API responses
   - Test loading states

2. Integration tests (command-bar.cy.ts):
   - Full user flow: open → search → view answer
   - Audio playback interaction
   - Mobile responsiveness
   - Accessibility (screen reader, keyboard nav)
   - Error states (API failure)

3. Visual regression tests:
   - Command bar in all states
   - Answer card with 1-5 citations
   - Audio player states
   - Dark mode consistency

Include data-testid attributes for reliable selection.
```

**Required Documentation:**
1. **Component Architecture**: `docs/sprint3/frontend_architecture.md`
   - Component hierarchy and data flow
   - State management approach
2. **UI/UX Decisions**: `docs/sprint3/design_decisions.md`
   - Why glassmorphism, animation timings
   - Accessibility considerations
3. **Test Coverage**: `docs/sprint3/frontend_test_results.md`
   - Component test coverage report
   - E2E test scenarios and results

---

## 🧪 Phase 3: Testing & QA

### Phase 3 Setup Prompt for Claude Code:
```
I'm starting Sprint 3 Phase 3 (Testing & QA) for PodInsightHQ.

Please read these essential context files:
@sprint3_command_bar_playbook.md - Complete sprint guide
@podinsight-business-overview.md - Business context
@PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md - Current system architecture
@docs/sprint3/implementation_log.md - What we've built so far
@docs/sprint3/issues_and_fixes.md - Known issues to test

Before we begin testing:
1. Review all test requirements in each phase section
2. Update the documentation:
   - test_results.md with comprehensive test plan
   - Create test coverage report structure
   - Set up test data fixtures

3. Verify all repositories have tests:
   - podinsight-etl: Audio generation tests
   - podinsight-api: Answer synthesis tests
   - podinsight-dashboard: Component & E2E tests

Current Phase: 3 (Testing all Sprint 3 features)
Repositories: All three (etl, api, dashboard)

Let's create a comprehensive test suite following the playbook specifications.
```

### Testing Matrix

| Layer | Tool | Test Scenarios |
|-------|------|----------------|
| **Unit** | Jest/Pytest | • Embedding dimensions<br>• Answer length constraints<br>• Citation extraction |
| **API** | HTTPx | • p95 latency < 200ms<br>• Concurrent requests<br>• Error handling |
| **E2E** | Cypress | • Slash key → Question → Answer flow<br>• Audio playback<br>• Mobile responsiveness |
| **Visual** | Percy | • Command bar states<br>• Dark mode consistency<br>• Loading states |

### Sample E2E Test:

```javascript
// cypress/e2e/command-bar.cy.js
describe('Command Bar', () => {
  it('provides answers to VC questions', () => {
    cy.visit('/');

    // Open command bar
    cy.get('body').type('/');
    cy.get('[data-testid="command-bar"]').should('be.visible');

    // Ask a question
    cy.get('input[placeholder*="Ask anything"]')
      .type('What are VCs saying about AI valuations?{enter}');

    // Verify answer appears
    cy.get('[data-testid="answer-text"]', { timeout: 3000 })
      .should('contain', 'valuation')
      .and('contain', '¹');

    // Verify citations
    cy.get('[data-testid="citation"]').should('have.length.gte', 2);

    // Play audio
    cy.get('[data-testid="audio-player"]').first().click();
    cy.get('audio').should('have.prop', 'paused', false);
  });
});
```

---

## 📊 Phase 4: Metrics & Monitoring

### Phase 4 Setup Prompt for Claude Code:
```
I'm starting Sprint 3 Phase 4 (Metrics & Monitoring) for PodInsightHQ.

Please read these essential context files:
@sprint3_command_bar_playbook.md - Complete sprint guide
@podinsight-business-overview.md - Business context
@PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md - Current system architecture
@docs/sprint3/test_results.md - Test outcomes to monitor

Before implementing analytics:
1. Review the KPIs and metrics requirements
2. Update documentation:
   - architecture_updates.md with analytics data flow
   - Create metrics_implementation.md for tracking setup
   - Document event naming conventions

3. Set up analytics infrastructure:
   - Amplitude events in frontend
   - Datadog APM in backend
   - Custom metrics for audio playback

Current Phase: 4 (Metrics & Monitoring)
Repositories: Primarily podinsight-dashboard and podinsight-api

Let's implement comprehensive tracking following the playbook KPIs.
```

### Key Performance Indicators

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Time to Answer (p95)** | < 2 seconds | Datadog APM trace on `/api/ask` |
| **Adoption Rate** | 40% of sessions | Amplitude: `command_bar_opened` event |
| **Citation Diversity** | ≥2 episodes/answer | MongoDB aggregation query |
| **Audio Engagement** | 30% play >5s | Custom event: `audio_played_duration` |

### Amplitude Events:

```javascript
// Track command bar usage
amplitude.track('command_bar_opened', {
  trigger_method: 'slash_key' | 'cmd_k' | 'click',
  session_duration_ms: Date.now() - sessionStart
});

amplitude.track('question_asked', {
  question_length: query.length,
  has_filters: !!filters,
  response_time_ms: responseTime
});

amplitude.track('audio_played', {
  episode_id: citation.episode_id,
  duration_seconds: playDuration,
  completion_percentage: (playDuration / 30) * 100
});
```

---

## 💰 Cost Analysis

| Component | Usage | Est. Cost | Credit Source |
|-----------|-------|-----------|---------------|
| **OpenAI GPT-3.5** | 1,000 answers | $18 | Pay-as-you-go |
| **Modal Query Embeds** | Already built | $0 | Existing endpoint |
| **MongoDB Atlas** | Vector operations | Covered | $500 credits |
| **Audio Clips (Lambda)** | ~500 clips/month | $5-10 | AWS Free Tier + minimal |
| **S3 Storage** | ~10GB growing | $2/month | Pay-as-you-go |
| **Total Monthly** | Normal usage | < $35 | Well within budget |

**Savings from On-Demand**:
- Avoided: $10,000/year in storage for unused clips
- Avoided: 229 hours of batch processing compute
- Gained: Pay only for clips users actually play

---

## ⚠️ Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Long Answers** | >2 sentences returned | Set `max_tokens=80`, `temperature=0` |
| **Single Episode Dominance** | One podcast in all citations | Apply diversity grouping in pipeline |
| **Atlas Index Error** | "Index not found" | Check case-sensitive name: `vector_index_768d` |
| **Audio Generation Timeout** | Clip takes >5s | Increase Lambda memory to 1GB |
| **First Play Slow** | 2-3s wait for audio | Add loading spinner, set user expectations |
| **Lambda Cold Start** | Inconsistent clip timing | Keep Lambda warm with scheduled pings |
| **FFmpeg Error** | Clip generation fails | Ensure FFmpeg layer properly configured |
| **S3 Permissions** | Can't access audio files | Check Lambda IAM role has S3 read/write |

---

## 🚀 Launch Checklist

### Pre-Launch Checklist
- [ ] Lambda function deployed for on-demand audio generation
- [ ] FFmpeg layer configured in Lambda
- [ ] API endpoint `/api/v1/audio_clips/{episode_id}` working
- [ ] Frontend handles loading state for first-play audio
- [ ] OpenAI API key configured and tested
- [ ] Command bar component renders correctly
- [ ] Keyboard shortcuts working (/, ⌘K, ESC)
- [ ] Answer synthesis returns 2 sentences
- [ ] Citations formatted with superscripts
- [ ] Audio players handle on-demand generation gracefully
- [ ] Mobile responsive design verified
- [ ] Error states handled gracefully
- [ ] Performance meets targets (<2s p95, audio <3s)

### Documentation Checklist
- [ ] Architecture Decision Record (ADR) for on-demand audio pivot
- [ ] Implementation logs updated daily
- [ ] Test results documented
- [ ] Architecture diagrams updated with Lambda flow
- [ ] API documentation includes audio endpoint
- [ ] Known issues tracked
- [ ] Performance benchmarks recorded (cache hit rates)
- [ ] Cost savings documented ($10K/year avoided)

### Post-Launch Monitoring
- [ ] Amplitude events firing correctly
- [ ] Error rates < 1%
- [ ] User adoption > 40%
- [ ] Audio play rate > 30%
- [ ] Audio generation success rate > 95%
- [ ] Cache hit rate > 80% after 7 days
- [ ] No critical bugs in first 48h

---

## 🏃 Quick Local Development Setup

### What This Is
A minimal setup to test the command bar locally without full infrastructure.

### Setup Steps

1. **Environment Variables** (`.env.local`):
```bash
# Use existing search API (no local Modal needed)
NEXT_PUBLIC_API_URL=https://podinsight-api.vercel.app
# For local testing without Modal
MODAL_ENABLED=false
# Your OpenAI key for answer synthesis
OPENAI_API_KEY=sk-...
```

2. **Mock Search Responses** (`/mocks/search.json`):
```json
{
  "answer": "VCs are increasingly cautious about AI agent valuations, citing concerns about defensibility and actual revenue generation¹².",
  "citations": [
    {
      "index": 1,
      "episode_id": "mock-123",
      "episode_title": "The AI Agent Reality Check",
      "podcast_name": "All-In",
      "timestamp": "23:45",
      "audio_url": "/mocks/audio1.mp3"
    }
  ]
}
```

3. **Local Development Mode**:
```bash
# Install dependencies
pnpm install

# Run with mock data
NEXT_PUBLIC_USE_MOCKS=true pnpm dev

# Test with real API
NEXT_PUBLIC_USE_MOCKS=false pnpm dev
```

4. **Testing the Flow**:
- Press `/` to open command bar
- Type "AI valuations"
- Hit Enter
- Should see mocked answer with citations
- Audio won't play (use placeholder sound)

This setup lets you iterate on UI without waiting for backend deployment.

---

## 📋 Future Improvements Roadmap

### 🟡 Fast Follower (After Demo Success)

#### 1. **Episode Quality & Coverage Scoring** (Size: L, Time: 2 days)
**What It Is**: Weight search results by episode authority and topic depth.

**Implementation**:
```javascript
// Add quality signals to chunks
{
  $addFields: {
    episode_quality_score: {
      $multiply: [
        { $log10: "$episode.play_count" },     // Popular episodes
        { $cond: ["$episode.is_flagship", 2, 1] }, // Curated shows
        { $divide: [1, { $daysSince: "$episode.published_at" }] } // Recency
      ]
    },
    coverage_score: {
      // How many chunks from same episode discuss this topic
      $size: { $filter: {
        input: "$episode_chunks",
        cond: { $gte: ["$$this.score", 0.7] }
      }}
    }
  }
}
```

**Why**: Prefer authoritative sources and episodes with deep coverage over random mentions.

#### 2. **OpenAI Response Caching** (Size: M, Time: 4 hours)
**What It Is**: Store LLM responses for identical queries to avoid regenerating the same answer.

**Implementation**:
- Redis/Memory cache with 1-hour TTL
- Key: Hash of (query + top chunk IDs)
- Saves ~$50/month at scale

**Why**: Reduces costs and improves response time for popular queries.

#### 3. **Basic Rate Limiting** (Size: M, Time: 3 hours)
**What It Is**: Prevent individual users from overwhelming the API with requests.

**Implementation**:
- Simple in-memory counter per IP
- Limit: 20 requests per minute
- Return 429 status with retry-after header

**Why**: Prevents demo day disasters if someone shares the link widely.

#### 4. **Local LLM Migration** (Size: L, Time: 3 days)
**What It Is**: Replace OpenAI with Mistral-7B or similar running on Modal.

**Implementation**:
```python
# Modal function with Mistral
@modal.function(gpu="A10G")
def generate_answer(chunks, query):
    model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-Instruct")
    # Generate answer with citations
    return synthesize(model, chunks, query)
```

**Why**: Cuts costs from $18/1000 answers to ~$0.50, improves latency, keeps data private.

### 🔴 Backlog (Post-Investment)

#### 1. **Full Caching Strategy** (Size: L, Time: 2 days)
**What It Is**: Multi-layer caching across the entire stack.

**Includes**:
- CDN for static assets
- Redis for API responses
- Browser cache for audio files
- Stale-while-revalidate patterns

#### 2. **Security Hardening** (Size: XL, Time: 1 week)
**What It Is**: Production-grade security measures.

**Includes**:
- Input sanitization (XSS prevention)
- SQL injection protection
- CORS configuration
- API key rotation
- WAF rules

#### 3. **Accessibility Compliance** (Size: L, Time: 3 days)
**What It Is**: Full WCAG 2.1 AA compliance.

**Includes**:
- Screen reader announcements
- Keyboard navigation testing
- Color contrast verification
- Focus trap management
- Alt text for all images

#### 4. **Privacy & GDPR** (Size: XL, Time: 1 week)
**What It Is**: Legal compliance for user data.

**Includes**:
- Privacy policy
- Cookie consent
- Data retention policies
- Right to deletion
- Audit logging

#### 5. **Integration Test Suite** (Size: L, Time: 3 days)
**What It Is**: Automated tests across all services.

**Includes**:
- ETL → API → Frontend flow
- Mock service framework
- CI/CD pipeline integration
- Performance regression tests

#### 6. **Rollout Strategy** (Size: M, Time: 2 days)
**What It Is**: Controlled feature release system.

**Includes**:
- Feature flags (LaunchDarkly/similar)
- Gradual rollout (10% → 50% → 100%)
- A/B testing framework
- Quick rollback mechanism

---

## 📚 Documentation Best Practices

### Repository Documentation Structure

Each repository should maintain sprint documentation:

```
repo-root/
├── docs/
│   ├── sprint3/
│   │   ├── README.md                    # Sprint overview & status
│   │   ├── implementation_log.md        # Daily progress, decisions
│   │   ├── test_results.md             # Running test log
│   │   ├── issues_and_fixes.md        # Problems encountered
│   │   └── architecture_updates.md     # System design changes
│   └── architecture/
│       ├── data_model.md               # Current data structures
│       ├── api_spec.md                 # Endpoint documentation
│       └── system_overview.md          # High-level architecture
```

### Sprint Documentation Requirements

**For Each Phase, Create:**

1. **Implementation Log** (`implementation_log.md`)
   ```markdown
   # Sprint 3 - Phase [X] Implementation Log

   ## [Date]
   ### What We Built
   - Feature: [description]
   - Files: [list of new/modified files]

   ### Decisions Made
   - Chose X over Y because...

   ### Challenges
   - Issue: [description]
   - Solution: [how we solved it]
   ```

2. **Test Results** (`test_results.md`)
   ```markdown
   # Test Results - [Feature Name]

   ## Unit Tests
   - Coverage: X%
   - Failed tests: [list]
   - Performance: [metrics]

   ## Integration Tests
   - Scenarios tested: [list]
   - Issues found: [list]

   ## Manual Testing
   - [ ] Checklist item 1
   - [x] Checklist item 2
   ```

3. **Architecture Updates** (`architecture_updates.md`)
   ```markdown
   # Architecture Changes - Sprint 3

   ## New Components
   - CommandBar: Frontend search interface
   - Audio clip storage: S3 structure

   ## Data Flow Changes
   - Added LLM synthesis step
   - New audio URL generation

   ## Performance Optimizations (Sprint 3 Enhancements)
   - Increased numCandidates: 20 → 100 for better recall
   - Expanded context window: 600 → 1000 tokens
   - UI optimization: Collapsible citations

   ## Performance Impact
   - Additional latency: +500ms for synthesis
   - Storage increase: ~50GB for audio clips
   - Negligible impact from numCandidates (+10ms)
   ```

---

## 🔄 Context Handoff Template

When Claude Code reaches context limits (~80%), use this template to start a new session:

```
I need to continue Sprint 3 implementation for PodInsightHQ command bar.

PROJECT CONTEXT:
@podinsight-business-overview.md
@PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md
@AUDIO_CLIP_ARCHITECTURE_ANALYSIS.md
@sprint3_command_bar_playbook.md

CURRENT STATUS:
Repository: [podinsight-api | podinsight-dashboard | podinsight-etl]
Phase: [1A | 1B | 2A | 2B]
Completed:
- [x] [completed task 1]
- [x] [completed task 2]
- [ ] [current task] <- WORKING ON THIS

RECENT WORK:
@[most_recent_file.py]
@docs/sprint3/implementation_log.md
@docs/sprint3/test_results.md

IMMEDIATE TASK:
[Specific description of what needs to be done next]

KEY DECISIONS MADE:
- [Important decision 1]
- [Important decision 2]
- CRITICAL: Pivoted to on-demand audio generation (saves $10K/year)

BLOCKING ISSUES:
- [Any blockers that need addressing]

Please continue implementation from where we left off.
```

### Essential Context Files

Always include these in new sessions:
1. **Business Context**: `podinsight-business-overview.md` - Why we're building this
2. **Technical Context**: `PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md` - Current system state
3. **Audio Architecture**: `AUDIO_CLIP_ARCHITECTURE_ANALYSIS.md` - Critical on-demand pivot
4. **Sprint Guide**: `sprint3_command_bar_playbook.md` - What we're building
5. **Recent Work**: Last 2-3 files you were working on
6. **Sprint Docs**: Current implementation log and test results

### Context Preservation Tips

1. **Commit Often**: Push changes before context gets full
2. **Document Decisions**: Write them in implementation_log.md immediately
3. **Test Results**: Keep running log of what works/fails
4. **Architecture Notes**: Update diagrams when data flow changes
5. **TODO Comments**: Leave clear markers in code for next session

---

## 🚀 Sprint 3 Success Checklist

### Pre-Launch Checklist
- [ ] Lambda function deployed for on-demand audio generation
- [ ] FFmpeg layer configured in Lambda
- [ ] API endpoint `/api/v1/audio_clips/{episode_id}` working
- [ ] Frontend handles loading state for first-play audio
- [ ] OpenAI API key configured and tested
- [ ] Command bar component renders correctly
- [ ] Keyboard shortcuts working (/, ⌘K, ESC)
- [ ] Answer synthesis returns 2 sentences
- [ ] Citations formatted with superscripts
- [ ] Audio players handle on-demand generation gracefully
- [ ] Mobile responsive design verified
- [ ] Error states handled gracefully
- [ ] Performance meets targets (<2s p95, audio <3s)

### Documentation Checklist
- [ ] Architecture Decision Record (ADR) for on-demand audio pivot
- [ ] Implementation logs updated daily
- [ ] Test results documented
- [ ] Architecture diagrams updated with Lambda flow
- [ ] API documentation includes audio endpoint
- [ ] Known issues tracked
- [ ] Performance benchmarks recorded (cache hit rates)
- [ ] Cost savings documented ($10K/year avoided)

### Post-Launch Monitoring
- [ ] Amplitude events firing correctly
- [ ] Error rates < 1%
- [ ] User adoption > 40%
- [ ] Audio play rate > 30%
- [ ] Audio generation success rate > 95%
- [ ] Cache hit rate > 80% after 7 days
- [ ] No critical bugs in first 48h
