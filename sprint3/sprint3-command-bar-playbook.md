# Sprint 3: Instant-Answer Command Bar Playbook

## 🎯 Sprint Overview

**Sprint Duration:** 5-6 working days
**Theme:** "Ask, listen, decide"
**Core Feature:** Conversational intelligence via command bar
**Success Metric:** "This feels like Perplexity but just for podcasts"

### Sprint Details
| Aspect | Details |
|--------|---------|
| **Target Users** | Time-poor VCs & founders needing instant insights |
| **Repositories** | `podinsight-etl`, `podinsight-api`, `podinsight-dashboard` |
| **Infrastructure** | MongoDB Atlas (vector search), Modal GPU (embeddings) |
| **Definition of Done** | `/` or `⌘K` → ask question → 2-sentence answer with citations → 30s audio plays inline (p95 < 2s) |

---

## ✅ Prerequisites Checklist

| Component | Requirement | Verification |
|-----------|-------------|--------------|
| **Semantic Chunks** | 823,763 chunks with 768-d embeddings in MongoDB | ✅ DONE - `db.transcript_chunks_768d.count()` |
| **Atlas Search Index** | `vector_index_768d` configured | ✅ DONE - Dimensions: 768, Similarity: cosine |
| **Modal Embedding Service** | Instructor-XL model deployed | ✅ DONE - `modal_web_endpoint_simple.py` |
| **Search API** | `/api/search` endpoint operational | ✅ DONE - 85-95% relevance achieved |
| **Audio Clips** | 30-second snippets in S3 | ⚠️ TODO - Path: `/audio_clips/{episode_id}/{chunk_idx}.mp3` |
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
- 🎯 **Audio Integration**: 30-second proof clips with inline playback
- 🎯 **Polished UX**: Glassmorphism, smooth animations, keyboard navigation

---

## 🔧 Phase 1: Backend Infrastructure

### Phase 1 Setup Prompt for Claude Code:
```
I'm starting Sprint 3 Phase 1 (Backend Infrastructure) for PodInsightHQ.

Please read these essential context files:
@sprint3_command_bar_playbook.md - Complete sprint guide
@podinsight-business-overview.md - Business context
@PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md - Current system architecture

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
Repository: podinsight-etl (for 1A), podinsight-api (for 1B)

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

### 1A-Alternative. Audio Clip Generation (NEW REQUIREMENT)

### Phase 1A Setup Prompt for Claude Code:
```
I'm implementing audio clip generation (Phase 1A) for Sprint 3.

Repository: podinsight-etl
Task: Generate 30-second audio clips for all transcript chunks

Please:
1. Create/update docs/sprint3/implementation_log.md with today's date
2. Review the audio generation requirements in the playbook
3. Set up test structure as specified
4. Document any S3 bucket configuration needed

Ready to implement audio_clip_generator.py following the specifications.
```

**Context:** Search works but we need 30-second audio clips for proof-of-listening.

**Why This Is Needed:**
- Search returns text chunks with timestamps
- Users want to hear the actual audio
- 30-second clips provide context without full episode download

**Definition of Done:**
✅ Script processes all episodes to generate 30s clips
✅ Clips stored in S3: `/audio_clips/{episode_id}/{chunk_idx}.mp3`
✅ Each clip centered on chunk timestamp
✅ Signed URLs generated on-demand

**Copy-Paste Prompt for Claude Code:**
```
I need a batch processor to generate 30-second audio clips for PodInsightHQ.

Context:
- MongoDB has 823,763 chunks with start_time and end_time
- S3 has original MP3s at: s3://pod-insights-raw/{feed_slug}/{guid}/audio/
- Need 30-second clips centered on each chunk's timestamp

Requirements:
1. Create audio_clip_generator.py that:
   - Queries MongoDB for chunks without clips
   - Downloads source MP3 from S3
   - Extracts 30s clip (15s before start_time, 15s after)
   - Handles edge cases (start/end of episode)
   - Uploads to: s3://pod-insights-clips/audio_clips/{episode_id}/{chunk_idx}.mp3

2. Use ffmpeg for extraction:
   ffmpeg -i input.mp3 -ss [start] -t 30 -c copy output.mp3

3. Process in batches of 100 to avoid memory issues
4. Add progress tracking and resume capability

Please implement with error handling for missing files.
```

**Testing Prompt for Claude Code:**
```
Create comprehensive tests for the audio clip generator.

Test Requirements:
1. Unit tests (test_audio_clip_generator.py):
   - Test clip extraction with mock ffmpeg
   - Test edge cases (clip at start/end of episode)
   - Test S3 upload with moto mock
   - Test batch processing logic
   - Test resume from interruption

2. Integration test script (test_audio_integration.py):
   - Download 3 test episodes
   - Generate clips for first 10 chunks each
   - Verify clip duration = 30s exactly
   - Verify audio quality preserved
   - Test S3 signed URL generation

