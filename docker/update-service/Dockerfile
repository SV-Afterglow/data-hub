FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    && apt-get clean

# Install Docker Compose plugin
RUN mkdir -p /usr/local/lib/docker/cli-plugins && \
    curl -SL https://github.com/docker/compose/releases/download/v2.23.3/docker-compose-linux-aarch64 -o /usr/local/lib/docker/cli-plugins/docker-compose && \
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY services/update-service/requirements.txt .

# Force pure Python implementation of msgpack
ENV MSGPACK_PUREPYTHON=1

# Install dependencies and psutil
RUN pip install --no-cache-dir -r requirements.txt psutil

# Copy service code
COPY services/update-service/updater.py .

# Make script executable
RUN chmod +x updater.py

CMD ["./updater.py"]
