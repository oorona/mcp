from fastmcp import Client
import asyncio
import json

# The Client automatically uses StreamableHttpTransport for HTTP URLs
client = Client("http://bot:6100/mcp")

async def main():
    async with client:
        await client.ping() 
        print("Ping successful!")
        #print("Client version:", client.version)
        print("--------------------------------------------------")
        tools = await client.list_tools()
        print(f"Available tools: {tools}")

        #beautiful_json_string = json.dumps(tools, indent=4, sort_keys=True)
        #print(beautiful_json_string)
        print("--------------------------------------------------")
        resources = await client.list_resources()
        print(f"Available resources: {resources}")
        #beautiful_json_string = json.dumps(resources, indent=4, sort_keys=True)
        #print(beautiful_json_string)
        print("--------------------------------------------------")
        #execution = await client.call_tool("get_piston_runtimes", {} )
        #print(f"Execution result: {execution}")
        #beautiful_json_string = json.dumps(execution, indent=4, sort_keys=True)
        #print(beautiful_json_string)

asyncio.run(main())