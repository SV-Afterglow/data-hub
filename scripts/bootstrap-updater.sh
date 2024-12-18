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

# Download the update service files
echo "Downloading update service files..."
REPO="sv-afterglow/data-hub"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/$REPO/$BRANCH"

# Create temporary directory
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# Download necessary files
curl -s "$BASE_URL/services/update-service/requirements.txt" > "$TMP_DIR/requirements.txt"
curl -s "$BASE_URL/services/update-service/updater.py" > "$TMP_DIR/updater.py"
curl -s "$BASE_URL/docker/update-service/Dockerfile" > "$TMP_DIR/Dockerfile"
curl -s "$BASE_URL/version.yml" > ~/.data-hub/version.yml

# Create docker-compose file for update service
cat > "$TMP_DIR/docker-compose.yml" << EOF
version: '3.8'

services:
  update-service:
    build:
      context: .
      dockerfile: Dockerfile
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

# Build and start the update service
echo "Building update service..."
cd "$TMP_DIR"
if ! docker-compose build; then
    echo -e "${RED}Failed to build update service${NC}"
    exit 1
fi

echo "Starting update service..."
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
echo -e "${YELLOW}Note: You may need to wait up to an hour for the first update check,${NC}"
echo -e "${YELLOW}or you can restart the service to check immediately:${NC}"
echo "docker-compose restart update-service"

# Cleanup
cd - > /dev/null
