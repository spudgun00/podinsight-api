#!/bin/bash
# Start API with correct environment

echo "🚀 Starting PodInsight API..."

# Always unset shell MONGODB_URI to prevent conflicts
unset MONGODB_URI

# Change to script directory
cd "$(dirname "$0")"

# Source the environment setup
source ./setup_env.sh

# Start the API
echo "Starting API server..."
python -m api.main
