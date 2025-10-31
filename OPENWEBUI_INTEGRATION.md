# OpenWebUI Integration Guide

## Problem

When connecting OpenWebUI directly to MCP servers, you get this error:
```
ERROR | open_webui.utils.tools:get_tool_server_data:584 - Could not fetch tool server spec from http://giphy:6700/mcp/openapi.json
```

**Why?** OpenWebUI expects OpenAPI-compatible endpoints (`/openapi.json`), but FastMCP servers use the MCP protocol over streamable HTTP.

## Solution: Use MCPO Proxy

The **mcpo** (Model Context Protocol Operator) acts as a translator between:
- **MCP servers** (your FastMCP services on port 6700)
- **OpenWebUI** (expects OpenAPI specs)

```
OpenWebUI → mcpo proxy (port 7700) → MCP server (port 6700)
```

## Setup Instructions

### 1. Start MCP Servers with MCPO Proxies

Instead of using `docker-compose.yml`, use the extended configuration:

```bash
# Stop any running services
docker-compose down

# Start MCP servers + MCPO proxies
docker-compose -f docker-compose-mcpo.yml up -d --build
```

This starts:
- **MCP Servers** (internal, port 6700): `giphymcp`, `ytmcp`, `wamcp`, `pistonmcp`, `cvemcp`, `usersmcp`, `tenormcp`
- **MCPO Proxies** (internal, port 7700): `giphymcpo`, `ytmcpo`, `wamcpo`, `pistonmcpo`, `cvemcpo`, `usersmcpo`, `tenormcpo`

### 2. Verify Services Are Running

```bash
# Check all containers are up
docker-compose -f docker-compose-mcpo.yml ps

# Test MCPO proxy from inside the network
docker exec openwebui curl http://giphymcpo:7700/openapi.json

# Or if you need to expose a port temporarily for testing:
# Add ports to docker-compose-mcpo.yml for the mcpo service you want to test
# ports:
#   - "7700:7700"
# Then: curl http://localhost:7700/openapi.json
```

### 3. Configure OpenWebUI

**Important:** All MCPO proxies now use the **same internal port 7700** within the Docker network. Each service has a unique container name.

1. Open **OpenWebUI** → ⚙️ **Admin Settings** → **External Tools**
2. Click **+ (Add Server)**
3. Configure each MCP server:

#### Giphy Server
- **Name**: Giphy MCP
- **Type**: MCP (Streamable HTTP)
- **Server URL**: `http://giphymcpo:7700`
- **Auth**: None (or configure as needed)
- Click **Save**

#### YouTube Server
- **Name**: YouTube MCP
- **Type**: MCP (Streamable HTTP)
- **Server URL**: `http://ytmcpo:7700`
- **Auth**: None
- Click **Save**

#### WolframAlpha Server
- **Name**: WolframAlpha MCP
- **Type**: MCP (Streamable HTTP)
- **Server URL**: `http://wamcpo:7700`
- **Auth**: None
- Click **Save**

#### Piston Server
- **Name**: Piston MCP
- **Type**: MCP (Streamable HTTP)
- **Server URL**: `http://pistonmcpo:7700`
- **Auth**: None
- Click **Save**

#### CVE Server
- **Name**: CVE MCP
- **Type**: MCP (Streamable HTTP)
- **Server URL**: `http://cvemcpo:7700`
- **Auth**: None
- Click **Save**

#### UserContext Server
- **Name**: UserContext MCP
- **Type**: MCP (Streamable HTTP)
- **Server URL**: `http://usersmcpo:7700`
- **Auth**: None
- Click **Save**

#### Tenor Server
- **Name**: Tenor MCP
- **Type**: MCP (Streamable HTTP)
- **Server URL**: `http://tenormcpo:7700`
- **Auth**: None
- Click **Save**

### 4. Network Configuration

#### OpenWebUI MUST be in the same Docker network (`intranet`):

Add OpenWebUI to the `intranet` network by updating your OpenWebUI docker-compose:
```yaml
services:
  openwebui:
    # ... your existing config ...
    networks:
      - default  # Your existing networks
      - intranet  # Add this

networks:
  intranet:
    external: true
  default:
    # Your existing network config
```

Then restart OpenWebUI:
```bash
docker-compose restart openwebui
# or
docker-compose up -d openwebui
```

