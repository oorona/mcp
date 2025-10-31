#!/usr/bin/env python3
"""
Interactive MCP Client

A console-based interactive interface for testing MCP servers.
Features:
- Interactive menu to select MCP servers
- Browse and select tools
- Full output display (no truncation)
- JSON pretty-printing
- Easy navigation and testing

Usage:
    python interactive_client.py
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from fastmcp import Client
import sys

# ANSI color codes for better UI
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Predefined test values for common parameters
DEFAULT_TEST_VALUES = {
    # Common parameters
    "query": "test",
    "search_term": "test",
    "search_query": "test",
    "partial_query": "cat",
    "q": "test",
    "limit": 5,
    "max_results": 5,
    "count": 5,
    "user_id": "811781544784035881",
    "discord_id": "811781544784035881",
    "days": 7,
    "language": "python",
    "code": "print('Hello, World!')",
    "cve_id": "CVE-2024-1234",
    "year": 2024,
    "video_id": "dQw4w9WgXcQ",
    "url": "https://example.com",
    "rating": "g",
    "content_filter": "medium",
    "locale": "en_US",
    "category": "trending",
    "tag": "funny",
    "offset": 0,
    "random": False,
    "safe_search": True
}

def get_default_value(param_name: str, param_type: str) -> Any:
    """Get a default test value for a parameter"""
    # Check if we have a predefined value
    if param_name in DEFAULT_TEST_VALUES:
        return DEFAULT_TEST_VALUES[param_name]
    
    # Otherwise, provide type-based defaults
    if param_type == 'integer':
        return 5
    elif param_type == 'number':
        return 5.0
    elif param_type == 'boolean':
        return False
    elif param_type == 'array':
        return ["test"]
    else:  # string
        return "test"

# MCP Server Configuration - Direct connections to individual MCP servers
SERVERS = {
    "giphy": {"url": "http://giphymcp:6700/mcp", "description": "GIF/sticker search, trending, random"},
    "youtube": {"url": "http://ytmcp:6700/mcp", "description": "Video search, transcripts, trending"},
    "wolframalpha": {"url": "http://wamcp:6700/mcp", "description": "Math, science, conversions"},
    "piston": {"url": "http://pistonmcp:6700/mcp", "description": "Code execution engine"},
    "cve": {"url": "http://cvemcp:6700/mcp", "description": "Vulnerability analysis"},
    "tenor": {"url": "http://tenormcp:6700/mcp", "description": "GIF search engine"},
    "usercontext": {"url": "http://usersmcp:6700/mcp", "description": "User analytics & history"}
}

def print_header(text: str):
    """Print a colored header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_section(text: str):
    """Print a section title"""
    print(f"\n{Colors.OKBLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'-'*len(text)}{Colors.ENDC}")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_json(data: Any, title: str = "Response"):
    """Print JSON data with pretty formatting"""
    print_section(title)
    try:
        if isinstance(data, str):
            # Try to parse if it's a JSON string
            try:
                data = json.loads(data)
            except:
                pass
        
        if isinstance(data, (dict, list)):
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(str(data))
    except Exception as e:
        print(f"Raw output: {data}")

