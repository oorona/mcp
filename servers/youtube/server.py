import os
import logging
import re # Not strictly used in the final version, but often kept
from typing import Any, Dict, Annotated
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import aiohttp
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

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
YOUTUBE_MCP_SERVER_PORT = int(os.getenv("YOUTUBE_MCP_SERVER_PORT", "6000"))

mcp = FastMCP(
    "Youtube",
    instructions="Retrieve the transcript or video details for a given YouTube video. Prioritizes manual transcripts, then auto-generated transcripts.",
    port=YOUTUBE_MCP_SERVER_PORT,
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
async def get_youtube_video_transcript(
    url: Annotated[
        str,
        Field(
            description="The URL of the YouTube video to retrieve the transcript/subtitles for. (e.g. https://www.youtube.com/watch?v=dQw4w9WgXcQ)"
        ),
    ],
) -> Dict[str, Any]:
    """
    Retrieve the transcript or video details for a given YouTube video.
    Tries to fetch a manual transcript first (preferring English), then an
    auto-generated transcript (preferring English). If no transcript is found,
    or if transcripts are disabled, it falls back to video details.
    The 'start' time in the transcript is formatted as MM:SS or HH:MM:SS.
    """
    logger.info(f"MCP Tool 'get_youtube_video_transcript' called with URL: {url}")
    try:
        video_id = _extract_video_id(url)
        logger.info(f"Successfully extracted video_id: {video_id} from URL: {url}")
        
        transcript_to_fetch = None
        preferred_languages = ['en']

        try:
            transcript_list = youtube_transcript_api.list_transcripts(video_id)
            logger.debug(f"Available transcripts for {video_id}: manual={list(transcript_list._manually_created_transcripts.keys()) if transcript_list._manually_created_transcripts else []}, generated={list(transcript_list._generated_transcripts.keys()) if transcript_list._generated_transcripts else []}")

            try:
                transcript_to_fetch = transcript_list.find_manually_created_transcript(preferred_languages)
                logger.info(f"Found manually created transcript in a preferred language for {video_id} ({transcript_to_fetch.language_code}).")
            except NoTranscriptFound:
                logger.info(f"No manually created transcript in preferred languages for {video_id}. Checking for any manual transcript.")
                manual_langs = [lang for lang in transcript_list._manually_created_transcripts]
                if manual_langs:
                    try:
                        transcript_to_fetch = transcript_list.find_manually_created_transcript([manual_langs[0]])
                        logger.info(f"Found manually created transcript in language: {manual_langs[0]} for {video_id}.")
                    except NoTranscriptFound:
                         logger.info(f"Could not fetch first available manual transcript for {video_id}.")

            if not transcript_to_fetch:
                logger.info(f"No manual transcript found. Checking for auto-generated transcript in preferred languages for {video_id}.")
                try:
                    transcript_to_fetch = transcript_list.find_generated_transcript(preferred_languages)
                    logger.info(f"Found auto-generated transcript in a preferred language for {video_id} ({transcript_to_fetch.language_code}).")
                except NoTranscriptFound:
                    logger.info(f"No auto-generated transcript in preferred languages for {video_id}. Checking for any auto-generated transcript.")
                    generated_langs = [lang for lang in transcript_list._generated_transcripts]
                    if generated_langs:
                        try:
                            transcript_to_fetch = transcript_list.find_generated_transcript([generated_langs[0]])
                            logger.info(f"Found auto-generated transcript in language: {generated_langs[0]} for {video_id}.")
                        except NoTranscriptFound:
                            logger.info(f"Could not fetch first available auto-generated transcript for {video_id}.")
            
            if transcript_to_fetch:
                logger.debug(f"Fetching transcript for {video_id}, type: {'manual' if not transcript_to_fetch.is_generated else 'auto-generated'}, lang: {transcript_to_fetch.language_code}")
                raw_transcript_data = transcript_to_fetch.fetch()

                # --- FIX for 'FetchedTranscriptSnippet' object is not a mapping ---
                formatted_transcript = []
                for segment_object in raw_transcript_data:
                    try:
                        # Access data using attributes, assuming the object has .text, .start, .duration
                        formatted_segment = {
                            'text': segment_object.text,
                            'start': _format_time(segment_object.start), # Use attribute .start
                            'duration': segment_object.duration  # Use attribute .duration
                        }
                        formatted_transcript.append(formatted_segment)
                    except AttributeError as e:
                        logger.error(f"Error accessing attributes on a transcript segment object: {e}. Segment: {segment_object}")
                        # Add a placeholder or skip this segment if it's malformed
                        formatted_transcript.append({
                            'text': '[Error processing segment data]',
                            'start': '00:00',
                            'duration': 0
                        })
                # --- End of FIX ---
                
                logger.info(f"Successfully fetched and formatted transcript for {video_id}.")
                return {
                    "video_id": video_id,
                    "transcript_type": "manual" if not transcript_to_fetch.is_generated else "auto-generated",
                    "language_code": transcript_to_fetch.language_code,
                    "transcript": formatted_transcript
                }
            else:
                logger.warning(f"No transcript (manual or auto-generated) found for video_id: {video_id}. Falling back to video details.")
                video_details = await get_video_details(video_id)
                return {
                    "video_id": video_id,
                    "video_details": video_details,
                    "info": "No transcript (manual or auto-generated) was found for this video."
                }

        except TranscriptsDisabled:
            logger.warning(f"Transcripts are disabled for video_id: {video_id}. Falling back to video details.")
            video_details = await get_video_details(video_id)
            return {
                "video_id": video_id,
                "video_details": video_details,
                "error": "Transcripts are disabled for this video."
            }
        except Exception as transcript_error: # Catch other potential errors from transcript fetching/processing
            logger.exception(f"Error processing transcript for video_id {video_id}: {transcript_error}. Falling back to video details.") # Changed to logger.exception to get traceback
            video_details = await get_video_details(video_id)
            return {
                "video_id": video_id,
                "video_details": video_details,
                "error": f"An error occurred while trying to fetch or process the transcript: {str(transcript_error)}"
            }
    except ValueError as e: # From _extract_video_id
        logger.error(f"Invalid YouTube URL provided: {url}. Error: {e}")
        return {
            "error": f"Invalid YouTube URL: {str(e)}"
        }
    except Exception as e: # Catch-all for other unexpected errors in the tool's main try block
        logger.exception(f"Unexpected error processing video URL {url}: {e}")
        return {
            "error": f"Failed to process request: {str(e)}"
        }

def main():
    logger.info(f"Starting Youtube MCP Server on port {YOUTUBE_MCP_SERVER_PORT} with log level {LOG_LEVEL_ENV}")
    mcp.run(transport="sse")

if __name__ == "__main__":
    main()