#!/bin/bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up build environment...${NC}"

# Create required directories
mkdir -p ~/data-hub/services/update-service
mkdir -p ~/data-hub/services/system-metrics
mkdir -p ~/data-hub/docker/update-service
mkdir -p ~/data-hub/docker/system-metrics

# Download service files
echo "Downloading service files..."
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/services/update-service/updater.py" > ~/data-hub/services/update-service/updater.py
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/services/update-service/requirements.txt" > ~/data-hub/services/update-service/requirements.txt
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/services/system-metrics/collector.py" > ~/data-hub/services/system-metrics/collector.py
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/services/system-metrics/requirements.txt" > ~/data-hub/services/system-metrics/requirements.txt

# Download Dockerfiles
echo "Downloading Dockerfiles..."
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/docker/update-service/Dockerfile" > ~/data-hub/docker/update-service/Dockerfile
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/docker/system-metrics/Dockerfile" > ~/data-hub/docker/system-metrics/Dockerfile

# Download docker-compose.yml
echo "Downloading docker-compose.yml..."
curl -s "https://raw.githubusercontent.com/sv-afterglow/data-hub/main/docker/compose/docker-compose.yaml" > ~/data-hub/docker-compose.yml

# Make scripts executable
chmod +x ~/data-hub/services/update-service/updater.py
chmod +x ~/data-hub/services/system-metrics/collector.py

echo -e "${GREEN}Build environment setup complete!${NC}"
