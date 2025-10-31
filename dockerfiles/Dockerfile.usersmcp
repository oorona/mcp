# Dockerfile.mcp
# Dockerfile

# 1. Use an official Python runtime as a parent image
FROM python:3.11-slim AS base

# 2. Set environment variables
ENV PYTHONUNBUFFERED=1

# 3. Set the working directory in the container
WORKDIR /app

# 4. Copy the requirements file and install dependencies

COPY servers/usercontext/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Copy the application code into the container
COPY servers/usercontext/server.py . 
# Copy the environment file
COPY servers/usercontext/.env .


# 6. Expose the port the app runs on
EXPOSE 6700

# 7. Define the command to run the application
CMD ["python", "server.py","--host", "0.0.0.0", "--port", "6700"]
