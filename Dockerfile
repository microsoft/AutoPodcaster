FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
#COPY . /app

# Install Tree-sitter and its language parsers
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*


# Install any needed packages specified in requirements.txt
# Copy the current directory contents into the container at /app
#COPY . /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY .env .
# Make port 8888 available to the world outside this container
EXPOSE 8888

# Run main.py when the container launches
#CMD ["python", "main.py"]
#CMD ["tail", "-f", "/dev/null"]
# Run Jupyter Notebook when the container launches
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]