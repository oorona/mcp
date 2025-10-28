#!/usr/bin/env python3
"""
WolframAlpha API Key Test Script

This script helps you test if your WolframAlpha API key is working correctly
before running the full MCP server setup.
"""

import os
import sys
from dotenv import load_dotenv
import requests

def test_wolframalpha_api():
    """Test WolframAlpha API key functionality"""
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key from environment
    app_id = os.getenv("WOLFRAMALPHA_APP_ID")
    
    if not app_id:
        print("❌ ERROR: WOLFRAMALPHA_APP_ID not found in environment variables")
        print("Please set your WolframAlpha App ID in the .env file")
        print("Get your App ID from: https://developer.wolframalpha.com/")
        return False
    
    if app_id == "your_wolframalpha_app_id_here":
        print("❌ ERROR: Please replace 'your_wolframalpha_app_id_here' with your actual WolframAlpha App ID")
        print("Get your App ID from: https://developer.wolframalpha.com/")
        return False
    
    print(f"🔍 Testing WolframAlpha API with App ID: {app_id[:8]}...")
    
    # Test API with a simple query
    test_query = "2+2"
    url = f"https://api.wolframalpha.com/v2/query"
    params = {
        "appid": app_id,
        "input": test_query,
        "format": "plaintext",
        "output": "json"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            print("✅ SUCCESS: WolframAlpha API key is working!")
            print(f"✅ Test query '{test_query}' completed successfully")
            return True
        elif response.status_code == 401:
            print("❌ ERROR: Invalid API key (401 Unauthorized)")
            print("Please check your WOLFRAMALPHA_APP_ID in the .env file")
            return False
        else:
            print(f"❌ ERROR: API request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Network error while testing API: {e}")
        return False

def main():
    print("WolframAlpha API Key Test")
    print("=" * 50)
    
    if test_wolframalpha_api():
        print("\n🎉 Your WolframAlpha API key is configured correctly!")
        print("You can now run: docker compose up --build")
        sys.exit(0)
    else:
        print("\n❗ Please fix the API key configuration and try again")
        print("\nSteps to get a WolframAlpha App ID:")
        print("1. Visit: https://developer.wolframalpha.com/")
        print("2. Sign up for a free account")
        print("3. Create a new app to get your App ID")
        print("4. Add your App ID to the .env file")
        sys.exit(1)

if __name__ == "__main__":
    main()