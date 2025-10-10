# 🔧 Frontend Fix Guide: Show All Search Results (Not Just Citations)

## Problem
Frontend is only showing 5 citations when it should show all relevant search results (10+).

---

## Root Cause

**Current Code (WRONG)**:
```typescript
// Only showing citations array (5 items)
{data.answer?.citations?.map((citation, index) => (
  <SourceCard key={index} citation={citation} />
))}

// Button text mixing arrays
const buttonText = `${data.answer.citations.length} of ${data.total_results}`;
// Results in: "5 of 18" ❌
```

**What's Wrong**:
- Frontend is mapping over `answer.citations` (5 items)
- Should be mapping over `results` (10+ items)

---

## API Response Structure

The backend returns TWO separate arrays:

```typescript
interface SearchResponse {
  answer: {
    text: string;
    citations: Citation[];  // 5 items - top sources for AI answer
    confidence?: number;
  } | null;
  results: SearchResult[];   // 10+ items - all relevant search results
  total_results: number;     // Total results above relevancy threshold
  limit: number;             // Items per page (default 10)
  offset: number;            // Current page offset
  search_id: string;
  query: string;
  cache_hit: boolean;
  search_method: string;
}

interface Citation {
  index: number;
  episode_id: string;
  episode_title: string;
  podcast_name: string;
  timestamp: string;
  start_seconds: number;
  similarity_score: number;
  chunk_text: string;
  // ... other metadata
}

interface SearchResult {
  episode_id: string;
  podcast_name: string;
  episode_title: string;
  published_at: string;
  published_date: string;
  similarity_score: number;
  excerpt: string;
  word_count: number;
  duration_seconds: number;
  timestamp: {
    start_time: number;
    end_time: number;
  };
  // ... other fields
}
```

---

## The Fix

### Step 1: Display Results Array (Not Citations)

**BEFORE (Wrong)**:
```typescript
const SearchResults = ({ data }) => {
  return (
    <div>
      <h2>Sources ({data.answer?.citations?.length || 0})</h2>
      {data.answer?.citations?.map((citation, index) => (
        <SourceCard key={citation.episode_id} citation={citation} />
      ))}
    </div>
  );
};
```

**AFTER (Correct)**:
```typescript
const SearchResults = ({ data }) => {
  return (
    <div>
      <h2>Results ({data.results?.length || 0} of {data.total_results})</h2>
      {data.results?.map((result) => (
        <ResultCard
          key={result.episode_id}
          result={result}
          onPlay={() => handlePlay(result)}
        />
      ))}
    </div>
  );
};
```

### Step 2: Fix "Load More" Button Logic

**BEFORE (Wrong)**:
```typescript
const buttonText = `${data.answer?.citations?.length || 0} of ${data.total_results}`;
const hasMore = data.answer?.citations?.length < data.total_results;
// Shows: "5 of 18" ❌
```

**AFTER (Correct)**:
```typescript
const [displayedResults, setDisplayedResults] = useState(data.results || []);

const buttonText = `${displayedResults.length} of ${data.total_results}`;
const hasMore = displayedResults.length < data.total_results;
// Shows: "10 of 18" ✅
```

### Step 3: Implement Pagination

```typescript
const SearchComponent = () => {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const LIMIT = 10;

  // Initial search
  const handleSearch = async (query: string) => {
    setLoading(true);
    try {
      const response = await fetch('https://podinsight-api.vercel.app/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit: LIMIT, offset: 0 })
      });

      const data = await response.json();

      setResults(data.results || []);
      setTotalResults(data.total_results || 0);
      setOffset(0);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  // Load more results
  const handleLoadMore = async () => {
    if (loading || results.length >= totalResults) return;

    setLoading(true);
    const nextOffset = offset + LIMIT;

    try {
      const response = await fetch('https://podinsight-api.vercel.app/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: currentQuery,  // Store from initial search
          limit: LIMIT,
          offset: nextOffset
        })
      });

      const data = await response.json();

      // Append new results to existing
      setResults(prev => [...prev, ...(data.results || [])]);
      setOffset(nextOffset);
    } catch (error) {
      console.error('Load more failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Display results */}
      {results.map(result => (
        <ResultCard key={result.episode_id} result={result} />
      ))}

      {/* Load More button */}
      {results.length < totalResults && (
        <button onClick={handleLoadMore} disabled={loading}>
          {loading ? 'Loading...' : `Load More (${results.length} of ${totalResults})`}
        </button>
      )}
    </div>
  );
};
```

