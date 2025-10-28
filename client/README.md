# MCP Multi-Server Client

A Docker-based production client for testing and interacting with MCP servers in the ecosystem.

## Overview

This client provides a clean, focused interface for testing all MCP servers with enhanced functionality:
- **Giphy** (6100) - Enhanced: GIF/sticker search, trending, random, translate, categories, autocomplete
- **YouTube** (6500) - Enhanced: Video search, transcript checking, trending, comments, channel info
- **UserContext** (6600) - User message history  
- **WolframAlpha** (6700) - Enhanced: Mathematical calculations, unit conversions, scientific data, equation solving, statistical analysis, definitions
- **Piston** (6800) - Enhanced: Auto-version selection, multiple language support
- **CVE** (6900) - Enhanced: Comprehensive vulnerability analysis and statistics
- **Tenor** (7200) - Enhanced: Advanced GIF search, categories, trending, autocomplete

## Features

### ✅ Server Testing
- Test individual servers or all servers at once
- Connectivity validation with ping
- Tool and resource enumeration
- Clear success/failure reporting

### 🔧 Tool Execution
- Call any tool on any server with arguments
- JSON argument parsing with fallback to strings
- Pretty-printed results with truncation
- Comprehensive error handling

### 📋 Tool Discovery
- List all available tools across all servers
- Show tool descriptions when available
- Organized by server for easy browsing

### 🚀 Enhanced Functionality Demos
- Interactive demos for each enhanced server
- Comprehensive testing of new features
- Auto-version selection demonstrations
- Real-world usage examples

## Usage

