import os
import logging
import random
from typing import Any, Dict, Annotated, Optional, List
from dotenv import load_dotenv
import aiohttp
from pydantic import Field

from fastmcp import FastMCP


# Load environment variables (rest of the initial setup is the same)
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
logger = logging.getLogger("giphy-mcp-server")

if numeric_log_level > logging.DEBUG:
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    #logging.getLogger("mcp.server.sse").setLevel(logging.WARNING)

GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")
if not GIPHY_API_KEY:
    logger.error("GIPHY_API_KEY environment variable is required and not set.")
    raise ValueError("GIPHY_API_KEY environment variable is required")

DEFAULT_GIPHY_TRENDING_RATING = "pg"
GIPHY_TRENDING_RATING = os.getenv("GIPHY_TRENDING_RATING", DEFAULT_GIPHY_TRENDING_RATING)
VALID_GIPHY_RATINGS = ["g", "pg", "pg-13", "r"]
if GIPHY_TRENDING_RATING.lower() not in VALID_GIPHY_RATINGS:
    logger.warning(
        f"Invalid GIPHY_TRENDING_RATING '{GIPHY_TRENDING_RATING}'. "
        f"Defaulting to '{DEFAULT_GIPHY_TRENDING_RATING}'. "
        f"Valid ratings are: {', '.join(VALID_GIPHY_RATINGS)}"
    )
    GIPHY_TRENDING_RATING = DEFAULT_GIPHY_TRENDING_RATING

GIPHY_API_BASE = "https://api.giphy.com/v1/gifs"
GIPHY_MCP_SERVER_PORT = int(os.getenv("GIPHY_MCP_SERVER_PORT", "6100"))

mcp = FastMCP(
    name="Giphy",
    instructions="Comprehensive Giphy integration: search GIFs/stickers, get trending content, random GIFs, translate phrases to GIFs, browse categories, get search suggestions, and more. All optimized for Discord with WebP priority."
    )

async def _make_giphy_request(endpoint: str, params: Dict[str, Any]) -> Any:
    # This function remains the same as before
    params["api_key"] = GIPHY_API_KEY
    url = f"{GIPHY_API_BASE}/{endpoint}"
    logger.debug(f"Making Giphy API request to: {url} with params: {params}")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"Giphy API request failed: {e.status} {e.message} for GET {url}")
            error_details = e.message
            try:
                error_body = await response.json()
                error_details = f"{e.message} - {error_body}"
            except Exception:
                pass
            raise RuntimeError(f"Giphy API Error ({e.status}): {error_details}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during Giphy API request: {e}")
            raise RuntimeError(f"Unexpected error during API call to {url}") from e

def _get_prioritized_image_url(gif_data: Dict[str, Any]) -> Optional[str]:
    """
    Gets the best available image URL (prioritizing WebP) from the renditions
    based on priority for Discord.
    Priority: downsized (<2MB), downsized_medium (<5MB), downsized_large (<8MB), fixed_width (200px).
    Tries to get WebP first, then falls back to GIF for each rendition type.
    """
    images = gif_data.get("images", {})
    # These are the Giphy rendition names we prefer for size/performance
    rendition_preference_order = [
        "downsized",
        "downsized_medium",
        "downsized_large",
        "fixed_width", # Typically 200px wide, good fallback
    ]

    for rendition_name in rendition_preference_order:
        rendition_data = images.get(rendition_name)
        if rendition_data:
            # Prioritize WebP URL for this rendition
            webp_url = rendition_data.get("webp")
            if webp_url:
                logger.debug(f"Selected WebP rendition '{rendition_name}' with URL: {webp_url}")
                return webp_url
            
            # Fallback to GIF URL for this rendition if WebP not found
            gif_url = rendition_data.get("url") # 'url' usually points to the GIF
            if gif_url:
                logger.debug(f"Selected GIF rendition '{rendition_name}' (WebP not found) with URL: {gif_url}")
                return gif_url
            
            # Some renditions might use gif_url specifically (less common for these preferred ones)
            specific_gif_url = rendition_data.get("gif_url")
            if specific_gif_url:
                logger.debug(f"Selected GIF rendition '{rendition_name}' (WebP not found, specific gif_url) with URL: {specific_gif_url}")
                return specific_gif_url

    # As a last resort, try original WebP, then original GIF.
    original_rendition = images.get("original", {})
    original_webp_url = original_rendition.get("webp")
    if original_webp_url:
        logger.warning(f"Using 'original' WebP URL for image ID {gif_data.get('id')}. File size might be large: {original_webp_url}")
        return original_webp_url
    
    original_gif_url = original_rendition.get("url")
    if original_gif_url:
        logger.warning(f"Using 'original' GIF URL for image ID {gif_data.get('id')} (WebP not found). File size might be large: {gif_url}")
        return original_gif_url

    logger.warning(f"No suitable image URL (WebP or GIF) found in renditions for Giphy ID {gif_data.get('id')}")
    return None

