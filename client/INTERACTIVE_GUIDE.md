# Interactive MCP Client - Quick Reference

## What's New?

✨ **Interactive Console Interface** - A beautiful, user-friendly way to test MCP servers!

### Key Features:
- 🎨 **Colorful UI** - Easy to read with ANSI colors
- 🔍 **Full Output** - No truncation! See complete JSON responses
- 📝 **Smart Parameter Input** - Type validation and help text
- 🎯 **Easy Navigation** - Number-based menus (no arrow keys needed)
- ✅ **Validation** - Shows required vs optional parameters

## Quick Start

### Option 1: Using the helper script (easiest)
```bash
cd client
./start.sh
```

### Option 2: Using docker compose directly
```bash
cd client
docker compose run --rm mcpclient
```

### Option 3: Local Python (if you have dependencies)
```bash
cd client
python interactive_client.py
```

## How It Works

### 1. Main Menu
```
Select an MCP server to test:
  1. giphy - GIF/sticker search, trending, random
  2. youtube - Video search, transcripts, trending
  3. wolframalpha - Math, science, conversions
  4. piston - Code execution engine
  5. cve - Vulnerability analysis
  6. tenor - GIF search engine
  7. usercontext - User analytics & history
  8. Exit
```

### 2. Tool Selection
After selecting a server, you'll see all available tools with:
- Tool name
- Description
- Parameters (with types and descriptions)
- Required parameters marked with ⚠ *
- **🚀 Special option: "RUN ALL TOOLS"** - Execute all tools with predefined test values

### 3. Parameter Input
For each parameter, you'll see:
```
⚠ query (string)
  Search term for GIFs
  Value: cats
```

Required parameters are marked with ⚠ *  
Optional parameters can be skipped with Enter

### 4. Execution & Results
- Review summary before execution
- Confirm with 'y'
- See **complete** formatted output
- No truncation - scroll to see everything!

## Tips & Tricks

### Navigation
- Type numbers to select options
- `0` to go back/cancel
- `Ctrl+C` to interrupt and return to main menu
- Press Enter after viewing results to continue

### Parameter Input
- **String**: Just type the value
- **Integer**: Type a number (e.g., `5`)
- **Boolean**: Type `true`, `yes`, `1`, or `y` for true
- **Array**: Comma-separated values (e.g., `cat,dog,bird`)
- **Optional**: Press Enter to skip

### Viewing Output
- JSON is automatically pretty-printed
- Full output is shown (no `...` truncation)
- Scroll in your terminal to see everything
- Press Enter when done reviewing

### Run All Tools Feature
- Automatically executes all tools on a server
- Uses predefined test values:
  - `query`: "test"
  - `user_id`: "811781544784035881"
  - `limit`: 5
  - `language`: "python"
  - `code`: "print('Hello, World!')"
  - And more sensible defaults...
- Shows summary of successful vs failed executions
- Option to view detailed results for each tool

### Color Coding
- 🟦 Blue = Headers and sections
- 🟩 Green = Success and tool names
- 🟧 Orange = Warnings and required markers
- 🟥 Red = Errors
- 🟦 Cyan = Info and parameter names

## Examples

### Quick Test All Tools
1. Select an MCP server (e.g., `1` for giphy)
2. Select the last option: `🚀 RUN ALL TOOLS (with default values)`
3. Confirm with `y`
4. Watch as all tools are executed automatically
5. Review summary (success/failed counts)
6. Optionally view detailed results for each tool

### Testing Giphy
1. Select `1` for giphy
2. Select a tool like `search_giphy_images`
3. Enter query: `funny cats`
4. Enter limit: `5` (or press Enter for default)
5. Confirm with `y`
6. View complete results with URLs, IDs, etc.

### Testing WolframAlpha
1. Select `3` for wolframalpha
2. Select `query_wolframalpha`
3. Enter query: `solve x^2 + 2x + 1 = 0`
4. Confirm with `y`
5. See full mathematical solution

### Testing UserContext
1. Select `7` for usercontext
2. Select `get_user_analytics`
3. Enter user_id: `811781544784035881`
4. Confirm with `y`
5. View complete analytics with word clouds, sentiment, etc.

## Troubleshooting

### "Failed to connect"
- Make sure MCP servers are running: `docker compose up -d` (from main directory)
- Check network exists: `docker network ls | grep intranet`
- Verify MCPO is running: `docker ps | grep mcpo`

### "No tools available"
- The server might not be responding
- Check server logs: `docker compose logs <servername>`
- Restart servers: `docker compose restart`

### Colors not showing
- Make sure your terminal supports ANSI colors
- Try a different terminal emulator
- Colors should work in most modern terminals

### Container rebuild needed
After code changes:
```bash
cd client
docker compose build
docker compose run --rm mcpclient
```

## Comparison: Interactive vs Legacy Client

| Feature | Interactive Client | Legacy Client |
|---------|-------------------|---------------|
| Interface | Menu-driven | Command-line args |
| Output | Full, formatted | Truncated |
| Parameters | Guided input | JSON strings |
| Colors | Yes ✓ | No ✗ |
| Ease of use | Beginner-friendly | Developer-focused |
| Automation | No | Yes ✓ |

**Use Interactive Client for**: Manual testing, exploration, learning  
**Use Legacy Client for**: Scripts, automation, CI/CD

## Files

- `interactive_client.py` - The new interactive interface
- `client.py` - Original command-line client
- `start.sh` - Quick start helper script
- `docker-compose.yml` - Container configuration
- `requirements.txt` - Python dependencies

## Need Help?

Check the main project README or:
1. Run `./start.sh` and explore the menus
2. Try a simple server like `giphy` first
3. Look at the parameter descriptions shown in the UI
4. Press `0` or Ctrl+C to go back if stuck
