#!/bin/bash
# Deployment commands for Search API

echo "🚀 PodInsightHQ Search API Deployment"
echo "===================================="

# Step 1: Login to Vercel (if needed)
echo "Step 1: Logging in to Vercel..."
vercel login

# Step 2: Deploy to production
echo -e "\nStep 2: Deploying to production..."
vercel --prod --yes

# Step 3: Test the deployment
echo -e "\nStep 3: Testing deployment..."
echo "Waiting 10 seconds for deployment to be ready..."
sleep 10

# Test health check
echo -e "\n📍 Testing health check..."
curl -s https://podinsight-api.vercel.app/ | python -m json.tool

# Test search endpoint
echo -e "\n🔍 Testing search endpoint..."
curl -s -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI agents and startup valuations",
    "limit": 3
  }' | python -m json.tool

echo -e "\n✅ Deployment complete!"
echo "Check logs with: vercel logs --prod"
