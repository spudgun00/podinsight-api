#!/bin/bash

echo "============================================================"
echo "🚀 PODINSIGHT 768D MODAL.COM VERIFICATION"
echo "📅 $(date)"
echo "============================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="https://podinsight-api.vercel.app"
MODAL_ENDPOINT="https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run"

echo -e "\n🔍 1. TESTING MODAL.COM ENDPOINT"
echo "============================================================"

# Test Modal health
echo "Testing Modal health endpoint..."
MODAL_HEALTH=$(curl -s -w "\n%{http_code}" "$MODAL_ENDPOINT/health" 2>/dev/null | tail -n1)
if [ "$MODAL_HEALTH" = "200" ]; then
    echo -e "${GREEN}✅ Modal endpoint is accessible${NC}"
else
    echo -e "${RED}❌ Modal endpoint not accessible (HTTP $MODAL_HEALTH)${NC}"
fi

# Test Modal embedding generation
echo -e "\nTesting Modal embedding generation..."
START_TIME=$(date +%s)
EMBEDDING_RESPONSE=$(curl -s -X POST "$MODAL_ENDPOINT/embed" \
    -H "Content-Type: application/json" \
    -d '{"text": "venture capital investment strategies"}' \
    2>/dev/null)
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

if echo "$EMBEDDING_RESPONSE" | grep -q "embedding"; then
    # Count dimensions (number of commas + 1)
    DIMENSIONS=$(echo "$EMBEDDING_RESPONSE" | grep -o "," | wc -l | xargs)
    DIMENSIONS=$((DIMENSIONS + 1))
    echo -e "${GREEN}✅ Embedding generated in ${ELAPSED} seconds${NC}"
    echo -e "${GREEN}✅ Embedding dimensions: $DIMENSIONS (expected: 768)${NC}"

    if [ "$DIMENSIONS" -eq 768 ]; then
        echo -e "${GREEN}✅ CONFIRMED: Using 768-dimensional embeddings${NC}"
    else
        echo -e "${RED}❌ ERROR: Expected 768 dimensions, got $DIMENSIONS${NC}"
    fi
else
    echo -e "${RED}❌ Failed to generate embedding${NC}"
fi

echo -e "\n🔍 2. TESTING SEARCH API"
echo "============================================================"

# Test main search endpoint
echo "Testing search for 'artificial intelligence'..."
SEARCH_RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/search" \
    -H "Content-Type: application/json" \
    -d '{"query": "artificial intelligence", "limit": 3}' \
    2>/dev/null)

if echo "$SEARCH_RESPONSE" | grep -q "results"; then
    # Count results
    RESULT_COUNT=$(echo "$SEARCH_RESPONSE" | grep -o '"chunk_id"' | wc -l | xargs)
    echo -e "${GREEN}✅ Search API responded successfully${NC}"
    echo -e "${GREEN}✅ Number of results: $RESULT_COUNT${NC}"

    if [ "$RESULT_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✅ Search is returning results (vector search working)${NC}"

        # Extract first score
        FIRST_SCORE=$(echo "$SEARCH_RESPONSE" | grep -o '"score":[0-9.]*' | head -n1 | cut -d: -f2)
        echo "   First result score: $FIRST_SCORE"
    else
        echo -e "${RED}❌ Search returned 0 results (vector search may not be working)${NC}"
    fi
else
    echo -e "${RED}❌ Search API error${NC}"
    echo "Response: $SEARCH_RESPONSE"
fi

echo -e "\n🔍 3. TESTING 768D SPECIFIC ENDPOINT"
echo "============================================================"

# Test 768D endpoint
echo "Testing 768D search endpoint..."
SEARCH_768D_RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/search_lightweight_768d" \
    -H "Content-Type: application/json" \
    -d '{"query": "startup founders", "limit": 3}' \
    2>/dev/null)

if echo "$SEARCH_768D_RESPONSE" | grep -q "results"; then
    RESULT_COUNT_768D=$(echo "$SEARCH_768D_RESPONSE" | grep -o '"chunk_id"' | wc -l | xargs)
    echo -e "${GREEN}✅ 768D endpoint working${NC}"
    echo -e "${GREEN}✅ Results returned: $RESULT_COUNT_768D${NC}"
else
    echo -e "${YELLOW}⚠️  768D endpoint may not be available${NC}"
fi

echo -e "\n🔍 4. BUSINESS CONTEXT TEST (INSTRUCTOR-XL SPECIALTY)"
echo "============================================================"

# Test business-specific queries
QUERIES=("venture capital" "B2B SaaS" "fundraising" "startup metrics")
TOTAL_RESULTS=0

for query in "${QUERIES[@]}"; do
    echo -n "Testing '$query'... "
    RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/search" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\", \"limit\": 5}" \
        2>/dev/null)

    COUNT=$(echo "$RESPONSE" | grep -o '"chunk_id"' | wc -l | xargs)
    TOTAL_RESULTS=$((TOTAL_RESULTS + COUNT))
    echo "Found $COUNT results"
done

AVG_RESULTS=$((TOTAL_RESULTS / ${#QUERIES[@]}))
echo -e "\n📊 Average results per business query: $AVG_RESULTS"

if [ "$AVG_RESULTS" -gt 3 ]; then
    echo -e "${GREEN}✅ Excellent business context understanding${NC}"
elif [ "$AVG_RESULTS" -gt 1 ]; then
    echo -e "${YELLOW}⚠️  Moderate business context understanding${NC}"
else
    echo -e "${RED}❌ Poor business context understanding${NC}"
fi

echo -e "\n============================================================"
echo "📊 VERIFICATION SUMMARY"
echo "============================================================"

# Quick test to differentiate between vector and text search
echo -e "\n🔍 5. VECTOR VS TEXT SEARCH TEST"
echo "Testing nonsense query (should return 0 with vector search)..."
NONSENSE_RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/search" \
    -H "Content-Type: application/json" \
    -d '{"query": "xyzabc123randomnonsense", "limit": 3}' \
    2>/dev/null)

NONSENSE_COUNT=$(echo "$NONSENSE_RESPONSE" | grep -o '"chunk_id"' | wc -l | xargs)
if [ "$NONSENSE_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ Nonsense query returned 0 results (good - using vector search)${NC}"
else
    echo -e "${YELLOW}⚠️  Nonsense query returned $NONSENSE_COUNT results (might be using text search)${NC}"
fi

echo -e "\n🎯 KEY INDICATORS:"
echo "1. Modal endpoint accessible: Check ✅ above"
echo "2. 768D embeddings confirmed: Check ✅ above"
echo "3. Search returning results: Check ✅ above"
echo "4. Business context working: Check ✅ above"
echo "5. Vector search behavior: Check ✅ above"

echo -e "\n📄 To verify MongoDB index exists, check MongoDB Atlas for:"
echo "   - Index name: vector_index_768d"
echo "   - Collection: transcript_chunks_768d"
echo "   - Field: embedding_768d"
echo "   - Dimensions: 768"
