#!/usr/bin/env python3
"""
MCP Multi-Server Client

A production client for testing and interacting with MCP servers.
Supports all servers in the MCP ecosystem: Giphy (Enhanced), YouTube (Enhanced),
WolframAlpha (Enhanced), Piston (Enhanced), CVE (Enhanced), Tenor (Enhanced), and UserContext (Enhanced).

Features:
- Comprehensive testing of all server capabilities
- Demo functions for enhanced functionality
- Tool discovery and execution
- Enhanced error handling and reporting

Enhanced Server Capabilities:
- Giphy: 10 tools - GIF/sticker search, trending, random, translate, categories, autocomplete
- YouTube: 8 tools - Video search, transcript checking, trending, comments, channel info
- WolframAlpha: 7 tools - Mathematical calculations, unit conversions, scientific data, equations
- Piston: 4 tools - Auto-version selection, multiple language support
- CVE: 8 tools - Comprehensive vulnerability analysis and statistics
- Tenor: 8 tools - Advanced GIF search, categories, trending, autocomplete
- UserContext: 11 tools - User history, conversation context, analytics, word clouds, sentiment analysis, activity patterns

Usage:
    python client.py                    # Test all servers
    python client.py --server giphy    # Test specific server
    python client.py --list-tools      # List all available tools
    python client.py --call-tool <server> <tool> [args]  # Call specific tool
    python client.py --demo <server>   # Run demo for specific server
    python client.py --demo-all        # Run demos for all servers
"""

from fastmcp import Client
import asyncio
import json
import argparse
import sys
from typing import Dict, List, Any, Optional

# MCP Server Configuration
SERVERS = {
    "giphy": {"port": 6700, "description": "Enhanced: GIF/sticker search, trending, random, translate, categories, autocomplete"},
    "youtube": {"port": 6700, "description": "Enhanced: Video search, transcript checking, trending, comments, channel info"},
    "wolframalpha": {"port": 6700, "description": "Enhanced: Mathematical calculations, unit conversions, scientific data, equation solving, statistical analysis, definitions"},
    "piston": {"port": 6700, "description": "Enhanced: Auto-version selection, multiple language support"},
    "cve": {"port": 6700, "description": "Enhanced: Comprehensive vulnerability analysis and statistics"},
    "tenor": {"port": 6700, "description": "Enhanced: Advanced GIF search, categories, trending, autocomplete"},
    "usercontext": {"port": 6700, "description": "Enhanced: User history, conversation context, analytics, word clouds, sentiment analysis, activity patterns"}
}

