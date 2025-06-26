# MongoDB Search Testing Guide

## 🚀 Quick Test URLs

### 1. API Health Check
```bash
curl https://podinsight-api.vercel.app/api/health
```

### 2. Basic Search Test
```bash
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI agents", "limit": 3}'
```

### 3. Different Search Queries
```bash
# Search for cryptocurrency discussions
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "cryptocurrency bitcoin", "limit": 2}'

# Search for startup topics
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "startup funding", "limit": 2}'

# Search for specific phrases
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "artificial intelligence", "limit": 3}'
```

## 🧪 Browser Testing

### Simple HTML Test Page
Save this as `test-search.html` and open in browser:

```html
<!DOCTYPE html>
<html>
<head>
    <title>PodInsight Search Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .search-box { margin: 20px 0; }
        input { padding: 10px; width: 300px; }
        button { padding: 10px 20px; margin-left: 10px; }
        .results { margin-top: 20px; }
        .result { border: 1px solid #ddd; padding: 15px; margin: 10px 0; }
        .excerpt { color: #333; margin: 10px 0; }
        .highlight { background-color: yellow; font-weight: bold; }
        .score { color: green; font-weight: bold; }
    </style>
</head>
<body>
    <h1>PodInsight Search Test</h1>

    <div class="search-box">
        <input type="text" id="query" placeholder="Search podcasts..." value="AI agents">
        <button onclick="search()">Search</button>
    </div>

    <div id="results" class="results"></div>

    <script>
    async function search() {
        const query = document.getElementById('query').value;
        const resultsDiv = document.getElementById('results');

        resultsDiv.innerHTML = '<p>Searching...</p>';

        try {
            const response = await fetch('https://podinsight-api.vercel.app/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, limit: 5 })
            });

            const data = await response.json();

            resultsDiv.innerHTML = `
                <h3>Found ${data.total_results} results</h3>
                ${data.results.map(r => `
                    <div class="result">
                        <h4>${r.podcast_name}</h4>
                        <p><strong>${r.episode_title || 'Untitled Episode'}</strong></p>
                        <p class="score">Relevance Score: ${r.similarity_score.toFixed(2)}</p>
                        <p class="excerpt">${r.excerpt.replace(/\*\*/g, '<span class="highlight">')}</p>
                        <small>Published: ${new Date(r.published_at).toLocaleDateString()}</small>
                    </div>
                `).join('')}
            `;
        } catch (error) {
            resultsDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
        }
    }

    // Search on page load
    search();
    </script>
</body>
</html>
```

## 📊 What to Look For

### ✅ Good Results (MongoDB Working)
- **Excerpts contain actual conversation**: "Today on the **AI** Daily Brief..."
- **Search terms are highlighted**: Look for **bold** terms
- **Relevance scores > 1.0**: MongoDB text scores
- **Natural text flow**: Real transcript content

### ❌ Fallback Results (Using pgvector)
- **Generic excerpts**: "Episode 7f54be60... This episode covers..."
- **Low scores**: 0.04 or 4% match scores
- **No real content**: Just metadata summaries

## 🔍 Advanced Testing

### Test with Python
```python
import requests
import json

# Test search function
def test_search(query, limit=3):
    url = "https://podinsight-api.vercel.app/api/search"
    payload = {"query": query, "limit": limit}

    response = requests.post(url, json=payload)
    data = response.json()

    print(f"\n🔍 Query: '{query}'")
    print(f"📊 Found {data['total_results']} results")

    for i, result in enumerate(data['results'], 1):
        print(f"\n--- Result {i} ---")
        print(f"Podcast: {result['podcast_name']}")
        print(f"Score: {result['similarity_score']:.2f}")
        print(f"Excerpt: {result['excerpt'][:200]}...")

# Test different queries
test_search("AI agents")
test_search("cryptocurrency")
test_search("venture capital")
```

### Check Cache Performance
```bash
# First request (cache miss)
time curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "limit": 3}' > /dev/null

# Second request (should be cached)
time curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "limit": 3}' > /dev/null
```

## 🎯 Expected Performance

- **Response Time**: 1-3 seconds (first request), <500ms (cached)
- **Relevance Scores**: 1.5-3.0 for good matches
- **Excerpt Length**: 150-400 characters with context
- **Highlighting**: Search terms wrapped in `**bold**`

## 🛠️ Troubleshooting

If search returns mock excerpts:
1. Check Vercel logs for MongoDB connection errors
2. Verify MONGODB_URI environment variable in Vercel
3. Check MongoDB Atlas network access (0.0.0.0/0)
4. Ensure motor/pymongo are in requirements.txt

---

*Created: June 19, 2025*
