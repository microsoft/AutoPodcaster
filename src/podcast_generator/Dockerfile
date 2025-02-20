# Use the official Python base image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Install system dependencies for Azure Speech SDK
RUN apt-get update && apt-get install -y \
    build-essential \
    libasound2 \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    libpulse0 \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . .

# Specify the command to run the application
CMD ["python", "podcast_generator.py"]