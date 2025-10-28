# WolframAlpha MCP Server Setup

## Issue: "Mathematical calculation failed"

The WolframAlpha MCP server requires a valid API key to function. Here's how to fix this:

## Quick Fix Steps

### 1. Get a WolframAlpha App ID
1. Visit [https://developer.wolframalpha.com/](https://developer.wolframalpha.com/)
2. Sign up for a free account (if you don't have one)
3. Create a new app to get your **App ID** (not API key)
4. Copy your App ID

### 2. Configure the API Key
1. Open the `.env` file in this directory
2. Replace `your_wolframalpha_app_id_here` with your actual App ID:
   ```bash
   WOLFRAMALPHA_APP_ID=YOUR-ACTUAL-APP-ID-HERE
   ```

### 3. Restart the Services
```bash
# Stop current containers
docker compose down

# Rebuild and start with new configuration
docker compose up --build
```

### 4. Test the WolframAlpha Service
```bash
# Test with the client
docker compose run --rm mcpclient python client.py --call-tool wamcp query "what is 2+2"

# Or test mathematical calculation
docker compose run --rm mcpclient python client.py --call-tool wamcp calculate "integrate x^2 from 0 to 5"
```

## Optional: Test API Key Before Docker

If you want to test your API key before running Docker:

```bash
# Install dependencies (if not already installed)
pip install python-dotenv requests

# Run the test script
python test_wolframalpha_api.py
```

## Troubleshooting

### Common Issues

1. **"Invalid API key"**: Make sure you're using the **App ID**, not an API key
2. **"App ID not found"**: Check that the `.env` file is in the correct directory
3. **"Mathematical calculation failed"**: Usually means the API key is missing or invalid

### Check Container Logs
```bash
# Check WolframAlpha server logs
docker logs wamcp

# Check all service logs
docker compose logs
```

### Verify Environment Variables
```bash
# Check if the environment variable is loaded
docker compose exec wamcp env | grep WOLFRAM
```

## API Key Limits

The free WolframAlpha App ID has usage limits:
- 2,000 queries per month
- Rate limiting may apply

For production use, consider upgrading to a paid plan.

## Support

If you continue having issues:
1. Verify your App ID at [https://developer.wolframalpha.com/portal/myapps](https://developer.wolframalpha.com/portal/myapps)
2. Check the container logs for specific error messages
3. Ensure the `.env` file is properly formatted (no spaces around the `=`)