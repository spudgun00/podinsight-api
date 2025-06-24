#!/bin/bash
# Deploy optimized Modal endpoint with GPU, snapshots, and volume caching
# This fixes the 150-second cold start issue

echo "🚀 Deploying optimized Modal endpoint..."
echo "=================================="

# Check if modal is installed
if ! command -v modal &> /dev/null; then
    echo "❌ Modal CLI not found. Please install with: pip install modal"
    exit 1
fi

# Check if logged in to Modal
if ! modal token identity &> /dev/null; then
    echo "❌ Not logged in to Modal. Please run: modal setup"
    exit 1
fi

# Deploy the optimized endpoint
echo "📦 Deploying podinsight-embeddings-optimized..."
modal deploy scripts/modal_web_endpoint_optimized.py

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🔍 Next steps:"
echo "1. Check the Modal dashboard for your endpoint URL"
echo "2. Update MODAL_EMBEDDING_URL in your .env file"
echo "3. Test the endpoint with: curl -X GET https://[your-url]/health"
echo ""
echo "⏱️  Expected performance:"
echo "   - First request (cold): ~7 seconds"
echo "   - Subsequent requests (warm): <200ms"
echo "   - Container stays warm for 10 minutes"
echo ""
echo "💰 Cost estimate:"
echo "   - 10 cold starts/day: ~$0.64/month"
echo "   - 100 cold starts/day: ~$6.40/month"
echo "   - Always-on GPU: $425-790/month (not recommended for low traffic)"