3. Manual testing checklist:
   - [ ] Run on 100 chunks, verify all succeed
   - [ ] Interrupt process, verify resume works
   - [ ] Check clips play in browser
   - [ ] Verify no audio artifacts at boundaries
   - [ ] Test with episodes < 30s total length

Include assertions for file sizes, durations, and S3 paths.
```

**Required Documentation:**
1. **Implementation Log**: `docs/sprint3/audio_generation_log.md`
   - Track design decisions, challenges, solutions
2. **Test Results**: `docs/sprint3/audio_test_results.md`
   - Document test runs, issues found, fixes applied
3. **Architecture Update**: `docs/sprint3/audio_architecture.md`
   - How audio clips fit into overall system
   - S3 bucket structure and access patterns

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
1. After getting search results, pass top 6 chunks to OpenAI:
   - Model: gpt-3.5-turbo-0125
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
         "chunk_index": 45,
         "audio_url": "https://s3.../audio_clips/abc123/45.mp3"
       }
     ],
     "raw_chunks": [...existing format...],
     "processing_time_ms": 2150
   }

4. Add OPENAI_API_KEY to environment variables
5. Handle OpenAI errors gracefully (fallback to raw chunks)

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
// Step-by-step pipeline for optimal results
[
  // 1. Vector Search (Semantic)
  {
    $vectorSearch: {
      index: "semantic_search_index",
      path: "embedding_768d",
      queryVector: embedding,
      numCandidates: 200,
      limit: 20
    }
  },

  // 2. Keyword Boost (Precision for names/numbers)
  {
    $search: {
      text: {
        query: user_terms,
        path: ["text", "episode_title"],
        score: { boost: { value: 5 } }
      }
    }
  },

  // 3. Composite Scoring
  {
    $addFields: {
      composite_score: {
        $add: [
          { $multiply: ["$score", 0.7] },  // Vector weight
          { $multiply: ["$search_score", 0.3] }  // BM25 weight
        ]
      }
    }
  },

  // 4. Diversity (Max 2 chunks per episode)
  {
    $group: {
      _id: "$episode_id",
      chunks: { $push: "$$ROOT" },
      max_score: { $max: "$composite_score" }
    }
  },
  { $unwind: { path: "$chunks", includeArrayIndex: "rank" } },
  { $match: { rank: { $lt: 2 } } },

  // 5. Final limit
  { $sort: { "chunks.composite_score": -1 } },
  { $limit: 6 }
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

### 2A. Global Command Bar Component

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

**Component Structure:**

```tsx
// components/CommandBar.tsx
import { useState, useEffect } from 'react';
import { Command } from 'cmdk';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { useHotkeys } from '@/hooks/use-hotkeys';
import { useScrollDirection } from '@/hooks/use-scroll-direction';

export function CommandBar() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState<AnswerResponse | null>(null);
  const scrollDirection = useScrollDirection();

  // Auto-hide on scroll down
  const isVisible = scrollDirection !== 'down' || open;

  // Keyboard shortcuts
  useHotkeys('/', () => setOpen(true));
  useHotkeys('cmd+k', () => setOpen(true));
  useHotkeys('escape', () => {
    setOpen(false);
    setAnswer(null);
  });

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
                    await handleSearch(query);
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
          </Command>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

### 2B. Answer Card Component

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
          {answer.citations.map((citation, idx) => (
            <SourceChip
              key={citation.episode_id}
              citation={citation}
              index={idx + 1}
            />
          ))}
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

        <MiniAudioPlayer
          src={citation.audio_url}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
        />
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
| **Modal Query Embeds** | 10,000 queries | ~$0.50 | $5,000 credits |
| **MongoDB Atlas** | Vector operations | Covered | $500 credits |
| **Total Monthly** | Normal usage | < $25 | Well within budget |

---

## ⚠️ Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Long Answers** | >2 sentences returned | Set `max_tokens=80`, `temperature=0` |
| **Single Episode Dominance** | One podcast in all citations | Apply diversity grouping in pipeline |
| **Atlas Index Error** | "Index not found" | Check case-sensitive name: `semantic_search_index` |
| **Audio 404** | Clips don't play | Generate signed URLs, check S3 permissions |
| **Slow Cold Start** | First query takes >5s | Pre-warm Modal endpoint every 10 min |

---

## 🚀 Launch Checklist

### Pre-Launch
- [ ] Modal endpoint deployed and tested
- [ ] Atlas search index verified (768d)
- [ ] Audio clips accessible from S3
- [ ] API endpoints load tested
- [ ] Frontend keyboard shortcuts working
- [ ] Mobile responsive design verified

