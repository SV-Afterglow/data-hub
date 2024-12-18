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

# Create required directories
echo "Creating directories..."
mkdir -p ~/.data-hub/backups
mkdir -p ~/.data-hub/update-service

# Download the update service files
echo "Downloading update service files..."
REPO="sv-afterglow/data-hub"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/$REPO/$BRANCH"

# Download files to the permanent location
curl -s "$BASE_URL/services/update-service/requirements.txt" > ~/.data-hub/update-service/requirements.txt
curl -s "$BASE_URL/services/update-service/updater.py" > ~/.data-hub/update-service/updater.py
curl -s "$BASE_URL/version.yml" > ~/.data-hub/version.yml

# Verify downloads
if [ ! -f ~/.data-hub/update-service/requirements.txt ] || [ ! -f ~/.data-hub/update-service/updater.py ]; then
    echo -e "${RED}Failed to download required files${NC}"
    exit 1
fi

# Create Dockerfile in the update-service directory
cat > ~/.data-hub/update-service/Dockerfile << 'EOF'
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
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

# Create temporary docker-compose file for building
cat > ~/.data-hub/update-service/docker-compose.build.yml << EOF
version: '3.8'
services:
  update-service:
    build: .
    image: ghcr.io/sv-afterglow/data-hub/update-service:latest
EOF

# Build the image first
echo "Building update service..."
cd ~/.data-hub/update-service
if ! docker-compose -f docker-compose.build.yml build; then
    echo -e "${RED}Failed to build update service${NC}"
    exit 1
fi

# Return to original directory
cd - > /dev/null

# Add update service to main docker-compose.yml
echo "Adding update service to docker-compose.yml..."
if [ -f docker-compose.yml ]; then
    # Create backup of original docker-compose.yml
    cp docker-compose.yml docker-compose.yml.bak
    
    # Remove any existing update-service configuration
    sed -i '/update-service:/,/^[^ ]/d' docker-compose.yml
    
    # Add update-service configuration
    cat >> docker-compose.yml << EOF

  update-service:
    image: ghcr.io/sv-afterglow/data-hub/update-service:latest
    restart: always
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /etc:/etc:ro
      - ~/.data-hub:/data
    environment:
      - GITHUB_REPO=sv-afterglow/data-hub
      - GITHUB_BRANCH=main
      - UPDATE_CHECK_INTERVAL=3600
EOF
else
    echo -e "${RED}docker-compose.yml not found in current directory${NC}"
    exit 1
fi

echo "Starting update service..."
if ! docker-compose up -d update-service; then
    echo -e "${RED}Failed to start update service${NC}"
    # Restore backup if start failed
    mv docker-compose.yml.bak docker-compose.yml
    exit 1
fi

# Clean up backup if everything succeeded
rm -f docker-compose.yml.bak

echo -e "${GREEN}Update service successfully installed!${NC}"
echo "The update service will now:"
echo "1. Check for updates every hour"
echo "2. Download and apply updates automatically"
echo "3. Handle rollbacks if updates fail"
echo ""
echo -e "${YELLOW}To check the update service logs:${NC}"
echo "docker-compose logs -f update-service"
echo ""
echo -e "${YELLOW}To restart the service:${NC}"
echo "docker-compose restart update-service"
