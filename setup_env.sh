#!/bin/bash
# This script ensures the correct environment variables are loaded from .env file

# Unset any existing MONGODB_URI to prevent override
unset MONGODB_URI

# Export all variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✅ Environment variables loaded from .env file"
    echo "   MONGODB_URI is now set correctly"
else
    echo "❌ .env file not found!"
    exit 1
fi
