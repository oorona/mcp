import os
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from fastmcp import FastMCP
import httpx

# Configure logging for better debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("userhistory")

load_dotenv()

USER_API_BASE_URL = os.getenv("USER_API_BASE_URL", "http://localhost:8000").rstrip("/")
USER_MCP_PORT = int(os.getenv("USER_MCP_PORT", "6600"))

# Debug helper function
def log_api_error(tool_name: str, api_url: str, error: Exception, extra_context: Dict = None):
    """Log detailed API error information for debugging"""
    logger.error(f"Tool '{tool_name}': API Error Details:")
    logger.error(f"  - Base URL from env: {USER_API_BASE_URL}")
    logger.error(f"  - Full URL attempted: {api_url}")
    logger.error(f"  - Error type: {type(error).__name__}")
    logger.error(f"  - Error message: {str(error)}")
    if extra_context:
        for key, value in extra_context.items():
            logger.error(f"  - {key}: {value}")
    
    # Additional DNS/network debugging
    if isinstance(error, httpx.RequestError):
        logger.error(f"  - Network Error: This is likely a DNS or connection issue")
        logger.error(f"  - Check that the service '{USER_API_BASE_URL}' is accessible from this container")
        logger.error(f"  - Verify the service is on the same Docker network")
        
        # Parse hostname from URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(USER_API_BASE_URL)
            logger.error(f"  - Hostname to resolve: {parsed.hostname}")
            logger.error(f"  - Port: {parsed.port or 'default'}")
        except:
            pass



mcp = FastMCP(
    "User history, conversation context and analytics",
)

#@mcp.tool()
async def test_api_connection() -> Dict[str, Any]:
    """
    Test the connection to the User API and return diagnostic information.
    
    This is a diagnostic tool that helps troubleshoot connection issues.
    
    Returns:
        Diagnostic information including:
        - configured_url: The base URL from environment
        - connection_status: Whether the connection succeeded
        - error_details: If connection failed, detailed error information
    """
    logger.info("Tool 'test_api_connection': Testing API connectivity")
    logger.info(f"  - Base URL: {USER_API_BASE_URL}")
    
    result = {
        "configured_url": USER_API_BASE_URL,
        "connection_status": "unknown",
        "test_timestamp": None,
        "error_details": None
    }
    
    # Try a simple health check or basic endpoint
    test_url = f"{USER_API_BASE_URL}/health"  # or any known endpoint
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.info(f"  - Attempting to connect to: {test_url}")
            response = await client.get(test_url)
            result["connection_status"] = "success"
            result["status_code"] = response.status_code
            result["test_timestamp"] = "connected"
            logger.info(f"  - Connection successful! Status: {response.status_code}")
            
    except httpx.RequestError as e:
        result["connection_status"] = "failed"
        result["error_type"] = type(e).__name__
        result["error_message"] = str(e)
        
        # Parse hostname for debugging
        try:
            from urllib.parse import urlparse
            parsed = urlparse(USER_API_BASE_URL)
            result["hostname"] = parsed.hostname
            result["port"] = parsed.port or "default"
            result["scheme"] = parsed.scheme
        except:
            pass
            
        log_api_error('test_api_connection', test_url, e)
        
    except Exception as e:
        result["connection_status"] = "error"
        result["error_type"] = type(e).__name__
        result["error_message"] = str(e)
        logger.error(f"  - Unexpected error: {e}", exc_info=True)
    
    return result



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


