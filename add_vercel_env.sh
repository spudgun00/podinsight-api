#!/bin/bash
# Script to add environment variables to Vercel

echo "🔧 Adding environment variables to Vercel..."
echo "========================================"
echo ""
echo "Run these commands one by one:"
echo ""

# HUGGINGFACE_API_KEY (NEW for Sprint 1)
echo "1. Add Hugging Face API key (NEW - required for search):"
echo "   vercel env add HUGGINGFACE_API_KEY production"
echo "   → When prompted, paste your Hugging Face API key (check .env file)"
echo ""

# SUPABASE_URL (same as Sprint 0)
echo "2. Add Supabase URL (if not already added):"
echo "   vercel env add SUPABASE_URL production"  
echo "   → When prompted, paste: https://ydbtuijwsvwwcxkgogtb.supabase.co"
echo ""

# SUPABASE_KEY (same as Sprint 0)
echo "3. Add Supabase key (if not already added):"
echo "   vercel env add SUPABASE_KEY production"
echo "   → When prompted, paste: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlkYnR1aWp3c3Z3d2N4a2dvZ3RiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5MTI0ODcsImV4cCI6MjA2NTQ4ODQ4N30.tCqj4RlE88XK4IolfA0gnkNyElkGWLzP41jfi5FfznY"
echo ""

echo "4. After adding all variables, redeploy:"
echo "   vercel --prod --yes"
echo ""

echo "5. To verify environment variables are set:"
echo "   vercel env ls production"