## Port Reference

### MCP Servers (Internal - Port 6700)
All MCP servers run on the same internal port for consistency:
- `giphymcp:6700` - MCP Protocol
- `ytmcp:6700` - MCP Protocol
- `wamcp:6700` - MCP Protocol
- `pistonmcp:6700` - MCP Protocol
- `cvemcp:6700` - MCP Protocol
- `usersmcp:6700` - MCP Protocol
- `tenormcp:6700` - MCP Protocol

### MCPO Proxies (Internal - Port 7700, OpenAPI Compatible)
**All proxies use the same port 7700**, differentiated by container name:
- `giphymcpo:7700` - OpenAPI/MCP Bridge
- `ytmcpo:7700` - OpenAPI/MCP Bridge
- `wamcpo:7700` - OpenAPI/MCP Bridge
- `pistonmcpo:7700` - OpenAPI/MCP Bridge
- `cvemcpo:7700` - OpenAPI/MCP Bridge
- `usersmcpo:7700` - OpenAPI/MCP Bridge
- `tenormcpo:7700` - OpenAPI/MCP Bridge

**No external ports are exposed** - all communication happens internally via the `intranet` Docker network.

## Testing the Integration

### 1. Test MCPO Proxy from OpenWebUI Container
```bash
# Get OpenAPI spec (should work)
docker exec openwebui curl http://giphymcpo:7700/openapi.json

# Test tool listing
docker exec openwebui curl -X POST http://giphymcpo:7700/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

### 2. Verify Network Connectivity
```bash
# Check if OpenWebUI can reach MCPO proxies
docker exec openwebui ping -c 2 giphymcpo
docker exec openwebui ping -c 2 ytmcpo
docker exec openwebui ping -c 2 wamcpo

# List containers on intranet network
docker network inspect intranet | grep Name
```

### 3. Test from OpenWebUI
1. Create a new chat in OpenWebUI
2. Type a message that would use the tools
3. Check that OpenWebUI can discover and call the MCP tools

### 4. Check Logs
```bash
# MCPO proxy logs
docker logs giphymcpo
docker logs ytmcpo

# MCP server logs
docker logs giphymcp
docker logs ytmcp

# OpenWebUI logs
docker logs openwebui
```

## Troubleshooting

### Error: "Could not fetch tool server spec"
**Solution**: Ensure you're using the MCPO proxy URL with the correct container name:
- ❌ Wrong: `http://giphymcp:6700` (MCP server directly)
- ✅ Correct: `http://giphymcpo:7700` (MCPO proxy)

### Error: "Connection refused"
**Solutions**:
1. Verify services are running: `docker-compose -f docker-compose-mcpo.yml ps`
2. Check network connectivity:
   ```bash
   # From OpenWebUI container
   docker exec openwebui ping giphymcpo
   docker exec openwebui curl http://giphymcpo:7700/openapi.json
   ```
3. **Ensure OpenWebUI is on the `intranet` network**
4. Restart all services:
   ```bash
   docker-compose -f docker-compose-mcpo.yml restart
   ```

### Error: "Network 'intranet' not found"
**Solution**:
```bash
docker network create intranet
docker-compose -f docker-compose-mcpo.yml up -d
```

### Tools not showing up in OpenWebUI
**Solutions**:
1. Verify the MCPO proxy is returning tools:
   ```bash
   docker exec openwebui curl http://giphymcpo:7700/mcp -X POST \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
   ```
2. Check that OpenWebUI is on the `intranet` network:
   ```bash
   docker network inspect intranet | grep openwebui
   ```
3. Restart OpenWebUI after adding servers
4. Check OpenWebUI logs for errors: `docker logs openwebui`

### MCPO proxy crashes or restarts
**Solution**: Check MCP server is accessible:
```bash
# From MCPO container
docker exec giphymcpo curl http://giphymcp:6700/mcp

# Check logs
docker logs giphymcpo
docker logs giphymcp
```

### OpenWebUI not in the intranet network
**Solution**: Add it to your OpenWebUI configuration and restart:
```yaml
networks:
  - intranet

networks:
  intranet:
    external: true
```

## Architecture Diagram

