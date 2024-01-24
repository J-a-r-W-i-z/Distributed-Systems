# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY ./server.py /app

# Run server.py when the container launches
CMD ["python", "-u", "server.py"]
