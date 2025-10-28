# Tenor MCP Server

A comprehensive Model Context Protocol (MCP) server that integrates with the Tenor GIF API to provide advanced GIF search, discovery, and management capabilities.

## Overview

The Tenor MCP server offers **8 powerful tools** for GIF and meme management, providing enterprise-grade functionality for applications requiring rich visual content integration.

## Features

### 🔍 Advanced Search & Discovery
- **Smart GIF Search** - Search with content filtering and quality optimization
- **Trending Analysis** - Real-time trending GIFs updated throughout the day
- **Random Discovery** - Randomized results for content variety
- **Categories** - Organized GIF collections with preview images

### 💭 Intelligent Assistance
- **Autocomplete** - Smart suggestions for partial search terms
- **Search Suggestions** - Related terms for better content discovery
- **Trending Terms** - Hourly updated trending search phrases

### 📊 Analytics & Optimization
- **Share Tracking** - Register user shares to improve search quality
- **Content Filtering** - Configurable safety ratings (G to R)
- **Multi-language Support** - 35+ languages with localized content

## API Endpoints

### Core Search Tools

#### `search_tenor_gifs`
Search for GIFs by keyword with advanced filtering options.

**Parameters:**
- `query` (string, required): Search term for GIFs
- `limit` (integer, optional): Number of results (1-50, default: 8)
- `content_filter` (string, optional): Safety filter ("off", "low", "medium", "high")

**Response:**
```json
{
  "results": [
    {
      "id": "12345678",
      "title": "Happy Cat Dancing",
      "url": "https://media.tenor.com/optimized-gif-url.gif",
      "item_url": "https://tenor.com/view/gif-page",
      "short_url": "https://tenor.com/shorturl",
      "has_audio": false,
      "tags": ["happy", "cat", "dancing"]
    }
  ],
  "query": "happy",
  "next": "pagination_token"
}
```

#### `get_trending_tenor_gifs`
Get currently trending GIFs, updated regularly throughout the day.

**Parameters:**
- `limit` (integer, optional): Number of results (1-50, default: 8)
- `content_filter` (string, optional): Safety filter level

#### `get_random_tenor_gifs`
Get randomized GIFs for a search term (different from ranked search results).

**Parameters:**
- `query` (string, required): Search term for random GIFs
- `limit` (integer, optional): Number of results (1-50, default: 5)

### Discovery & Categorization

#### `get_tenor_categories`
Get organized GIF categories with preview images.

**Parameters:**
- `category_type` (string, optional): "featured" (default), "emoji", or "trending"

**Response:**
```json
{
  "categories": [
    {
      "name": "Excited",
      "search_term": "excited", 
      "search_url": "https://g.tenor.com/v1/search?q=excited&key=...",
      "preview_image": "https://media.tenor.com/preview.gif"
    }
  ],
  "type": "featured"
}
```

#### `get_tenor_trending_terms`
Get trending search terms updated hourly by Tenor's AI.

**Parameters:**
- `limit` (integer, optional): Number of terms (1-20, default: 10)

### Smart Assistance

#### `get_tenor_autocomplete`
Get autocomplete suggestions for partial search terms.

**Parameters:**
- `partial_query` (string, required): Partial search term (min 2 characters)
- `limit` (integer, optional): Number of suggestions (1-20, default: 5)

#### `get_tenor_search_suggestions`
Get related search terms for better GIF discovery.

**Parameters:**
- `query` (string, required): Search term for related suggestions
- `limit` (integer, optional): Number of suggestions (1-20, default: 5)

### Analytics

#### `register_tenor_share`
Register that a user shared a GIF to help improve search results.

**Parameters:**
- `gif_id` (string, required): ID of the shared GIF
- `search_query` (string, optional): Search term that led to the share

## Configuration

### Environment Variables

#### Required
- `TENOR_API_KEY`: Your Tenor API key (get free key at tenor.com/gifapi)

#### Optional
- `TENOR_MCP_SERVER_PORT`: Server port (default: 7200)
- `TENOR_CONTENT_FILTER`: Default content filter ("off", "low", "medium", "high", default: "medium")
- `TENOR_LOCALE`: Default locale (default: "en_US")
- `LOG_LEVEL`: Logging level (default: "INFO")

### Content Filtering

Tenor provides flexible content filtering based on MPAA-style ratings:

- **high**: G-rated content only
- **medium**: G and PG content (default)
- **low**: G, PG, and PG-13 content  
- **off**: All content except explicit nudity (G, PG, PG-13, R)

### Multi-language Support

Supports 35+ languages including:
- English, Spanish, French, German, Italian
- Portuguese, Russian, Arabic, Chinese, Japanese
- Korean, Hindi, Turkish, Dutch, and more

## Docker Deployment

### Using Docker Compose

The server is pre-configured in `docker-compose.yml`:

