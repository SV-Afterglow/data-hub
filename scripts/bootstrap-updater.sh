#!/bin/bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Bootstrap Update Service Installation${NC}"
echo "This script will install the update service on your device."

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}Please don't run as root. Script will use sudo when needed.${NC}"
    exit 1
fi

# Ensure docker is installed and running
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! systemctl is-active --quiet docker; then
    echo -e "${YELLOW}Docker is not running. Starting Docker...${NC}"
    sudo systemctl start docker
fi

# Clean up any existing update services
echo "Cleaning up existing update services..."
docker stop data-hub_update-service_1 update-service_update-service_1 2>/dev/null || true
docker rm data-hub_update-service_1 update-service_update-service_1 2>/dev/null || true
rm -f ~/docker-compose.yml

# Create required directories
echo "Creating directories..."
mkdir -p ~/.data-hub/update-service

# Download the update service files
echo "Downloading update service files..."
REPO="sv-afterglow/data-hub"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/$REPO/$BRANCH"

# Download files to the update service directory
curl -s "$BASE_URL/services/update-service/requirements.txt" > ~/.data-hub/update-service/requirements.txt
curl -s "$BASE_URL/services/update-service/updater.py" > ~/.data-hub/update-service/updater.py
curl -s "$BASE_URL/version.yml" > ~/.data-hub/version.yml

# Create update service compose file
cat > ~/.data-hub/update-service/docker-compose.yaml << 'EOF'
version: '2'

services:
  update-service:
    build: .
    container_name: data-hub_update-service_1
    restart: always
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /etc:/etc:ro
      - ~/.data-hub:/data
    environment:
      - GITHUB_REPO=sv-afterglow/data-hub
      - GITHUB_BRANCH=main
      - UPDATE_CHECK_INTERVAL=3600
      - INFLUX_URL=http://influxdb:8086
    networks:
      - data-hub

networks:
  data-hub:
    external:
      name: data-hub_default
EOF

# Create Dockerfile for update service
cat > ~/.data-hub/update-service/Dockerfile << 'EOF'
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY updater.py .

# Make script executable
RUN chmod +x updater.py

CMD ["./updater.py"]
EOF

# Verify downloads
if [ ! -f ~/.data-hub/update-service/requirements.txt ] || [ ! -f ~/.data-hub/update-service/updater.py ]; then
    echo -e "${RED}Failed to download required files${NC}"
    exit 1
fi

# Build and start the update service
echo "Building and starting update service..."
cd ~/.data-hub/update-service
if ! docker-compose up -d; then
    echo -e "${RED}Failed to start update service${NC}"
    exit 1
fi

echo -e "${GREEN}Update service successfully installed!${NC}"
echo "The update service will now:"
echo "1. Check for updates every hour"
echo "2. Download and apply updates automatically"
echo "3. Handle rollbacks if updates fail"
echo ""
echo -e "${YELLOW}To check the update service logs:${NC}"
echo "docker-compose -f ~/.data-hub/update-service/docker-compose.yaml logs -f"
echo ""
echo -e "${YELLOW}To restart the service:${NC}"
echo "docker-compose -f ~/.data-hub/update-service/docker-compose.yaml restart"
