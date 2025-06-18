#!/bin/bash
echo "🔍 Testing PodInsightHQ Search API"
echo "=================================="
echo ""

# Test 1: Basic search
echo "Test 1: Searching for 'AI agents'..."
echo "-------------------------------------"
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI agents", "limit": 3}' \
  -s | python3 -m json.tool
echo ""

# Test 2: Different query
echo "Test 2: Searching for 'product market fit'..."
echo "---------------------------------------------"
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "product market fit", "limit": 2}' \
  -s | python3 -m json.tool
echo ""

# Test 3: Topic velocity
echo "Test 3: Getting topic velocity data..."
echo "--------------------------------------"
curl https://podinsight-api.vercel.app/api/topic-velocity?weeks=4 \
  -s | python3 -m json.tool | head -50
echo ""

echo "✅ Tests complete!"