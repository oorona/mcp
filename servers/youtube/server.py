import os
import logging
import re
from typing import Any, Dict, List, Optional, Annotated
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import aiohttp
from pydantic import Field
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

from fastmcp import FastMCP
# Load environment variables from .env file
load_dotenv()

# --- Start Logging Configuration ---
# Get log level from environment variable, default to INFO
DEFAULT_LOG_LEVEL = "INFO"
LOG_LEVEL_ENV = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()

numeric_log_level = getattr(logging, LOG_LEVEL_ENV, None)
if not isinstance(numeric_log_level, int):
    print(f"Warning: Invalid LOG_LEVEL '{LOG_LEVEL_ENV}' in .env file. Defaulting to '{DEFAULT_LOG_LEVEL}'.")
    numeric_log_level = getattr(logging, DEFAULT_LOG_LEVEL)

logging.basicConfig(
    level=numeric_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("youtube-mcp-server") # Your application's logger

# --- MODIFICATION START: Control Library Log Levels ---
# Only quiet down verbose libraries if your app's log level isn't set to DEBUG
# This allows you to still see their DEBUG logs if you set LOG_LEVEL=DEBUG for your app.
if numeric_log_level > logging.DEBUG: # e.g., if your app is at INFO, WARNING, ERROR
    logging.getLogger("sse_starlette").setLevel(logging.WARNING)
    logging.getLogger("mcp.server.sse").setLevel(logging.WARNING)
    # You can also control Uvicorn's loggers if needed:
    # logging.getLogger("uvicorn").setLevel(logging.WARNING)
    # logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    # logging.getLogger("uvicorn.access").setLevel(logging.INFO) # Access logs are usually kept at INFO
# --- MODIFICATION END ---

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    logger.error("YOUTUBE_API_KEY environment variable is required and not set.")
    raise ValueError("YOUTUBE_API_KEY environment variable is required")

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_MCP_SERVER_PORT = int(os.getenv("YOUTUBE_MCP_SERVER_PORT", "6500"))

mcp = FastMCP(
    name="Youtube",
    instructions="Comprehensive YouTube integration providing video details, transcripts, search, channel information, and playlist management. Prioritizes manual transcripts over auto-generated ones when available."
)

logger.info("Initializing YouTubeTranscriptApi")
youtube_transcript_api = YouTubeTranscriptApi()

def _format_time(seconds: float) -> str:
    """Converts seconds into HH:MM:SS or MM:SS format."""
    total_seconds = int(seconds)
    minutes, sec = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    else:
        return f"{minutes:02d}:{sec:02d}"

def _extract_video_id(url: str) -> str:
    """
    Extract the YouTube video ID from various URL formats.
    """
    logger.debug(f"Attempting to extract video ID from URL: {url}")
    if not url:
        logger.error("Empty URL provided to _extract_video_id")
        raise ValueError("Empty URL provided")
        
    if "youtube.com/watch" in url: # Standard watch?v=VIDEO_ID
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        video_ids = query_params.get("v")
        if video_ids and len(video_ids[0]) > 0:
            logger.debug(f"Extracted video ID {video_ids[0]} using standard pattern.")
            return video_ids[0]
            
    if "youtu.be/" in url: # Short youtu.be/VIDEO_ID
        parsed_url = urlparse(url)
        path = parsed_url.path
        if path and path.startswith("/"):
            video_id = path[1:].split("?")[0]
            logger.debug(f"Extracted video ID {video_id} using short URL pattern.")
            return video_id
            
    if "youtube.com/embed/" in url: # Embed /embed/VIDEO_ID
        parsed_url = urlparse(url)
        path = parsed_url.path
        if path and path.startswith("/embed/"):
            video_id = path[7:].split("?")[0]
            logger.debug(f"Extracted video ID {video_id} using embedded URL pattern.")
            return video_id
            
    if "youtube.com/shorts/" in url: # Shorts /shorts/VIDEO_ID
        parsed_url = urlparse(url)
        path = parsed_url.path
        if path and path.startswith("/shorts/"):
            video_id = path[8:].split("?")[0]
            logger.debug(f"Extracted video ID {video_id} using shorts URL pattern.")
            return video_id
    
    logger.warning(f"Could not extract video ID from URL: {url}")
    raise ValueError(f"Could not extract video ID from URL: {url}")

async def _make_youtube_request(endpoint: str, params: Dict[str, Any], headers: Dict[str, Any] = None) -> Any:
    """
    Makes an HTTP request to the YouTube Data API.
    """
    params["key"] = YOUTUBE_API_KEY
    url = f"{YOUTUBE_API_BASE}/{endpoint}"
    logger.debug(f"Making YouTube API request to: {url} with params: {params}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"YouTube API request failed: {e.status} {e.message} for GET {url}")
            error_details = e.message
            try:
                error_body = await e.response.json()
                error_details = f"{e.message} - {error_body}"
            except Exception:
                pass
            raise RuntimeError(f"YouTube API Error ({e.status}): {error_details}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during YouTube API request: {e}")
            raise RuntimeError(f"Unexpected error during API call to {url}") from e

async def get_video_details(
    video_id: Annotated[
        str,
        Field(
            description="The ID of the YouTube video to get details for."
        ),
    ]
) -> Dict[str, Any]:
    """Get detailed information about a specific YouTube video."""
    logger.info(f"Function 'get_video_details' called with video_id: {video_id}")
    try:
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": video_id
        }
        
        result = await _make_youtube_request("videos", params)
        
        if not result.get("items"):
            logger.warning(f"No video found with ID: {video_id} in get_video_details")
            return {"error": f"No video found with ID: {video_id}"}
        
        video = result["items"][0]
        snippet = video.get("snippet", {})
        content_details = video.get("contentDetails", {})
        statistics = video.get("statistics", {})
        
        details = {
            "id": video.get("id"),
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "publishedAt": snippet.get("publishedAt"),
            "channelId": snippet.get("channelId"),
            "channelTitle": snippet.get("channelTitle"),
            "thumbnailUrl": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "tags": snippet.get("tags", []),
            "categoryId": snippet.get("categoryId"),
            "duration": content_details.get("duration"),
            "viewCount": statistics.get("viewCount"),
            "likeCount": statistics.get("likeCount"),
            "commentCount": statistics.get("commentCount"),
            "url": f"https://www.youtube.com/watch?v={video_id}"
        }
        logger.debug(f"Returning video details for {video_id}: {details.get('title')}")
        return details
    except Exception as e:
        logger.exception(f"Error executing get_video_details for video_id {video_id}: {e}")
        raise e

@mcp.tool()
async def search_youtube_videos(
    query: Annotated[
        str,
        Field(
            description="The search query to find YouTube videos."
        ),
    ],
    max_results: Annotated[
        int,
        Field(
            description="Maximum number of results to return (1-50, default: 10).",
            default=10
        ),
    ] = 10,
    order: Annotated[
        str,
        Field(
            description="Order of results: relevance, date, rating, viewCount, title (default: relevance).",
            default="relevance"
        ),
    ] = "relevance"
) -> Dict[str, Any]:
    """Search for YouTube videos based on a query."""
    logger.info(f"Searching YouTube videos with query: {query}, max_results: {max_results}, order: {order}")
    
    try:
        params = {
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": min(max_results, 50),
            "order": order
        }
        
        result = await _make_youtube_request("search", params)
        
        if not result.get("items"):
            return {"results": [], "total_results": 0, "query": query}
        
        videos = []
        for item in result["items"]:
            snippet = item.get("snippet", {})
            video_info = {
                "id": item.get("id", {}).get("videoId"),
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "publishedAt": snippet.get("publishedAt"),
                "channelId": snippet.get("channelId"),
                "channelTitle": snippet.get("channelTitle"),
                "thumbnailUrl": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "url": f"https://www.youtube.com/watch?v={item.get('id', {}).get('videoId')}"
            }
            videos.append(video_info)
        
        return {
            "results": videos,
            "total_results": len(videos),
            "query": query,
            "order": order
        }
        
    except Exception as e:
        logger.exception(f"Error searching YouTube videos: {e}")
        return {"error": f"Failed to search videos: {str(e)}"}

@mcp.tool()
async def get_channel_info(
    channel_id: Annotated[
        str,
        Field(
            description="The YouTube channel ID to get information for."
        ),
    ]
) -> Dict[str, Any]:
    """Get detailed information about a YouTube channel."""
    logger.info(f"Getting channel info for channel_id: {channel_id}")
    
    try:
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": channel_id
        }
        
        result = await _make_youtube_request("channels", params)
        
        if not result.get("items"):
            return {"error": f"No channel found with ID: {channel_id}"}
        
        channel = result["items"][0]
        snippet = channel.get("snippet", {})
        statistics = channel.get("statistics", {})
        content_details = channel.get("contentDetails", {})
        
        channel_info = {
            "id": channel.get("id"),
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "customUrl": snippet.get("customUrl"),
            "publishedAt": snippet.get("publishedAt"),
            "thumbnailUrl": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "country": snippet.get("country"),
            "viewCount": statistics.get("viewCount"),
            "subscriberCount": statistics.get("subscriberCount"),
            "videoCount": statistics.get("videoCount"),
            "uploadsPlaylistId": content_details.get("relatedPlaylists", {}).get("uploads"),
            "url": f"https://www.youtube.com/channel/{channel_id}"
        }
        
        return channel_info
        
    except Exception as e:
        logger.exception(f"Error getting channel info: {e}")
        return {"error": f"Failed to get channel info: {str(e)}"}

