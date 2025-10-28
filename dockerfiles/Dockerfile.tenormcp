FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY servers/tenor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server code
COPY servers/tenor/ .

# Create a non-root user
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Expose the port
EXPOSE 6700

# Run the server
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "6700"]