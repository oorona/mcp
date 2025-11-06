# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file for the giphy server
COPY servers/giphy/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Giphy server code into the container
# It will be copied to /app/servers/giphy
COPY servers/giphy/server.py . 
# Copy the environment file
COPY servers/giphy/.env .


# Make GIPHY_MCP_SERVER_PORT available
EXPOSE 6700

# Define environment variables
ENV PYTHONUNBUFFERED 1
ENV GIPHY_MCP_SERVER_PORT=6700
# GIPHY_API_KEY should be set via docker-compose

# Run server.py when the container launches
CMD ["python", "server.py","--host", "0.0.0.0", "--port", "6700"]