@mcp.tool()
async def get_video_comments(
    video_id: Annotated[
        str,
        Field(
            description="The ID of the YouTube video to get comments for."
        ),
    ],
    max_results: Annotated[
        int,
        Field(
            description="Maximum number of comments to return (1-100, default: 20).",
            default=20
        ),
    ] = 20,
    order: Annotated[
        str,
        Field(
            description="Order of comments: time, relevance (default: relevance).",
            default="relevance"
        ),
    ] = "relevance"
) -> Dict[str, Any]:
    """Get comments for a YouTube video."""
    logger.info(f"Getting comments for video_id: {video_id}, max_results: {max_results}")
    
    try:
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(max_results, 100),
            "order": order,
            "textFormat": "plainText"
        }
        
        result = await _make_youtube_request("commentThreads", params)
        
        if not result.get("items"):
            return {"comments": [], "total_results": 0, "video_id": video_id}
        
        comments = []
        for item in result["items"]:
            comment = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            comment_info = {
                "id": item.get("id"),
                "text": comment.get("textDisplay"),
                "author": comment.get("authorDisplayName"),
                "authorChannelId": comment.get("authorChannelId", {}).get("value"),
                "likeCount": comment.get("likeCount"),
                "publishedAt": comment.get("publishedAt"),
                "updatedAt": comment.get("updatedAt")
            }
            comments.append(comment_info)
        
        return {
            "comments": comments,
            "total_results": len(comments),
            "video_id": video_id,
            "order": order
        }
        
    except Exception as e:
        logger.exception(f"Error getting video comments: {e}")
        return {"error": f"Failed to get comments: {str(e)}"}

