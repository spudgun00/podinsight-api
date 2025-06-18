#!/bin/bash
echo "🌐 Starting local test server..."
echo "================================"
echo ""
echo "Server will run at: http://localhost:8000/frontend_test.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
cd "$(dirname "$0")"
python3 -m http.server 8000