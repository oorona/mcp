# CVE MCP Server

A FastMCP server that provides access to the National Vulnerability Database (NVD) for retrieving CVE (Common Vulnerabilities and Exposures) information.

## Features

- **Recent CVEs**: Get recently published or modified vulnerabilities
- **CVE Details**: Retrieve comprehensive information for specific CVE IDs
- **Severity Search**: Find vulnerabilities by CVSS severity level (LOW, MEDIUM, HIGH, CRITICAL)
- **Keyword Search**: Search CVEs by product, vendor, or technology keywords
- **Statistics**: Get vulnerability trends and statistics

## Available Tools

### `get_recent_cves`
Retrieve recent CVEs from the NVD.
- `results_per_page` (optional): Number of CVEs to retrieve (max 2000, default 20)
- `days_back` (optional): How many days back to search (default 7 days)

### `get_cve_details`
Get detailed information for a specific CVE.
- `cve_id` (required): The CVE ID (e.g., "CVE-2021-44228")

### `search_cves_by_severity`
Search CVEs by CVSS severity level.
- `severity` (required): "LOW", "MEDIUM", "HIGH", or "CRITICAL"
- `results_per_page` (optional): Number of results (max 2000, default 50)
- `days_back` (optional): Days to search back (default 30)

### `search_cves_by_keyword`
Search CVEs by keyword in descriptions.
- `keyword` (required): Search term (e.g., "apache", "mysql", "windows")
- `results_per_page` (optional): Number of results (max 2000, default 50)
- `days_back` (optional): Days to search back (default 30, 0 for all time)

### `get_cve_statistics`
Get vulnerability statistics and trends.
- `days_back` (optional): Period to analyze (default 30 days)

### `get_product_vulnerability_summary` ⭐ *New*
Get comprehensive vulnerability summary for a specific product.
- `product_name` (required): Product to analyze (e.g., "apache", "nginx", "mysql")
- `vendor` (optional): Vendor name to refine search (e.g., "microsoft", "oracle")
- `severity_threshold` (optional): Minimum severity ("LOW", "MEDIUM", "HIGH", "CRITICAL")
- `days_back` (optional): Analysis period in days (default 365)

### `get_cve_trends` ⭐ *New*
Analyze CVE publication trends over time.
- `period` (optional): Analysis granularity ("weekly", "monthly", "yearly", default "monthly")
- `severity_filter` (optional): Filter by severity level
- `months_back` (optional): Historical data period (default 12, max 24)

### `get_remediation_info` ⭐ *New*
Get comprehensive remediation information for a CVE.
- `cve_id` (required): The CVE ID to analyze
- `include_patches` (optional): Include detailed patch info (default True)

## Configuration

### Environment Variables

- `CVE_MCP_PORT`: Server port (default: 6900)
- `NVD_API_KEY`: Optional NVD API key for higher rate limits
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### NVD API Key

While not required, an NVD API key increases rate limits from 5 requests per 30 seconds to 50 requests per 30 seconds. Get one at: https://nvd.nist.gov/developers/request-an-api-key

## Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Run the server
python server.py
```

### Docker
```bash
# Build and run with Docker Compose
docker-compose up cvemcp

# Or build manually
docker build -f Dockerfile.cvemcp -t cvemcp .
docker run -p 6900:6900 cvemcp
```

## Usage Examples

### Python Client
```python
from fastmcp import Client

async def example():
    client = Client("http://localhost:6900/mcp")
    
    async with client:
        # Get recent high-severity CVEs
        recent = await client.call_tool("search_cves_by_severity", {
            "severity": "HIGH",
            "results_per_page": 10
        })
        
        # Get details for a specific CVE
        details = await client.call_tool("get_cve_details", {
            "cve_id": "CVE-2021-44228"
        })
        
        # Search for Apache vulnerabilities
        apache_cves = await client.call_tool("search_cves_by_keyword", {
            "keyword": "apache",
            "results_per_page": 5
        })
        
        # NEW: Get comprehensive product vulnerability summary
        nginx_summary = await client.call_tool("get_product_vulnerability_summary", {
            "product_name": "nginx",
            "severity_threshold": "MEDIUM",
            "days_back": 365
        })
        
        # NEW: Analyze CVE trends over time
        trends = await client.call_tool("get_cve_trends", {
            "period": "monthly",
            "months_back": 12,
            "severity_filter": "HIGH"
        })
        
        # NEW: Get remediation information
        remediation = await client.call_tool("get_remediation_info", {
            "cve_id": "CVE-2021-44228",
            "include_patches": True
        })
```

### curl Examples
```bash
# Get recent CVEs
curl -X POST http://localhost:6900/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "get_recent_cves", "arguments": {"results_per_page": 5}}'

# Search by severity
curl -X POST http://localhost:6900/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "search_cves_by_severity", "arguments": {"severity": "CRITICAL"}}'

# Get CVE details
curl -X POST http://localhost:6900/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "get_cve_details", "arguments": {"cve_id": "CVE-2021-44228"}}'

# NEW: Product vulnerability summary
curl -X POST http://localhost:6900/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "get_product_vulnerability_summary", "arguments": {"product_name": "apache", "severity_threshold": "HIGH"}}'

# NEW: CVE trends analysis
curl -X POST http://localhost:6900/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "get_cve_trends", "arguments": {"period": "monthly", "months_back": 6}}'

# NEW: Remediation information
curl -X POST http://localhost:6900/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{"name": "get_remediation_info", "arguments": {"cve_id": "CVE-2021-44228"}}'
```

## Data Sources

This server uses the National Vulnerability Database (NVD) API v2.0:
- Base URL: https://services.nvd.nist.gov/rest/json/cves/2.0
- Documentation: https://nvd.nist.gov/developers/vulnerabilities
- Data includes CVE records, CVSS scores, affected products, and references

## Rate Limits

- **Without API key**: 5 requests per 30 seconds
- **With API key**: 50 requests per 30 seconds

The server implements proper error handling for rate limit responses.

## Troubleshooting

### Common Issues

**403 Forbidden**: API access denied
- Check if you need an API key
- Verify the API key is correctly configured

**429 Too Many Requests**: Rate limit exceeded
- Wait before making more requests
- Consider adding an NVD API key

**No results**: CVE not found
- Verify CVE ID format (e.g., "CVE-2021-44228")
- Check if the CVE exists in the NVD

### Logging

Set `LOG_LEVEL=DEBUG` for detailed request/response logging.

## Security Considerations

- This server provides read-only access to public vulnerability data
- No authentication is required for the NVD API
- Consider implementing access controls in production environments
- The NVD API may have usage restrictions for commercial applications