@mcp.tool()
async def get_trending_videos(
    region_code: Annotated[
        str,
        Field(
            description="The region code for trending videos (e.g., 'US', 'GB', 'JP', default: 'US').",
            default="US"
        ),
    ] = "US",
    category_id: Annotated[
        Optional[str],
        Field(
            description="Category ID to filter trending videos (optional).",
            default=None
        ),
    ] = None,
    max_results: Annotated[
        int,
        Field(
            description="Maximum number of trending videos to return (1-50, default: 25).",
            default=25
        ),
    ] = 25
) -> Dict[str, Any]:
    """Get trending YouTube videos for a specific region."""
    logger.info(f"Getting trending videos for region: {region_code}, category: {category_id}")
    
    try:
        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": min(max_results, 50)
        }
        
        if category_id:
            params["videoCategoryId"] = category_id
        
        result = await _make_youtube_request("videos", params)
        
        if not result.get("items"):
            return {"trending_videos": [], "total_results": 0, "region": region_code}
        
        videos = []
        for item in result["items"]:
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            video_info = {
                "id": item.get("id"),
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "channelTitle": snippet.get("channelTitle"),
                "publishedAt": snippet.get("publishedAt"),
                "thumbnailUrl": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "viewCount": statistics.get("viewCount"),
                "likeCount": statistics.get("likeCount"),
                "commentCount": statistics.get("commentCount"),
                "url": f"https://www.youtube.com/watch?v={item.get('id')}"
            }
            videos.append(video_info)
        
        return {
            "trending_videos": videos,
            "total_results": len(videos),
            "region": region_code,
            "category_id": category_id
        }
        
    except Exception as e:
        logger.exception(f"Error getting trending videos: {e}")
        return {"error": f"Failed to get trending videos: {str(e)}"}

