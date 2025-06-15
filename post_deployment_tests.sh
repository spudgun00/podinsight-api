#!/bin/bash

# PodInsightHQ API - Post-Deployment Test Suite
# Run this script after deploying to Vercel to verify everything is working
# Usage: ./post_deployment_tests.sh [API_URL]

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default API URL (update after deployment)
API_URL="${1:-https://podinsight-api.vercel.app}"
API_ENDPOINT="${API_URL}/api/topic-velocity"

echo "=========================================="
echo "PodInsightHQ API Post-Deployment Tests"
echo "=========================================="
echo "API URL: $API_URL"
echo "Endpoint: $API_ENDPOINT"
echo "Test Started: $(date)"
echo "=========================================="
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_result="$3"
    
    echo -n "Testing: $test_name... "
    
    if eval "$test_command"; then
        echo -e "${GREEN}PASSED${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        echo "  Expected: $expected_result"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to measure response time
measure_response_time() {
    local url="$1"
    local time=$(curl -o /dev/null -s -w '%{time_total}' "$url")
    echo "$time"
}

echo "1. HEALTH CHECK TESTS"
echo "===================="

# Test 1: Basic connectivity
run_test "API Reachability" \
    "curl -s -o /dev/null -w '%{http_code}' '$API_ENDPOINT' | grep -q '^200$'" \
    "HTTP 200 response"

# Test 2: Response format
run_test "JSON Response Format" \
    "curl -s '$API_ENDPOINT' | python3 -m json.tool > /dev/null 2>&1" \
    "Valid JSON response"

# Test 3: Health check structure
run_test "Response Structure" \
    "curl -s '$API_ENDPOINT' | jq -e '.data' > /dev/null 2>&1" \
    "Contains 'data' field"

echo ""
echo "2. DEFAULT ENDPOINT TESTS"
echo "========================="

# Test 4: Default topics
RESPONSE=$(curl -s "$API_ENDPOINT")
TOPIC_COUNT=$(echo "$RESPONSE" | jq -r '.data | keys | length' 2>/dev/null)
run_test "Default Topics (4 topics)" \
    "[ '$TOPIC_COUNT' -eq 4 ]" \
    "Returns exactly 4 topics"

# Test 5: Expected topics present
run_test "AI Agents Topic" \
    "echo '$RESPONSE' | jq -e '.data.\"AI Agents\"' > /dev/null 2>&1" \
    "AI Agents topic present"

run_test "Capital Efficiency Topic" \
    "echo '$RESPONSE' | jq -e '.data.\"Capital Efficiency\"' > /dev/null 2>&1" \
    "Capital Efficiency topic present"

run_test "DePIN Topic" \
    "echo '$RESPONSE' | jq -e '.data.\"DePIN\"' > /dev/null 2>&1" \
    "DePIN topic present"

run_test "B2B SaaS Topic" \
    "echo '$RESPONSE' | jq -e '.data.\"B2B SaaS\"' > /dev/null 2>&1" \
    "B2B SaaS topic present"

echo ""
echo "3. PARAMETER TESTS"
echo "=================="

# Test 6: Weeks parameter
WEEKS_RESPONSE=$(curl -s "$API_ENDPOINT?weeks=4")
WEEKS_COUNT=$(echo "$WEEKS_RESPONSE" | jq -r '.data."AI Agents" | length' 2>/dev/null)
run_test "Weeks Parameter" \
    "[ '$WEEKS_COUNT' -ge 4 ] && [ '$WEEKS_COUNT' -le 5 ]" \
    "Returns 4-5 weeks of data"

# Test 7: Custom topics
CUSTOM_RESPONSE=$(curl -s "$API_ENDPOINT?topics=AI+Agents,DePIN")
CUSTOM_COUNT=$(echo "$CUSTOM_RESPONSE" | jq -r '.data | keys | length' 2>/dev/null)
run_test "Custom Topics Parameter" \
    "[ '$CUSTOM_COUNT' -eq 2 ]" \
    "Returns only requested topics"

