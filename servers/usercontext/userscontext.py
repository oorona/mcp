import os
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import httpx

from fastmcp import FastMCP

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("userhistory")

USER_API_BASE_URL = os.getenv("USER_API_BASE_URL", "http://localhost:8000").rstrip("/")
USER_MCP_PORT = int(os.getenv("USER_MCP_PORT", "6600"))



mcp = FastMCP(
    name="User history",
    instructions="Retrieve las message for a given user_id.",
)



@mcp.tool()
async def get_user_context(
    # No ctx parameter here
    user_id: int,
    n: int = 10 # Default number of messages if not specified
) -> List[Dict[str, Any]]:
    """
    Fetches the last N messages for a given user_id from the User Messages API.

    Args:
        user_id: The unique identifier for the user.
        n: The maximum number of recent messages to retrieve. Defaults to 10.

    Returns:
        A list of message objects, each containing 'timestamp' and 'content'.

    Raises:
        httpx.HTTPStatusError: If the API returns an error status code (4xx or 5xx).
        httpx.RequestError: If there's a problem connecting to the API.
        Exception: For other unexpected errors during the process.
    """
    api_url = f"{USER_API_BASE_URL}/users/{user_id}/messages"
    params = {"count": n}

    # Use the function name directly in logs since ctx isn't available
    logger.warning(f"Tool 'get_user_context': Requesting {n} messages for user {user_id} from {api_url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, params=params, timeout=15.0) # Add a timeout
            response.raise_for_status()
            messages = response.json()
            logger.info(f"Tool 'get_user_context': Successfully retrieved {len(messages)} messages for user {user_id}")
            return messages

    except httpx.HTTPStatusError as e:
        logger.error(f"Tool 'get_user_context': API request failed for user {user_id} with status {e.response.status_code}: {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Tool 'get_user_context': Could not connect to the API at {api_url}: {e}")
        raise Exception(f"Network error contacting user API: {e}") from e
    except Exception as e:
        logger.error(f"Tool 'get_user_context': An unexpected error occurred for user {user_id}: {e}", exc_info=True)
        raise Exception(f"Unexpected error fetching user context: {e}") from e


def main():
    mcp.run(transport="streamable-http",
        host="0.0.0.0",
        port=USER_MCP_PORT,
        log_level="info"
    )


if __name__ == "__main__":
    main()