def get_choice(prompt: str, options: List[str], allow_back: bool = True) -> Optional[str]:
    """Display menu and get user choice"""
    while True:
        print(f"\n{Colors.BOLD}{prompt}{Colors.ENDC}")
        for i, option in enumerate(options, 1):
            print(f"  {Colors.OKCYAN}{i}.{Colors.ENDC} {option}")
        
        if allow_back:
            print(f"  {Colors.WARNING}0.{Colors.ENDC} Back/Cancel")
        
        try:
            choice = input(f"\n{Colors.BOLD}Enter choice: {Colors.ENDC}").strip()
            
            if allow_back and choice == "0":
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                return options[choice_num - 1]
            else:
                print_error(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print_error("Please enter a valid number")
        except KeyboardInterrupt:
            print("\n")
            return None

async def call_tool_interactive(client: Client, tool) -> None:
    """Call a tool with user-provided parameters"""
    
    # Get tool name and schema
    tool_name = tool.name if hasattr(tool, 'name') else tool.get('name', 'Unknown')
    input_schema = tool.inputSchema if hasattr(tool, 'inputSchema') else tool.get('inputSchema', {})
    
    print_section(f"Calling Tool: {tool_name}")
    
    # Get parameters
    arguments = {}
    properties = input_schema.get('properties', {})
    required = input_schema.get('required', [])
    
    if properties:
        print_info("Enter parameters (press Enter to skip optional parameters):\n")
        
        for param_name, param_info in properties.items():
            is_required = param_name in required
            param_type = param_info.get('type', 'string')
            param_desc = param_info.get('description', '')
            
            while True:
                req_marker = f"{Colors.WARNING}*{Colors.ENDC}" if is_required else " "
                prompt = f"{req_marker} {param_name} ({param_type})"
                if param_desc:
                    prompt += f"\n  {Colors.OKCYAN}{param_desc}{Colors.ENDC}"
                prompt += f"\n  Value: "
                
                value = input(prompt).strip()
                
                # Skip if optional and empty
                if not value and not is_required:
                    break
                
                # Validate required fields
                if not value and is_required:
                    print_error("This parameter is required!")
                    continue
                
                # Type conversion
                try:
                    if param_type == 'integer':
                        arguments[param_name] = int(value)
                    elif param_type == 'number':
                        arguments[param_name] = float(value)
                    elif param_type == 'boolean':
                        arguments[param_name] = value.lower() in ('true', 'yes', '1', 'y')
                    elif param_type == 'array':
                        # Simple comma-separated list
                        arguments[param_name] = [item.strip() for item in value.split(',')]
                    else:
                        arguments[param_name] = value
                    break
                except ValueError:
                    print_error(f"Invalid value for type {param_type}")
    
    # Confirm execution
    print_section("Execution Summary")
    print(f"Tool: {Colors.BOLD}{tool_name}{Colors.ENDC}")
    if arguments:
        print(f"Arguments:\n{json.dumps(arguments, indent=2)}")
    else:
        print("No arguments")
    
    confirm = input(f"\n{Colors.BOLD}Execute? (y/n): {Colors.ENDC}").strip().lower()
    if confirm != 'y':
        print_warning("Execution cancelled")
        return
    
    # Execute
    try:
        print_info("Executing...")
        result = await client.call_tool(tool_name, arguments)
        
        # Display full result
        print_json(result, f"Tool Result: {tool_name}")
        
        # Wait for user to review
        input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")
        
    except Exception as e:
        print_error(f"Tool execution failed: {str(e)}")
        input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

async def run_all_tools_with_defaults(client: Client, tools: List, server_name: str) -> None:
    """Run all tools with predefined default values"""
    print_header(f"Running All Tools on {server_name.upper()}")
    print_warning(f"This will execute all {len(tools)} tools with default test values")
    
    confirm = input(f"\n{Colors.BOLD}Continue? (y/n): {Colors.ENDC}").strip().lower()
    if confirm != 'y':
        print_warning("Cancelled")
        return
    
    results = []
    for i, tool in enumerate(tools, 1):
        tool_name = tool.name if hasattr(tool, 'name') else tool.get('name', 'Unknown')
        input_schema = tool.inputSchema if hasattr(tool, 'inputSchema') else tool.get('inputSchema', {})
        
        print_section(f"[{i}/{len(tools)}] Testing: {tool_name}")
        
        # Build arguments with default values
        arguments = {}
        properties = input_schema.get('properties', {})
        required = input_schema.get('required', [])
        
        for param_name, param_info in properties.items():
            param_type = param_info.get('type', 'string')
            default_value = get_default_value(param_name, param_type)
            arguments[param_name] = default_value
            print(f"  {param_name}: {default_value}")
        
        # Execute
        try:
            result = await client.call_tool(tool_name, arguments)
            print_success(f"✓ {tool_name} executed successfully")
            results.append({
                "tool": tool_name,
                "status": "success",
                "arguments": arguments,
                "result": result
            })
        except Exception as e:
            print_error(f"✗ {tool_name} failed: {str(e)}")
            results.append({
                "tool": tool_name,
                "status": "error",
                "arguments": arguments,
                "error": str(e)
            })
        
        print()  # Blank line between tools
    
    # Summary
    print_header("Execution Summary")
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = len(results) - success_count
    
    print(f"{Colors.OKGREEN}✓ Successful: {success_count}{Colors.ENDC}")
    print(f"{Colors.FAIL}✗ Failed: {error_count}{Colors.ENDC}")
    
    # Show details
    show_details = input(f"\n{Colors.BOLD}Show detailed results? (y/n): {Colors.ENDC}").strip().lower()
    if show_details == 'y':
        for result in results:
            if result['status'] == 'success':
                print_json(result['result'], f"✓ {result['tool']}")
            else:
                print_error(f"✗ {result['tool']}: {result['error']}")
            input(f"\n{Colors.BOLD}Press Enter for next...{Colors.ENDC}")
    
    input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

async def test_server(server_name: str):
    """Interactive testing for a single server"""
    print_header(f"Testing MCP Server: {server_name.upper()}")
    print_info(f"Description: {SERVERS[server_name]['description']}")
    
    url = SERVERS[server_name]["url"]
    print_info(f"Connecting to {server_name} at {url}...")
    
    try:
        async with Client(url) as client:
            print_success(f"Connected to {server_name}")
            
            # List all tools
            tools_response = await client.list_tools()
            
            # Handle different response formats
            if isinstance(tools_response, dict) and "tools" in tools_response:
                tools = tools_response["tools"]
            elif isinstance(tools_response, list):
                tools = tools_response
            else:
                tools = []
            
            if not tools:
                print_warning("No tools available on this server")
                return
            
            # Display tools
            print_section(f"Available Tools on {server_name}")
            for i, tool in enumerate(tools, 1):
                # Handle both dict and object tools
                tool_name = tool.name if hasattr(tool, 'name') else tool.get('name', 'Unknown')
                tool_desc = tool.description if hasattr(tool, 'description') else tool.get('description', '')
                
                print(f"\n{Colors.OKGREEN}{i}. {tool_name}{Colors.ENDC}")
                if tool_desc:
                    print(f"   {tool_desc}")
                
                # Get input schema
                input_schema = tool.inputSchema if hasattr(tool, 'inputSchema') else tool.get('inputSchema', {})
                if input_schema and 'properties' in input_schema:
                    params = input_schema['properties']
                    if params:
                        print(f"   {Colors.OKCYAN}Parameters:{Colors.ENDC}")
                        for param_name, param_info in params.items():
                            required = param_name in input_schema.get('required', [])
                            req_str = f"{Colors.WARNING}*{Colors.ENDC}" if required else " "
                            param_type = param_info.get('type', 'any')
                            param_desc = param_info.get('description', '')
                            print(f"     {req_str} {param_name} ({param_type}): {param_desc}")
            
            # Interactive tool selection loop
            while True:
                tool_names = []
                for tool in tools:
                    name = tool.name if hasattr(tool, 'name') else tool.get('name', 'Unknown')
                    desc = tool.description if hasattr(tool, 'description') else tool.get('description', 'No description')
                    tool_names.append(f"{name} - {desc}")
                
                # Add special option to run all tools
                tool_names.append(f"{Colors.WARNING}🚀 RUN ALL TOOLS (with default values){Colors.ENDC}")
                
                choice = get_choice("Select a tool to test:", tool_names)
                
                if choice is None:
                    break
                
                # Check if user selected "Run All Tools"
                if "RUN ALL TOOLS" in choice:
                    await run_all_tools_with_defaults(client, tools, server_name)
                    continue
                
                # Find the selected tool
                tool_index = tool_names.index(choice)
                selected_tool = tools[tool_index]
                
                await call_tool_interactive(client, selected_tool)
                
    except Exception as e:
        print_error(f"Failed to connect to {server_name}: {str(e)}")
        input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

async def main():
    """Main interactive loop"""
    print_header("MCP Interactive Client")
    print_info("Welcome! This tool helps you test MCP servers interactively.")
    
    while True:
        # Server selection
        server_options = [f"{name} - {info['description']}" for name, info in SERVERS.items()]
        server_options.append(f"{Colors.FAIL}Exit{Colors.ENDC}")
        
        choice = get_choice("Select an MCP server to test:", server_options, allow_back=False)
        
        if choice is None or "Exit" in choice:
            print_header("Goodbye!")
            break
        
        # Extract server name from choice
        server_name = choice.split(" - ")[0]
        
        try:
            await test_server(server_name)
        except KeyboardInterrupt:
            print("\n")
            confirm = input(f"{Colors.WARNING}Return to main menu? (y/n): {Colors.ENDC}").strip().lower()
            if confirm != 'y':
                break
        except Exception as e:
            print_error(f"Unexpected error: {str(e)}")
            input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Interrupted by user. Goodbye!{Colors.ENDC}")
        sys.exit(0)
