#!/bin/bash
# Comprehensive deployment testing script

echo "🧪 PodInsightHQ Search API - Deployment Testing"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# API URL
API_URL="https://podinsight-api.vercel.app"

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to test endpoint
test_endpoint() {
    local test_name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local expected_status=${5:-200}

    echo -e "\n📋 Test: $test_name"
    echo "----------------------------------------"

    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}\n%{time_total}" "$API_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}\n%{time_total}" -X POST \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_URL$endpoint")
    fi

    # Parse response
    body=$(echo "$response" | head -n -2)
    status=$(echo "$response" | tail -n 2 | head -n 1)
    time=$(echo "$response" | tail -n 1)

    # Check status code
    if [ "$status" -eq "$expected_status" ]; then
        echo -e "${GREEN}✅ Status: $status (expected)${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ Status: $status (expected $expected_status)${NC}"
        ((TESTS_FAILED++))
    fi

    # Check response time
    if (( $(echo "$time < 2.0" | bc -l) )); then
        echo -e "${GREEN}✅ Response time: ${time}s${NC}"
    else
        echo -e "${YELLOW}⚠️  Response time: ${time}s (>2s)${NC}"
    fi

    # Show response preview
    echo -e "\nResponse preview:"
    echo "$body" | python -m json.tool 2>/dev/null | head -20 || echo "$body" | head -20
}

# 1. Basic Health Check
echo -e "\n${YELLOW}=== 1. BASIC HEALTH CHECK ===${NC}"
test_endpoint "Health Check" "GET" "/" "" 200

# 2. Test Search Endpoint
echo -e "\n\n${YELLOW}=== 2. TEST SEARCH ENDPOINT ===${NC}"
test_endpoint "Search: AI agents and startup funding" "POST" "/api/search" \
    '{"query": "AI agents and startup funding", "limit": 5}' 200

# 3. Test Different Queries
echo -e "\n\n${YELLOW}=== 3. TEST DIFFERENT QUERIES ===${NC}"

queries=(
    "product market fit"
    "B2B SaaS metrics"
    "venture capital"
    "DePIN infrastructure"
    "blockchain technology"
)

for query in "${queries[@]}"; do
    test_endpoint "Search: $query" "POST" "/api/search" \
        "{\"query\": \"$query\", \"limit\": 3}" 200
    sleep 1  # Avoid rate limiting
done

# 4. Test Edge Cases
echo -e "\n\n${YELLOW}=== 4. TEST EDGE CASES ===${NC}"

# Empty query
test_endpoint "Empty Query (should fail)" "POST" "/api/search" \
    '{"query": "", "limit": 5}' 422

# Query too long
long_query=$(python3 -c "print('x' * 501)")
test_endpoint "Query Too Long (should fail)" "POST" "/api/search" \
    "{\"query\": \"$long_query\", \"limit\": 5}" 422

# Invalid limit
test_endpoint "Invalid Limit (should fail)" "POST" "/api/search" \
    '{"query": "test", "limit": 100}' 422

# 5. Test Caching
echo -e "\n\n${YELLOW}=== 5. TEST CACHING ===${NC}"
echo "Running same query twice to test caching..."

# First request
echo -e "\nFirst request:"
time1=$(curl -s -w "%{time_total}" -o /dev/null -X POST \
    -H "Content-Type: application/json" \
    -d '{"query": "cache test query", "limit": 2}' \
    "$API_URL/api/search")
echo "Time: ${time1}s"

# Second request (should be cached)
echo -e "\nSecond request (should be faster):"
time2=$(curl -s -w "%{time_total}" -o /dev/null -X POST \
    -H "Content-Type: application/json" \
    -d '{"query": "cache test query", "limit": 2}' \
    "$API_URL/api/search")
echo "Time: ${time2}s"

if (( $(echo "$time2 < $time1" | bc -l) )); then
    echo -e "${GREEN}✅ Caching appears to be working${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠️  Cache might not be working optimally${NC}"
fi

# Summary
echo -e "\n\n${YELLOW}=== TEST SUMMARY ===${NC}"
echo "----------------------------------------"
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✅ ALL TESTS PASSED! Deployment successful.${NC}"
else
    echo -e "\n${RED}❌ Some tests failed. Check the results above.${NC}"
fi

# Quick Frontend Test Command
echo -e "\n\n${YELLOW}=== QUICK FRONTEND TEST ===${NC}"
echo "Run this in your browser console:"
echo "----------------------------------------"
cat << 'EOF'
fetch('https://podinsight-api.vercel.app/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'AI startup valuations', limit: 5 })
}).then(r => r.json()).then(console.log)
EOF

echo -e "\n\n${YELLOW}=== CHECK LOGS ===${NC}"
echo "To view deployment logs, run:"
echo "vercel logs podinsight-api --prod"