@mcp.tool()
async def check_transcript_availability(
    video_id: Annotated[
        str,
        Field(
            description="The YouTube video ID to check transcript availability for."
        ),
    ]
) -> Dict[str, Any]:
    """Check what transcripts are available for a YouTube video without fetching them."""
    logger.info(f"Checking transcript availability for video_id: {video_id}")
    
    try:
        transcript_list = youtube_transcript_api.list(video_id)
        
        available_transcripts = {
            "video_id": video_id,
            "manual_transcripts": [],
            "auto_generated_transcripts": [],
            "total_count": 0
        }
        
        # Get manual transcripts
        if hasattr(transcript_list, '_manually_created_transcripts') and transcript_list._manually_created_transcripts:
            for lang_code, transcript in transcript_list._manually_created_transcripts.items():
                available_transcripts["manual_transcripts"].append({
                    "language_code": lang_code,
                    "language": transcript.language,
                    "is_translatable": transcript.is_translatable
                })
        
        # Get auto-generated transcripts
        if hasattr(transcript_list, '_generated_transcripts') and transcript_list._generated_transcripts:
            for lang_code, transcript in transcript_list._generated_transcripts.items():
                available_transcripts["auto_generated_transcripts"].append({
                    "language_code": lang_code,
                    "language": transcript.language,
                    "is_translatable": transcript.is_translatable
                })
        
        available_transcripts["total_count"] = len(available_transcripts["manual_transcripts"]) + len(available_transcripts["auto_generated_transcripts"])
        
        if available_transcripts["total_count"] == 0:
            available_transcripts["info"] = "No transcripts available for this video"
        
        return available_transcripts
        
    except TranscriptsDisabled:
        return {
            "video_id": video_id,
            "error": "Transcripts are disabled for this video",
            "manual_transcripts": [],
            "auto_generated_transcripts": [],
            "total_count": 0
        }
    except NoTranscriptFound:
        return {
            "video_id": video_id,
            "info": "No transcripts found for this video",
            "manual_transcripts": [],
            "auto_generated_transcripts": [],
            "total_count": 0
        }
    except Exception as e:
        logger.exception(f"Error checking transcript availability: {e}")
        return {
            "error": f"Failed to check transcript availability: {str(e)}",
            "video_id": video_id
        }
    try:
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": video_id
        }
        
        result = await _make_youtube_request("videos", params)
        
        if not result.get("items"):
            logger.warning(f"No video found with ID: {video_id} in get_video_details")
            return {"error": f"No video found with ID: {video_id}"}
        
        video = result["items"][0]
        snippet = video.get("snippet", {})
        content_details = video.get("contentDetails", {})
        statistics = video.get("statistics", {})
        
        details = {
            "id": video.get("id"),
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "publishedAt": snippet.get("publishedAt"),
            "channelId": snippet.get("channelId"),
            "channelTitle": snippet.get("channelTitle"),
            "thumbnailUrl": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "tags": snippet.get("tags", []),
            "categoryId": snippet.get("categoryId"),
            "duration": content_details.get("duration"),
            "viewCount": statistics.get("viewCount"),
            "likeCount": statistics.get("likeCount"),
            "commentCount": statistics.get("commentCount"),
            "url": f"https://www.youtube.com/watch?v={video_id}"
        }
        logger.debug(f"Returning video details for {video_id}: {details.get('title')}")
        return details
    except Exception as e:
        logger.exception(f"Error executing get_video_details for video_id {video_id}: {e}")
        raise e

