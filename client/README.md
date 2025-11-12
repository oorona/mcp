# MCP Interactive Client Demo

A complete, self-contained interactive MCP client for testing and interacting with MCP servers.

## Quick Start

### Option 1: Run with Docker (Recommended)
```bash
# Start interactive client
./start.sh

# Rebuild and start
./start.sh --rebuild
```

### Option 2: Run locally with Python
```bash
# Install dependencies
pip install -r requirements.txt

# Run interactive client
python interactive_client.py
```

## Features

### Interactive Console Client (`interactive_client.py`)
- Console-based menu interface with color-coded output
- Browse servers and tools interactively
- Full JSON output (no truncation) 
- Run individual tools or test all tools with default values
- Environment variable support for URL configuration
- Easy navigation with numbered menus

## URL Configuration

The client automatically loads configuration from the `.env` file in the same directory.

### Default Behavior (HTTPS)
Uses production HTTPS URLs from `.env` file:
- `MCP_GIPHY_URL=https://giphymcp.iktdts.com/mcp`
- `MCP_YOUTUBE_URL=https://ytmcp.iktdts.com/mcp`
- etc.

### Override for Local Development
Edit `.env` file and uncomment the Docker URLs:
```bash
# Comment out HTTPS URLs and uncomment these:
MCP_GIPHY_URL=http://giphymcp:6700/mcp
MCP_YOUTUBE_URL=http://ytmcp:6700/mcp
# etc.
```

## Files Included

- `interactive_client.py` - Interactive console client
- `docker-compose.yml` - Docker configuration with .env support
- `Dockerfile` - Container build instructions  
- `start.sh` - Quick start script
- `requirements.txt` - Python dependencies (includes python-dotenv)
- `.env` - Environment configuration (HTTPS URLs by default)
- `.env.example` - Environment variable examples

## Interactive Menu Navigation

The client is designed to be user-friendly with minimal typing required:

### 🎯 **Easy Navigation**
- **Enter Key**: Press Enter to go back or exit (no need to type numbers)
- **Number Selection**: Type 1-7 to select servers, or tool numbers
- **Clean Menus**: No redundant options - just numbers and Enter
- **Auto-Exit**: Press Enter on main menu to exit
- **Auto-Back**: Press Enter on any submenu to go back

### 🎯 **Smart Parameter Input**
- **Default Values**: Shown for optional parameters (just press Enter to use)
- **Skip Optional**: Press Enter to skip optional parameters
- **Required Fields**: Marked with `*` - must provide a value
- **Type Hints**: Shows expected type (string, integer, boolean, etc.)

### 🎯 **Intelligent Confirmations**
- **Enter = Yes**: Most confirmations default to "yes" when you press Enter
- **Clear Indicators**: `(Y/n)` means Enter = Yes, `(y/N)` means Enter = No
- **No Typing**: Just press Enter for default actions

## Interactive Menu Options

1. **Select MCP Server** - Choose from 7 available servers
2. **Browse Tools** - See all available tools for a server
3. **Execute Tool** - Run a tool with interactive parameter input
4. **Run All Tools** - Test all tools with predefined values
5. **Test Server Connection** - Check if server is reachable

## Usage Flow

```
1. Start client → Main menu
2. Select server (1-7) → Server menu  
3. Choose action:
   - List tools
   - Execute specific tool
   - Run all tools with defaults
   - Test connection
4. View full JSON results
5. Return to main menu or exit
```