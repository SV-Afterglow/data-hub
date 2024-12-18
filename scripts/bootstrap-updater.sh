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
mkdir -p ~/.data-hub

# Download the version file if it doesn't exist
if [ ! -f ~/.data-hub/version.yml ]; then
    echo "Downloading initial version file..."
    curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/version.yml" > ~/.data-hub/version.yml
fi

# Check if docker-compose.yml exists, if not download the initial version
if [ ! -f ~/data-hub/docker-compose.yml ]; then
    echo "Downloading initial docker-compose.yml..."
    mkdir -p ~/data-hub
    curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/docker/compose/docker-compose.yaml" > ~/data-hub/docker-compose.yml
fi

# Start or restart the services using docker-compose
echo "Starting services..."
cd ~/data-hub
docker-compose pull
docker-compose up -d

echo -e "${GREEN}Update service successfully installed!${NC}"
echo "The update service will now:"
echo "1. Check for updates every hour"
echo "2. Download and apply updates automatically"
echo "3. Handle rollbacks if updates fail"
echo ""
echo -e "${YELLOW}To check the update service logs:${NC}"
echo "docker-compose -f ~/data-hub/docker-compose.yml logs -f update-service"
echo ""
echo -e "${YELLOW}To restart all services:${NC}"
echo "docker-compose -f ~/data-hub/docker-compose.yml restart"
