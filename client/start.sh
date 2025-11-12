#!/bin/bash
# Quick start script for MCP Interactive Client

cd "$(dirname "$0")"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --rebuild, -r    Rebuild Docker image without cache"
    echo "  --help, -h       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0               # Normal start"
    echo "  $0 --rebuild     # Rebuild and start"
    echo "  $0 -r            # Rebuild and start (short form)"
}

# Parse command line arguments
REBUILD=false
case "$1" in
    --rebuild|-r)
        REBUILD=true
        echo "🔄 Rebuild mode enabled"
        ;;
    --help|-h)
        show_usage
        exit 0
        ;;
    "")
        # No arguments, proceed normally
        ;;
    *)
        echo "❌ Error: Unknown option '$1'"
        echo ""
        show_usage
        exit 1
        ;;
esac

echo "�🚀 Starting MCP Interactive Client..."
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

# Build container
if [ "$REBUILD" = true ]; then
    echo "🔨 Rebuilding client container (no cache)..."
    docker compose build --no-cache
else
    echo "🔨 Building client container..."
    docker compose build
fi

echo ""
echo "▶️  Running interactive client..."
echo ""

docker compose run --rm mcpclient
