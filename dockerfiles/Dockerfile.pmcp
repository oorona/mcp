# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY ./servers/piston/requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server script into the container at /app
COPY ./servers/piston/server.py /app/server.py

EXPOSE 6700

# Define environment variables (defaults, can be overridden in docker-compose)
ENV PISTON_API_BASE_URL="https://emkc.org/api/v2/piston"
ENV LOG_LEVEL="INFO"
# Run server.py when the container launches
CMD ["python", "server.py","--host", "0.0.0.0", "--port", "6700"]