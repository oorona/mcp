#!/bin/bash
# Quick start script for MCP Interactive Client

cd "$(dirname "$0")"

echo "🚀 Starting MCP Interactive Client..."
echo ""

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    exit 1
fi

# Check if intranet network exists
if ! docker network ls | grep -q intranet; then
    echo "⚠️  Creating 'intranet' Docker network..."
    docker network create intranet
fi

# Build and run
echo "🔨 Building client container..."
docker compose build

echo ""
echo "▶️  Running interactive client..."
echo ""

docker compose run --rm mcpclient