@mcp.tool()
async def get_conversation_context(
    channel_id: int,
    minutes: int = 60  # Default to last 60 minutes
) -> List[Dict[str, Any]]:
    """
    Fetches recent conversation context from a Discord channel for LLM analysis.
    
    This tool retrieves messages from all users in a channel within the specified time window,
    providing context about the ongoing conversation. Useful for understanding what users
    are discussing and providing relevant responses.

    Args:
        channel_id: The Discord channel ID to get conversation context from.
        minutes: How many minutes back to retrieve conversation history. Defaults to 60.

    Returns:
        A list of conversation messages with user information, sorted chronologically.
        Each message contains:
        - timestamp: When the message was sent
        - content: The message text
        - user_id: Discord user ID
        - username: Display name of the user
        - channel_id: Discord channel ID  
        - channel_name: Name of the channel

    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        httpx.RequestError: If there's a problem connecting to the API.
        Exception: For other unexpected errors during the process.
    """
    api_url = f"{USER_API_BASE_URL}/conversation/{channel_id}"
    params = {"minutes": minutes}

    logger.warning(f"Tool 'get_conversation_context': Requesting {minutes} minutes of conversation for channel {channel_id} from {api_url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, params=params, timeout=15.0)
            response.raise_for_status()
            messages = response.json()
            logger.info(f"Tool 'get_conversation_context': Successfully retrieved {len(messages)} conversation messages for channel {channel_id}")
            return messages

    except httpx.HTTPStatusError as e:
        logger.error(f"Tool 'get_conversation_context': API request failed for channel {channel_id} with status {e.response.status_code}: {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Tool 'get_conversation_context': Could not connect to the API at {api_url}: {e}")
        raise Exception(f"Network error contacting conversation API: {e}") from e
    except Exception as e:
        logger.error(f"Tool 'get_conversation_context': An unexpected error occurred for channel {channel_id}: {e}", exc_info=True)
        raise Exception(f"Unexpected error fetching conversation context: {e}") from e


#@mcp.tool()
async def list_conversation_channels() -> List[Dict[str, Any]]:
    """
    Lists Discord channels that have available conversation history.
    
    This tool helps identify which channels have conversation data available.
    Use this to find channel IDs before calling get_conversation_context.
    
    Returns:
        A list of channels with conversation data, each containing:
        - channel_id: Discord channel ID (use this with get_conversation_context)
        - channel_name: Human-readable channel name
        - last_activity: When the most recent message was sent
        - message_count: Approximate number of recent messages (last 24 hours)
    
    Example usage:
        1. Call list_conversation_channels() to see available channels
        2. Use a channel_id from the results with get_conversation_context()
    
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code.
        httpx.RequestError: If there's a problem connecting to the API.
        Exception: For other unexpected errors during the process.
    """
    api_url = f"{USER_API_BASE_URL}/channels"

    logger.warning(f"Tool 'list_conversation_channels': Requesting list of channels with conversation data from {api_url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, timeout=10.0)
            response.raise_for_status()
            channels = response.json()
            logger.info(f"Tool 'list_conversation_channels': Successfully retrieved {len(channels)} channels with conversation history")
            return channels

    except httpx.HTTPStatusError as e:
        logger.error(f"Tool 'list_conversation_channels': API request failed with status {e.response.status_code}: {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Tool 'list_conversation_channels': Could not connect to the API at {api_url}: {e}")
        raise Exception(f"Network error contacting channels API: {e}") from e
    except Exception as e:
        logger.error(f"Tool 'list_conversation_channels': An unexpected error occurred: {e}", exc_info=True)
        raise Exception(f"Unexpected error fetching channel list: {e}") from e


# --- ANALYTICS TOOLS ---

@mcp.tool()
async def get_user_word_cloud(
    user_id: int,
    top_words: int = 50
) -> Dict[str, Any]:
    """
    Generates word cloud data for a specific user showing their most commonly used words.
    
    This tool analyzes a user's message history to identify frequently used terms,
    which helps understand their interests, communication style, and topics they discuss.
    
    Args:
        user_id: The Discord user ID to analyze.
        top_words: Number of top words to return (default 50, max 200).
    
    Returns:
        Word frequency data including:
        - words: List of {word, count} objects sorted by frequency
        - total_messages: Number of messages analyzed
        - total_words: Total word count
        - unique_words: Number of unique words used
    
    Use cases:
        - Understanding user interests and communication patterns
        - Generating personalized content recommendations
        - Identifying user expertise areas
    """
    api_url = f"{USER_API_BASE_URL}/analytics/user/{user_id}/wordcloud"
    params = {"top_words": min(top_words, 200)}

    logger.warning(f"Tool 'get_user_word_cloud': Analyzing word usage for user {user_id}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Tool 'get_user_word_cloud': Retrieved word cloud data for user {user_id}")
            return data

    except httpx.HTTPStatusError as e:
        logger.error(f"Tool 'get_user_word_cloud': API request failed for user {user_id} with status {e.response.status_code}: {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Tool 'get_user_word_cloud': Could not connect to the API: {e}")
        raise Exception(f"Network error contacting analytics API: {e}") from e
    except Exception as e:
        logger.error(f"Tool 'get_user_word_cloud': An unexpected error occurred for user {user_id}: {e}", exc_info=True)
        raise Exception(f"Unexpected error fetching word cloud: {e}") from e


@mcp.tool()
async def get_user_activity_pattern(
    user_id: int
) -> Dict[str, Any]:
    """
    Analyzes when a user is most active throughout the day and week.
    
    This tool examines a user's messaging patterns to identify their activity schedule,
    helping understand their timezone, availability, and engagement patterns.
    
    Args:
        user_id: The Discord user ID to analyze.
    
    Returns:
        Activity pattern data including:
        - activity_by_hour: Message count for each hour (0-23)
        - activity_by_day: Message count for each day of week
        - most_active_hour: Peak activity hour
        - most_active_day: Peak activity day
        - total_messages: Total messages analyzed
    
    Use cases:
        - Optimal timing for user engagement
        - Understanding user availability patterns
        - Timezone inference and scheduling
    """
    api_url = f"{USER_API_BASE_URL}/analytics/user/{user_id}/activity"

    logger.warning(f"Tool 'get_user_activity_pattern': Analyzing activity pattern for user {user_id}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Tool 'get_user_activity_pattern': Retrieved activity pattern for user {user_id}")
            return data

    except httpx.HTTPStatusError as e:
        logger.error(f"Tool 'get_user_activity_pattern': API request failed for user {user_id} with status {e.response.status_code}: {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Tool 'get_user_activity_pattern': Could not connect to the API: {e}")
        raise Exception(f"Network error contacting analytics API: {e}") from e
    except Exception as e:
        logger.error(f"Tool 'get_user_activity_pattern': An unexpected error occurred for user {user_id}: {e}", exc_info=True)
        raise Exception(f"Unexpected error fetching activity pattern: {e}") from e


@mcp.tool()
async def get_user_sentiment_analysis(
    user_id: int
) -> Dict[str, Any]:
    """
    Performs sentiment analysis on a user's message history.
    
    This tool analyzes the emotional tone of a user's messages to understand their
    general mood, communication style, and emotional patterns.
    
    Args:
        user_id: The Discord user ID to analyze.
    
    Returns:
        Sentiment analysis including:
        - sentiment_summary: Breakdown of positive/negative/neutral messages
        - average_sentiment: Overall sentiment score (-1 to 1)
        - overall_mood: General mood classification
        - total_messages: Number of messages analyzed
    
    Use cases:
        - Understanding user emotional state
        - Identifying users who might need support
        - Tailoring communication tone
        - Community mood monitoring
    """
    api_url = f"{USER_API_BASE_URL}/analytics/user/{user_id}/sentiment"

    logger.warning(f"Tool 'get_user_sentiment_analysis': Analyzing sentiment for user {user_id}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Tool 'get_user_sentiment_analysis': Retrieved sentiment analysis for user {user_id}")
            return data

    except httpx.HTTPStatusError as e:
        logger.error(f"Tool 'get_user_sentiment_analysis': API request failed for user {user_id} with status {e.response.status_code}: {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Tool 'get_user_sentiment_analysis': Could not connect to the API: {e}")
        raise Exception(f"Network error contacting analytics API: {e}") from e
    except Exception as e:
        logger.error(f"Tool 'get_user_sentiment_analysis': An unexpected error occurred for user {user_id}: {e}", exc_info=True)
        raise Exception(f"Unexpected error fetching sentiment analysis: {e}") from e


@mcp.tool()
async def get_channel_activity_stats(
    channel_id: int,
    hours: int = 24
) -> Dict[str, Any]:
    """
    Analyzes activity statistics for a specific channel.
    
    This tool examines channel activity patterns including peak hours, user participation,
    and engagement metrics to understand channel dynamics.
    
    Args:
        channel_id: The Discord channel ID to analyze.
        hours: Number of hours of history to analyze (default 24, max 168).
    
    Returns:
        Channel activity statistics including:
        - total_messages: Message count in timeframe
        - unique_users: Number of different users who posted
        - messages_per_hour: Average message rate
        - peak_hour: Most active hour
        - top_users: Most active users in channel
        - activity_by_hour: Hourly message distribution
    
    Use cases:
        - Channel management and optimization
        - Understanding community engagement
        - Identifying active contributors
        - Peak time analysis for announcements
    """
    api_url = f"{USER_API_BASE_URL}/analytics/channel/{channel_id}/activity"
    params = {"hours": min(hours, 168)}

    logger.warning(f"Tool 'get_channel_activity_stats': Analyzing activity for channel {channel_id}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Tool 'get_channel_activity_stats': Retrieved activity stats for channel {channel_id}")
            return data

    except httpx.HTTPStatusError as e:
        logger.error(f"Tool 'get_channel_activity_stats': API request failed for channel {channel_id} with status {e.response.status_code}: {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Tool 'get_channel_activity_stats': Could not connect to the API: {e}")
        raise Exception(f"Network error contacting analytics API: {e}") from e
    except Exception as e:
        logger.error(f"Tool 'get_channel_activity_stats': An unexpected error occurred for channel {channel_id}: {e}", exc_info=True)
        raise Exception(f"Unexpected error fetching channel activity stats: {e}") from e


@mcp.tool()
async def get_channel_sentiment_trend(
    channel_id: int,
    hours: int = 24
) -> Dict[str, Any]:
    """
    Analyzes sentiment trends in a channel over time.
    
    This tool tracks how the emotional tone of conversations changes in a channel,
    helping identify mood shifts, controversial topics, or positive/negative trends.
    
    Args:
        channel_id: The Discord channel ID to analyze.
        hours: Number of hours of history to analyze (default 24, max 168).
    
    Returns:
        Sentiment trend analysis including:
        - hourly_sentiment: Sentiment scores by hour
        - overall_sentiment: Average sentiment for the period
        - sentiment_distribution: Breakdown of positive/negative/neutral
        - overall_mood: General mood classification
        - total_messages: Number of messages analyzed
    
    Use cases:
        - Monitoring community mood
        - Identifying trending topics causing emotional responses
        - Conflict detection and resolution
        - Understanding reaction to announcements
    """
    api_url = f"{USER_API_BASE_URL}/analytics/channel/{channel_id}/sentiment"
    params = {"hours": min(hours, 168)}

    logger.warning(f"Tool 'get_channel_sentiment_trend': Analyzing sentiment trend for channel {channel_id}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Tool 'get_channel_sentiment_trend': Retrieved sentiment trend for channel {channel_id}")
            return data

    except httpx.HTTPStatusError as e:
        logger.error(f"Tool 'get_channel_sentiment_trend': API request failed for channel {channel_id} with status {e.response.status_code}: {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Tool 'get_channel_sentiment_trend': Could not connect to the API: {e}")
        raise Exception(f"Network error contacting analytics API: {e}") from e
    except Exception as e:
        logger.error(f"Tool 'get_channel_sentiment_trend': An unexpected error occurred for channel {channel_id}: {e}", exc_info=True)
        raise Exception(f"Unexpected error fetching sentiment trend: {e}") from e


@mcp.tool()
async def get_activity_heatmap(
    days: int = 7
) -> Dict[str, Any]:
    """
    Generates a server-wide activity heatmap showing when the community is most active.
    
    This tool analyzes activity patterns across all channels to create a comprehensive
    view of when the Discord server has the highest engagement.
    
    Args:
        days: Number of days of history to analyze (default 7, max 30).
    
    Returns:
        Activity heatmap data including:
        - heatmap_data: Activity count by day of week and hour
        - peak_activity: When the server is most active
        - total_messages: Total messages across all channels
        - channels_analyzed: Number of channels included
        - average_messages_per_day: Daily message average
    
    Use cases:
        - Optimal timing for server-wide announcements
        - Understanding global community patterns
        - Event planning and scheduling
        - Resource allocation during peak times
        - Moderation staffing optimization
    """
    api_url = f"{USER_API_BASE_URL}/analytics/heatmap"
    params = {"days": min(days, 30)}

    logger.warning(f"Tool 'get_activity_heatmap': Generating activity heatmap for last {days} days")
    logger.warning(f"Tool 'get_activity_heatmap': DEBUG - Base URL: {USER_API_BASE_URL}")
    logger.warning(f"Tool 'get_activity_heatmap': DEBUG - Full URL: {api_url}")
    logger.warning(f"Tool 'get_activity_heatmap': DEBUG - Parameters: {params}")

    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Tool 'get_activity_heatmap': DEBUG - Making request to {api_url}")
            response = await client.get(api_url, params=params, timeout=20.0)
            logger.info(f"Tool 'get_activity_heatmap': DEBUG - Response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Tool 'get_activity_heatmap': Retrieved activity heatmap data")
            return data

    except httpx.HTTPStatusError as e:
        logger.error(f"Tool 'get_activity_heatmap': API request failed with status {e.response.status_code}: {e.response.text}")
        log_api_error('get_activity_heatmap', api_url, e, {'status_code': e.response.status_code})
        raise
    except httpx.RequestError as e:
        logger.error(f"Tool 'get_activity_heatmap': Could not connect to the API: {e}")
        log_api_error('get_activity_heatmap', api_url, e, {'params': params})
        raise Exception(f"Network error contacting analytics API at {api_url}: {e}") from e
    except Exception as e:
        logger.error(f"Tool 'get_activity_heatmap': An unexpected error occurred: {e}", exc_info=True)
        log_api_error('get_activity_heatmap', api_url, e)
        raise Exception(f"Unexpected error fetching activity heatmap: {e}") from e


#@mcp.tool()
async def get_user_engagement_metrics(
    user_id: int
) -> Dict[str, Any]:
    """
    Analyzes detailed engagement metrics for a user including communication patterns.
    
    This tool provides comprehensive engagement analysis including message types,
    word usage patterns, reply behavior, and cross-channel/guild activity.
    
    Args:
        user_id: The Discord user ID to analyze.
    
    Returns:
        Detailed engagement metrics including:
        - total_messages: Total message count
        - total_words: Total word count across all messages
        - average_words_per_message: Communication verbosity
        - reply_count: Number of replies to other messages
        - reply_percentage: Percentage of messages that are replies
        - attachment_count: Number of messages with attachments
        - embed_count: Number of messages with embeds
        - channel_diversity: Number of different channels used
        - guild_diversity: Number of different servers active in
        - message_length_stats: Min/max/median word counts
    
    Use cases:
        - Understanding user communication style and engagement level
        - Identifying power users and active community members
        - Analyzing cross-platform activity patterns
        - Measuring user investment in community discussions
    """
    api_url = f"{USER_API_BASE_URL}/analytics/user/{user_id}/engagement"

    logger.warning(f"Tool 'get_user_engagement_metrics': Analyzing engagement for user {user_id}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Tool 'get_user_engagement_metrics': Retrieved engagement metrics for user {user_id}")
            return data

    except httpx.HTTPStatusError as e:
        logger.error(f"Tool 'get_user_engagement_metrics': API request failed for user {user_id} with status {e.response.status_code}: {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Tool 'get_user_engagement_metrics': Could not connect to the API: {e}")
        raise Exception(f"Network error contacting analytics API: {e}") from e
    except Exception as e:
        logger.error(f"Tool 'get_user_engagement_metrics': An unexpected error occurred for user {user_id}: {e}", exc_info=True)
        raise Exception(f"Unexpected error fetching engagement metrics: {e}") from e


#@mcp.tool()
async def get_guild_analytics_overview(
    guild_id: int,
    days: int = 7
) -> Dict[str, Any]:
    """
    Provides comprehensive guild-wide analytics and community insights.
    
    This tool analyzes server-wide activity patterns, identifies top contributors,
    and provides overview statistics for community health assessment.
    
    Args:
        guild_id: The Discord guild (server) ID to analyze.
        days: Number of days of history to analyze (default 7, max 30).
    
    Returns:
        Guild analytics overview including:
        - total_messages: Message count across all channels
        - unique_users: Number of active users
        - active_channels: Number of channels with activity
        - messages_per_day: Daily average message rate
        - average_messages_per_user: Per-user activity level
        - top_channels: Most active channels with message counts
        - top_users: Most active users with message counts
    
    Use cases:
        - Community health monitoring and growth tracking
        - Identifying most engaged channels and users
        - Server moderation and resource allocation
        - Understanding community dynamics and participation
        - Planning events and announcements for peak engagement
    """
    api_url = f"{USER_API_BASE_URL}/analytics/guild/{guild_id}/overview"
    params = {"days": min(days, 30)}

    logger.warning(f"Tool 'get_guild_analytics_overview': Analyzing guild overview for guild {guild_id}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, params=params, timeout=20.0)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Tool 'get_guild_analytics_overview': Retrieved guild overview for guild {guild_id}")
            return data

    except httpx.HTTPStatusError as e:
        logger.error(f"Tool 'get_guild_analytics_overview': API request failed for guild {guild_id} with status {e.response.status_code}: {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Tool 'get_guild_analytics_overview': Could not connect to the API: {e}")
        raise Exception(f"Network error contacting analytics API: {e}") from e
    except Exception as e:
        logger.error(f"Tool 'get_guild_analytics_overview': An unexpected error occurred for guild {guild_id}: {e}", exc_info=True)
        raise Exception(f"Unexpected error fetching guild overview: {e}") from e


def main():
    logger.info(f"Starting UserContext MCP server on port {USER_MCP_PORT}")
    logger.info(f"API Base URL: {USER_API_BASE_URL}")
    logger.info("Registered tools: get_user_context, get_conversation_context, get_user_word_cloud, get_user_activity_pattern, get_user_sentiment_analysis, get_channel_activity_stats, get_channel_sentiment_trend, get_activity_heatmap")
    logger.info("Using streamable HTTP transport for REST API compatibility")

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=USER_MCP_PORT,
        log_level="info"
    )


if __name__ == "__main__":
    main()

