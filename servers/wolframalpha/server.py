import os
import logging
from typing import Dict, Any, List, Optional, Annotated
from dotenv import load_dotenv
import wolframalpha
import httpx
import asyncio
import json
import re
from urllib.parse import quote

from fastmcp import FastMCP
from pydantic import Field
# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

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
    instructions="Comprehensive WolframAlpha integration providing computational queries, mathematical calculations, data analysis, unit conversions, scientific computations, and knowledge retrieval. Supports multiple query types and output formats."
)

logger.info("Initializing WolframAlpha MCP Server")

def _extract_primary_result(res) -> str:
    """Extract the most relevant result from WolframAlpha response."""
    if not hasattr(res, 'pods') or not res.pods:
        return "No result found"
    
    # Look for specific pod types that typically contain the main answer
    priority_pods = ['Result', 'Solution', 'Answer', 'Value', 'Decimal approximation']
    
    for pod in res.pods:
        if hasattr(pod, 'title') and pod.title in priority_pods:
            if hasattr(pod, 'subpods') and pod.subpods:
                for subpod in pod.subpods:
                    if hasattr(subpod, 'plaintext') and subpod.plaintext:
                        return subpod.plaintext.strip()
    
    # If no priority pods found, return the first meaningful result
    for pod in res.pods:
        if hasattr(pod, 'subpods') and pod.subpods:
            for subpod in pod.subpods:
                if hasattr(subpod, 'plaintext') and subpod.plaintext:
                    text = subpod.plaintext.strip()
                    if len(text) > 0 and text != "Input interpretation:":
                        return text
    
    return "Result found but no text available"

def _format_mathematical_result(res) -> Dict[str, Any]:
    """Format mathematical computation results."""
    result = {"has_mathematical_content": False, "calculations": []}
    
    if not hasattr(res, 'pods') or not res.pods:
        return result
    
    for pod in res.pods:
        if hasattr(pod, 'title') and hasattr(pod, 'subpods'):
            # Check if this pod contains mathematical content
            math_keywords = ['Result', 'Solution', 'Plot', 'Derivative', 'Integral', 'Equation', 'Graph']
            if any(keyword in pod.title for keyword in math_keywords):
                result["has_mathematical_content"] = True
                
                pod_data = {"title": pod.title, "content": []}
                for subpod in pod.subpods:
                    subpod_info = {}
                    if hasattr(subpod, 'plaintext') and subpod.plaintext:
                        subpod_info["text"] = subpod.plaintext
                    if hasattr(subpod, 'img') and subpod.img and hasattr(subpod.img, 'src'):
                        subpod_info["image_url"] = subpod.img.src
                    if subpod_info:
                        pod_data["content"].append(subpod_info)
                
                if pod_data["content"]:
                    result["calculations"].append(pod_data)
    
    return result

async def _make_wolfram_request(query: str, timeout: float = 30.0) -> str:
    """Make a direct HTTP request to WolframAlpha API to bypass library header issues."""
    url = "https://api.wolframalpha.com/v2/query"
    params = {
        "appid": WOLFRAMALPHA_APP_ID,
        "input": query,
        "scantimeout": "15.0",
        "podtimeout": "15.0",
        "plaintext": "true"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.text

def _extract_result_from_xml(response_text):
    """Extract meaningful result from WolframAlpha XML response."""
    try:
        import xml.etree.ElementTree as ET
        
        # Parse the XML response
        root = ET.fromstring(response_text)
        
        # Look for pods with plaintext results
        priority_pod_titles = ['Result', 'Solution', 'Answer', 'Value', 'Decimal approximation', 'Definition']
        
        # First, try to find priority pods
        for pod in root.findall('.//pod'):
            title = pod.get('title', '')
            if title in priority_pod_titles:
                for subpod in pod.findall('.//subpod'):
                    plaintext = subpod.find('plaintext')
                    if plaintext is not None and plaintext.text:
                        return plaintext.text.strip()
        
        # If no priority pods found, return the first meaningful result
        for pod in root.findall('.//pod'):
            title = pod.get('title', '')
            # Skip input interpretation pods
            if 'Input' not in title and 'interpretation' not in title.lower():
                for subpod in pod.findall('.//subpod'):
                    plaintext = subpod.find('plaintext')
                    if plaintext is not None and plaintext.text:
                        text = plaintext.text.strip()
                        if len(text) > 0:
                            return text
        
        return "No meaningful result found"
    except Exception as e:
        logger.error(f"Error parsing WolframAlpha response: {e}")
        return f"Error parsing response: {str(e)}"

def _extract_comprehensive_data(response_text):
    """Extract comprehensive data structure from WolframAlpha XML response for calculate_math function."""
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response_text)
        
        calculations = []
        primary_result = "No result found"
        
        # Extract all pods with meaningful content
        for pod in root.findall('.//pod'):
            title = pod.get('title', '')
            if title and 'Input' not in title:
                pod_content = []
                for subpod in pod.findall('.//subpod'):
                    plaintext = subpod.find('plaintext')
                    if plaintext is not None and plaintext.text:
                        text = plaintext.text.strip()
                        if text:
                            pod_content.append({"text": text})
                
                if pod_content:
                    calculations.append({
                        "title": title,
                        "content": pod_content
                    })
                    
                    # Set primary result from priority pods
                    if title in ['Result', 'Solution', 'Answer', 'Value', 'Decimal approximation']:
                        primary_result = pod_content[0]["text"]
        
        return {
            "primary_result": primary_result,
            "success": len(calculations) > 0,
            "calculations": calculations
        }
    except Exception as e:
        logger.error(f"Error extracting comprehensive data: {e}")
        return {
            "primary_result": f"Error: {str(e)}",
            "success": False,
            "calculations": []
        }