```yaml
tenormcp:
  build:
    context: .
    dockerfile: Dockerfile.tenormcp
  container_name: tenormcp
  ports:
    - "7200:7200"
  environment:
    - TENOR_MCP_SERVER_PORT=7200
    - TENOR_API_KEY=${TENOR_API_KEY}
    - TENOR_CONTENT_FILTER=medium
    - TENOR_LOCALE=en_US
    - LOG_LEVEL=INFO
  networks:
    - llmnet
```

### Manual Docker Build

```bash
# Build the image
docker build -f Dockerfile.tenormcp -t tenor-mcp .

# Run the container
docker run -d \
  --name tenor-mcp \
  -p 7200:7200 \
  -e TENOR_API_KEY=your_api_key \
  -e TENOR_CONTENT_FILTER=medium \
  tenor-mcp
```

## Development Setup

### Local Development

1. **Install dependencies:**
   ```bash
   cd servers/tenor
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export TENOR_API_KEY=your_api_key
   export TENOR_MCP_SERVER_PORT=7200
   ```

3. **Run the server:**
   ```bash
   python server.py
   ```

### API Key Setup

1. Visit [Tenor Developer Dashboard](https://tenor.com/developer/dashboard)
2. Create a free account
3. Generate an API key
4. Set the `TENOR_API_KEY` environment variable

## Testing

### Test Client

Use the included test client to verify functionality:

```bash
# Test all servers including Tenor
python test_client.py --host bot

# Test with verbose output  
python test_client.py --verbose
```

### Manual Testing

```bash
# Test connectivity
curl http://localhost:7200/mcp/ping

# Search for GIFs
curl -X POST http://localhost:7200/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{
    "name": "search_tenor_gifs",
    "arguments": {
      "query": "excited",
      "limit": 5
    }
  }'
```

## Integration Examples

### Basic GIF Search
```python
from fastmcp import Client

async def search_gifs():
    client = Client("http://localhost:7200/mcp")
    async with client:
        result = await client.call_tool(
            "search_tenor_gifs",
            {"query": "celebration", "limit": 10}
        )
        return result["results"]
```

### Trending Content
```python
async def get_trending():
    client = Client("http://localhost:7200/mcp")
    async with client:
        # Get trending GIFs
        gifs = await client.call_tool("get_trending_tenor_gifs", {"limit": 5})
        
        # Get trending search terms
        terms = await client.call_tool("get_tenor_trending_terms", {"limit": 10})
        
        return {"gifs": gifs["results"], "terms": terms["trending_terms"]}
```

### Smart Search with Autocomplete
```python
async def smart_search(partial_term: str):
    client = Client("http://localhost:7200/mcp")
    async with client:
        # Get autocomplete suggestions
        suggestions = await client.call_tool(
            "get_tenor_autocomplete", 
            {"partial_query": partial_term, "limit": 5}
        )
        
        # Search using first suggestion
        if suggestions["suggestions"]:
            results = await client.call_tool(
                "search_tenor_gifs",
                {"query": suggestions["suggestions"][0], "limit": 8}
            )
            return results["results"]
```

## Tenor vs Giphy Advantages

### API Completeness
- **8 vs 2 endpoints**: More comprehensive functionality
- **Advanced categorization**: Organized content discovery  
- **Smart suggestions**: Autocomplete and related terms
- **Trending analysis**: Real-time trend tracking

### Search Quality
- **Share tracking**: AI learns from user behavior
- **Random discovery**: Avoids repetitive results
- **Multi-language**: Better global content support
- **Content filtering**: More granular safety controls

### Performance
- **Global CDN**: Edge network (g.tenor.com) for faster delivery
- **Optimized formats**: Multiple GIF sizes and formats
- **Efficient API**: Reduced response sizes with media filtering

## Rate Limits & Best Practices

### API Limits
- **Free tier**: Generous limits for development and small applications
- **Commercial use**: Contact Tenor for higher limits and enterprise features

### Optimization Tips
1. **Use media filtering**: Set `media_filter=minimal` to reduce response size
2. **Implement caching**: Cache trending content and categories
3. **Register shares**: Use `register_tenor_share` to improve search quality
4. **Content filtering**: Set appropriate filters for your audience
5. **Pagination**: Use `next` tokens for large result sets

### Error Handling
The server provides detailed error responses:
```json
{
  "error": "Tenor API Error (429): Rate limit exceeded",
  "info": "Request failed - please try again later"
}
```

## Support & Contributing

### Issues & Feature Requests
- Report issues in the repository
- Request features for enhanced functionality
- Contribute improvements via pull requests

### Resources
- [Tenor API Documentation](https://tenor.com/gifapi/documentation)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)
- [MCP Specification](https://modelcontextprotocol.io)

---

**Tenor MCP Server** - Comprehensive GIF management for the Model Context Protocol ecosystem.