@mcp.tool()
async def get_random_giphy_image(
    tag: Annotated[
        Optional[str],
        Field(description="Optional tag to filter random GIF (e.g., 'funny', 'cat'). If not provided, returns completely random GIF.")
    ] = None
) -> Dict[str, Any]:
    """
    Gets a random GIF from Giphy, optionally filtered by tag.
    Returns a single random image URL prioritizing WebP format.
    """
    logger.info(f"MCP Tool 'get_random_giphy_image' called with tag: '{tag}'")
    
    try:
        params = {
            "rating": GIPHY_TRENDING_RATING
        }
        if tag:
            params["tag"] = tag

        api_response = await _make_giphy_request("random", params)
        gif_data = api_response.get("data")

        if not gif_data:
            logger.warning(f"No random GIF found for tag: '{tag}'")
            return {"info": f"No random GIF found for tag: '{tag}'", "image_url": None}

        image_url = _get_prioritized_image_url(gif_data)
        if not image_url:
            logger.warning(f"Could not find suitable rendition for random GIF ID: {gif_data.get('id')}")
            return {"info": "Could not process the random GIF.", "image_url": None}

        logger.info(f"Selected random GIF ID: {gif_data.get('id')}, Title: '{gif_data.get('title')}'")
        return {
            "image_url": image_url,
            "title": gif_data.get("title"),
            "id": gif_data.get("id"),
            "giphy_page_url": gif_data.get("url"),
            "tag_used": tag,
            "rating_used": GIPHY_TRENDING_RATING
        }

    except RuntimeError as e:
        logger.error(f"Giphy API interaction failed for random GIF with tag '{tag}': {e}")
        return {"error": f"Giphy API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_random_giphy_image with tag '{tag}': {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def translate_to_giphy_image(
    phrase: Annotated[
        str,
        Field(description="Word or phrase to translate into the perfect GIF (e.g., 'excited', 'good morning', 'thank you')")
    ]
) -> Dict[str, Any]:
    """
    Uses Giphy's translate algorithm to convert words/phrases into the perfect GIF.
    This is Giphy's special sauce for finding the most relevant GIF for expressions.
    """
    logger.info(f"MCP Tool 'translate_to_giphy_image' called with phrase: '{phrase}'")
    
    if not phrase:
        return {"error": "Phrase cannot be empty."}

    try:
        params = {
            "s": phrase,
            "rating": GIPHY_TRENDING_RATING
        }

        api_response = await _make_giphy_request("translate", params)
        gif_data = api_response.get("data")

        if not gif_data:
            logger.warning(f"No GIF translation found for phrase: '{phrase}'")
            return {"info": f"No GIF translation found for phrase: '{phrase}'", "image_url": None}

        image_url = _get_prioritized_image_url(gif_data)
        if not image_url:
            logger.warning(f"Could not find suitable rendition for translated GIF ID: {gif_data.get('id')}")
            return {"info": "Could not process the translated GIF.", "image_url": None}

        logger.info(f"Translated phrase '{phrase}' to GIF ID: {gif_data.get('id')}, Title: '{gif_data.get('title')}'")
        return {
            "image_url": image_url,
            "title": gif_data.get("title"),
            "id": gif_data.get("id"),
            "giphy_page_url": gif_data.get("url"),
            "original_phrase": phrase,
            "rating_used": GIPHY_TRENDING_RATING
        }

    except RuntimeError as e:
        logger.error(f"Giphy API interaction failed for translate phrase '{phrase}': {e}")
        return {"error": f"Giphy API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in translate_to_giphy_image with phrase '{phrase}': {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_giphy_categories() -> Dict[str, Any]:
    """
    Gets a list of available GIF categories from Giphy.
    Useful for discovering content themes and browsing options.
    """
    logger.info("MCP Tool 'get_giphy_categories' called")
    
    try:
        params = {}
        api_response = await _make_giphy_request("categories", params)
        categories_data = api_response.get("data", [])

        if not categories_data:
            logger.warning("No categories found from Giphy API")
            return {"info": "No categories found", "categories": []}

        categories = []
        for category in categories_data:
            categories.append({
                "name": category.get("name"),
                "name_encoded": category.get("name_encoded"),
                "subcategories": category.get("subcategories", [])
            })

        logger.info(f"Retrieved {len(categories)} categories from Giphy")
        return {
            "categories": categories,
            "total_count": len(categories)
        }

    except RuntimeError as e:
        logger.error(f"Giphy API interaction failed for categories: {e}")
        return {"error": f"Giphy API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_giphy_categories: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_giphy_autocomplete(
    query: Annotated[
        str,
        Field(description="Partial search term to get autocomplete suggestions (e.g., 'hap' might suggest 'happy', 'halloween')")
    ],
    limit: Annotated[
        Optional[int],
        Field(description="Maximum number of suggestions to return. Default is 5.")
    ] = 5
) -> Dict[str, Any]:
    """
    Gets autocomplete suggestions for search terms from Giphy.
    Helps users discover related search terms and complete their queries.
    """
    logger.info(f"MCP Tool 'get_giphy_autocomplete' called with query: '{query}', limit: {limit}")
    
    if not query:
        return {"error": "Query cannot be empty."}
    
    if limit <= 0:
        return {"error": "Limit must be a positive number."}

    try:
        params = {
            "q": query,
            "limit": limit
        }

        api_response = await _make_giphy_request("search/tags", params)
        terms_data = api_response.get("data", [])

        if not terms_data:
            logger.warning(f"No autocomplete suggestions found for query: '{query}'")
            return {"info": f"No suggestions found for '{query}'", "suggestions": []}

        suggestions = [term.get("name") for term in terms_data if term.get("name")]
        
        logger.info(f"Retrieved {len(suggestions)} autocomplete suggestions for query '{query}'")
        return {
            "query": query,
            "suggestions": suggestions,
            "count": len(suggestions)
        }

    except RuntimeError as e:
        logger.error(f"Giphy API interaction failed for autocomplete query '{query}': {e}")
        return {"error": f"Giphy API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_giphy_autocomplete with query '{query}': {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_trending_search_terms() -> Dict[str, Any]:
    """
    Gets the most popular trending search terms on Giphy.
    Useful for discovering what's currently popular and trending.
    """
    logger.info("MCP Tool 'get_trending_search_terms' called")
    
    try:
        params = {}
        api_response = await _make_giphy_request("trending/searches", params)
        terms = api_response.get("data", [])

        if not terms:
            logger.warning("No trending search terms found")
            return {"info": "No trending search terms found", "trending_terms": []}

        logger.info(f"Retrieved {len(terms)} trending search terms")
        return {
            "trending_terms": terms,
            "count": len(terms)
        }

    except RuntimeError as e:
        logger.error(f"Giphy API interaction failed for trending search terms: {e}")
        return {"error": f"Giphy API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_trending_search_terms: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_giphy_image_by_id(
    gif_id: Annotated[
        str,
        Field(description="The Giphy GIF ID to retrieve (e.g., 'xT4uQulxzV39haRFjG')")
    ]
) -> Dict[str, Any]:
    """
    Gets a specific GIF by its Giphy ID.
    Useful when you know the exact GIF you want to retrieve.
    """
    logger.info(f"MCP Tool 'get_giphy_image_by_id' called with ID: '{gif_id}'")
    
    if not gif_id:
        return {"error": "GIF ID cannot be empty."}

    try:
        params = {
            "rating": GIPHY_TRENDING_RATING
        }

        api_response = await _make_giphy_request(gif_id, params)
        gif_data = api_response.get("data")

        if not gif_data:
            logger.warning(f"No GIF found for ID: '{gif_id}'")
            return {"info": f"No GIF found for ID: '{gif_id}'", "image_url": None}

        image_url = _get_prioritized_image_url(gif_data)
        if not image_url:
            logger.warning(f"Could not find suitable rendition for GIF ID: {gif_id}")
            return {"info": "Could not process the requested GIF.", "image_url": None}

        logger.info(f"Retrieved GIF ID: {gif_id}, Title: '{gif_data.get('title')}'")
        return {
            "image_url": image_url,
            "title": gif_data.get("title"),
            "id": gif_data.get("id"),
            "giphy_page_url": gif_data.get("url"),
            "username": gif_data.get("username"),
            "source": gif_data.get("source"),
            "rating": gif_data.get("rating"),
            "create_datetime": gif_data.get("create_datetime")
        }

    except RuntimeError as e:
        logger.error(f"Giphy API interaction failed for GIF ID '{gif_id}': {e}")
        return {"error": f"Giphy API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_giphy_image_by_id with ID '{gif_id}': {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def search_giphy_stickers(
    query: Annotated[
        str,
        Field(description="Search term for stickers (e.g., 'happy', 'thumbs up', 'hello'). Must be in English.")
    ],
    search_limit: Annotated[
        Optional[int],
        Field(description="Number of stickers to fetch from Giphy to choose from. Default is 5.")
    ] = 5
) -> Dict[str, Any]:
    """
    Searches Giphy specifically for stickers (transparent background animations).
    Returns the most relevant sticker prioritizing WebP format.
    """
    logger.info(f"MCP Tool 'search_giphy_stickers' called with query: '{query}', search_limit: {search_limit}")
    
    if not query:
        return {"error": "Search query cannot be empty."}
    if search_limit <= 0:
        return {"error": "Search limit must be a positive number."}

    try:
        params = {
            "q": query,
            "limit": search_limit,
            "rating": GIPHY_TRENDING_RATING,
            "lang": "en"
        }

        # Use stickers search endpoint
        url = f"https://api.giphy.com/v1/stickers/search"
        params["api_key"] = GIPHY_API_KEY
        
        logger.debug(f"Making Giphy Stickers API request to: {url} with params: {params}")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    api_response = await response.json()
            except aiohttp.ClientResponseError as e:
                logger.error(f"Giphy Stickers API request failed: {e.status} {e.message}")
                raise RuntimeError(f"Giphy Stickers API Error ({e.status}): {e.message}") from e

        api_data_list: List[Dict[str, Any]] = api_response.get("data", [])

        if not api_data_list:
            logger.warning(f"No stickers found for query: '{query}'")
            return {"info": f"No stickers found for query: '{query}'.", "image_url": None}

        suitable_stickers = []
        for item_data in api_data_list:
            image_url = _get_prioritized_image_url(item_data)
            if image_url:
                suitable_stickers.append({
                    "id": item_data.get("id"),
                    "title": item_data.get("title"),
                    "url": image_url,
                    "giphy_page_url": item_data.get("url")
                })
        
        if not suitable_stickers:
            logger.warning(f"No stickers with suitable renditions found for query: '{query}' from {len(api_data_list)} initial results.")
            return {"info": f"No stickers with suitable renditions found for '{query}'.", "image_url": None}

        # Choose the first sticker, which is the most relevant
        chosen_sticker = suitable_stickers[0]
        logger.info(f"Selected top sticker ID: {chosen_sticker['id']}, Title: '{chosen_sticker['title']}' for query '{query}'")

        return {
            "image_url": chosen_sticker["url"],
            "title": chosen_sticker["title"],
            "id": chosen_sticker["id"],
            "giphy_page_url": chosen_sticker["giphy_page_url"],
            "query": query,
            "content_type": "sticker"
        }

    except RuntimeError as e:
        logger.error(f"Giphy Stickers API interaction failed for query '{query}': {e}")
        return {"error": f"Giphy Stickers API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in search_giphy_stickers for query '{query}': {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_trending_giphy_stickers(
    limit: Annotated[
        Optional[int],
        Field(description="Number of trending stickers to fetch. Default is 5, maximum is 25.")
    ] = 5
) -> Dict[str, Any]:
    """
    Gets trending stickers from Giphy.
    Returns a list of currently popular stickers with transparent backgrounds.
    """
    logger.info(f"MCP Tool 'get_trending_giphy_stickers' called with limit: {limit}")
    
    if limit <= 0 or limit > 25:
        return {"error": "Limit must be between 1 and 25."}

    try:
        params = {
            "limit": limit,
            "rating": GIPHY_TRENDING_RATING
        }

        # Use stickers trending endpoint
        url = f"https://api.giphy.com/v1/stickers/trending"
        params["api_key"] = GIPHY_API_KEY
        
        logger.debug(f"Making Giphy Trending Stickers API request to: {url} with params: {params}")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    api_response = await response.json()
            except aiohttp.ClientResponseError as e:
                logger.error(f"Giphy Trending Stickers API request failed: {e.status} {e.message}")
                raise RuntimeError(f"Giphy Trending Stickers API Error ({e.status}): {e.message}") from e

        api_data_list: List[Dict[str, Any]] = api_response.get("data", [])

        if not api_data_list:
            logger.warning(f"No trending stickers found for rating '{GIPHY_TRENDING_RATING}'")
            return {"info": f"No trending stickers found for rating '{GIPHY_TRENDING_RATING}'", "stickers": []}

        trending_stickers = []
        for item_data in api_data_list:
            image_url = _get_prioritized_image_url(item_data)
            if image_url:
                trending_stickers.append({
                    "id": item_data.get("id"),
                    "title": item_data.get("title"),
                    "url": image_url,
                    "giphy_page_url": item_data.get("url"),
                    "username": item_data.get("username")
                })
        
        if not trending_stickers:
            logger.warning(f"No trending stickers with suitable renditions found from {len(api_data_list)} initial results")
            return {"info": "No trending stickers with suitable renditions found", "stickers": []}

        logger.info(f"Retrieved {len(trending_stickers)} trending stickers")
        return {
            "stickers": trending_stickers,
            "count": len(trending_stickers),
            "rating_used": GIPHY_TRENDING_RATING,
            "content_type": "stickers"
        }

    except RuntimeError as e:
        logger.error(f"Giphy Trending Stickers API interaction failed: {e}")
        return {"error": f"Giphy Trending Stickers API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_trending_giphy_stickers: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_giphy_image_by_search(
    query: Annotated[
        str,
        Field(description="The search term for the image (e.g., 'funny cat', 'happy dance'). must be in English.")
    ],
    search_limit: Annotated[
        Optional[int],
        Field(description="Number of images to fetch from Giphy to choose from. Default is 5.")
    ] = 5
) -> Dict[str, Any]:
    """
    Searches Giphy for images matching the query, then returns a URL
    for the most relevant image (prioritizing WebP).
    The image rendition is chosen to be suitable for Discord.
    """
    logger.info(f"MCP Tool 'get_giphy_image_by_search' called with query: '{query}', search_limit: {search_limit}")
    if not query:
        return {"error": "Search query cannot be empty."}
    if search_limit <= 0:
        return {"error": "Search limit must be a positive number."}

    try:
        params = {
            "q": query,
            "limit": search_limit,
            "rating": GIPHY_TRENDING_RATING,
            "lang": "en"
        }
        api_response = await _make_giphy_request("search", params)
        api_data_list: List[Dict[str, Any]] = api_response.get("data", [])

        if not api_data_list:
            logger.warning(f"No images found for query: '{query}'")
            return {"info": f"No images found for query: '{query}'.", "image_url": None} 

        suitable_images = []
        for item_data in api_data_list:
            image_url = _get_prioritized_image_url(item_data)
            if image_url:
                suitable_images.append({
                    "id": item_data.get("id"),
                    "title": item_data.get("title"),
                    "url": image_url,
                    "giphy_page_url": item_data.get("url") 
                })
        
        if not suitable_images:
            logger.warning(f"No images with suitable renditions found for query: '{query}' from {len(api_data_list)} initial results.")
            return {"info": f"No images with suitable renditions found for '{query}'.", "image_url": None}

        # Choose the first image, which is the most relevant
        chosen_image = suitable_images[0]
        logger.info(f"Selected top image ID: {chosen_image['id']}, Title: '{chosen_image['title']}' for query '{query}'")

        return {
            "image_url": chosen_image["url"], 
            "title": chosen_image["title"],
            "id": chosen_image["id"],
            "giphy_page_url": chosen_image["giphy_page_url"],
            "query": query
        }

    except RuntimeError as e:
        logger.error(f"Giphy API interaction failed for query '{query}': {e}")
        return {"error": f"Giphy API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_giphy_image_by_search for query '{query}': {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_top_trending_giphy_image() -> Dict[str, Any]:
    """
    Fetches the current top trending image (prioritizing WebP) from Giphy.
    The image rendition is chosen to be suitable for Discord.
    The content rating is based on the GIPHY_TRENDING_RATING environment variable.
    """
    logger.info(f"MCP Tool 'get_top_trending_giphy_image' called. Using rating: {GIPHY_TRENDING_RATING}")
    try:
        params = {
            "limit": 1,
            "rating": GIPHY_TRENDING_RATING
        }
        api_response = await _make_giphy_request("trending", params)
        api_data_list: List[Dict[str, Any]] = api_response.get("data", [])

        if not api_data_list:
            logger.warning(f"No trending images found for rating '{GIPHY_TRENDING_RATING}'.")
            return {"info": f"No trending images found for rating '{GIPHY_TRENDING_RATING}'.", "image_url": None}

        top_item_data = api_data_list[0]
        image_url = _get_prioritized_image_url(top_item_data)

        if not image_url:
            logger.warning(f"Could not find a suitable rendition for the top trending image ID: {top_item_data.get('id')}")
            return {"info": "Could not process the top trending image.", "image_url": None}

        logger.info(f"Fetched top trending image ID: {top_item_data.get('id')}, Title: '{top_item_data.get('title')}'")
        return {
            "image_url": image_url,
            "title": top_item_data.get("title"),
            "id": top_item_data.get("id"),
            "giphy_page_url": top_item_data.get("url"),
            "rating_used": GIPHY_TRENDING_RATING
        }

    except RuntimeError as e:
        logger.error(f"Giphy API interaction failed for trending images: {e}")
        return {"error": f"Giphy API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_top_trending_giphy_image: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

def main():
    logger.info(f"Starting Giphy MCP Server on port {GIPHY_MCP_SERVER_PORT} with log level {LOG_LEVEL_ENV}")
    mcp.run(transport="streamable-http",
        host="0.0.0.0",
        port=GIPHY_MCP_SERVER_PORT,
        log_level=LOG_LEVEL_ENV.lower()
    )

if __name__ == "__main__":
    main()