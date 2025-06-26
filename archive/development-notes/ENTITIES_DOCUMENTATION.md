# Entity Search Documentation

## Overview

Entity Search is a powerful feature that tracks mentions of people, companies, places, and monetary values across all 1,171 podcast episodes. Unlike transcript search which finds conversations, entity search helps you understand WHO and WHAT is being discussed most frequently.

## What are Entities?

Entities are automatically extracted named items from podcast transcripts, categorized into four types:

1. **PERSON** - Individual people mentioned by name
   - Examples: "Sam Altman", "Elon Musk", "Marc Andreessen"
   - Use case: Track thought leaders, founders, investors

2. **ORG** - Organizations and companies
   - Examples: "OpenAI", "Sequoia Capital", "Y Combinator"
   - Use case: Monitor company buzz, competitive intelligence

3. **GPE** - Geopolitical entities (places)
   - Examples: "Silicon Valley", "San Francisco", "China"
   - Use case: Track geographic trends and market focus

4. **MONEY** - Monetary amounts and valuations
   - Examples: "$100 million", "a billion dollars", "$10B valuation"
   - Use case: Understand investment sizes and market valuations

## Entity Search vs Transcript Search

### When to Use Entity Search

**Entity Search** answers questions like:
- "How often is OpenAI mentioned across all podcasts?"
- "Which companies are trending up in mentions?"
- "Who are the most discussed people in the VC ecosystem?"
- "What funding amounts are being discussed?"

**Best for:**
- Tracking buzz and mindshare
- Competitive intelligence
- Trend analysis
- Understanding who/what matters in the ecosystem

### When to Use Transcript Search

**Transcript Search** answers questions like:
- "What are VCs saying about AI agent valuations?"
- "Find discussions about product-market fit"
- "What concerns do founders have about fundraising?"
- "Show me conversations about remote work"

**Best for:**
- Finding specific insights and opinions
- Research on topics and themes
- Extracting quotes and context
- Understanding the "why" behind trends

## API Endpoint

### GET /api/entities

Search and filter entities across all podcast episodes.

**Parameters:**
- `search` (optional) - Search term for entity names (fuzzy match)
- `type` (optional) - Filter by entity type: PERSON, ORG, GPE, MONEY
- `limit` (optional) - Number of results to return (default: 20, max: 100)
- `timeframe` (optional) - Time filter like "30d", "60d", "90d"

**Example Requests:**

```bash
# Search for OpenAI mentions
GET /api/entities?search=OpenAI&limit=5

# Find top mentioned people
GET /api/entities?type=PERSON&limit=10

# See trending companies in last 30 days
GET /api/entities?type=ORG&timeframe=30d&limit=20

# Find investment amounts discussed
GET /api/entities?type=MONEY&limit=10
```

**Response Format:**

```json
{
  "success": true,
  "entities": [
    {
      "name": "OpenAI",
      "type": "ORG",
      "mention_count": 494,      // Total times mentioned
      "episode_count": 412,      // Unique episodes
      "trend": "down",          // up/down/stable
      "recent_mentions": [
        {
          "episode_title": "This Week in Startups - 65 min (Jun 15, 2025)",
          "date": "June 15, 2025",
          "context": "Mentioned in This Week in Startups - 65 min (Jun 15, 2025)"
        }
      ]
    }
  ],
  "total_entities": 15234,
  "filters": {
    "search": "OpenAI",
    "type": null,
    "timeframe": null,
    "limit": 5
  }
}
```

## Use Cases

### 1. Company Intelligence
Track how often competitors or potential partners are mentioned:
```
Search: "Anthropic" → See 127 mentions across 89 episodes
Trend: "up" → Growing mindshare in the ecosystem
```

### 2. People Tracking
Monitor thought leaders and key figures:
```
Type: PERSON, Limit: 20 → See most discussed people
"Steve Jobs" → 7 mentions, trending stable
Note: Generic first names (Tommy, Mark) are filtered for quality
```

### 3. Investment Intelligence
Understand funding landscape:
```
Type: MONEY → See common funding amounts
"$100 million" → Mentioned in 45 episodes
"billion dollar" → Mentioned in 89 episodes
```

### 4. Trend Analysis
Compare recent activity to historical:
```
Timeframe: 30d → See what's hot right now
"AI" entities dominate with 5x normal activity
```

## Understanding Trends

The trend indicator shows whether an entity is being mentioned more or less frequently:

- **"up"** - Recent mentions (last 4 weeks) are >50% higher than previous period
- **"down"** - Recent mentions are >50% lower than previous period
- **"stable"** - Mention frequency is relatively constant

This helps identify:
- Rising companies and people
- Declining interest in certain topics
- Stable, consistently-discussed entities

## Limitations

1. **Name Variations** - "OpenAI" and "Open AI" may be counted separately
2. **Context Missing** - Shows mention count but not sentiment or context
3. **Entity Extraction** - Automated extraction may miss some entities or include errors
4. **No Semantic Understanding** - Can't distinguish between positive/negative mentions
5. **Single Names Filtered** - Generic first names (Tommy, Mark, etc.) are excluded for quality

## Best Practices

1. **Start Broad, Then Narrow**
   - First search without filters to see all matches
   - Then add type/timeframe filters to refine

2. **Use Multiple Searches**
   - Search "Sequoia" and "Sequoia Capital" separately
   - Some entities have multiple common names

3. **Combine with Transcript Search**
   - Use entity search to find WHO/WHAT is hot
   - Use transcript search to understand WHY

4. **Monitor Trends Over Time**
   - Weekly checks on key entities
   - Compare 30d vs 90d timeframes
   - Track competitive mindshare

## Example Workflows

### Competitive Intelligence Workflow
1. Entity Search: Your company name → Baseline mentions
2. Entity Search: Main competitors → Compare mention counts
3. Set timeframe to 30d → See recent trends
4. Transcript Search: Company names → Read actual discussions

### Investment Research Workflow
1. Entity Search: Type=MONEY → See funding ranges
2. Entity Search: Top VCs (type=ORG) → Active investors
3. Entity Search: Trending companies (30d) → Hot startups
4. Transcript Search: "[Company] valuation" → Detailed context

### People Research Workflow
1. Entity Search: Type=PERSON, limit=50 → Key figures
2. Filter by trend="up" → Rising influencers
3. Search specific names → Track individual mindshare
4. Transcript Search: Person name → What they're known for

## Technical Notes

- Entity extraction was performed during initial data processing
- Uses NLP named entity recognition (NER)
- Entities are normalized (e.g., "Y Combinator" and "YC" linked)
- Real-time aggregation from ~150k extracted entities
- Optimized for sub-second response times
- Quality filters remove generic single-name PERSON entities
- Episode titles include podcast name and duration for context

## Future Enhancements

Planned improvements for entity search:

1. **Entity Relationships** - See which entities appear together
2. **Sentiment Analysis** - Positive/negative mention context
3. **Entity Timelines** - Visualize mention frequency over time
4. **Smart Grouping** - Auto-group related entities (YC + Y Combinator)
5. **Export Capabilities** - Download entity data for analysis