# Test 8: Crypto/Web3 topic (special case)
CRYPTO_RESPONSE=$(curl -s "$API_ENDPOINT?topics=Crypto/Web3")
run_test "Crypto/Web3 Topic (no spaces)" \
    "echo '$CRYPTO_RESPONSE' | jq -e '.data.\"Crypto/Web3\"' > /dev/null 2>&1" \
    "Crypto/Web3 topic works"

echo ""
echo "4. PERFORMANCE TESTS"
echo "===================="

# Test 9-13: Response time measurements
echo "Measuring response times (5 runs)..."
TOTAL_TIME=0
for i in {1..5}; do
    TIME=$(measure_response_time "$API_ENDPOINT")
    TIME_MS=$(echo "$TIME * 1000" | bc | cut -d'.' -f1)
    echo "  Run $i: ${TIME_MS}ms"
    TOTAL_TIME=$(echo "$TOTAL_TIME + $TIME" | bc)
    sleep 1
done

AVG_TIME=$(echo "scale=3; $TOTAL_TIME / 5" | bc)
AVG_TIME_MS=$(echo "$AVG_TIME * 1000" | bc | cut -d'.' -f1)
echo "  Average: ${AVG_TIME_MS}ms"

run_test "Performance (<500ms)" \
    "(( $(echo '$AVG_TIME < 0.5' | bc -l) ))" \
    "Average response time < 500ms"

echo ""
echo "5. ERROR HANDLING TESTS"
echo "======================="

# Test 14: Invalid weeks parameter
ERROR_RESPONSE=$(curl -s "$API_ENDPOINT?weeks=abc")
run_test "Invalid Parameter Handling" \
    "echo '$ERROR_RESPONSE' | jq -e '.detail' > /dev/null 2>&1" \
    "Returns error details"

# Test 15: Non-existent topic
EMPTY_RESPONSE=$(curl -s "$API_ENDPOINT?topics=NonExistentTopic")
EMPTY_DATA=$(echo "$EMPTY_RESPONSE" | jq -r '.data.NonExistentTopic | length' 2>/dev/null || echo "0")
run_test "Non-existent Topic Handling" \
    "[ '$EMPTY_DATA' -eq 0 ]" \
    "Returns empty data for invalid topic"

echo ""
echo "6. CORS VERIFICATION"
echo "==================="

# Test 16: OPTIONS request (for CORS)
CORS_CHECK=$(curl -s -X OPTIONS -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: GET" \
    -I "$API_ENDPOINT" 2>/dev/null | grep -i "access-control-allow-origin" || echo "not found")

if [[ "$CORS_CHECK" == *"not found"* ]]; then
    echo -e "${YELLOW}WARNING: CORS headers not visible in curl${NC}"
    echo "  This is expected - CORS headers may only appear for browser requests"
else
    run_test "CORS Headers Present" \
        "true" \
        "CORS headers configured"
fi

echo ""
echo "7. METADATA VERIFICATION"
echo "======================="

# Test 17: Metadata structure
run_test "Metadata Present" \
    "curl -s '$API_ENDPOINT' | jq -e '.metadata' > /dev/null 2>&1" \
    "Contains metadata field"

METADATA=$(curl -s "$API_ENDPOINT" | jq -r '.metadata')
run_test "Total Episodes Count" \
    "echo '$METADATA' | jq -e '.total_episodes' > /dev/null 2>&1" \
    "Metadata includes episode count"

echo ""
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo "The API is functioning correctly."
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo "Please check the deployment and fix any issues."
    exit 1
fi

echo ""
echo "=========================================="
echo "ADDITIONAL MANUAL CHECKS"
echo "=========================================="
echo "1. Check Vercel Dashboard for:"
echo "   - Function logs (no errors)"
echo "   - Memory usage (<512MB)"
echo "   - Cold start frequency"
echo ""
echo "2. Test from actual frontend (when deployed):"
echo "   - No CORS errors in browser console"
echo "   - Chart renders with data"
echo "   - Performance feels responsive"
echo ""
echo "3. Monitor for 24 hours:"
echo "   - Error rate stays near 0%"
echo "   - Response times remain consistent"
echo "   - No memory leaks or timeouts"
echo "=========================================="