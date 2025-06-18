#!/bin/bash
echo "🔍 Testing Search API Step by Step"
echo "=================================="
echo ""

# Test 1: Check if the API is responding
echo "1. Health check..."
curl -s https://podinsight-api.vercel.app/ | python3 -m json.tool | grep -E "(HUGGINGFACE|SUPABASE)" || echo "Failed"
echo ""

# Test 2: Test with a simple query
echo "2. Testing search with verbose output..."
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 1}' \
  -w "\nHTTP Status: %{http_code}\nResponse Time: %{time_total}s\n" \
  -v 2>&1 | grep -E "(HTTP|detail|error)" || true
echo ""

# Test 3: Check if it's a specific issue with the search
echo "3. Testing a different endpoint (topics)..."
curl -s https://podinsight-api.vercel.app/api/topics | python3 -m json.tool | head -10
echo ""

echo "To check Vercel logs for the actual error:"
echo "1. Go to: https://vercel.com/james-projects-eede2cf2/podinsight-api"
echo "2. Click on 'Functions' tab"
echo "3. Look for recent errors in the logs"