# MCP Setup and Troubleshooting Guide

## Quick Setup

### 1. Create Network
```bash
docker network create intranet
```

### 2. Set up Environment Variables (Optional but Recommended)
```bash
# Copy the template
cp .env.template .env

# Edit .env file with your API keys
nano .env  # or use your preferred editor
```

### 3. Start MCP Servers
```bash
# Start all servers
docker-compose up -d

# Or start specific servers
docker-compose up -d giphymcp pistonmcp cvemcp
```

### 4. Test with Client
```bash
# From the project root
cd client
python client.py

# Or run specific tests
python client.py --server piston
python client.py --demo piston
```

## API Keys (Optional for Basic Testing)

### Required for Full Functionality:
- **Giphy**: https://developers.giphy.com/
- **YouTube**: https://console.developers.google.com/
- **WolframAlpha**: https://developer.wolframalpha.com/

### Servers that Work Without API Keys:
- **Piston**: Code execution (works out of the box)
- **CVE**: Vulnerability database (works with rate limits)
- **UserContext**: User history (if API server is running)

## Troubleshooting

### "No address associated with hostname" Error
**Problem**: Client can't connect to servers
**Solution**: 
1. Make sure Docker containers are running: `docker-compose ps`
2. Check if ports are exposed: `docker-compose logs giphymcp`
3. Use `localhost` instead of container names when running client outside Docker

### "Connection refused" Error
**Problem**: Server not running or wrong port
**Solutions**:
1. Start servers: `docker-compose up -d`
2. Check logs: `docker-compose logs [service_name]`
3. Verify ports in docker-compose.yml match client config

### "Missing API Key" Errors
**Problem**: External APIs require authentication
**Solutions**:
1. Test with servers that don't require keys first (Piston, CVE)
2. Get API keys and add to .env file
3. Uncomment environment variables in docker-compose.yml

### Docker Network Issues
**Problem**: Containers can't communicate
**Solutions**:
1. Create external network: `docker network create intranet`
2. Restart containers: `docker-compose down && docker-compose up -d`

## Quick Test Commands

```bash
# Test basic connectivity
python client.py --server piston

# Test enhanced functionality (no API keys needed)
python client.py --demo piston

# Test specific tools
python client.py --call-tool piston get_piston_runtimes
python client.py --call-tool cve get_cve_statistics

# With API keys configured:
python client.py --call-tool giphy get_top_trending_giphy_image
python client.py --call-tool youtube search_youtube_videos query="Python" max_results=3
```

## Docker Compose Status Check
```bash
# Check running containers
docker-compose ps

# View logs
docker-compose logs
docker-compose logs giphymcp

# Restart specific service
docker-compose restart giphymcp

# Stop all
docker-compose down

# Rebuild and start
docker-compose up --build -d
```