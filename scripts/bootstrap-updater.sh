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

# Add update service to main docker-compose.yml
echo "Adding update service to docker-compose.yml..."
if [ -f docker-compose.yml ]; then
    # Check if update-service is already in the file
    if ! grep -q "update-service:" docker-compose.yml; then
        # Add two newlines and the update-service configuration
        echo -e "\n  update-service:\n\
    build:\n\
      context: ~/.data-hub/update-service\n\
      dockerfile: Dockerfile\n\
    image: ghcr.io/sv-afterglow/data-hub/update-service:latest\n\
    restart: always\n\
    volumes:\n\
      - /var/run/docker.sock:/var/run/docker.sock\n\
      - /etc:/etc:ro\n\
      - ~/.data-hub:/data\n\
    environment:\n\
      - GITHUB_REPO=sv-afterglow/data-hub\n\
      - GITHUB_BRANCH=main\n\
      - UPDATE_CHECK_INTERVAL=3600" >> docker-compose.yml
    fi
else
    echo -e "${RED}docker-compose.yml not found in current directory${NC}"
    exit 1
fi

# Build and start the update service
echo "Building update service..."
if ! docker-compose build update-service; then
    echo -e "${RED}Failed to build update service${NC}"
    exit 1
fi

echo "Starting update service..."
if ! docker-compose up -d update-service; then
    echo -e "${RED}Failed to start update service${NC}"
    exit 1
fi

echo -e "${GREEN}Update service successfully installed!${NC}"
echo "The update service will now:"
echo "1. Check for updates every hour"
echo "2. Download and apply updates automatically"
echo "3. Handle rollbacks if updates fail"
echo ""
echo -e "${YELLOW}Note: You may need to wait up to an hour for the first update check,${NC}"
echo -e "${YELLOW}or you can restart the service to check immediately:${NC}"
echo "docker-compose restart update-service"
