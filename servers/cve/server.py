import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
import httpx
from pydantic import Field, BaseModel
from typing_extensions import Annotated

from fastmcp import FastMCP

# Load environment variables from .env file if present
load_dotenv()

# --- Logging Configuration ---
DEFAULT_LOG_LEVEL = "INFO"
LOG_LEVEL_ENV = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
numeric_log_level = getattr(logging, LOG_LEVEL_ENV, logging.INFO)
if not isinstance(numeric_log_level, int):
    print(f"Warning: Invalid LOG_LEVEL '{LOG_LEVEL_ENV}'. Defaulting to '{DEFAULT_LOG_LEVEL}'.")
    numeric_log_level = logging.INFO

logging.basicConfig(
    level=numeric_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cve-mcp-server")

# Silence verbose libraries when not in debug mode
if numeric_log_level > logging.DEBUG:
    logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Environment Variables ---
NVD_API_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_API_KEY = os.getenv("NVD_API_KEY")  # Optional, increases rate limits
CVE_MCP_PORT = int(os.getenv("CVE_MCP_PORT", "6900"))

# --- MCP Server Initialization ---
mcp = FastMCP(
    name="cve", 
    instructions=(
        "This server provides tools to retrieve CVE (Common Vulnerabilities and Exposures) information "
        "from the National Vulnerability Database (NVD). It can search for CVEs by various criteria "
        "including severity levels, date ranges, specific CVE IDs, and affected products/vendors. "
        "Use this server to get current vulnerability information, analyze security threats, "
        "and research specific vulnerabilities."
    )
)

# --- Pydantic Models for NVD API ---
class CVEMetrics(BaseModel):
    baseScore: Optional[float] = None
    baseSeverity: Optional[str] = None
    vectorString: Optional[str] = None

class CVEDescription(BaseModel):
    lang: str
    value: str

class CVEReference(BaseModel):
    url: str
    source: Optional[str] = None

class CVEVulnerability(BaseModel):
    id: str
    published: Optional[str] = None
    lastModified: Optional[str] = None
    vulnStatus: Optional[str] = None
    descriptions: List[CVEDescription] = []
    references: List[CVEReference] = []

# --- Helper Functions ---
async def _make_nvd_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """Make a request to the NVD CVE API with proper headers and error handling"""
    headers = {
        "User-Agent": "CVE-MCP-Server/1.0"
    }
    
    # Add API key if available (increases rate limits)
    if NVD_API_KEY:
        headers["apiKey"] = NVD_API_KEY
        
    logger.debug(f"Making NVD API request with params: {params}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                NVD_API_BASE_URL,
                params=params,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"NVD API request failed: {e.response.status_code} {e.response.text}")
            if e.response.status_code == 403:
                raise RuntimeError("NVD API access denied. Consider adding an API key or reducing request frequency.")
            elif e.response.status_code == 429:
                raise RuntimeError("NVD API rate limit exceeded. Please wait before making more requests.")
            else:
                raise RuntimeError(f"NVD API Error ({e.response.status_code}): {e.response.text}")
                
        except httpx.RequestError as e:
            logger.error(f"Network error connecting to NVD API: {e}")
            raise RuntimeError(f"Network error connecting to NVD API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during NVD API request: {e}")
            raise RuntimeError(f"Unexpected error during API call: {str(e)}")

def _extract_cve_summary(cve_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key information from a CVE record for summary display"""
    cve = cve_data.get("cve", {})
    
    # Get primary description (English first)
    description = "No description available"
    descriptions = cve.get("descriptions", [])
    for desc in descriptions:
        if desc.get("lang") == "en":
            description = desc.get("value", description)
            break
    if description == "No description available" and descriptions:
        description = descriptions[0].get("value", description)
    
    # Extract CVSS metrics
    metrics = cve.get("metrics", {})
    cvss_v3 = metrics.get("cvssMetricV31", []) or metrics.get("cvssMetricV30", [])
    cvss_v2 = metrics.get("cvssMetricV2", [])
    
    base_score = None
    severity = None
    vector_string = None
    
    # Prefer CVSS v3 over v2
    if cvss_v3:
        cvss_data = cvss_v3[0].get("cvssData", {})
        base_score = cvss_data.get("baseScore")
        severity = cvss_v3[0].get("baseSeverity")
        vector_string = cvss_data.get("vectorString")
    elif cvss_v2:
        cvss_data = cvss_v2[0].get("cvssData", {})
        base_score = cvss_data.get("baseScore")
        severity = cvss_v2[0].get("baseSeverity")
        vector_string = cvss_data.get("vectorString")
    
    # Get references (limit to first 5 for summary)
    references = []
    for ref in cve.get("references", [])[:5]:
        references.append({
            "url": ref.get("url"),
            "source": ref.get("source")
        })
    
    return {
        "id": cve.get("id"),
        "description": description,
        "published": cve.get("published"),
        "lastModified": cve.get("lastModified"),
        "vulnStatus": cve.get("vulnStatus"),
        "baseScore": base_score,
        "severity": severity,
        "vectorString": vector_string,
        "references": references,
        "referenceCount": len(cve.get("references", []))
    }

# --- MCP Tools ---
@mcp.tool()
async def get_recent_cves(
    limit: Annotated[
        Optional[int], 
        Field(description="Number of CVEs to retrieve (max 2000, default 20)")
    ] = 20,
    days_back: Annotated[
        Optional[int],
        Field(description="How many days back to search (default 7 days)")
    ] = 7
) -> Dict[str, Any]:
    """
    Retrieve recent CVEs from the National Vulnerability Database.
    Returns CVEs published or modified within the specified number of days.
    """
    logger.info(f"Tool 'get_recent_cves' called with limit: {limit}, days_back: {days_back}")
    
    if limit and (limit < 1 or limit > 2000):
        return {"error": "limit must be between 1 and 2000"}
    
    if days_back and days_back < 1:
        return {"error": "days_back must be at least 1"}
    
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            "resultsPerPage": limit,
            "lastModStartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "lastModEndDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000")
        }
        
        response = await _make_nvd_request(params)
        
        # Extract and summarize CVEs
        vulnerabilities = response.get("vulnerabilities", [])
        cve_summaries = []
        
        for vuln in vulnerabilities:
            summary = _extract_cve_summary(vuln)
            cve_summaries.append(summary)
        
        logger.info(f"Successfully retrieved {len(cve_summaries)} recent CVEs")
        
        return {
            "totalResults": response.get("totalResults", 0),
            "resultsPerPage": response.get("resultsPerPage", 0),
            "startIndex": response.get("startIndex", 0),
            "timestamp": response.get("timestamp"),
            "searchPeriod": f"{days_back} days",
            "cves": cve_summaries
        }
        
    except RuntimeError as e:
        logger.error(f"NVD API error in get_recent_cves: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error in get_recent_cves: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_cve_details(
    cve_id: Annotated[
        str,
        Field(description="The CVE ID to retrieve (e.g., 'CVE-2021-44228')")
    ]
) -> Dict[str, Any]:
    """
    Retrieve detailed information for a specific CVE by its ID.
    Returns comprehensive vulnerability details including CVSS scores, references, and affected products.
    """
    logger.info(f"Tool 'get_cve_details' called with cve_id: {cve_id}")
    
    # Validate CVE ID format
    if not cve_id.upper().startswith("CVE-"):
        return {"error": "CVE ID must start with 'CVE-' (e.g., 'CVE-2021-44228')"}
    
    try:
        params = {
            "cveId": cve_id.upper()
        }
        
        response = await _make_nvd_request(params)
        
        vulnerabilities = response.get("vulnerabilities", [])
        if not vulnerabilities:
            logger.warning(f"No CVE found with ID: {cve_id}")
            return {"error": f"No CVE found with ID: {cve_id}"}
        
        # Get the full CVE details
        cve_data = vulnerabilities[0]
        cve = cve_data.get("cve", {})
        
        # Extract all descriptions
        descriptions = []
        for desc in cve.get("descriptions", []):
            descriptions.append({
                "language": desc.get("lang"),
                "value": desc.get("value")
            })
        
        # Extract all CVSS metrics
        metrics = cve.get("metrics", {})
        cvss_metrics = {
            "cvssV31": metrics.get("cvssMetricV31", []),
            "cvssV30": metrics.get("cvssMetricV30", []),
            "cvssV2": metrics.get("cvssMetricV2", [])
        }
        
        # Extract weaknesses/CWEs
        weaknesses = []
        for weakness in cve.get("weaknesses", []):
            for desc in weakness.get("description", []):
                weaknesses.append({
                    "source": weakness.get("source"),
                    "type": weakness.get("type"),
                    "description": desc.get("value")
                })
        
        # Extract configurations (affected products)
        configurations = cve.get("configurations", [])
        
        # Extract all references
        references = []
        for ref in cve.get("references", []):
            references.append({
                "url": ref.get("url"),
                "source": ref.get("source"),
                "tags": ref.get("tags", [])
            })
        
        logger.info(f"Successfully retrieved details for {cve_id}")
        
        return {
            "id": cve.get("id"),
            "sourceIdentifier": cve.get("sourceIdentifier"),
            "published": cve.get("published"),
            "lastModified": cve.get("lastModified"),
            "vulnStatus": cve.get("vulnStatus"),
            "descriptions": descriptions,
            "cvssMetrics": cvss_metrics,
            "weaknesses": weaknesses,
            "configurations": configurations,
            "references": references,
            "cveTags": cve.get("cveTags", [])
        }
        
    except RuntimeError as e:
        logger.error(f"NVD API error in get_cve_details: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error in get_cve_details: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def search_cves_by_severity(
    severity: Annotated[
        str,
        Field(description="CVSS severity level: 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'")
    ],
    limit: Annotated[
        Optional[int],
        Field(description="Number of CVEs to retrieve (max 2000, default 50)")
    ] = 50,
    days_back: Annotated[
        Optional[int],
        Field(description="How many days back to search (default 30 days)")
    ] = 30
) -> Dict[str, Any]:
    """
    Search for CVEs by CVSS severity level within a specified time period.
    Severity levels: LOW (0.1-3.9), MEDIUM (4.0-6.9), HIGH (7.0-8.9), CRITICAL (9.0-10.0).
    """
    logger.info(f"Tool 'search_cves_by_severity' called with severity: {severity}")
    
    severity = severity.upper()
    if severity not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        return {"error": "Severity must be one of: LOW, MEDIUM, HIGH, CRITICAL"}
    
    if limit and (limit < 1 or limit > 2000):
        return {"error": "limit must be between 1 and 2000"}
    
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            "resultsPerPage": limit,
            "lastModStartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "lastModEndDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "cvssV3Severity": severity
        }
        
        response = await _make_nvd_request(params)
        
        # Extract and summarize CVEs
        vulnerabilities = response.get("vulnerabilities", [])
        cve_summaries = []
        
        for vuln in vulnerabilities:
            summary = _extract_cve_summary(vuln)
            # Only include if it matches the requested severity
            if summary.get("severity") == severity:
                cve_summaries.append(summary)
        
        logger.info(f"Successfully retrieved {len(cve_summaries)} CVEs with severity {severity}")
        
        return {
            "totalResults": response.get("totalResults", 0),
            "resultsPerPage": response.get("resultsPerPage", 0),
            "startIndex": response.get("startIndex", 0),
            "timestamp": response.get("timestamp"),
            "searchCriteria": {
                "severity": severity,
                "searchPeriod": f"{days_back} days"
            },
            "cves": cve_summaries
        }
        
    except RuntimeError as e:
        logger.error(f"NVD API error in search_cves_by_severity: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error in search_cves_by_severity: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def search_cves_by_keyword(
    keyword: Annotated[
        str,
        Field(description="Keyword to search in CVE descriptions (e.g., 'apache', 'mysql', 'windows')")
    ],
    limit: Annotated[
        Optional[int],
        Field(description="Number of CVEs to retrieve (max 2000, default 50)")
    ] = 50,
    days_back: Annotated[
        Optional[int],
        Field(description="How many days back to search (default 30 days, 0 for all time)")
    ] = 30
) -> Dict[str, Any]:
    """
    Search for CVEs containing a specific keyword in their description.
    Useful for finding vulnerabilities related to specific products, vendors, or technologies.
    """
    logger.info(f"Tool 'search_cves_by_keyword' called with keyword: {keyword}")
    
    if not keyword or len(keyword.strip()) < 2:
        return {"error": "Keyword must be at least 2 characters long"}
    
    if limit and (limit < 1 or limit > 2000):
        return {"error": "limit must be between 1 and 2000"}
    
    try:
        params = {
            "resultsPerPage": limit,
            "keywordSearch": keyword.strip()
        }
        
        # Add date range if specified
        if days_back and days_back > 0:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            params["lastModStartDate"] = start_date.strftime("%Y-%m-%dT%H:%M:%S.000")
            params["lastModEndDate"] = end_date.strftime("%Y-%m-%dT%H:%M:%S.000")
        
        response = await _make_nvd_request(params)
        
        # Extract and summarize CVEs
        vulnerabilities = response.get("vulnerabilities", [])
        cve_summaries = []
        
        for vuln in vulnerabilities:
            summary = _extract_cve_summary(vuln)
            cve_summaries.append(summary)
        
        logger.info(f"Successfully retrieved {len(cve_summaries)} CVEs matching keyword '{keyword}'")
        
        return {
            "totalResults": response.get("totalResults", 0),
            "resultsPerPage": response.get("resultsPerPage", 0),
            "startIndex": response.get("startIndex", 0),
            "timestamp": response.get("timestamp"),
            "searchCriteria": {
                "keyword": keyword,
                "searchPeriod": f"{days_back} days" if days_back > 0 else "all time"
            },
            "cves": cve_summaries
        }
        
    except RuntimeError as e:
        logger.error(f"NVD API error in search_cves_by_keyword: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error in search_cves_by_keyword: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

#@mcp.tool()
async def get_cve_statistics(
    days_back: Annotated[
        Optional[int],
        Field(description="How many days back to analyze (default 30 days)")
    ] = 30
) -> Dict[str, Any]:
    """
    Get statistics about CVEs including counts by severity level and recent trends.
    Provides an overview of the vulnerability landscape.
    """
    logger.info(f"Tool 'get_cve_statistics' called with days_back: {days_back}")
    
    try:
        # Get recent CVEs for analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            "resultsPerPage": 2000,  # Get as many as possible for statistics
            "lastModStartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "lastModEndDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000")
        }
        
        response = await _make_nvd_request(params)
        
        vulnerabilities = response.get("vulnerabilities", [])
        
        # Count by severity
        severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "UNKNOWN": 0}
        
        # Count by status
        status_counts = {}
        
        # Count by year
        year_counts = {}
        
        for vuln in vulnerabilities:
            summary = _extract_cve_summary(vuln)
            
            # Count severity
            severity = summary.get("severity", "UNKNOWN")
            if severity in severity_counts:
                severity_counts[severity] += 1
            else:
                severity_counts["UNKNOWN"] += 1
            
            # Count status
            status = summary.get("vulnStatus", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by year
            published = summary.get("published", "")
            if published:
                year = published[:4]
                year_counts[year] = year_counts.get(year, 0) + 1
        
        # Calculate percentages
        total_cves = len(vulnerabilities)
        severity_percentages = {}
        for severity, count in severity_counts.items():
            if total_cves > 0:
                severity_percentages[severity] = round((count / total_cves) * 100, 1)
            else:
                severity_percentages[severity] = 0.0
        
        logger.info(f"Successfully calculated statistics for {total_cves} CVEs")
        
        return {
            "analysisPeriod": f"{days_back} days",
            "totalCves": total_cves,
            "totalResults": response.get("totalResults", 0),
            "timestamp": response.get("timestamp"),
            "severityBreakdown": {
                "counts": severity_counts,
                "percentages": severity_percentages
            },
            "statusBreakdown": status_counts,
            "yearBreakdown": year_counts,
            "topSeverities": sorted(
                [(k, v) for k, v in severity_counts.items() if k != "UNKNOWN"], 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
        }
        
    except RuntimeError as e:
        logger.error(f"NVD API error in get_cve_statistics: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error in get_cve_statistics: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_product_vulnerability_summary(
    product_name: Annotated[
        str,
        Field(description="Product name to search for (e.g., 'apache', 'mysql', 'windows', 'nginx')")
    ],
    vendor: Annotated[
        Optional[str],
        Field(description="Optional vendor name to refine search (e.g., 'microsoft', 'oracle')")
    ] = None,
    severity_threshold: Annotated[
        Optional[str],
        Field(description="Minimum severity level to include: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL' (default: MEDIUM)")
    ] = "MEDIUM",
    days_back: Annotated[
        Optional[int],
        Field(description="How many days back to analyze (default 365 days)")
    ] = 365
) -> Dict[str, Any]:
    """
    Get a comprehensive vulnerability summary for a specific product including:
    - Total CVE count by severity level
    - Most recent vulnerabilities  
    - Trend analysis over time
    - Critical patches needed
    - Risk assessment
    """
    logger.info(f"Tool 'get_product_vulnerability_summary' called with product: {product_name}, vendor: {vendor}")
    
    if not product_name or len(product_name.strip()) < 2:
        return {"error": "Product name must be at least 2 characters long"}
    
    severity_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    if severity_threshold not in severity_levels:
        return {"error": f"Severity threshold must be one of: {', '.join(severity_levels)}"}
    
    try:
        # Build search query
        search_terms = [product_name.strip()]
        if vendor:
            search_terms.append(vendor.strip())
        keyword = " ".join(search_terms)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Get comprehensive data (use larger page size for analysis)
        params = {
            "resultsPerPage": 2000,
            "keywordSearch": keyword,
            "lastModStartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "lastModEndDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000")
        }
        
        response = await _make_nvd_request(params)
        vulnerabilities = response.get("vulnerabilities", [])
        
        # Analyze vulnerabilities
        severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "UNKNOWN": 0}
        recent_cves = []
        critical_patches = []
        monthly_counts = {}
        total_base_score = 0
        scored_cves = 0
        
        for vuln in vulnerabilities:
            summary = _extract_cve_summary(vuln)
            severity = summary.get("severity", "UNKNOWN")
            base_score = summary.get("baseScore")
            
            # Count by severity
            if severity in severity_counts:
                severity_counts[severity] += 1
            else:
                severity_counts["UNKNOWN"] += 1
            
            # Track base scores for average calculation
            if base_score is not None:
                total_base_score += base_score
                scored_cves += 1
            
            # Collect recent CVEs (last 30 days)
            if summary.get("published"):
                pub_date = summary["published"][:10]  # YYYY-MM-DD
                pub_datetime = datetime.strptime(pub_date, "%Y-%m-%d")
                if (datetime.now() - pub_datetime).days <= 30:
                    recent_cves.append(summary)
                
                # Monthly trend analysis
                month_key = pub_date[:7]  # YYYY-MM
                monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
            
            # Identify critical patches needed (HIGH/CRITICAL from last 90 days)
            if severity in ["HIGH", "CRITICAL"] and summary.get("published"):
                pub_datetime = datetime.strptime(summary["published"][:10], "%Y-%m-%d")
                if (datetime.now() - pub_datetime).days <= 90:
                    critical_patches.append(summary)
        
        # Calculate risk metrics
        total_cves = len(vulnerabilities)
        avg_base_score = round(total_base_score / scored_cves, 2) if scored_cves > 0 else None
        
        # Risk level assessment
        high_critical_count = severity_counts["HIGH"] + severity_counts["CRITICAL"]
        risk_level = "LOW"
        if high_critical_count > 50:
            risk_level = "CRITICAL"
        elif high_critical_count > 20:
            risk_level = "HIGH"
        elif high_critical_count > 5:
            risk_level = "MEDIUM"
        
        # Sort data for output
        recent_cves.sort(key=lambda x: x.get("published", ""), reverse=True)
        critical_patches.sort(key=lambda x: x.get("baseScore", 0), reverse=True)
        
        logger.info(f"Successfully analyzed {total_cves} CVEs for product '{product_name}'")
        
        return {
            "product": product_name,
            "vendor": vendor,
            "analysisPeriod": f"{days_back} days",
            "totalCves": total_cves,
            "riskAssessment": {
                "level": risk_level,
                "averageBaseScore": avg_base_score,
                "highCriticalCount": high_critical_count
            },
            "severityBreakdown": severity_counts,
            "recentCves": recent_cves[:10],  # Last 10 recent CVEs
            "criticalPatchesNeeded": critical_patches[:15],  # Top 15 critical patches
            "monthlyTrend": dict(sorted(monthly_counts.items())[-12:]),  # Last 12 months
            "recommendations": [
                f"Monitor {high_critical_count} HIGH/CRITICAL vulnerabilities",
                f"Prioritize patching {len(critical_patches)} recent high-risk CVEs",
                f"Average CVSS score of {avg_base_score} indicates {'high' if avg_base_score and avg_base_score > 7 else 'moderate'} risk level"
            ] if avg_base_score else []
        }
        
    except RuntimeError as e:
        logger.error(f"NVD API error in get_product_vulnerability_summary: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error in get_product_vulnerability_summary: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

#@mcp.tool()
async def get_cve_trends(
    period: Annotated[
        str,
        Field(description="Trend analysis period: 'weekly', 'monthly', or 'yearly' (default: monthly)")
    ] = "monthly",
    severity_filter: Annotated[
        Optional[str],
        Field(description="Optional severity filter: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'")
    ] = None,
    months_back: Annotated[
        int,
        Field(description="How many months of historical data to analyze (default: 12, max: 24)")
    ] = 12
) -> Dict[str, Any]:
    """
    Analyze CVE publication trends over time including:
    - CVE count over specified periods
    - Severity distribution trends  
    - Peak vulnerability periods
    - Comparison to historical averages
    - Trend direction analysis
    """
    logger.info(f"Tool 'get_cve_trends' called with period: {period}, severity_filter: {severity_filter}")
    
    if period not in ["weekly", "monthly", "yearly"]:
        return {"error": "Period must be one of: weekly, monthly, yearly"}
    
    if severity_filter and severity_filter not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        return {"error": "Severity filter must be one of: LOW, MEDIUM, HIGH, CRITICAL"}
    
    if months_back < 1 or months_back > 24:
        return {"error": "months_back must be between 1 and 24"}
    
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)
        
        params = {
            "resultsPerPage": 2000,
            "lastModStartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "lastModEndDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000")
        }
        
        # Add severity filter if specified
        if severity_filter:
            params["cvssV3Severity"] = severity_filter
        
        response = await _make_nvd_request(params)
        vulnerabilities = response.get("vulnerabilities", [])
        
        # Process data by time periods
        period_data = {}
        severity_trends = {}
        
        for vuln in vulnerabilities:
            summary = _extract_cve_summary(vuln)
            published = summary.get("published")
            severity = summary.get("severity", "UNKNOWN")
            
            if not published:
                continue
                
            # Parse publication date
            pub_date = datetime.strptime(published[:10], "%Y-%m-%d")
            
            # Generate period key based on requested granularity
            if period == "weekly":
                # Get week number (ISO week)
                year, week, _ = pub_date.isocalendar()
                period_key = f"{year}-W{week:02d}"
            elif period == "monthly":
                period_key = pub_date.strftime("%Y-%m")
            else:  # yearly
                period_key = pub_date.strftime("%Y")
            
            # Count CVEs by period
            period_data[period_key] = period_data.get(period_key, 0) + 1
            
            # Track severity trends
            if period_key not in severity_trends:
                severity_trends[period_key] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "UNKNOWN": 0}
            
            if severity in severity_trends[period_key]:
                severity_trends[period_key][severity] += 1
            else:
                severity_trends[period_key]["UNKNOWN"] += 1
        
        # Sort periods chronologically
        sorted_periods = sorted(period_data.keys())
        
        # Calculate statistics
        period_counts = [period_data.get(p, 0) for p in sorted_periods]
        total_cves = sum(period_counts)
        avg_per_period = round(total_cves / len(sorted_periods), 2) if sorted_periods else 0
        
        # Find peaks and trends
        max_period = max(period_data.items(), key=lambda x: x[1]) if period_data else (None, 0)
        min_period = min(period_data.items(), key=lambda x: x[1]) if period_data else (None, 0)
        
        # Calculate trend direction (simple linear trend)
        trend_direction = "stable"
        if len(period_counts) >= 3:
            recent_avg = sum(period_counts[-3:]) / 3
            earlier_avg = sum(period_counts[:3]) / 3
            if recent_avg > earlier_avg * 1.2:
                trend_direction = "increasing"
            elif recent_avg < earlier_avg * 0.8:
                trend_direction = "decreasing"
        
        # Generate insights
        insights = []
        if max_period[1] > avg_per_period * 1.5:
            insights.append(f"Peak vulnerability period: {max_period[0]} with {max_period[1]} CVEs")
        if trend_direction != "stable":
            insights.append(f"CVE publication trend is {trend_direction}")
        
        high_severity_periods = []
        for period_key, severities in severity_trends.items():
            high_critical = severities.get("HIGH", 0) + severities.get("CRITICAL", 0)
            if high_critical > 10:  # Threshold for concerning periods
                high_severity_periods.append((period_key, high_critical))
        
        if high_severity_periods:
            high_severity_periods.sort(key=lambda x: x[1], reverse=True)
            insights.append(f"High-risk periods detected: {len(high_severity_periods)} periods with >10 HIGH/CRITICAL CVEs")
        
        logger.info(f"Successfully analyzed trends for {total_cves} CVEs over {len(sorted_periods)} {period} periods")
        
        return {
            "analysis": {
                "period": period,
                "timeRange": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                "severityFilter": severity_filter,
                "totalCves": total_cves,
                "periodsAnalyzed": len(sorted_periods)
            },
            "trends": {
                "periodData": dict(zip(sorted_periods, period_counts)),
                "averagePerPeriod": avg_per_period,
                "peakPeriod": {"period": max_period[0], "count": max_period[1]},
                "quietPeriod": {"period": min_period[0], "count": min_period[1]},
                "trendDirection": trend_direction
            },
            "severityTrends": {k: severity_trends[k] for k in sorted_periods[-6:]},  # Last 6 periods
            "insights": insights,
            "recommendations": [
                f"Average {avg_per_period} CVEs per {period[:-2]} - monitor for spikes above {avg_per_period * 1.5:.1f}",
                f"Trend is {trend_direction} - {'consider increased monitoring' if trend_direction == 'increasing' else 'maintain current monitoring'}",
                f"Focus on {len(high_severity_periods)} high-severity periods identified" if high_severity_periods else "No concerning high-severity periods detected"
            ]
        }
        
    except RuntimeError as e:
        logger.error(f"NVD API error in get_cve_trends: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error in get_cve_trends: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def get_remediation_info(
    cve_id: Annotated[
        str,
        Field(description="The CVE ID to get remediation information for (e.g., 'CVE-2021-44228')")
    ],
    include_patches: Annotated[
        bool,
        Field(description="Whether to include detailed patch information (default: True)")
    ] = True
) -> Dict[str, Any]:
    """
    Get comprehensive remediation information for a CVE including:
    - Available patches and updates
    - Vendor advisories and links
    - Workarounds and mitigations  
    - Remediation timeline and urgency
    - Configuration changes needed
    """
    logger.info(f"Tool 'get_remediation_info' called with cve_id: {cve_id}")
    
    # Validate CVE ID format
    if not cve_id.upper().startswith("CVE-"):
        return {"error": "CVE ID must start with 'CVE-' (e.g., 'CVE-2021-44228')"}
    
    try:
        # Get the CVE details first
        params = {
            "cveId": cve_id.upper()
        }
        
        response = await _make_nvd_request(params)
        vulnerabilities = response.get("vulnerabilities", [])
        
        if not vulnerabilities:
            return {"error": f"No CVE found with ID: {cve_id}"}
        
        cve_data = vulnerabilities[0]
        cve = cve_data.get("cve", {})
        
        # Extract basic CVE info
        published = cve.get("published")
        last_modified = cve.get("lastModified")
        vuln_status = cve.get("vulnStatus")
        
        # Calculate urgency based on CVSS score and age
        metrics = cve.get("metrics", {})
        cvss_v3 = metrics.get("cvssMetricV31", []) or metrics.get("cvssMetricV30", [])
        cvss_v2 = metrics.get("cvssMetricV2", [])
        
        base_score = None
        severity = None
        vector_string = None
        
        if cvss_v3:
            cvss_data = cvss_v3[0].get("cvssData", {})
            base_score = cvss_data.get("baseScore")
            severity = cvss_v3[0].get("baseSeverity")
            vector_string = cvss_data.get("vectorString")
        elif cvss_v2:
            cvss_data = cvss_v2[0].get("cvssData", {})
            base_score = cvss_data.get("baseScore")
            severity = cvss_v2[0].get("baseSeverity")
            vector_string = cvss_data.get("vectorString")
        
        # Calculate remediation urgency
        urgency = "LOW"
        urgency_factors = []
        
        if base_score:
            if base_score >= 9.0:
                urgency = "CRITICAL"
                urgency_factors.append("Critical CVSS score (9.0+)")
            elif base_score >= 7.0:
                urgency = "HIGH"
                urgency_factors.append("High CVSS score (7.0+)")
            elif base_score >= 4.0:
                urgency = "MEDIUM"
                urgency_factors.append("Medium CVSS score (4.0+)")
        
        # Check CVE age
        if published:
            pub_date = datetime.strptime(published[:10], "%Y-%m-%d")
            days_old = (datetime.now() - pub_date).days
            if days_old < 30:
                urgency_factors.append("Recently published (< 30 days)")
                if urgency == "LOW":
                    urgency = "MEDIUM"
        
        # Analyze references for remediation info
        references = cve.get("references", [])
        patch_references = []
        advisory_references = []
        vendor_references = []
        mitigation_references = []
        
        for ref in references:
            url = ref.get("url", "")
            source = ref.get("source", "")
            tags = ref.get("tags", [])
            
            ref_info = {
                "url": url,
                "source": source,
                "tags": tags,
                "type": "general"
            }
            
            # Categorize references based on content and tags
            url_lower = url.lower()
            tags_lower = [tag.lower() for tag in tags]
            
            if any(keyword in url_lower for keyword in ["patch", "update", "fix", "security-update"]):
                ref_info["type"] = "patch"
                patch_references.append(ref_info)
            elif any(keyword in url_lower for keyword in ["advisory", "bulletin", "alert"]):
                ref_info["type"] = "advisory" 
                advisory_references.append(ref_info)
            elif any(keyword in url_lower for keyword in ["vendor", "microsoft", "oracle", "apache"]):
                ref_info["type"] = "vendor"
                vendor_references.append(ref_info)
            elif any(keyword in url_lower for keyword in ["mitigation", "workaround", "configuration"]):
                ref_info["type"] = "mitigation"
                mitigation_references.append(ref_info)
            
            # Check tags for additional categorization
            if "patch" in tags_lower or "vendor-advisory" in tags_lower:
                if ref_info not in patch_references:
                    patch_references.append(ref_info)
        
        # Generate remediation recommendations
        recommendations = []
        if base_score and base_score >= 7.0:
            recommendations.append("URGENT: Apply security patches immediately due to high CVSS score")
        if patch_references:
            recommendations.append(f"Review {len(patch_references)} available patches/updates")
        if mitigation_references:
            recommendations.append(f"Implement {len(mitigation_references)} available mitigations if patching not possible")
        if vuln_status == "Analyzed":
            recommendations.append("CVE has been fully analyzed - prioritize based on your environment")
        
        # Calculate remediation timeline
        timeline = "Standard (30 days)"
        if severity == "CRITICAL":
            timeline = "Emergency (1-3 days)"
        elif severity == "HIGH":
            timeline = "Urgent (7-14 days)" 
        elif severity == "MEDIUM":
            timeline = "Priority (14-30 days)"
        
        # Configuration analysis (basic)
        configurations = cve.get("configurations", [])
        affected_products = []
        for config in configurations:
            for node in config.get("nodes", []):
                for cpe_match in node.get("cpeMatch", []):
                    if cpe_match.get("vulnerable", False):
                        criteria = cpe_match.get("criteria", "")
                        if criteria:
                            affected_products.append(criteria)
        
        logger.info(f"Successfully analyzed remediation info for {cve_id}")
        
        return {
            "cveId": cve_id,
            "basicInfo": {
                "published": published,
                "lastModified": last_modified,
                "vulnStatus": vuln_status,
                "baseScore": base_score,
                "severity": severity,
                "vectorString": vector_string
            },
            "remediationUrgency": {
                "level": urgency,
                "timeline": timeline,
                "factors": urgency_factors
            },
            "remediationResources": {
                "patches": patch_references[:10] if include_patches else f"{len(patch_references)} patches available",
                "advisories": advisory_references[:5],
                "vendorInfo": vendor_references[:5],
                "mitigations": mitigation_references[:5],
                "totalReferences": len(references)
            },
            "affectedProducts": affected_products[:10],  # Limit for readability
            "recommendations": recommendations,
            "actionItems": [
                f"1. Review {len(patch_references)} available patches" if patch_references else "1. Check vendor sites for patches",
                f"2. Implement mitigations from {len(mitigation_references)} sources" if mitigation_references else "2. Implement temporary mitigations",
                f"3. Test and deploy patches within {timeline.lower()}",
                "4. Verify remediation effectiveness",
                "5. Update vulnerability management system"
            ]
        }
        
    except RuntimeError as e:
        logger.error(f"NVD API error in get_remediation_info: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error in get_remediation_info: {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

def main():
    logger.info(f"Starting CVE MCP Server on port {CVE_MCP_PORT} with log level {LOG_LEVEL_ENV}")
    logger.info(f"NVD API Base URL: {NVD_API_BASE_URL}")
    if NVD_API_KEY:
        logger.info("NVD API key configured (enhanced rate limits)")
    else:
        logger.info("No NVD API key configured (using public rate limits)")
    logger.info("Registered tools: get_recent_cves, get_cve_details, search_cves_by_severity, search_cves_by_keyword, get_product_vulnerability_summary, get_remediation_info")

    mcp.run(transport="streamable-http",
        host="0.0.0.0",
        port=CVE_MCP_PORT,
        log_level=LOG_LEVEL_ENV.lower()
    )

if __name__ == "__main__":
    main()