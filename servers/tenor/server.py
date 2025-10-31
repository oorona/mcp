import os
import logging
import random
from typing import Any, Dict, Annotated, Optional, List
from dotenv import load_dotenv
import aiohttp
from pydantic import Field

from fastmcp import FastMCP


# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

DEFAULT_LOG_LEVEL = "INFO"
LOG_LEVEL_ENV = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
numeric_log_level = getattr(logging, LOG_LEVEL_ENV, None)
if not isinstance(numeric_log_level, int):
    print(f"Warning: Invalid LOG_LEVEL '{LOG_LEVEL_ENV}'. Defaulting to '{DEFAULT_LOG_LEVEL}'.")
    numeric_log_level = getattr(logging, DEFAULT_LOG_LEVEL)

logging.basicConfig(
    level=numeric_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tenor-mcp-server")

if numeric_log_level > logging.DEBUG:
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

TENOR_API_KEY = os.getenv("TENOR_API_KEY")
if not TENOR_API_KEY:
    logger.error("TENOR_API_KEY environment variable is required and not set.")
    raise ValueError("TENOR_API_KEY environment variable is required")

DEFAULT_TENOR_CONTENT_FILTER = "medium"
TENOR_CONTENT_FILTER = os.getenv("TENOR_CONTENT_FILTER", DEFAULT_TENOR_CONTENT_FILTER)
VALID_TENOR_CONTENT_FILTERS = ["off", "low", "medium", "high"]
if TENOR_CONTENT_FILTER.lower() not in VALID_TENOR_CONTENT_FILTERS:
    logger.warning(
        f"Invalid TENOR_CONTENT_FILTER '{TENOR_CONTENT_FILTER}'. "
        f"Defaulting to '{DEFAULT_TENOR_CONTENT_FILTER}'. "
        f"Valid filters are: {', '.join(VALID_TENOR_CONTENT_FILTERS)}"
    )
    TENOR_CONTENT_FILTER = DEFAULT_TENOR_CONTENT_FILTER

DEFAULT_TENOR_LOCALE = "en_US"
TENOR_LOCALE = os.getenv("TENOR_LOCALE", DEFAULT_TENOR_LOCALE)

# Tenor API v2 configuration
TENOR_API_BASE = "https://tenor.googleapis.com/v2"
TENOR_CLIENT_KEY = os.getenv("TENOR_CLIENT_KEY", "mcp_tenor_server")
TENOR_MCP_SERVER_PORT = int(os.getenv("TENOR_MCP_SERVER_PORT", "7200"))

mcp = FastMCP(
    name="Tenor",
    instructions="Search and retrieve GIFs and memes from Tenor. Provides search, trending, categories, autocomplete, and personalized GIF experiences."
)

async def _make_tenor_request(endpoint: str, params: Dict[str, Any]) -> Any:
    """Make a request to the Tenor API v2"""
    params["key"] = TENOR_API_KEY
    params["client_key"] = TENOR_CLIENT_KEY
    url = f"{TENOR_API_BASE}/{endpoint}"
    logger.debug(f"Making Tenor API v2 request to: {url} with params: {params}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"Tenor API request failed: {e.status} {e.message} for GET {url}")
            error_details = e.message
            try:
                error_body = await response.json()
                error_details = f"{e.message} - {error_body}"
            except Exception:
                pass
            raise RuntimeError(f"Tenor API Error ({e.status}): {error_details}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during Tenor API request: {e}")
            raise RuntimeError(f"Unexpected error during API call to {url}") from e

def _get_best_gif_url(gif_data: Dict[str, Any]) -> Optional[str]:
    """
    Gets the best available GIF URL from the media_formats object (Tenor API v2).
    Priority: tinygif (mobile optimized), gif (high quality), mp4 (fallback)
    """
    # v2 API uses media_formats directly (not in an array)
    media_formats = gif_data.get("media_formats", {})
    if not media_formats:
        return None
    
    # Priority order for GIF formats
    format_preference = ["tinygif", "gif", "mp4"]
    
    for format_name in format_preference:
        format_data = media_formats.get(format_name)
        if format_data and format_data.get("url"):
            logger.debug(f"Selected format '{format_name}' with URL: {format_data['url']}")
            return format_data["url"]
    
    # Fallback to any available format
    for format_name, format_data in media_formats.items():
        if isinstance(format_data, dict) and format_data.get("url"):
            logger.debug(f"Fallback to format '{format_name}' with URL: {format_data['url']}")
            return format_data["url"]
    
    logger.warning(f"No suitable GIF URL found for Tenor ID {gif_data.get('id')}")
    return None

@mcp.tool()
async def search_tenor_gifs(
    query: Annotated[
        str,
        Field(description="The search term for GIFs (e.g., 'funny cat', 'happy dance'). Can be in multiple languages.")
    ],
    limit: Annotated[
        Optional[int],
        Field(description="Number of GIFs to return. Default is 8, max is 50.")
    ] = 8,
    content_filter: Annotated[
        Optional[str],
        Field(description="Content safety filter: 'off', 'low', 'medium', 'high'. Default is 'medium'.")
    ] = None
) -> Dict[str, Any]:
    """
    Search Tenor for GIFs matching the query. Returns the most relevant GIFs with optimized URLs.
    """
    logger.info(f"MCP Tool 'search_tenor_gifs' called with query: '{query}', limit: {limit}")
    
    if not query:
        return {"error": "Search query cannot be empty."}
    if limit <= 0 or limit > 50:
        return {"error": "Limit must be between 1 and 50."}

    try:
        params = {
            "q": query,
            "limit": limit,
            "locale": TENOR_LOCALE,
            "contentfilter": content_filter or TENOR_CONTENT_FILTER,
            "media_filter": "minimal"  # Reduces response size
        }
        
        api_response = await _make_tenor_request("search", params)
        results = api_response.get("results", [])
        
        if not results:
            logger.warning(f"No GIFs found for query: '{query}'")
            return {"info": f"No GIFs found for query: '{query}'.", "results": []}

        formatted_results = []
        for gif_data in results:
            gif_url = _get_best_gif_url(gif_data)
            if gif_url:
                formatted_results.append({
                    "id": gif_data.get("id"),
                    "title": gif_data.get("title"),
                    "url": gif_url,
                    "item_url": gif_data.get("itemurl"),
                    "short_url": gif_data.get("url"),
                    "has_audio": gif_data.get("hasaudio", False),
                    "tags": gif_data.get("tags", [])
                })

        logger.info(f"Found {len(formatted_results)} suitable GIFs for query '{query}'")
        return {
            "results": formatted_results,
            "query": query,
            "next": api_response.get("next", "0")
        }

    except RuntimeError as e:
        logger.error(f"Tenor API interaction failed for query '{query}': {e}")
        return {"error": f"Tenor API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in search_tenor_gifs for query '{query}': {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_trending_tenor_gifs(
    limit: Annotated[
        Optional[int],
        Field(description="Number of trending GIFs to return. Default is 8, max is 50.")
    ] = 8,
    content_filter: Annotated[
        Optional[str],
        Field(description="Content safety filter: 'off', 'low', 'medium', 'high'. Default is 'medium'.")
    ] = None
) -> Dict[str, Any]:
    """
    Get the current trending GIFs from Tenor. Updated regularly throughout the day.
    """
    logger.info(f"MCP Tool 'get_trending_tenor_gifs' called with limit: {limit}")
    
    if limit <= 0 or limit > 50:
        return {"error": "Limit must be between 1 and 50."}

    try:
        params = {
            "limit": limit,
            "locale": TENOR_LOCALE,
            "contentfilter": content_filter or TENOR_CONTENT_FILTER,
            "media_filter": "minimal"
        }
        
        # v2 API uses 'featured' instead of 'trending'
        api_response = await _make_tenor_request("featured", params)
        results = api_response.get("results", [])
        
        if not results:
            logger.warning("No trending GIFs found")
            return {"info": "No trending GIFs found.", "results": []}

        formatted_results = []
        for gif_data in results:
            gif_url = _get_best_gif_url(gif_data)
            if gif_url:
                formatted_results.append({
                    "id": gif_data.get("id"),
                    "title": gif_data.get("title"),
                    "url": gif_url,
                    "item_url": gif_data.get("itemurl"),
                    "short_url": gif_data.get("url"),
                    "has_audio": gif_data.get("hasaudio", False),
                    "tags": gif_data.get("tags", [])
                })

        logger.info(f"Found {len(formatted_results)} trending GIFs")
        return {
            "results": formatted_results,
            "next": api_response.get("next", "0")
        }

    except RuntimeError as e:
        logger.error(f"Tenor API interaction failed for trending GIFs: {e}")
        return {"error": f"Tenor API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_trending_tenor_gifs: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_tenor_categories(
    category_type: Annotated[
        Optional[str],
        Field(description="Type of categories: 'featured' (default), 'emoji', or 'trending'")
    ] = "featured"
) -> Dict[str, Any]:
    """
    Get GIF categories from Tenor. Categories include preview GIFs and search URLs.
    """
    logger.info(f"MCP Tool 'get_tenor_categories' called with type: '{category_type}'")
    
    valid_types = ["featured", "emoji", "trending"]
    if category_type not in valid_types:
        return {"error": f"Invalid category type. Must be one of: {', '.join(valid_types)}"}

    try:
        params = {
            "type": category_type,
            "locale": TENOR_LOCALE,
            "contentfilter": TENOR_CONTENT_FILTER
        }
        
        api_response = await _make_tenor_request("categories", params)
        categories = api_response.get("tags", [])
        
        if not categories:
            logger.warning(f"No categories found for type: '{category_type}'")
            return {"info": f"No categories found for type: '{category_type}'.", "categories": []}

        formatted_categories = []
        for category in categories:
            formatted_categories.append({
                "name": category.get("name"),
                "search_term": category.get("searchterm"),
                "search_url": category.get("path"),
                "preview_image": category.get("image")
            })

        logger.info(f"Found {len(formatted_categories)} categories of type '{category_type}'")
        return {
            "categories": formatted_categories,
            "type": category_type
        }

    except RuntimeError as e:
        logger.error(f"Tenor API interaction failed for categories: {e}")
        return {"error": f"Tenor API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_tenor_categories: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_tenor_autocomplete(
    partial_query: Annotated[
        str,
        Field(description="Partial search term to get autocomplete suggestions for (e.g., 'exc' -> 'excited')")
    ],
    limit: Annotated[
        Optional[int],
        Field(description="Number of suggestions to return. Default is 5, max is 20.")
    ] = 5
) -> Dict[str, Any]:
    """
    Get autocomplete suggestions for a partial search term. Helps users complete searches faster.
    """
    logger.info(f"MCP Tool 'get_tenor_autocomplete' called with partial_query: '{partial_query}'")
    
    if not partial_query or len(partial_query) < 2:
        return {"error": "Partial query must be at least 2 characters long."}
    if limit <= 0 or limit > 20:
        return {"error": "Limit must be between 1 and 20."}

    try:
        params = {
            "q": partial_query,
            "limit": limit,
            "locale": TENOR_LOCALE
        }
        
        api_response = await _make_tenor_request("autocomplete", params)
        suggestions = api_response.get("results", [])
        
        logger.info(f"Found {len(suggestions)} autocomplete suggestions for '{partial_query}'")
        return {
            "suggestions": suggestions,
            "partial_query": partial_query
        }

    except RuntimeError as e:
        logger.error(f"Tenor API interaction failed for autocomplete: {e}")
        return {"error": f"Tenor API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_tenor_autocomplete: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_tenor_search_suggestions(
    query: Annotated[
        str,
        Field(description="Search term to get related suggestions for (e.g., 'smile' -> 'happy', 'grin')")
    ],
    limit: Annotated[
        Optional[int],
        Field(description="Number of suggestions to return. Default is 5, max is 20.")
    ] = 5
) -> Dict[str, Any]:
    """
    Get search suggestions for a given term. Helps users discover related search terms.
    """
    logger.info(f"MCP Tool 'get_tenor_search_suggestions' called with query: '{query}'")
    
    if not query:
        return {"error": "Search query cannot be empty."}
    if limit <= 0 or limit > 20:
        return {"error": "Limit must be between 1 and 20."}

    try:
        params = {
            "q": query,
            "limit": limit,
            "locale": TENOR_LOCALE
        }
        
        api_response = await _make_tenor_request("search_suggestions", params)
        suggestions = api_response.get("results", [])
        
        logger.info(f"Found {len(suggestions)} search suggestions for '{query}'")
        return {
            "suggestions": suggestions,
            "query": query
        }

    except RuntimeError as e:
        logger.error(f"Tenor API interaction failed for search suggestions: {e}")
        return {"error": f"Tenor API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_tenor_search_suggestions: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_tenor_trending_terms(
    limit: Annotated[
        Optional[int],
        Field(description="Number of trending terms to return. Default is 10, max is 20.")
    ] = 10
) -> Dict[str, Any]:
    """
    Get current trending search terms. Updated hourly by Tenor's AI.
    """
    logger.info(f"MCP Tool 'get_tenor_trending_terms' called with limit: {limit}")
    
    if limit <= 0 or limit > 20:
        return {"error": "Limit must be between 1 and 20."}

    try:
        params = {
            "limit": limit,
            "locale": TENOR_LOCALE
        }
        
        api_response = await _make_tenor_request("trending_terms", params)
        terms = api_response.get("results", [])
        
        logger.info(f"Found {len(terms)} trending terms")
        return {
            "trending_terms": terms,
            "locale": TENOR_LOCALE
        }

    except RuntimeError as e:
        logger.error(f"Tenor API interaction failed for trending terms: {e}")
        return {"error": f"Tenor API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_tenor_trending_terms: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_random_tenor_gifs(
    query: Annotated[
        str,
        Field(description="Search term for random GIFs (e.g., 'dance', 'celebration')")
    ],
    limit: Annotated[
        Optional[int],
        Field(description="Number of random GIFs to return. Default is 5, max is 50.")
    ] = 5
) -> Dict[str, Any]:
    """
    Get randomized GIFs for a search term. Different from search - returns random results instead of ranked.
    """
    logger.info(f"MCP Tool 'get_random_tenor_gifs' called with query: '{query}', limit: {limit}")
    
    if not query:
        return {"error": "Search query cannot be empty."}
    if limit <= 0 or limit > 50:
        return {"error": "Limit must be between 1 and 50."}

    try:
        # v2 API doesn't have a dedicated 'random' endpoint
        # Use 'search' with random parameter for randomized results
        params = {
            "q": query,
            "limit": limit,
            "locale": TENOR_LOCALE,
            "contentfilter": TENOR_CONTENT_FILTER,
            "media_filter": "minimal",
            "random": "true"  # Request random results
        }
        
        api_response = await _make_tenor_request("search", params)
        results = api_response.get("results", [])
        
        if not results:
            logger.warning(f"No random GIFs found for query: '{query}'")
            return {"info": f"No random GIFs found for query: '{query}'.", "results": []}

        formatted_results = []
        for gif_data in results:
            gif_url = _get_best_gif_url(gif_data)
            if gif_url:
                formatted_results.append({
                    "id": gif_data.get("id"),
                    "title": gif_data.get("title"),
                    "url": gif_url,
                    "item_url": gif_data.get("itemurl"),
                    "short_url": gif_data.get("url"),
                    "has_audio": gif_data.get("hasaudio", False),
                    "tags": gif_data.get("tags", [])
                })

        logger.info(f"Found {len(formatted_results)} random GIFs for query '{query}'")
        return {
            "results": formatted_results,
            "query": query,
            "type": "random"
        }

    except RuntimeError as e:
        logger.error(f"Tenor API interaction failed for random GIFs: {e}")
        return {"error": f"Tenor API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_random_tenor_gifs: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def register_tenor_share(
    gif_id: Annotated[
        str,
        Field(description="The ID of the GIF that was shared")
    ],
    search_query: Annotated[
        Optional[str],
        Field(description="The search term that led to this share (helps improve search results)")
    ] = None
) -> Dict[str, Any]:
    """
    Register that a user shared a GIF. This helps Tenor's AI improve search results.
    """
    logger.info(f"MCP Tool 'register_tenor_share' called with gif_id: '{gif_id}'")
    
    if not gif_id:
        return {"error": "GIF ID cannot be empty."}

    try:
        params = {
            "id": gif_id,
            "locale": TENOR_LOCALE
        }
        
        if search_query:
            params["q"] = search_query
        
        api_response = await _make_tenor_request("registershare", params)
        status = api_response.get("status", "unknown")
        
        logger.info(f"Share registered for GIF ID: {gif_id}, status: {status}")
        return {
            "status": status,
            "gif_id": gif_id,
            "search_query": search_query
        }

    except RuntimeError as e:
        logger.error(f"Tenor API interaction failed for share registration: {e}")
        return {"error": f"Tenor API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in register_tenor_share: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

def main():
    logger.info(f"Starting Tenor MCP Server on port {TENOR_MCP_SERVER_PORT} with log level {LOG_LEVEL_ENV}")
    mcp.run(transport="streamable-http",
        host="0.0.0.0",
        port=TENOR_MCP_SERVER_PORT,
        log_level=LOG_LEVEL_ENV.lower()
    )

if __name__ == "__main__":
    main()