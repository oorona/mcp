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
    instructions="Retrieve a random WebP image from Giphy based on a search query or get the current top trending WebP image. Optimized for Discord."
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

def _get_prioritized_image_url(gif_data: Dict[str, Any]) -> Optional[str]: # Renamed function
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
        logger.warning(f"Using 'original' GIF URL for image ID {gif_data.get('id')} (WebP not found). File size might be large: {original_gif_url}")
        return original_gif_url

    logger.warning(f"No suitable image URL (WebP or GIF) found in renditions for Giphy ID {gif_data.get('id')}")
    return None

@mcp.tool()
async def get_random_giphy_image( # Renamed tool function
    query: Annotated[
        str,
        Field(description="The search term for the image (e.g., 'funny cat', 'happy dance'). must be in English.")
    ],
    search_limit: Annotated[
        Optional[int],
        Field(description="Number of images to fetch from Giphy to choose from. Default is 10.")
    ] = 10
) -> Dict[str, Any]:
    """
    Searches Giphy for images matching the query, then returns a URL
    for a single, randomly selected image (prioritizing WebP).
    The image rendition is chosen to be suitable for Discord.
    """
    logger.info(f"MCP Tool 'get_random_giphy_image' called with query: '{query}', search_limit: {search_limit}")
    # ... (input validation remains the same) ...
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
            return {"info": f"No images found for query: '{query}'.", "image_url": None} # Changed key

        suitable_images = []
        for item_data in api_data_list:
            image_url = _get_prioritized_image_url(item_data) # Using new helper
            if image_url:
                suitable_images.append({
                    "id": item_data.get("id"),
                    "title": item_data.get("title"),
                    "url": image_url, # This will now often be a WebP URL
                    "giphy_page_url": item_data.get("url") 
                })
        
        if not suitable_images:
            logger.warning(f"No images with suitable renditions found for query: '{query}' from {len(api_data_list)} initial results.")
            return {"info": f"No images with suitable renditions found for '{query}'.", "image_url": None} # Changed key

        chosen_image = random.choice(suitable_images)
        logger.info(f"Randomly selected image ID: {chosen_image['id']}, Title: '{chosen_image['title']}' for query '{query}'")

        return {
            "image_url": chosen_image["url"], # Changed key
            "title": chosen_image["title"],
            "id": chosen_image["id"],
            "giphy_page_url": chosen_image["giphy_page_url"],
            "query": query
        }

    except RuntimeError as e:
        logger.error(f"Giphy API interaction failed for query '{query}': {e}")
        return {"error": f"Giphy API error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error in get_random_giphy_image for query '{query}': {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_top_trending_giphy_image() -> Dict[str, Any]: # Renamed tool function
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
            return {"info": f"No trending images found for rating '{GIPHY_TRENDING_RATING}'.", "image_url": None} # Changed key

        top_item_data = api_data_list[0]
        image_url = _get_prioritized_image_url(top_item_data) # Using new helper

        if not image_url:
            logger.warning(f"Could not find a suitable rendition for the top trending image ID: {top_item_data.get('id')}")
            return {"info": "Could not process the top trending image.", "image_url": None} # Changed key

        logger.info(f"Fetched top trending image ID: {top_item_data.get('id')}, Title: '{top_item_data.get('title')}'")
        return {
            "image_url": image_url, # Changed key
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