### Launch Day
- [ ] Enable feature flag for 10% users
- [ ] Monitor Datadog for errors
- [ ] Check Amplitude for adoption
- [ ] Gather initial user feedback
- [ ] Fix any critical issues

### Post-Launch
- [ ] Analyze search query patterns
- [ ] Optimize slow queries
- [ ] Expand to 100% users
- [ ] Plan v2 features based on usage

---

## 📚 Implementation Resources

### Claude Code Context Files
```
@sprint3_playbook.md          # This document
@database_schema.md           # MongoDB collections
@api/answer_generator.py      # Answer generation logic
@components/CommandBar.tsx    # Frontend component
@tests/e2e/command-bar.cy.js # E2E test suite
```

### Quick Start Prompts

**For Backend (Claude Code):**
```
I'm implementing Sprint 3 command bar for PodInsightHQ.
Current task: Phase 1B - Answer pipeline in podinsight-api
Need: MongoDB aggregation with vector + keyword scoring
Context: @sprint3_playbook.md @database_schema.md
Requirement: 6 diverse chunks, <200ms processing
```

**For Frontend (Claude Code):**
```
Building Sprint 3 command bar UI for PodInsightHQ.
Current task: Phase 2A - Global command bar component
Stack: Next.js 14, TypeScript, Tailwind, Radix UI
Context: @sprint3_playbook.md @components/CommandBar.tsx
Style: Dark glassmorphism, 640px max width, smooth animations
```

---

## 🎯 Success Criteria

The command bar succeeds when:
1. **Users say "wow"** - The experience feels magical
2. **Answers are trustworthy** - Citations prove claims
3. **Audio adds value** - 30-second clips provide context
4. **Performance delights** - Sub-2s responses feel instant
5. **Adoption is natural** - 40%+ users try it without prompting

**The ultimate test:** Would a busy VC choose this over listening to a full episode?

---

## 📐 Visual Reference

### Why This Flow Matters for VCs
1. **Zero cognitive load** until they ask something
2. **Proof beats hype** - instant audio receipts build trust
3. **Speed demo** - searching 1.4K episodes yet surfacing 2 clips feels magical

### Implementation Placement
| Repo | Location | Key Files |
|------|----------|-----------|
| `podinsight-dashboard` | `/components/command-bar/` | `CommandBar.tsx`, `SearchResultCard.tsx` |
| `podinsight-api` | `/routes/search/` | `answer.py` (vector + keyword hybrid) |
| `podinsight-etl` | Already complete | Embeddings in `semantic_chunks` |

**Note:** The command bar overlay is absolutely positioned to avoid re-layout of existing charts.

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

   ## Performance Impact
   - Additional latency: +500ms for synthesis
   - Storage increase: ~50GB for audio clips
   ```

---

## 🔄 Context Handoff Template

When Claude Code reaches context limits (~80%), use this template to start a new session:

```
I need to continue Sprint 3 implementation for PodInsightHQ command bar.

PROJECT CONTEXT:
@podinsight-business-overview.md
@PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md
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

BLOCKING ISSUES:
- [Any blockers that need addressing]

Please continue implementation from where we left off.
```

### Essential Context Files

Always include these in new sessions:
1. **Business Context**: `podinsight-business-overview.md` - Why we're building this
2. **Technical Context**: `PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md` - Current system state
3. **Sprint Guide**: `sprint3_command_bar_playbook.md` - What we're building
4. **Recent Work**: Last 2-3 files you were working on
5. **Sprint Docs**: Current implementation log and test results

### Context Preservation Tips

1. **Commit Often**: Push changes before context gets full
2. **Document Decisions**: Write them in implementation_log.md immediately
3. **Test Results**: Keep running log of what works/fails
4. **Architecture Notes**: Update diagrams when data flow changes
5. **TODO Comments**: Leave clear markers in code for next session

---

## 🚀 Sprint 3 Success Checklist

### Pre-Launch Checklist
- [ ] Audio clips generated for top 1000 episodes
- [ ] OpenAI API key configured and tested
- [ ] Command bar component renders correctly
- [ ] Keyboard shortcuts working (/, ⌘K, ESC)
- [ ] Answer synthesis returns 2 sentences
- [ ] Citations formatted with superscripts
- [ ] Audio players load and play clips
- [ ] Mobile responsive design verified
- [ ] Error states handled gracefully
- [ ] Performance meets targets (<2s p95)

### Documentation Checklist
- [ ] Implementation logs updated daily
- [ ] Test results documented
- [ ] Architecture diagrams updated
- [ ] API documentation current
- [ ] Known issues tracked
- [ ] Performance benchmarks recorded

### Post-Launch Monitoring
- [ ] Amplitude events firing correctly
- [ ] Error rates < 1%
- [ ] User adoption > 40%
- [ ] Audio play rate > 30%
- [ ] No critical bugs in first 48h
