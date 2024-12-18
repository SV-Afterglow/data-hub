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

# Download files directly to the mounted data directory
curl -s "$BASE_URL/services/update-service/requirements.txt" > ~/.data-hub/requirements.txt
curl -s "$BASE_URL/services/update-service/updater.py" > ~/.data-hub/updater.py
curl -s "$BASE_URL/version.yml" > ~/.data-hub/version.yml

# Download docker-compose.yaml to the correct location
COMPOSE_DIR="docker/compose"
mkdir -p "$COMPOSE_DIR"
curl -s "$BASE_URL/docker/compose/docker-compose.yaml" > "$COMPOSE_DIR/docker-compose.yaml"

# Verify downloads
if [ ! -f ~/.data-hub/requirements.txt ] || [ ! -f ~/.data-hub/updater.py ]; then
    echo -e "${RED}Failed to download required files${NC}"
    exit 1
fi

echo "Starting services..."
if ! docker-compose -f "$COMPOSE_DIR/docker-compose.yaml" up -d; then
    echo -e "${RED}Failed to start services${NC}"
    exit 1
fi

echo -e "${GREEN}Update service successfully installed!${NC}"
echo "The update service will now:"
echo "1. Check for updates every hour"
echo "2. Download and apply updates automatically"
echo "3. Handle rollbacks if updates fail"
echo ""
echo -e "${YELLOW}To check the update service logs:${NC}"
echo "docker-compose -f docker/compose/docker-compose.yaml logs -f update-service"
echo ""
echo -e "${YELLOW}To restart the service:${NC}"
echo "docker-compose -f docker/compose/docker-compose.yaml restart update-service"
