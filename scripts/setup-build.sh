#!/bin/bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up build environment...${NC}"

cd ~/data-hub

# Create required directories
mkdir -p services/update-service
mkdir -p services/system-metrics
mkdir -p docker/update-service
mkdir -p docker/system-metrics

# Download service files
echo "Downloading service files..."
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/services/update-service/updater.py" > services/update-service/updater.py
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/services/update-service/requirements.txt" > services/update-service/requirements.txt
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/services/system-metrics/collector.py" > services/system-metrics/collector.py
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/services/system-metrics/requirements.txt" > services/system-metrics/requirements.txt

# Download Dockerfiles
echo "Downloading Dockerfiles..."
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/docker/update-service/Dockerfile" > docker/update-service/Dockerfile
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/docker/system-metrics/Dockerfile" > docker/system-metrics/Dockerfile

# Download docker-compose.yml
echo "Downloading docker-compose.yml..."
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/docker/compose/docker-compose.yaml" > docker-compose.yml

# Make scripts executable
chmod +x services/update-service/updater.py
chmod +x services/system-metrics/collector.py

echo -e "${GREEN}Build environment setup complete!${NC}"
echo -e "${YELLOW}You can now run:${NC}"
echo "docker-compose build update-service"
echo "docker-compose up -d"