---

## Complete Example: Before & After

### BEFORE (Only showing 5 citations)

```typescript
function SearchResults({ data }: { data: SearchResponse }) {
  if (!data.answer?.citations) return null;

  const citations = data.answer.citations;
  const totalResults = data.total_results;

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-500">
        {citations.length} sources
      </div>

      {citations.map((citation, index) => (
        <SourceCard key={index} citation={citation} />
      ))}

      <button>
        Load More ({citations.length} of {totalResults})
      </button>
    </div>
  );
}
// Shows: 5 source cards, button says "5 of 18" ❌
```

### AFTER (Showing all results with pagination)

```typescript
function SearchResults({ initialData, query }: { initialData: SearchResponse, query: string }) {
  const [results, setResults] = useState(initialData.results);
  const [loading, setLoading] = useState(false);
  const totalResults = initialData.total_results;
  const hasMore = results.length < totalResults;

  const loadMore = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          limit: 10,
          offset: results.length  // Fetch from current position
        })
      });

      const data = await response.json();
      setResults(prev => [...prev, ...data.results]);
    } catch (error) {
      console.error('Failed to load more:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-500">
        Showing {results.length} of {totalResults} results
      </div>

      {results.map(result => (
        <ResultCard
          key={result.episode_id}
          result={result}
          onClick={() => console.log('Play:', result.episode_id)}
        />
      ))}

      {hasMore && (
        <button
          onClick={loadMore}
          disabled={loading}
          className="btn btn-primary"
        >
          {loading ? 'Loading...' : `Load More (${results.length} of ${totalResults})`}
        </button>
      )}
    </div>
  );
}
// Shows: 10+ result cards, button says "10 of 18", loads more on click ✅
```

---

## Quick Checklist

- [ ] Replace `data.answer.citations.map()` with `data.results.map()`
- [ ] Change button text from `citations.length` to `results.length`
- [ ] Update "Load More" to append results from new API call
- [ ] Use `offset` parameter for pagination
- [ ] Hide button when `results.length === total_results`
- [ ] Update TypeScript types to use `SearchResult` not `Citation`

---

## Testing

After making changes:

1. **Initial Load**: Should see 10 results
2. **Button Text**: Should show "10 of 18 results" (or similar)
3. **Click Load More**: Should fetch 8 more results
4. **After Loading**: Should show "18 of 18 results"
5. **Button Hidden**: Button should disappear when all loaded

---

## API Response Examples

### Example Response (Initial Load):
```json
{
  "answer": {
    "text": "AI agents are being discussed...",
    "citations": [5 citation objects]
  },
  "results": [10 result objects],
  "total_results": 18,
  "limit": 10,
  "offset": 0
}
```

### Example Response (Load More, offset=10):
```json
{
  "answer": {
    "text": "AI agents are being discussed...",
    "citations": [5 citation objects]
  },
  "results": [8 result objects],
  "total_results": 18,
  "limit": 10,
  "offset": 10
}
```

---

## Questions?

If you have issues:
1. Check console for API response structure
2. Verify you're reading `data.results` not `data.answer.citations`
3. Ensure pagination uses `offset` parameter correctly
4. Test with `curl` to see exact API response

**Backend team**: All fixes deployed and working ✅
**Frontend team**: Need to switch from citations to results array ⚠️
