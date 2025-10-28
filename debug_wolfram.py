#!/usr/bin/env python3

import os
import asyncio
import traceback
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_wolfram():
    try:
        # Import the required modules
        import wolframalpha
        
        # Get the API key
        app_id = os.environ.get('WOLFRAMALPHA_APP_ID')
        print(f"Using App ID: {app_id}")
        
        # Initialize client
        client = wolframalpha.Client(app_id)
        print("Client initialized successfully")
        
        # Test a simple query
        print("Testing query: 2+2")
        res = await client.aquery('2+2', plaintext=True)
        
        print(f"Response type: {type(res)}")
        print(f"Has success attr: {hasattr(res, 'success')}")
        if hasattr(res, 'success'):
            print(f"Success: {res.success}")
        
        print(f"Has pods attr: {hasattr(res, 'pods')}")
        if hasattr(res, 'pods'):
            print(f"Number of pods: {len(res.pods) if res.pods else 0}")
            
            if res.pods:
                for i, pod in enumerate(res.pods):
                    print(f"Pod {i}: {pod.title if hasattr(pod, 'title') else 'No title'}")
                    if hasattr(pod, 'subpods') and pod.subpods:
                        for j, subpod in enumerate(pod.subpods):
                            if hasattr(subpod, 'plaintext'):
                                print(f"  Subpod {j}: {subpod.plaintext}")
        
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        print(f"Error type: {type(e)}")
        print("Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_wolfram())