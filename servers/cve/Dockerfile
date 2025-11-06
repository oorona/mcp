# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY servers/cve/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the CVE server code
COPY servers/cve/ .

# Expose the port
EXPOSE 6700

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CVE_MCP_PORT=6700

# Run the server
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "6700"]