```
┌─────────────────┐
│   OpenWebUI     │ (must be on 'intranet' network)
└────────┬────────┘
         │ HTTP (OpenAPI)
         │
    ┌────┴────┬────────┬────────┬────────┬────────┬────────┐
    │         │        │        │        │        │        │
    ▼         ▼        ▼        ▼        ▼        ▼        ▼
┌─────────┐ ┌───────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│giphymcpo│ │ytmcpo │ │wamcpo│ │pmcpo │ │cvecpo│ │userpo│ │tenmcpo│
│  :7700  │ │ :7700 │ │:7700 │ │:7700 │ │:7700 │ │:7700 │ │:7700 │
└────┬────┘ └───┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
     │          │        │        │        │        │        │
     │ MCP Protocol (streamable HTTP on port 6700)  │        │
     │          │        │        │        │        │        │
     ▼          ▼        ▼        ▼        ▼        ▼        ▼
┌─────────┐ ┌───────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│giphymcp │ │ytmcp  │ │wamcp │ │piston│ │cvemcp│ │usermcp│ │tenmcp│
│  :6700  │ │ :6700 │ │:6700 │ │:6700 │ │:6700 │ │:6700 │ │:6700 │
│(FastMCP)│ │(Fast) │ │(Fast)│ │(Fast)│ │(Fast)│ │(Fast)│ │(Fast)│
└─────────┘ └───────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘
```

## Important Notes

1. **All MCPO proxies use port 7700** - simplified architecture
2. **No external ports exposed** - everything communicates via Docker network
3. **OpenWebUI MUST be on the `intranet` network** to reach the services
4. **Use container names** for service discovery (e.g., `giphymcpo:7700`)
5. **MCP servers on port 6700** are for internal/direct MCP client access only
6. **API keys** (GIPHY_API_KEY, YOUTUBE_API_KEY, etc.) must be set in environment or `.env` file
7. **OpenWebUI v0.6.31+** is required for MCP support

## Quick Commands

```bash
# Start everything
docker network create intranet  # One time only
docker-compose -f docker-compose-mcpo.yml up -d --build

# Check status
docker-compose -f docker-compose-mcpo.yml ps

# View logs
docker-compose -f docker-compose-mcpo.yml logs -f

# Rebuild after changes
docker-compose -f docker-compose-mcpo.yml up -d --build

# Stop everything
docker-compose -f docker-compose-mcpo.yml down

# Test MCPO endpoints (from inside network)
docker exec openwebui curl http://giphymcpo:7700/openapi.json
docker exec openwebui curl http://ytmcpo:7700/openapi.json
docker exec openwebui curl http://wamcpo:7700/openapi.json
docker exec openwebui curl http://pistonmcpo:7700/openapi.json
docker exec openwebui curl http://cvemcpo:7700/openapi.json
docker exec openwebui curl http://usersmcpo:7700/openapi.json
docker exec openwebui curl http://tenormcpo:7700/openapi.json
```

## Environment Variables

Create a `.env` file in the project root with your API keys:

```bash
# Required for Giphy
GIPHY_API_KEY=your_giphy_api_key_here

# Required for YouTube
YOUTUBE_API_KEY=your_youtube_api_key_here

# Required for WolframAlpha
WOLFRAMALPHA_APP_ID=your_wolframalpha_app_id_here

# Optional for Tenor
TENOR_API_KEY=your_tenor_api_key_here

# Optional for NVD (higher rate limits)
NVD_API_KEY=your_nvd_api_key_here

# Optional - User Context API
USER_API_BASE_URL=http://usercontext_api:9000/api/v1
```

## Summary of Changes

### Standardized Architecture:
- **MCP Servers**: All on port `6700`
- **MCPO Proxies**: All on port `7700`
- **No external ports**: All internal Docker network communication
- **Simplified URLs**: Just change the container name, port stays `7700`

### Benefits:
✅ Simpler configuration - one port to remember for MCPO (7700)  
✅ More secure - no external port exposure  
✅ Easier to scale - add new services with same pattern  
✅ Better isolation - services only accessible within Docker network  
✅ Consistent with Docker networking best practices  

## References

- [OpenWebUI MCP Documentation](https://docs.openwebui.com/features/mcp/)
- [MCPO Project](https://github.com/open-webui/mcpo)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/jlowin/fastmcp)