@mcp.tool()
async def get_youtube_video_transcript(
    url: Annotated[
        str,
        Field(
            description="The URL of the YouTube video to retrieve the transcript/subtitles for. (e.g. https://www.youtube.com/watch?v=dQw4w9WgXcQ)"
        ),
    ],
    language_preference: Annotated[
        Optional[str],
        Field(
            description="Preferred language code (e.g., 'en', 'es', 'fr'). If not specified, defaults to English then any available language.",
            default=None
        ),
    ] = None,
    include_timestamps: Annotated[
        bool,
        Field(
            description="Whether to include timestamp information in the transcript (default: True).",
            default=True
        ),
    ] = True
) -> Dict[str, Any]:
    """
    Retrieve the transcript or video details for a given YouTube video.
    Tries to fetch a manual transcript first (preferring specified language or English), then an
    auto-generated transcript. If no transcript is found, or if transcripts are disabled, 
    it falls back to video details with helpful information about transcript availability.
    """
    logger.info(f"MCP Tool 'get_youtube_video_transcript' called with URL: {url}, language_preference: {language_preference}")
    try:
        video_id = _extract_video_id(url)
        logger.info(f"Successfully extracted video_id: {video_id} from URL: {url}")
        
        transcript_to_fetch = None
        preferred_languages = [language_preference] if language_preference else ['en']

        try:
            transcript_list = youtube_transcript_api.list(video_id)
            logger.debug(f"Available transcripts for {video_id}: manual={list(transcript_list._manually_created_transcripts.keys()) if transcript_list._manually_created_transcripts else []}, generated={list(transcript_list._generated_transcripts.keys()) if transcript_list._generated_transcripts else []}")

            # Try manual transcripts first
            try:
                transcript_to_fetch = transcript_list.find_manually_created_transcript(preferred_languages)
                logger.info(f"Found manually created transcript in preferred language for {video_id} ({transcript_to_fetch.language_code}).")
            except NoTranscriptFound:
                logger.info(f"No manually created transcript in preferred languages for {video_id}. Checking for any manual transcript.")
                manual_langs = [lang for lang in transcript_list._manually_created_transcripts] if transcript_list._manually_created_transcripts else []
                if manual_langs:
                    try:
                        transcript_to_fetch = transcript_list.find_manually_created_transcript([manual_langs[0]])
                        logger.info(f"Found manually created transcript in language: {manual_langs[0]} for {video_id}.")
                    except NoTranscriptFound:
                         logger.info(f"Could not fetch first available manual transcript for {video_id}.")

            # If no manual transcript, try auto-generated
            if not transcript_to_fetch:
                logger.info(f"No manual transcript found. Checking for auto-generated transcript in preferred languages for {video_id}.")
                try:
                    transcript_to_fetch = transcript_list.find_generated_transcript(preferred_languages)
                    logger.info(f"Found auto-generated transcript in preferred language for {video_id} ({transcript_to_fetch.language_code}).")
                except NoTranscriptFound:
                    logger.info(f"No auto-generated transcript in preferred languages for {video_id}. Checking for any auto-generated transcript.")
                    generated_langs = [lang for lang in transcript_list._generated_transcripts] if transcript_list._generated_transcripts else []
                    if generated_langs:
                        try:
                            transcript_to_fetch = transcript_list.find_generated_transcript([generated_langs[0]])
                            logger.info(f"Found auto-generated transcript in language: {generated_langs[0]} for {video_id}.")
                        except NoTranscriptFound:
                            logger.info(f"Could not fetch first available auto-generated transcript for {video_id}.")
            
            if transcript_to_fetch:
                logger.debug(f"Fetching transcript for {video_id}, type: {'manual' if not transcript_to_fetch.is_generated else 'auto-generated'}, lang: {transcript_to_fetch.language_code}")
                raw_transcript_data = transcript_to_fetch.fetch()

                formatted_transcript = []
                full_text = ""
                
                for segment_object in raw_transcript_data:
                    try:
                        if include_timestamps:
                            formatted_segment = {
                                'text': segment_object.text,
                                'start': _format_time(segment_object.start),
                                'duration': segment_object.duration
                            }
                            formatted_transcript.append(formatted_segment)
                        
                        full_text += segment_object.text + " "
                        
                    except AttributeError as e:
                        logger.error(f"Error accessing attributes on a transcript segment object: {e}. Segment: {segment_object}")
                        if include_timestamps:
                            formatted_transcript.append({
                                'text': '[Error processing segment data]',
                                'start': '00:00',
                                'duration': 0
                            })
                
                result = {
                    "video_id": video_id,
                    "transcript_type": "manual" if not transcript_to_fetch.is_generated else "auto-generated",
                    "language_code": transcript_to_fetch.language_code,
                    "language": transcript_to_fetch.language,
                    "full_text": full_text.strip()
                }
                
                if include_timestamps:
                    result["transcript"] = formatted_transcript
                    result["segment_count"] = len(formatted_transcript)
                
                logger.info(f"Successfully fetched and formatted transcript for {video_id}.")
                return result
            else:
                logger.warning(f"No transcript (manual or auto-generated) found for video_id: {video_id}. Falling back to video details.")
                
                # Get available transcript info
                transcript_info = await check_transcript_availability(video_id)
                video_details = await get_video_details(video_id)
                
                return {
                    "video_id": video_id,
                    "video_details": video_details,
                    "transcript_availability": transcript_info,
                    "info": "No transcript available for this video. Check transcript_availability for details."
                }

        except TranscriptsDisabled:
            logger.warning(f"Transcripts are disabled for video_id: {video_id}. Falling back to video details.")
            video_details = await get_video_details(video_id)
            return {
                "video_id": video_id,
                "video_details": video_details,
                "error": "Transcripts are disabled for this video."
            }
        except Exception as transcript_error:
            logger.exception(f"Error processing transcript for video_id {video_id}: {transcript_error}. Falling back to video details.")
            video_details = await get_video_details(video_id)
            transcript_info = await check_transcript_availability(video_id)
            return {
                "video_id": video_id,
                "video_details": video_details,
                "transcript_availability": transcript_info,
                "error": f"An error occurred while trying to fetch or process the transcript: {str(transcript_error)}"
            }
    except ValueError as e:
        logger.error(f"Invalid YouTube URL provided: {url}. Error: {e}")
        return {
            "error": f"Invalid YouTube URL: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Unexpected error processing video URL {url}: {e}")
        return {
            "error": f"Failed to process request: {str(e)}"
        }

