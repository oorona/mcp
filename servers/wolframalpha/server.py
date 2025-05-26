import os
import logging
from typing import Dict, Any, List # Ensure List is imported
from dotenv import load_dotenv
import wolframalpha
import httpx # For specific exception handling
import asyncio # For asyncio.TimeoutError


from fastmcp import FastMCP
# Load environment variables from .env file
load_dotenv()

# --- Logging Configuration ---
DEFAULT_LOG_LEVEL = "INFO"
LOG_LEVEL_ENV = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
numeric_log_level = getattr(logging, LOG_LEVEL_ENV, logging.INFO)
if not isinstance(numeric_log_level, int):
    print(f"Warning: Invalid LOG_LEVEL '{LOG_LEVEL_ENV}'. Defaulting to '{DEFAULT_LOG_LEVEL}'.")
    numeric_log_level = getattr(logging, DEFAULT_LOG_LEVEL)

logging.basicConfig(
    level=numeric_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("wolframalpha-mcp-server")

# --- MODIFICATION START: Control Library Log Levels ---
if numeric_log_level > logging.DEBUG: # e.g., if your app is at INFO, WARNING, ERROR
    logging.getLogger("sse_starlette").setLevel(logging.WARNING)
    logging.getLogger("mcp.server.sse").setLevel(logging.WARNING)
# --- MODIFICATION END ---

# Environment variables
WOLFRAMALPHA_APP_ID = os.getenv("WOLFRAMALPHA_APP_ID")
if not WOLFRAMALPHA_APP_ID:
    logger.error("WOLFRAMALPHA_APP_ID environment variable is required and not set.")
    raise ValueError("WOLFRAMALPHA_APP_ID environment variable is required")

WOLFRAMALPHA_MCP_SERVER_PORT = int(os.getenv("WOLFRAMALPHA_MCP_SERVER_PORT", "6700"))

# Initialize Wolfram Alpha client
try:
    wolfram_client = wolframalpha.Client(WOLFRAMALPHA_APP_ID)
    logger.info("Successfully initialized Wolfram Alpha client.")
except Exception as e:
    logger.error(f"Failed to initialize Wolfram Alpha client: {e}")
    raise

# Initialize FastMCP
mcp = FastMCP(
    name="WolframAlpha",
    instructions="Query the Wolfram Alpha API. Useful for computation, data analysis, and general knowledge."
    )

logger.info("Initializing WolframAlpha MCP Server")

@mcp.tool()
async def query_wolfram_alpha(
    query: str,
    include_pods: str = None,
    exclude_pods: str = None,
    plaintext: bool = False # This is the parameter from our MCP tool
) -> Dict[str, Any]:
    """
    Sends a query to the Wolfram Alpha API using asynchronous 'aquery' and returns the results.
    Uses the library's 'plaintext' parameter to control formatting and handles errors using httpx exceptions.
    """
    logger.info(f"MCP Tool 'query_wolfram_alpha' called with query: '{query}'")
    logger.debug(f"Parameters - include_pods: {include_pods}, exclude_pods: {exclude_pods}, plaintext: {plaintext}")

    additional_params = {}
    if include_pods:
        additional_params['includepodid'] = include_pods
    if exclude_pods:
        additional_params['excludepodid'] = exclude_pods

    try:
        # Use the library's own 'plaintext' parameter.
        # If plaintext=True, library sets API format=plaintext.
        # If plaintext=False, library does not set API format from this, API uses defaults (with output=xml).
        res = await wolfram_client.aquery(
            query,
            scantimeout=10.0,
            podtimeout=10.0,
            plaintext=plaintext,  # Pass our tool's plaintext variable directly here
            **additional_params
        )

        # --- Start Result Processing ---
        if not hasattr(res, 'pods') or not res.pods:
            logger.warning(f"Wolfram Alpha returned no pods for query: '{query}'")
            primary_result_text = "No definitive result found."
            if hasattr(res, 'success') and res.success and hasattr(res, 'results'):
                results_list = list(res.results)
                if len(results_list) > 0:
                    first_result = results_list[0]
                    primary_result_text = first_result.text if hasattr(first_result, 'text') else "Result found, but no text."
            elif hasattr(res, 'didyoumeans') and res.didyoumeans:
                try:
                    suggestions = [item['val'] for item in res.didyoumeans if isinstance(item, dict) and 'val' in item]
                    if suggestions:
                         primary_result_text = f"Did you mean: {', '.join(suggestions)}?"
                except TypeError:
                    logger.warning("Could not parse 'didyoumeans' suggestions.")
            return {
                "query": query,
                "info": "Wolfram Alpha did not return specific pods or direct results.",
                "primary_result": primary_result_text,
                "success": res.success if hasattr(res, 'success') else False
            }

        output_pods = []
        if hasattr(res, 'pods'):
            for pod in res.pods:
                pod_title = pod.title if hasattr(pod, 'title') else "Untitled Pod"
                pod_id_val = pod.id if hasattr(pod, 'id') else None # Renamed to avoid conflict with id()
                pod_scanner = pod.scanner if hasattr(pod, 'scanner') else None
                pod_data = {"title": pod_title, "id": pod_id_val, "scanner": pod_scanner, "subpods": []}

                if hasattr(pod, 'subpods'):
                    for subpod in pod.subpods:
                        subpod_content = {}
                        if hasattr(subpod, 'plaintext') and subpod.plaintext:
                            subpod_content["plaintext"] = subpod.plaintext
                        if hasattr(subpod, 'img') and subpod.img and hasattr(subpod.img, 'src'):
                             subpod_content["image_url"] = subpod.img.src
                        if hasattr(subpod, 'mathml') and subpod.mathml:
                            subpod_content["mathml"] = subpod.mathml
                        if hasattr(subpod, 'title') and subpod.title:
                             subpod_content["title"] = subpod.title
                        pod_data["subpods"].append(subpod_content)
                output_pods.append(pod_data)
        
        logger.info(f"Successfully processed Wolfram Alpha query: '{query}'")
        return {
            "query": query,
            "success": res.success if hasattr(res, 'success') else False,
            "pods": output_pods,
            "data_types": res.datatypes if hasattr(res, 'datatypes') else "",
            "timed_out_pods": res.timedoutpods if hasattr(res, 'timedoutpods') else "",
            "warnings": [w.text for w in res.warnings if hasattr(w, 'text')] if hasattr(res, 'warnings') and res.warnings else [],
            "assumptions": res.assumptions if hasattr(res, 'assumptions') else None,
            "did_you_means": [item['val'] for item in res.didyoumeans if isinstance(item, dict) and 'val' in item] if hasattr(res, 'didyoumeans') and res.didyoumeans else []
        }
        # --- End Result Processing ---

    except httpx.HTTPStatusError as e:
        response_text = e.response.text if e.response and hasattr(e.response, 'text') else ""
        status_code = e.response.status_code if e.response else "Unknown Status"
        logger.error(f"Wolfram Alpha API HTTP Status Error for query '{query}': {status_code} - {response_text}", exc_info=True)
        return {"error": f"Wolfram Alpha API Error ({status_code}): {response_text}"}
    except httpx.TimeoutException as e:
        logger.error(f"Wolfram Alpha API Timeout for query '{query}': {str(e)}", exc_info=True)
        return {"error": f"Wolfram Alpha query timed out: {str(e)}"}
    except httpx.RequestError as e:
        logger.error(f"Wolfram Alpha API Request Error for query '{query}': {str(e)}", exc_info=True)
        return {"error": f"Wolfram Alpha network/request error: {str(e)}"}
    except asyncio.TimeoutError as e:
        logger.error(f"Asyncio Timeout Error during Wolfram Alpha query operation '{query}': {str(e)}", exc_info=True)
        return {"error": f"Wolfram Alpha query operation timed out: {str(e)}"}
    except ValueError as e: # Catching the specific ValueError from the library for API errors like 2500
        logger.error(f"Wolfram Alpha library Value Error (likely API error in response) for query '{query}': {str(e)}", exc_info=True)
        return {"error": f"Wolfram Alpha API processing error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error of type {type(e).__name__} processing Wolfram Alpha query '{query}': {e}")
        return {"error": f"An unexpected error occurred ({type(e).__name__}): {str(e)}"}

def main():
    logger.info(f"Starting WolframAlpha MCP Server on port {WOLFRAMALPHA_MCP_SERVER_PORT} with log level {LOG_LEVEL_ENV}")
    mcp.run(transport="streamable-http",
        host="0.0.0.0",
        port=WOLFRAMALPHA_MCP_SERVER_PORT,
        log_level=LOG_LEVEL_ENV.lower()
    )

if __name__ == "__main__":
    main()