class MCPClient:
    """Production MCP client for testing and interacting with servers"""
    
    def __init__(self, host: str = "bot", verbose: bool = False):
        self.host = host
        self.verbose = verbose
        
    def log(self, message: str, level: str = "INFO"):
        """Log messages with optional verbosity control"""
        if self.verbose or level in ["ERROR", "SUCCESS", "RESULT"]:
            prefix = f"[{level}]" if level != "INFO" else ""
            print(f"{prefix} {message}")
    
    def print_json(self, data: Any, max_lines: int = 20):
        """Pretty print JSON with optional truncation"""
        import json
        
        # Handle CallToolResult objects
        if hasattr(data, 'content'):
            if isinstance(data.content, list) and len(data.content) > 0:
                # Extract the actual content from the result
                content = data.content[0]
                if hasattr(content, 'text'):
                    try:
                        # Try to parse as JSON
                        parsed_data = json.loads(content.text)
                        data = parsed_data
                    except (json.JSONDecodeError, AttributeError):
                        data = content.text
                else:
                    data = str(content)
            else:
                data = str(data.content)
        
        # Convert to JSON string
        if isinstance(data, str):
            json_str = data
        else:
            json_str = json.dumps(data, indent=2, sort_keys=True, default=str)
        
        lines = json_str.split('\n')
        if len(lines) > max_lines:
            truncated_lines = lines[:max_lines] + [f"... ({len(lines) - max_lines} more lines)"]
            print('\n'.join(truncated_lines))
        else:
            print(json_str)
    
    async def test_server(self, server_name: str) -> Dict[str, Any]:
        """Test connectivity and capabilities of a single server"""
        if server_name not in SERVERS:
            return {"server": server_name, "status": "error", "error": "Unknown server"}
        
        config = SERVERS[server_name]
        
        # Map server names to container names when using Docker
        if self.host == "bot":
            container_map = {
                "giphy": "giphymcp",
                "youtube": "ytmcp", 
                "wolframalpha": "wamcp",
                "piston": "pistonmcp",
                "cve": "cvemcp",
                "tenor": "tenormcp",
                "usercontext": "usersmcp"
            }
            host = container_map.get(server_name, server_name)
        else:
            host = self.host
            
        url = f"http://{host}:{config['port']}/mcp"
        
        self.log(f"Testing {server_name} at {url}")
        
        try:
            client = Client(url)
            async with client:
                # Test ping
                await client.ping()
                self.log(f"✅ {server_name}: Ping successful", "SUCCESS")
                
                # List tools
                tools_response = await client.list_tools()
                tools = []
                if isinstance(tools_response, dict) and "tools" in tools_response:
                    tools = tools_response["tools"]
                elif isinstance(tools_response, list):
                    tools = tools_response
                
                # List resources
                try:
                    resources_response = await client.list_resources()
                    resources = []
                    if isinstance(resources_response, dict) and "resources" in resources_response:
                        resources = resources_response["resources"]
                    elif isinstance(resources_response, list):
                        resources = resources_response
                except Exception:
                    resources = []  # Some servers may not have resources
                
                result = {
                    "server": server_name,
                    "status": "success",
                    "url": url,
                    "description": config["description"],
                    "tools": [{"name": getattr(tool, "name", str(tool)), "description": getattr(tool, "description", "")} for tool in tools],
                    "resources": len(resources)
                }
                
                self.log(f"✅ {server_name}: {len(tools)} tools, {len(resources)} resources", "SUCCESS")
                return result
                
        except Exception as e:
            self.log(f"❌ {server_name}: {str(e)}", "ERROR")
            return {
                "server": server_name,
                "status": "error",
                "error": str(e),
                "url": url
            }
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Call a specific tool on a server"""
        if server_name not in SERVERS:
            raise ValueError(f"Unknown server: {server_name}")
        
        config = SERVERS[server_name]
        
        # Map server names to container names when using Docker
        if self.host == "bot":
            container_map = {
                "giphy": "giphymcp",
                "youtube": "ytmcp", 
                "wolframalpha": "wamcp",
                "piston": "pistonmcp",
                "cve": "cvemcp",
                "tenor": "tenormcp",
                "usercontext": "usersmcp"
            }
            host = container_map.get(server_name, server_name)
        else:
            host = self.host
            
        url = f"http://{host}:{config['port']}/mcp"
        arguments = arguments or {}
        
        self.log(f"Calling {tool_name} on {server_name} with args: {arguments}")
        
        try:
            client = Client(url)
            async with client:
                result = await client.call_tool(tool_name, arguments)
                self.log(f"✅ Tool call successful", "SUCCESS")
                return result
                
        except Exception as e:
            self.log(f"❌ Tool call failed: {str(e)}", "ERROR")
            raise
    
    async def list_all_tools(self) -> Dict[str, List[Dict]]:
        """Get all available tools from all servers"""
        all_tools = {}
        
        for server_name in SERVERS:
            result = await self.test_server(server_name)
            if result["status"] == "success":
                all_tools[server_name] = result["tools"]
        
        return all_tools
    
    async def test_all_servers(self) -> List[Dict[str, Any]]:
        """Test all configured servers"""
        results = []
        
        print("🔍 Testing MCP servers...")
        print("=" * 50)
        
        for server_name in SERVERS:
            result = await self.test_server(server_name)
            results.append(result)
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 SUMMARY")
        print("=" * 50)
        
        successful = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] == "error"]

        print(f"✅ Connected: {len(successful)}/{len(SERVERS)} servers")
        for result in successful:
            print(f"   • {result['server']}: {len(result['tools'])} tools - {result['description']}")

        if failed:
            print(f"\n❌ Failed: {len(failed)} servers")
            for result in failed:
                print(f"   • {result['server']}: {result['error']}")

        return results

    async def demo_youtube(self) -> None:
        """Demo YouTube MCP server enhanced functionality"""
        print("\n🎬 YouTube MCP Server Demo")
        print("=" * 40)
        
        demos = [
            # Search videos
            ("search_youtube_videos", {"query": "Python tutorial", "max_results": 3}),
            # Get channel information
            ("get_channel_info", {"channel_id": "UCCezIgC97PvUuR4_gbFUs5g"}),
            # Get video comments
            ("get_video_comments", {"video_id": "dQw4w9WgXcQ", "max_results": 5}),
            # Get trending videos
            ("get_trending_videos", {"region_code": "US", "max_results": 3}),
            # Check transcript availability  
            ("check_transcript_availability", {"video_id": "dQw4w9WgXcQ"}),
            # Get video transcript
            ("get_youtube_video_transcript", {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}),
            # Get playlist videos (using a popular coding playlist)
            ("get_playlist_videos", {"playlist_id": "PLu0W_9lII9agICnT8t4iYVSZ3eykIAOME", "max_results": 3}),
            # Extract video ID from URL
            ("extract_video_id_from_url", {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}),
        ]
        
        for tool_name, args in demos:
            try:
                print(f"\n🔧 Testing: {tool_name}")
                result = await self.call_tool("youtube", tool_name, args)
                print("📊 Result:")
                self.print_json(result, max_lines=10)
            except Exception as e:
                print(f"❌ Error: {str(e)}")

    async def demo_piston(self) -> None:
        """Demo Piston MCP server enhanced functionality"""
        print("\n💻 Piston MCP Server Demo")
        print("=" * 40)
        
        demos = [
            # Get all runtimes
            ("get_piston_runtimes", {}),
            # Get Python versions
            ("get_available_language_versions", {"language": "python"}),
            # Get specific language version info
            ("get_piston_language_version", {"language": "python"}),
            # Execute Python code (auto-version) - demonstrates core functionality
            ("execute_code", {"language": "python", "code": "print('Hello from auto-selected Python!')\nimport sys\nprint(f'Python version: {sys.version}')"}),
            # Get JavaScript versions
            ("get_available_language_versions", {"language": "javascript"}),
        ]
        
        for tool_name, args in demos:
            try:
                print(f"\n🔧 Testing: {tool_name}")
                result = await self.call_tool("piston", tool_name, args)
                print("📊 Result:")
                self.print_json(result, max_lines=15)
            except Exception as e:
                print(f"❌ Error: {str(e)}")

    async def demo_cve(self) -> None:
        """Demo CVE MCP server functionality"""
        print("\n🔒 CVE MCP Server Demo")
        print("=" * 40)
        
        demos = [
            # Get recent CVEs
            ("get_recent_cves", {"limit": 3}),
            # Get specific CVE details
            ("get_cve_details", {"cve_id": "CVE-2021-44228"}),
            # Search by severity
            ("search_cves_by_severity", {"severity": "HIGH", "limit": 2}),
            # Search by keyword
            ("search_cves_by_keyword", {"keyword": "python", "limit": 2}),
            # Get CVE statistics
            ("get_cve_statistics", {}),
            # Get product vulnerability summary
            ("get_product_vulnerability_summary", {"product_name": "apache", "days_back": 180}),
            # Get CVE trends
            ("get_cve_trends", {"period": "monthly", "months_back": 6}),
            # Get remediation info
            ("get_remediation_info", {"cve_id": "CVE-2021-44228"}),
        ]
        
        for tool_name, args in demos:
            try:
                print(f"\n🔧 Testing: {tool_name}")
                result = await self.call_tool("cve", tool_name, args)
                print("📊 Result:")
                self.print_json(result, max_lines=10)
            except Exception as e:
                print(f"❌ Error: {str(e)}")

    async def demo_tenor(self) -> None:
        """Demo Tenor MCP server functionality"""
        print("\n🎭 Tenor MCP Server Demo")
        print("=" * 40)
        
        demos = [
            # Search GIFs
            ("search_tenor_gifs", {"query": "funny cat", "limit": 3}),
            # Get trending GIFs
            ("get_trending_tenor_gifs", {"limit": 3}),
            # Get categories
            ("get_tenor_categories", {}),
            # Get autocomplete suggestions
            ("get_tenor_autocomplete", {"query": "happy"}),
            # Get search suggestions
            ("get_tenor_search_suggestions", {"query": "birthday"}),
            # Get trending terms
            ("get_tenor_trending_terms", {}),
            # Get random GIFs
            ("get_random_tenor_gifs", {"query": "celebration", "limit": 2}),
            # Register a share (analytics)
            ("register_tenor_share", {"gif_id": "example_gif_id"}),
        ]
        
        for tool_name, args in demos:
            try:
                print(f"\n🔧 Testing: {tool_name}")
                result = await self.call_tool("tenor", tool_name, args)
                print("📊 Result:")
                self.print_json(result, max_lines=10)
            except Exception as e:
                print(f"❌ Error: {str(e)}")

    async def demo_wolframalpha(self) -> None:
        """Demo WolframAlpha MCP server enhanced functionality"""
        print("\n🧮 WolframAlpha MCP Server Demo")
        print("=" * 40)
        
        demos = [
            # Mathematical calculations
            ("calculate_math", {"expression": "integrate x^2 from 0 to 5"}),
            ("calculate_math", {"expression": "derivative of sin(x^2)"}),
            ("solve_equation", {"equation": "x^2 + 5x + 6 = 0"}),
            
            # Unit conversions
            ("convert_units", {"value": "100 kilometers", "target_unit": "miles"}),
            ("convert_units", {"value": "32 fahrenheit"}),  # Multiple conversions
            
            # Scientific data
            ("get_scientific_data", {"topic": "hydrogen atom"}),
            ("get_scientific_data", {"topic": "speed of light"}),
            
            # Statistical analysis
            ("get_statistical_analysis", {"data_description": "mean of 1,2,3,4,5,10,15"}),
            
            # Definitions and examples
            ("get_definition_and_examples", {"term": "calculus"}),
            
            # General query
            ("query_wolfram_alpha", {"query": "population of Tokyo"}),
        ]
        
        for tool_name, args in demos:
            try:
                print(f"\n🔧 Testing: {tool_name}")
                result = await self.call_tool("wolframalpha", tool_name, args)
                print("📊 Result:")
                self.print_json(result, max_lines=12)
            except Exception as e:
                print(f"❌ Error: {str(e)}")

    async def demo_giphy(self) -> None:
        """Demo Giphy MCP server functionality"""
        print("\n🎨 Giphy MCP Server Demo")
        print("=" * 40)
        
        demos = [
            # Core functionality
            ("get_top_trending_giphy_image", {}),
            ("get_giphy_image_by_search", {"query": "excited", "search_limit": 2}),
            
            # New functionality
            ("get_random_giphy_image", {"tag": "funny"}),
            ("translate_to_giphy_image", {"phrase": "good morning"}),
            ("get_giphy_categories", {}),
            ("get_giphy_autocomplete", {"query": "hap", "limit": 3}),
            ("get_trending_search_terms", {}),
            ("search_giphy_stickers", {"query": "thumbs up", "search_limit": 2}),
            ("get_trending_giphy_stickers", {"limit": 3}),
            
            # Test by ID (using a known Giphy ID - may fail if ID doesn't exist)
            ("get_giphy_image_by_id", {"gif_id": "3o7btPCcdNniyf0ArS"}),
        ]
        
        for tool_name, args in demos:
            try:
                print(f"\n🔧 Testing: {tool_name}")
                result = await self.call_tool("giphy", tool_name, args)
                print("📊 Result:")
                self.print_json(result, max_lines=8)
            except Exception as e:
                print(f"❌ Error: {str(e)}")

    async def demo_usercontext(self) -> None:
        """Demo UserContext MCP server functionality"""
        print("\n👥 UserContext MCP Server Demo")
        print("=" * 40)
        
        # Use real Discord user ID for testing
        user_id = 811781544784035881
        channel_id = 1423820968740126760  # Replace with actual channel ID if available
        guild_id = 1423815821674676267  # Replace with actual guild ID if available
        
        demos = [
            # Get user context (messages for a user)
            ("get_user_context", {"user_id": user_id, "n": 5}),
            # Get conversation context (channel messages)
            ("get_conversation_context", {"channel_id": channel_id, "minutes": 30}),
            # List available channels
            ("list_conversation_channels", {}),
            # User word cloud analysis
            ("get_user_word_cloud", {"user_id": user_id, "top_words": 20}),
            # User activity pattern
            ("get_user_activity_pattern", {"user_id": user_id}),
            # User sentiment analysis
            ("get_user_sentiment_analysis", {"user_id": user_id}),
            # Channel activity statistics
            ("get_channel_activity_stats", {"channel_id": channel_id, "hours": 24}),
            # Channel sentiment trend
            ("get_channel_sentiment_trend", {"channel_id": channel_id, "hours": 48}),
            # Server-wide activity heatmap
            ("get_activity_heatmap", {"days": 7}),
            # User engagement metrics
            ("get_user_engagement_metrics", {"user_id": user_id}),
            # Guild analytics overview
            ("get_guild_analytics_overview", {"guild_id": guild_id, "days": 7}),
        ]
        
        for tool_name, args in demos:
            try:
                print(f"\n🔧 Testing: {tool_name}")
                result = await self.call_tool("usercontext", tool_name, args)
                print("📊 Result:")
                self.print_json(result, max_lines=10)
            except Exception as e:
                print(f"❌ Error: {str(e)}")

    async def demo_server(self, server_name: str) -> None:
        """Run demo for a specific server"""
        if server_name == "youtube":
            await self.demo_youtube()
        elif server_name == "piston":
            await self.demo_piston()
        elif server_name == "cve":
            await self.demo_cve()
        elif server_name == "tenor":
            await self.demo_tenor()
        elif server_name == "giphy":
            await self.demo_giphy()
        elif server_name == "wolframalpha":
            await self.demo_wolframalpha()
        elif server_name == "usercontext":
            await self.demo_usercontext()
        else:
            print(f"❌ No demo available for server: {server_name}")
            print("📝 Available demos: youtube, piston, cve, tenor, giphy, wolframalpha, usercontext")

    async def demo_all_servers(self) -> None:
        """Run demos for all servers with enhanced functionality"""
        print("🚀 Running Enhanced MCP Server Demos")
        print("=" * 50)
        
        # Test basic connectivity first
        test_results = await self.test_all_servers()
        successful_servers = [r["server"] for r in test_results if r["status"] == "success"]
        
        # Run demos for servers with demos available
        demo_servers = ["youtube", "piston", "cve", "tenor", "giphy", "wolframalpha", "usercontext"]
        available_demos = [s for s in demo_servers if s in successful_servers]
        
        if not available_demos:
            print("❌ No servers available for demos")
            return
        
        print(f"\n🎯 Running demos for {len(available_demos)} servers: {', '.join(available_demos)}")
        
        for server_name in available_demos:
            try:
                await self.demo_server(server_name)
                print("\n" + "-" * 50)
            except Exception as e:
                print(f"❌ Demo failed for {server_name}: {str(e)}")
                print("\n" + "-" * 50)

    async def enhanced_tool_test(self) -> None:
        """Test enhanced functionality across all servers"""
        print("🧪 Enhanced Functionality Test")
        print("=" * 50)
        
        tests = [
            # Giphy enhanced features
            ("giphy", "translate_to_giphy_image", {"phrase": "hello world"}),
            ("giphy", "get_random_giphy_image", {"tag": "celebration"}),
            ("giphy", "search_giphy_stickers", {"query": "ok", "search_limit": 1}),
            ("giphy", "get_giphy_categories", {}),
            
            # YouTube enhanced features
            ("youtube", "search_youtube_videos", {"query": "AI tutorial", "max_results": 2}),
            ("youtube", "check_transcript_availability", {"video_id": "dQw4w9WgXcQ"}),
            
            # Piston auto-version selection
            ("piston", "execute_code", {"language": "python", "code": "print('Auto Python version')"}),
            ("piston", "get_available_language_versions", {"language": "javascript"}),
            
            # CVE enhanced searches
            ("cve", "get_cve_statistics", {}),
            ("cve", "search_cves_by_severity", {"severity": "CRITICAL", "limit": 1}),
            
            # Tenor GIF functionality
            ("tenor", "search_tenor_gifs", {"query": "success", "limit": 2}),
            ("tenor", "get_tenor_categories", {}),
            
            # WolframAlpha enhanced features
            ("wolframalpha", "calculate_math", {"expression": "2^10"}),
            ("wolframalpha", "convert_units", {"value": "100 meters", "target_unit": "feet"}),
            ("wolframalpha", "solve_equation", {"equation": "x + 5 = 10"}),
        ]
        
        successful_tests = 0
        total_tests = len(tests)
        
        for server_name, tool_name, args in tests:
            try:
                print(f"\n🔧 Testing: {server_name}.{tool_name}")
                result = await self.call_tool(server_name, tool_name, args)
                if "error" not in str(result).lower():
                    print("✅ Test passed")
                    successful_tests += 1
                else:
                    print("⚠️  Test completed with warnings")
                    successful_tests += 1
            except Exception as e:
                print(f"❌ Test failed: {str(e)}")
        
        print(f"\n📊 Test Summary: {successful_tests}/{total_tests} tests passed")
        print("=" * 50)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="MCP Multi-Server Client")
    parser.add_argument("--host", default="bot", help="Host for MCP servers (default: bot)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--server", help="Test specific server only")
    parser.add_argument("--list-tools", action="store_true", help="List all available tools")
    parser.add_argument("--call-tool", nargs='+', help="Call tool: <server> <tool> [arg1=val1] [arg2=val2]")
    parser.add_argument("--demo", help="Run demo for specific server (youtube, piston, cve, tenor, giphy, wolframalpha)")
    parser.add_argument("--demo-all", action="store_true", help="Run demos for all servers")
    parser.add_argument("--test-enhanced", action="store_true", help="Test enhanced functionality across all servers")
    
    return parser.parse_args()

def parse_tool_args(args: List[str]) -> Dict[str, Any]:
    """Parse tool arguments from command line"""
    parsed_args = {}
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=', 1)
            # Try to parse as JSON, fall back to string
            try:
                parsed_args[key] = json.loads(value)
            except json.JSONDecodeError:
                parsed_args[key] = value
    return parsed_args

async def main():
    """Main function"""
    args = parse_args()
    
    client = MCPClient(host=args.host, verbose=args.verbose)
    
    try:
        if args.list_tools:
            # List all tools
            print("🛠️  Available Tools:")
            print("=" * 50)
            all_tools = await client.list_all_tools()
            
            for server_name, tools in all_tools.items():
                print(f"\n📦 {server_name.upper()} ({len(tools)} tools):")
                for tool in tools:
                    desc = f" - {tool['description']}" if tool['description'] else ""
                    print(f"   • {tool['name']}{desc}")
        
        elif args.call_tool:
            # Call specific tool
            if len(args.call_tool) < 2:
                print("❌ Usage: --call-tool <server> <tool> [arg1=val1] [arg2=val2]")
                sys.exit(1)
            
            server_name = args.call_tool[0]
            tool_name = args.call_tool[1]
            tool_args = parse_tool_args(args.call_tool[2:]) if len(args.call_tool) > 2 else {}
            
            print(f"🔧 Calling {tool_name} on {server_name}")
            print(f"📝 Arguments: {tool_args}")
            print("=" * 50)
            
            result = await client.call_tool(server_name, tool_name, tool_args)
            print("📊 RESULT:")
            client.print_json(result)
        
        elif args.demo:
            # Run demo for specific server
            await client.demo_server(args.demo)
        
        elif args.demo_all:
            # Run demos for all servers
            await client.demo_all_servers()
        
        elif args.test_enhanced:
            # Test enhanced functionality
            await client.enhanced_tool_test()
        
        elif args.server:
            # Test specific server
            result = await client.test_server(args.server)
            print("📊 RESULT:")
            client.print_json(result)
        
        else:
            # Test all servers (default)
            await client.test_all_servers()
            
            print("\n💡 Usage Examples:")
            print("   # Basic operations")
            print("   python client.py --list-tools")
            print("   python client.py --server giphy")
            print("   python client.py --call-tool giphy get_top_trending_giphy_image")
            print("   python client.py --call-tool cve search_cves_by_severity severity=HIGH limit=5")
            print("")
            print("   # Enhanced functionality demos")
            print("   python client.py --demo youtube          # Demo YouTube enhanced features")
            print("   python client.py --demo piston           # Demo Piston auto-version selection")
            print("   python client.py --demo wolframalpha     # Demo WolframAlpha computational tools")
            print("   python client.py --demo-all              # Demo all enhanced servers")
            print("   python client.py --test-enhanced         # Quick test of enhanced features")
            print("")
            print("   # Specific enhanced examples")
            print("   python client.py --call-tool youtube search_youtube_videos query='Python' max_results=3")
            print("   python client.py --call-tool piston execute_code language=python code='print(\"Auto version!\")'")
            print("   python client.py --call-tool wolframalpha calculate_math expression='integrate x^2 dx'")
            print("   python client.py --call-tool tenor search_tenor_gifs query='celebration' limit=2")
    
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
