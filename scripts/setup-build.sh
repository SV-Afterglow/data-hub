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

# Create docker-compose.yml with correct paths
echo "Creating docker-compose.yml..."
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  update-service:
    build:
      context: .
      dockerfile: docker/update-service/Dockerfile
    restart: always
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /etc:/etc:ro
      - ~/.data-hub:/data
      - .:/home/admin/data-hub
    environment:
      - GITHUB_REPO=sv-afterglow/data-hub
      - GITHUB_BRANCH=main
      - UPDATE_CHECK_INTERVAL=3600
      - INFLUX_URL=http://influxdb:8086
      - HOME=/home/admin
    networks:
      - data-hub
    depends_on:
      - influxdb

  system-metrics:
    build:
      context: .
      dockerfile: docker/system-metrics/Dockerfile
    restart: always
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /sys/class/thermal:/sys/class/thermal:ro
    environment:
      - INFLUX_URL=http://influxdb:8086
      - COLLECTION_INTERVAL=10
    depends_on:
      - influxdb
    networks:
      - data-hub

  influxdb:
    image: influxdb:1.8
    restart: always
    ports:
      - "8086:8086"
    volumes:
      - ~/influxdb-data:/var/lib/influxdb
    environment:
      - INFLUXDB_DB=signalk
      - INFLUXDB_HTTP_AUTH_ENABLED=false
    networks:
      - data-hub
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8086/ping"]
      interval: 5s
      timeout: 3s
      retries: 3
      start_period: 5s

  grafana:
    image: grafana/grafana:latest
    restart: always
    ports:
      - "3001:3000"
    volumes:
      - ~/grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - influxdb
    networks:
      - data-hub

  watchtower:
    image: containrrr/watchtower
    restart: always
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --cleanup --interval 30
    networks:
      - data-hub

networks:
  data-hub:
    driver: bridge
EOF

# Make scripts executable
chmod +x services/update-service/updater.py
chmod +x services/system-metrics/collector.py

echo -e "${GREEN}Build environment setup complete!${NC}"
echo -e "${YELLOW}Starting services...${NC}"

# Start InfluxDB first and wait for it to be healthy
docker-compose up -d influxdb
echo "Waiting for InfluxDB to be healthy..."
until curl -s http://localhost:8086/ping > /dev/null; do
    echo -n "."
    sleep 1
done
echo -e "\nInfluxDB is ready"

# Start the update service
echo "Starting update service..."
docker-compose up -d update-service

echo -e "${GREEN}Services started!${NC}"
echo -e "${YELLOW}To check the update service logs:${NC}"
echo "docker-compose logs -f update-service"
