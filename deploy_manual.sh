#!/bin/bash
# Manual deployment steps for PodInsightHQ Search API

echo "🚀 PodInsightHQ Search API - Manual Deployment Guide"
echo "=================================================="
echo ""
echo "Please follow these steps:"
echo ""
echo "1️⃣  Login to Vercel:"
echo "   vercel login"
echo ""
echo "2️⃣  Link your project (if not already linked):"
echo "   vercel link"
echo ""
echo "3️⃣  Add environment variables:"
echo ""
echo "   vercel env add HUGGINGFACE_API_KEY production"
echo "   → Paste your Hugging Face API key from .env file"
echo ""
echo "   vercel env add SUPABASE_URL production"
echo "   → Paste your Supabase URL from .env"
echo ""
echo "   vercel env add SUPABASE_KEY production"
echo "   → Paste your Supabase anon key from .env"
echo ""
echo "4️⃣  Deploy to production:"
echo "   vercel --prod"
echo ""
echo "5️⃣  Test the deployment:"
echo "   ./test_deployment.sh"
echo ""
echo "=================================================="
echo ""
read -p "Press Enter to see your current environment variables..."

echo ""
echo "Your current .env values:"
if [ -f .env ]; then
    grep -E "SUPABASE_URL|SUPABASE_KEY" .env | sed 's/=.*$/=<hidden>/'
else
    echo "No .env file found"
fi

echo ""
echo "Hugging Face API Key: Check your .env file"