# Dashboard Integration Guide

## Running the Dashboard

### Quick Start
```bash
# Navigate to dashboard directory
cd /Users/jamesgill/PodInsights/podinsight-dashboard

# Install dependencies (if needed)
npm install

# Start the development server
npm run dev
```

The dashboard will be available at: **http://localhost:3000**

### Alternative Start Methods

1. **Using the start script (recommended)**
   ```bash
   cd /Users/jamesgill/PodInsights/podinsight-dashboard
   ./start-dev.sh
   ```
   This automatically handles port conflicts and cleanup.

2. **With health monitoring**
   ```bash
   cd /Users/jamesgill/PodInsights/podinsight-dashboard
   node run-dev.js
   ```

### Common Issues

If port 3000 is already in use:
```bash
# Kill the process using port 3000
lsof -ti :3000 | xargs kill -9

# Then start the server again
npm run dev
```

## Quick Test in Browser Console

Open your dashboard in the browser and paste this in the console:

```javascript
// Test the search API from your dashboard
fetch('https://podinsight-api.vercel.app/api/search', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({query: 'AI agents', limit: 5})
})
.then(r => r.json())
.then(data => {
  console.log('Search Results:', data);
  console.log('Found episodes:', data.results.length);
  data.results.forEach(r => 
    console.log(`- ${r.podcast_name}: ${r.excerpt.substring(0, 100)}...`)
  );
});
```

## Integration Steps

### 1. Copy the Search Component

Copy `dashboard-search-component.tsx` to your dashboard repository:

```bash
# In your dashboard repo
cp ../podinsight-api/dashboard-search-component.tsx components/search/SearchInterface.tsx
```

### 2. Add to Your Dashboard

Option A: Add to existing page:

```tsx
// In any page or component
import { SearchInterface } from '@/components/search/SearchInterface';

export default function DashboardPage() {
  return (
    <div>
      {/* Your existing dashboard content */}
      
      {/* Add search section */}
      <SearchInterface />
    </div>
  );
}
```

Option B: Create a dedicated search page:

```tsx
// app/search/page.tsx or pages/search.tsx
import { SearchInterface } from '@/components/search/SearchInterface';

export default function SearchPage() {
  return (
    <main className="container mx-auto py-8">
      <SearchInterface />
    </main>
  );
}
```

### 3. Add Navigation

Add a search link to your navigation:

```tsx
<Link href="/search" className="nav-link">
  Search Episodes
</Link>
```

## API Endpoints Available

1. **Search** (POST)
   - URL: `https://podinsight-api.vercel.app/api/search`
   - Body: `{"query": "your search", "limit": 10, "offset": 0}`

2. **Topic Velocity** (GET)
   - URL: `https://podinsight-api.vercel.app/api/topic-velocity`
   - Query params: `?interval=weekly&topics=AI%20Agents,B2B%20SaaS`

3. **Health Check** (GET)
   - URL: `https://podinsight-api.vercel.app/api/health`

## Test the Integration

1. Start your dashboard locally
2. Add the search component
3. Try searching for:
   - "AI agents"
   - "venture capital"
   - "B2B SaaS metrics"
   - "DePIN infrastructure"

## Troubleshooting

### CORS Issues
If you get CORS errors, the API already has CORS enabled for all origins. Check browser console for details.

### No Results
The search uses semantic similarity. Try broader terms like "AI" or "SaaS" to test.

### Slow Response
First search for a query takes ~2-3 seconds (generating embedding). Subsequent searches are cached and faster.

## Next Steps

Once basic search works, you can:
1. Add filters by date range
2. Filter by specific podcasts
3. Add pagination for more results
4. Save searches (requires auth)
5. Play audio clips (requires audio endpoint)