### Prerequisites
1. **Create the Docker network** (if it doesn't exist):
```bash
docker network create intranet
```

2. **Start MCP servers** (from the main project directory):
```bash
# Start MCP servers only
docker-compose up -d

# OR start MCP servers with operators
docker-compose -f docker-compose-mcpo.yml up -d
```

### Basic Testing
```bash
# Test all servers (default behavior)
docker-compose run --rm mcpclient

# Test specific server
docker-compose run --rm mcpclient python client.py --server giphy

# Verbose output
docker-compose run --rm mcpclient python client.py --verbose
```

### Enhanced Functionality Demos
```bash
# Run demos for enhanced server functionality
docker-compose run --rm mcpclient python client.py --demo giphy
docker-compose run --rm mcpclient python client.py --demo youtube
docker-compose run --rm mcpclient python client.py --demo piston
docker-compose run --rm mcpclient python client.py --demo cve
docker-compose run --rm mcpclient python client.py --demo tenor
docker-compose run --rm mcpclient python client.py --demo wolframalpha

# Run demos for all servers
docker-compose run --rm mcpclient python client.py --demo-all

# Quick test of enhanced features
docker-compose run --rm mcpclient python client.py --test-enhanced
```

### Tool Discovery
```bash
# List all available tools
docker-compose run --rm mcpclient python client.py --list-tools

# Example output:
# 📦 GIPHY (10 tools):
#    • get_giphy_image_by_search - Search GIFs by query
#    • get_top_trending_giphy_image - Get trending GIF
#    • get_random_giphy_image - Get random GIF (with optional tag)
#    • translate_to_giphy_image - Convert phrases to perfect GIFs
#    • get_giphy_categories - Browse available categories
#    • get_giphy_autocomplete - Get search suggestions
#    • get_trending_search_terms - Popular search terms
#    • get_giphy_image_by_id - Get specific GIF by ID
#    • search_giphy_stickers - Search for stickers
#    • get_trending_giphy_stickers - Get trending stickers
# 📦 CVE (8 tools):
#    • get_recent_cves
#    • search_cves_by_severity
#    • get_product_vulnerability_summary
#    ...
```

### Tool Execution
```bash
# Simple tool call (no arguments)
docker-compose run --rm mcpclient python client.py --call-tool giphy get_top_trending_giphy_image

# Enhanced YouTube features
docker-compose run --rm mcpclient python client.py --call-tool youtube search_youtube_videos query="Python tutorial" max_results=3
docker-compose run --rm mcpclient python client.py --call-tool youtube check_transcript_availability video_id=dQw4w9WgXcQ
docker-compose run --rm mcpclient python client.py --call-tool youtube get_trending_videos region_code=US max_results=5

# Enhanced Piston features (auto-version selection)
docker-compose run --rm mcpclient python client.py --call-tool piston execute_code language=python code="print('Auto-selected Python version!')"
docker-compose run --rm mcpclient python client.py --call-tool piston get_available_language_versions language=python
docker-compose run --rm mcpclient python client.py --call-tool piston get_piston_runtimes

# Enhanced CVE features
docker-compose run --rm mcpclient python client.py --call-tool cve get_cve_statistics
docker-compose run --rm mcpclient python client.py --call-tool cve search_cves_by_severity severity=HIGH limit=5
docker-compose run --rm mcpclient python client.py --call-tool cve get_cve_trends

# Enhanced Tenor features
docker-compose run --rm mcpclient python client.py --call-tool tenor search_tenor_gifs query="celebration" limit=3
docker-compose run --rm mcpclient python client.py --call-tool tenor get_trending_tenor_gifs limit=5
docker-compose run --rm mcpclient python client.py --call-tool tenor get_tenor_categories

# Enhanced WolframAlpha features
docker-compose run --rm mcpclient python client.py --call-tool wolframalpha calculate_math expression="integrate x^2 from 0 to 5"
docker-compose run --rm mcpclient python client.py --call-tool wolframalpha convert_units value="100 km" target_unit="miles"
docker-compose run --rm mcpclient python client.py --call-tool wolframalpha solve_equation equation="x^2 + 5x + 6 = 0"
docker-compose run --rm mcpclient python client.py --call-tool wolframalpha get_scientific_data topic="hydrogen atom"
docker-compose run --rm mcpclient python client.py --call-tool wolframalpha get_statistical_analysis data_description="mean of 1,2,3,4,5"

# Complex arguments (JSON parsing)
docker-compose run --rm mcpclient python client.py --call-tool piston execute_code language=javascript code="console.log('Hello Node.js!');"

# String arguments
docker-compose run --rm mcpclient python client.py --call-tool giphy get_giphy_image_by_search query="funny cats" search_limit=3

# Enhanced Giphy features
docker-compose run --rm mcpclient python client.py --call-tool giphy get_random_giphy_image tag="celebration"
docker-compose run --rm mcpclient python client.py --call-tool giphy translate_to_giphy_image phrase="good morning"
docker-compose run --rm mcpclient python client.py --call-tool giphy search_giphy_stickers query="thumbs up" search_limit=2
docker-compose run --rm mcpclient python client.py --call-tool giphy get_giphy_categories
docker-compose run --rm mcpclient python client.py --call-tool giphy get_giphy_autocomplete query="hap" limit=5
docker-compose run --rm mcpclient python client.py --call-tool giphy get_trending_search_terms
docker-compose run --rm mcpclient python client.py --call-tool giphy get_trending_giphy_stickers limit=3
```

## Docker Setup

### Container Architecture
The client runs in a Docker container connected to the `intranet` network, allowing it to communicate with all MCP servers using their container names:
- **giphy** → `giphymcp:6100`
- **youtube** → `ytmcp:6500`
- **usercontext** → `usersmcp:6600`
- **wolframalpha** → `wamcp:6700`
- **piston** → `pistonmcp:6800`
- **cve** → `cvemcp:6900`
- **tenor** → `tenormcp:7200`

### Quick Start
```bash
# 1. Create network (one time setup)
docker network create intranet

# 2. Start from main project directory
cd /path/to/mcp
docker-compose up -d

# 3. Run client from client directory
cd client
docker-compose run --rm mcpclient
```

### Alternative: One-Line Execution
```bash
# Test all servers (default)
docker-compose run --rm mcpclient

# List all tools
docker-compose run --rm mcpclient python client.py --list-tools

# Call specific tool
docker-compose run --rm mcpclient python client.py --call-tool cve get_recent_cves limit=5
```

## Configuration

### Network Architecture
The client runs in Docker and connects to MCP servers via the `intranet` Docker network using container names as hostnames.

### Default Connection
- **Host**: `bot` (automatically maps to Docker container names: `giphymcp`, `ytmcp`, etc.)
- **Network**: `intranet` Docker network
- **Transport**: HTTP

For local development (running client outside Docker), use `--host localhost`.

### Server Ports
The client uses these default ports:
- Giphy: 6100
- YouTube: 6500  
- UserContext: 6600
- WolframAlpha: 6700
- Piston: 6800
- CVE: 6900
- Tenor: 7200

## Examples

### Quick Server Health Check
```bash
$ docker-compose run --rm mcpclient
🔍 Testing MCP servers...
==================================================
[SUCCESS] ✅ giphy: Ping successful
[SUCCESS] ✅ giphy: 10 tools, 0 resources
[SUCCESS] ✅ wolframalpha: Ping successful
[SUCCESS] ✅ wolframalpha: 7 tools, 0 resources
[SUCCESS] ✅ piston: Ping successful
[SUCCESS] ✅ piston: 4 tools, 1 resources
[SUCCESS] ✅ cve: Ping successful  
[SUCCESS] ✅ cve: 8 tools, 0 resources
[SUCCESS] ✅ tenor: Ping successful
[SUCCESS] ✅ tenor: 8 tools, 0 resources

==================================================
📊 SUMMARY
==================================================
✅ Connected: 6/7 servers
   • giphy: 10 tools - Enhanced GIF/sticker search and discovery
   • youtube: 8 tools - Enhanced video search and analysis
   • wolframalpha: 7 tools - Mathematical calculations and scientific data
   • piston: 4 tools - Code execution with auto-version selection
   • cve: 8 tools - Comprehensive vulnerability database
   • tenor: 8 tools - Advanced GIF and meme search

❌ Failed: 1 servers
   • usercontext: Connection refused
```

### Enhanced Demo Output
```bash
$ docker-compose run --rm mcpclient python client.py --demo piston
� Piston MCP Server Demo
========================================

� Testing: get_piston_runtimes
📊 Result:
{
  "total_runtimes": 89,
  "total_languages": 35,
  "language_summary": [
    {
      "language": "python",
      "version_count": 3,
      "highest_version": "3.11.2",
      "versions": ["3.11.2", "3.10.9", "2.7.18"]
    }
  ]
}

🔧 Testing: execute_code (auto-version)
📊 Result:
{
  "language": "python", 
  "version": "3.11.2",
  "run": {
    "stdout": "Hello from auto-selected Python!\nPython version: 3.11.2",
    "code": 0
  },
  "version_selection": {
    "requested_version": null,
    "selected_version": "3.11.2",
    "auto_selected": true
  }
}

🔬 Testing: calculate_math (WolframAlpha)
📊 Result:
{
  "result": "2.7182818284590451",
  "interpretation": "mathematical constant e",
  "calculation_steps": ["natural exponential function", "mathematical constant"]
}

🔧 Testing: convert_units (WolframAlpha)
📊 Result:
{
  "result": "32 degrees Fahrenheit",
  "conversion": "0 degrees Celsius = 32 degrees Fahrenheit",
  "formula": "°F = (°C × 9/5) + 32"
}

🎨 Testing: translate_to_giphy_image (Giphy)
📊 Result:
{
  "image_url": "https://media3.giphy.com/media/26BRuo6sLetdllPAQ/giphy.webp",
  "title": "good morning coffee GIF",
  "id": "26BRuo6sLetdllPAQ",
  "giphy_page_url": "https://giphy.com/gifs/coffee-morning-26BRuo6sLetdllPAQ",
  "original_phrase": "good morning"
}

🔧 Testing: get_giphy_categories (Giphy)
📊 Result:
{
  "categories": [
    {"name": "actions", "name_encoded": "actions"},
    {"name": "reactions", "name_encoded": "reactions"},
    {"name": "celebrities", "name_encoded": "celebrities"}
  ],
  "total_count": 27
}
```

### Enhanced Tool Discovery
```bash
$ docker-compose run --rm mcpclient python client.py --list-tools
🛠️  Available Tools:
==================================================

📦 GIPHY (10 tools):
   • get_giphy_image_by_search - Search GIFs by query
   • get_top_trending_giphy_image - Get trending GIF
   • get_random_giphy_image - Get random GIF (with optional tag)
   • translate_to_giphy_image - Convert phrases to perfect GIFs
   • get_giphy_categories - Browse available categories
   • get_giphy_autocomplete - Get search suggestions
   • get_trending_search_terms - Popular search terms
   • get_giphy_image_by_id - Get specific GIF by ID
   • search_giphy_stickers - Search for stickers
   • get_trending_giphy_stickers - Get trending stickers

📦 YOUTUBE (8 tools):
   • search_youtube_videos - Search for YouTube videos
   • get_channel_info - Get detailed channel information
   • get_video_comments - Get comments for a video
   • get_trending_videos - Get trending videos by region
   • check_transcript_availability - Check available transcripts
   • get_playlist_videos - Get videos from a playlist
   • extract_video_id_from_url - Extract and validate video IDs
   • get_youtube_video_transcript - Enhanced transcript retrieval

📦 PISTON (4 tools):
   • execute_code - Execute code with auto-version selection
   • get_piston_runtimes - List all available languages
   • get_available_language_versions - Get versions for specific language
   • get_piston_language_version - Get single version info

📦 WOLFRAMALPHA (7 tools):
   • calculate_math - Perform mathematical calculations
   • convert_units - Convert between measurement units
   • get_scientific_data - Retrieve scientific information
   • solve_equation - Solve mathematical equations
   • get_statistical_analysis - Perform statistical computations
   • get_definition_and_examples - Get definitions and examples
   • query_wolfram_alpha - General WolframAlpha queries

📦 CVE (8 tools):
   • get_recent_cves - Get recent vulnerabilities
   • get_cve_details - Get detailed CVE information  
   • search_cves_by_severity - Search by severity level
   • search_cves_by_keyword - Search by keyword
   • get_cve_statistics - Get vulnerability statistics
   • get_product_vulnerability_summary - Product vulnerability analysis
   • get_cve_trends - Analyze vulnerability trends
   • get_remediation_info - Get remediation recommendations

📦 TENOR (8 tools):
   • search_tenor_gifs - Search for GIFs
   • get_trending_tenor_gifs - Get trending GIFs
   • get_tenor_categories - Get available categories
   • get_tenor_autocomplete - Get search suggestions
   • get_tenor_search_suggestions - Enhanced search suggestions
   • get_tenor_trending_terms - Get trending search terms
   • get_random_tenor_gifs - Get random GIFs by query
   • register_tenor_share - Register GIF sharing analytics
```

### Tool Execution Examples
```bash
$ docker-compose run --rm mcpclient python client.py --call-tool piston execute_code language=python code="print('Auto Python version!')"
🔧 Calling execute_code on piston
📝 Arguments: {'language': 'python', 'code': "print('Auto Python version!')"}
==================================================
[SUCCESS] ✅ Tool call successful
📊 RESULT:
{
  "language": "python",
  "version": "3.11.2", 
  "run": {
    "stdout": "Auto Python version!\n",
    "stderr": "",
    "output": "Auto Python version!\n",
    "code": 0
  },
  "version_selection": {
    "requested_version": null,
    "selected_version": "3.11.2",
    "auto_selected": true
  }
}

$ docker-compose run --rm mcpclient python client.py --call-tool wolframalpha calculate_math expression="2^10"
🔧 Calling calculate_math on wolframalpha
📝 Arguments: {'expression': '2^10'}
==================================================
[SUCCESS] ✅ Tool call successful
📊 RESULT:
{
  "expression": "2^10",
  "primary_result": "1024",
  "success": true,
  "mathematical_analysis": {
    "has_mathematical_content": true,
    "calculations": [
      {
        "title": "Result",
        "content": [{"text": "1024"}]
      }
    ]
  },
  "has_visual_elements": false
}
```

## Error Handling

The client provides clear error messages for common issues:

### Connection Errors
```bash
❌ giphy: HTTPConnectionPool(host='bot', port=6100): Max retries exceeded
```

### Tool Errors  
```bash
❌ Tool call failed: Unknown tool 'invalid_tool_name'
```

### Argument Errors
```bash
❌ Usage: --call-tool <server> <tool> [arg1=val1] [arg2=val2]
```

## Integration

### Docker Commands
```bash
# Interactive mode (default behavior)
docker-compose run --rm mcpclient

# Enhanced demo commands
docker-compose run --rm mcpclient python client.py --demo-all
docker-compose run --rm mcpclient python client.py --demo giphy
docker-compose run --rm mcpclient python client.py --demo piston
docker-compose run --rm mcpclient python client.py --test-enhanced

# One-shot commands
docker-compose run --rm mcpclient python client.py --list-tools
docker-compose run --rm mcpclient python client.py --call-tool giphy get_top_trending_giphy_image

# Enhanced functionality examples
docker-compose run --rm mcpclient python client.py --call-tool youtube search_youtube_videos query="AI tutorial" max_results=3
docker-compose run --rm mcpclient python client.py --call-tool piston execute_code language=python code="import sys; print(sys.version)"
docker-compose run --rm mcpclient python client.py --call-tool wolframalpha calculate_math expression="integrate x^2 dx"
docker-compose run --rm mcpclient python client.py --call-tool tenor search_tenor_gifs query="success" limit=2

# With shell access for debugging
docker-compose run --rm mcpclient bash
```

### In Scripts (Local Development)
```python
from client import MCPClient

async def test_servers():
    # For Docker environment, use container hostnames
    client = MCPClient(host="bot", verbose=True)
    
    # Test all servers
    results = await client.test_all_servers()
    
    # Call specific tool
    result = await client.call_tool("giphy", "get_top_trending_giphy_image")
    
    return results, result
```

### Network Connectivity
```bash
# Check if containers can reach each other
docker-compose run --rm mcpclient ping giphymcp
docker-compose run --rm mcpclient ping cvemcp

# Debug network issues
docker network ls
docker network inspect intranet
```

## Development

### Adding New Servers
To add a new MCP server to the client:

1. Add server configuration to `SERVERS` dict:
```python
SERVERS = {
    # ... existing servers ...
    "newserver": {"port": 8000, "host": "bot", "description": "New server description"}
}
```

2. No other changes needed - the client automatically discovers tools and resources.

### Customizing Output
The client provides several customization options:
- `--verbose` for detailed logging
- JSON truncation (configurable via `max_lines` parameter)
- Color-coded status messages (✅ ❌ 🔧 📊)

## Troubleshooting

### Common Issues

**"Network 'intranet' not found"**
```bash
docker network create intranet
```

**"No such service: mcpclient"**
```bash
# Make sure you're in the client directory
cd client
docker-compose run --rm mcpclient
```

**"Connection refused"** 
- Check if MCP servers are running: `docker-compose ps` (from main directory)
- Verify network connectivity: `docker network inspect intranet`
- Start servers: `docker-compose up -d` (from main directory)

**"Container name conflicts"**
```bash
# Stop and remove existing containers
docker-compose down
docker-compose up -d
```

**"Permission denied" or Docker issues**
```bash
# Check Docker permissions
sudo docker ps
# Or add user to docker group
sudo usermod -a -G docker $USER
```

### Debugging Commands
```bash
# Check running containers
docker-compose ps

# View logs
docker-compose logs mcpclient
docker-compose logs giphymcp

# Network inspection
docker network inspect intranet

# Interactive debugging
docker-compose run --rm mcpclient bash
# Inside container:
# ping giphymcp
# python client.py --verbose
```

---

This Docker-based client provides a clean, production-ready interface for testing and interacting with all MCP servers in the ecosystem through containerized deployment.