@mcp.tool()
async def calculate_math(
    expression: Annotated[
        str,
        Field(description="Mathematical expression to calculate (e.g., '2+2', 'sqrt(16)', 'integrate x^2 dx')")
    ]
) -> Dict[str, Any]:
    """
    Perform mathematical calculations and return formatted results.
    Optimized for mathematical expressions, equations, and computations.
    """
    logger.info(f"Tool 'calculate_math' called with expression: '{expression}'")
    
    try:
        # Use direct HTTP request to bypass wolframalpha library header issues
        data = await _make_wolfram_request(expression)
        result = _extract_comprehensive_data(data)
        
        return {
            "expression": expression,
            "primary_result": result["primary_result"],
            "success": result["success"],
            "mathematical_analysis": {
                "has_mathematical_content": result["success"],
                "calculations": result["calculations"]
            },
            "has_visual_elements": False  # XML API doesn't include images by default
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in calculate_math: {e}")
        logger.error(f"Full traceback: {error_details}")
        return {"error": f"Mathematical calculation failed: {str(e)} | Details: {error_details[:200]}", "expression": expression}

@mcp.tool()
async def convert_units(
    value: Annotated[
        str,
        Field(description="Value with unit to convert (e.g., '100 kilometers', '5 pounds', '32 fahrenheit')")
    ],
    target_unit: Annotated[
        Optional[str],
        Field(description="Target unit for conversion (optional - if not specified, common conversions will be shown)")
    ] = None
) -> Dict[str, Any]:
    """
    Convert units between different measurement systems.
    Supports length, weight, temperature, currency, and many other unit types.
    """
    if target_unit:
        query = f"{value} to {target_unit}"
    else:
        query = f"convert {value}"
    
    logger.info(f"Tool 'convert_units' called with query: '{query}'")
    
    try:
        # Use direct HTTP request to bypass wolframalpha library header issues
        data = await _make_wolfram_request(query)
        result = _extract_result_from_xml(data)
        
        return {
            "original_value": value,
            "target_unit": target_unit,
            "query": query,
            "conversion_result": result,
            "success": result != "No meaningful result found"
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in convert_units: {e}")
        logger.error(f"Full traceback: {error_details}")
        return {"error": f"Unit conversion failed: {str(e)}", "original_value": value}

@mcp.tool()
async def get_scientific_data(
    topic: Annotated[
        str,
        Field(description="Scientific topic or entity to get data about (e.g., 'hydrogen atom', 'speed of light', 'DNA structure')")
    ]
) -> Dict[str, Any]:
    """
    Retrieve scientific data, constants, properties, and information.
    Useful for chemistry, physics, biology, astronomy, and other scientific domains.
    """
    logger.info(f"Tool 'get_scientific_data' called with topic: '{topic}'")
    
    try:
        # Use direct HTTP request to bypass wolframalpha library header issues
        data = await _make_wolfram_request(topic)
        result = _extract_result_from_xml(data)
        
        return {
            "topic": topic,
            "scientific_data": result,
            "success": result != "No meaningful result found"
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in get_scientific_data: {e}")
        logger.error(f"Full traceback: {error_details}")
        return {"error": f"Scientific data retrieval failed: {str(e)}", "topic": topic}

@mcp.tool()
async def solve_equation(
    equation: Annotated[
        str,
        Field(description="Equation to solve (e.g., 'x^2 + 5x + 6 = 0', '2x + 3 = 7', 'sin(x) = 0.5')")
    ]
) -> Dict[str, Any]:
    """
    Solve mathematical equations and return solutions with steps when available.
    """
    query = f"solve {equation}"
    logger.info(f"Tool 'solve_equation' called with equation: '{equation}'")
    
    try:
        # Use direct HTTP request to bypass wolframalpha library header issues
        data = await _make_wolfram_request(query)
        result = _extract_result_from_xml(data)
        
        return {
            "equation": equation,
            "solution": result,
            "success": result != "No meaningful result found"
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in solve_equation: {e}")
        logger.error(f"Full traceback: {error_details}")
        return {"error": f"Equation solving failed: {str(e)}", "equation": equation}

@mcp.tool()
async def get_statistical_analysis(
    data_description: Annotated[
        str,
        Field(description="Description of data or statistical query (e.g., 'mean of 1,2,3,4,5', 'normal distribution', 'regression analysis')")
    ]
) -> Dict[str, Any]:
    """
    Perform statistical analysis and data computations.
    Supports descriptive statistics, probability distributions, and statistical tests.
    """
    logger.info(f"Tool 'get_statistical_analysis' called with: '{data_description}'")
    
    try:
        # Use direct HTTP request to bypass wolframalpha library header issues
        data = await _make_wolfram_request(data_description)
        result = _extract_result_from_xml(data)
        
        return {
            "query": data_description,
            "statistical_analysis": result,
            "success": result != "No meaningful result found"
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in get_statistical_analysis: {e}")
        logger.error(f"Full traceback: {error_details}")
        return {"error": f"Statistical analysis failed: {str(e)}", "query": data_description}

@mcp.tool()
async def get_definition_and_examples(
    term: Annotated[
        str,
        Field(description="Term or concept to get definition and examples for (e.g., 'derivative', 'photosynthesis', 'inflation')")
    ]
) -> Dict[str, Any]:
    """
    Get definitions, explanations, and examples for terms and concepts.
    Useful for educational purposes and understanding complex topics.
    """
    query = f"define {term}"
    logger.info(f"Tool 'get_definition_and_examples' called with term: '{term}'")
    
    try:
        # Use direct HTTP request to bypass wolframalpha library header issues
        data = await _make_wolfram_request(query)
        result = _extract_result_from_xml(data)
        
        return {
            "term": term,
            "definition": result,
            "success": result != "No meaningful result found"
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in get_definition_and_examples: {e}")
        logger.error(f"Full traceback: {error_details}")
        return {"error": f"Definition retrieval failed: {str(e)}", "term": term}

@mcp.tool()
async def query_wolfram_alpha(
    query: Annotated[
        str,
        Field(description="General query to send to WolframAlpha (use specialized tools for math, units, science, etc. when possible)")
    ],
    include_pods: Annotated[
        Optional[str],
        Field(description="Comma-separated list of pod IDs to include in results")
    ] = None,
    exclude_pods: Annotated[
        Optional[str],
        Field(description="Comma-separated list of pod IDs to exclude from results")
    ] = None,
    plaintext: Annotated[
        bool,
        Field(description="Return results in plain text format (default: False for rich content)")
    ] = False
) -> Dict[str, Any]:
    """
    General-purpose WolframAlpha query tool. For better results, consider using specialized tools:
    - calculate_math() for mathematical expressions
    - convert_units() for unit conversions  
    - get_scientific_data() for scientific information
    - solve_equation() for solving equations
    - get_statistical_analysis() for statistics
    - get_definition_and_examples() for definitions
    
    This tool provides access to the full WolframAlpha response with all available pods.
    """
    logger.info(f"MCP Tool 'query_wolfram_alpha' called with query: '{query}'")
    logger.debug(f"Parameters - include_pods: {include_pods}, exclude_pods: {exclude_pods}, plaintext: {plaintext}")

    additional_params = {}
    if include_pods:
        additional_params['includepodid'] = include_pods
    if exclude_pods:
        additional_params['excludepodid'] = exclude_pods

    try:
        # Use direct HTTP request to bypass wolframalpha library header issues
        data = await _make_wolfram_request(query)
        result = _extract_result_from_xml(data)
        
        return {
            "query": query,
            "result": result,
            "success": result != "No meaningful result found"
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in query_wolfram_alpha: {e}")
        logger.error(f"Full traceback: {error_details}")
        return {"error": f"Wolfram Alpha query failed: {str(e)}", "query": query}

def main():
    logger.info(f"Starting WolframAlpha MCP Server on port {WOLFRAMALPHA_MCP_SERVER_PORT} with log level {LOG_LEVEL_ENV}")
    mcp.run(transport="streamable-http",
        host="0.0.0.0",
        port=WOLFRAMALPHA_MCP_SERVER_PORT,
        log_level=LOG_LEVEL_ENV.lower()
    )

if __name__ == "__main__":
    main()