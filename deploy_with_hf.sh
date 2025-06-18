#!/bin/bash
# Deploy with Hugging Face API key

echo "🚀 Deploying PodInsightHQ Search API with Hugging Face"
echo "====================================================="

# Add the environment variable to Vercel
echo "Setting Hugging Face API key..."
vercel env add HUGGINGFACE_API_KEY production < .env.production

echo -e "\n📦 Deploying to production..."
vercel --prod --yes

echo -e "\n✅ Deployment initiated!"
echo -e "\nOnce deployed, test with:"
echo "curl -X POST https://podinsight-api.vercel.app/api/search \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"query\": \"AI agents\", \"limit\": 3}'"