# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY ./servers/wolframalpha/requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server script into the container at /app
COPY ./servers/wolframalpha/server.py /app/server.py
COPY servers/wolframalpha/.env .

EXPOSE 6700

# Run wolframalpha_server.py when the container launches
CMD ["python", "server.py","--host", "0.0.0.0", "--port", "6700"]
