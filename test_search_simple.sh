#\!/bin/bash

echo "Testing PodInsight Search API..."
echo "================================"

# Test search with curl
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI agents", "limit": 3}' \
  | python3 -m json.tool

echo -e "\n\nTo test in your browser, use a tool like:"
echo "1. Postman (https://www.postman.com/)"
echo "2. Thunder Client (VS Code extension)"
echo "3. Or use the browser console:"
echo ""
echo "fetch('https://podinsight-api.vercel.app/api/search', {"
echo "  method: 'POST',"
echo "  headers: {'Content-Type': 'application/json'},"
echo "  body: JSON.stringify({query: 'AI agents', limit: 3})"
echo "}).then(r => r.json()).then(console.log)"