@mcp.tool()
async def get_playlist_videos(
    playlist_id: Annotated[
        str,
        Field(
            description="The YouTube playlist ID to get videos from."
        ),
    ],
    max_results: Annotated[
        int,
        Field(
            description="Maximum number of videos to return (1-50, default: 25).",
            default=25
        ),
    ] = 25
) -> Dict[str, Any]:
    """Get videos from a YouTube playlist."""
    logger.info(f"Getting videos from playlist_id: {playlist_id}, max_results: {max_results}")
    
    try:
        params = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": min(max_results, 50)
        }
        
        result = await _make_youtube_request("playlistItems", params)
        
        if not result.get("items"):
            return {"videos": [], "total_results": 0, "playlist_id": playlist_id}
        
        videos = []
        for item in result["items"]:
            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})
            video_info = {
                "video_id": content_details.get("videoId"),
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "position": snippet.get("position"),
                "publishedAt": snippet.get("publishedAt"),
                "channelTitle": snippet.get("channelTitle"),
                "thumbnailUrl": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "url": f"https://www.youtube.com/watch?v={content_details.get('videoId')}"
            }
            videos.append(video_info)
        
        return {
            "videos": videos,
            "total_results": len(videos),
            "playlist_id": playlist_id
        }
        
    except Exception as e:
        logger.exception(f"Error getting playlist videos: {e}")
        return {"error": f"Failed to get playlist videos: {str(e)}"}

@mcp.tool()
async def extract_video_id_from_url(
    url: Annotated[
        str,
        Field(
            description="YouTube URL to extract video ID from (supports various YouTube URL formats)."
        ),
    ]
) -> Dict[str, Any]:
    """Extract video ID from various YouTube URL formats and validate the video exists."""
    logger.info(f"Extracting video ID from URL: {url}")
    
    try:
        video_id = _extract_video_id(url)
        
        # Validate the video exists by getting basic details
        video_details = await get_video_details(video_id)
        
        if "error" in video_details:
            return {
                "video_id": video_id,
                "url": url,
                "error": "Video ID extracted but video not found or unavailable"
            }
        
        return {
            "video_id": video_id,
            "url": url,
            "title": video_details.get("title"),
            "channel": video_details.get("channelTitle"),
            "duration": video_details.get("duration"),
            "valid": True
        }
        
    except ValueError as e:
        return {
            "url": url,
            "error": f"Could not extract video ID: {str(e)}",
            "valid": False
        }
    except Exception as e:
        logger.exception(f"Error processing URL: {e}")
        return {
            "url": url,
            "error": f"Error processing URL: {str(e)}",
            "valid": False
        }

def main():
    logger.info(f"Starting Youtube MCP Server on port {YOUTUBE_MCP_SERVER_PORT} with log level {LOG_LEVEL_ENV}")
    mcp.run(transport="streamable-http",
        host="0.0.0.0",
        port=YOUTUBE_MCP_SERVER_PORT,
        log_level=LOG_LEVEL_ENV.lower()
    )

if __name__ == "__main__":
    main()