#!/bin/bash
set -e  # Exit on any error

echo "Starting Data Hub setup..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
  echo "Please don't run as root. Script will use sudo when needed."
  exit 1
fi

# System updates
echo "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install required packages
echo "Installing required packages..."
sudo apt install -y \
    git \
    docker.io \
    docker-compose \
    can-utils

# Add user to docker group
sudo usermod -aG docker $USER

# Configure SPI interface
echo "Enabling SPI interface..."
sudo raspi-config nonint do_spi 0

# Setup CAN interface
echo "Configuring CAN interface..."
sudo tee /etc/network/interfaces.d/can0 << EOF
auto can0
iface can0 inet manual
    pre-up /sbin/ip link set can0 type can bitrate 250000
    up /sbin/ip link set can0 up
    down /sbin/ip link set can0 down
EOF

# Configure kernel modules
echo "Setting up kernel modules..."
if ! grep -q "mcp251x" /etc/modules; then
    sudo tee -a /etc/modules << EOF
mcp251x
can_dev
can
can_raw
EOF
fi

# Create directories for persistent data
echo "Creating data directories..."
mkdir -p ~/influxdb-data
mkdir -p ~/.signalk
mkdir -p ~/grafana-data

# Create InfluxDB configuration
echo "Configuring InfluxDB..."
cat > ~/influxdb.conf << EOF
[meta]
  dir = "/var/lib/influxdb/meta"

[data]
  dir = "/var/lib/influxdb/data"
  wal-dir = "/var/lib/influxdb/wal"

[http]
  enabled = true
  bind-address = ":8086"
  auth-enabled = false
EOF

# Create docker-compose file with InfluxDB
echo "Creating docker-compose configuration..."
cat > docker-compose.yml << EOF
version: '3'
services:
  signalk:
    image: signalk/signalk-server:latest
    restart: always
    network_mode: host
    volumes:
      - ~/.signalk:/home/node/.signalk
      - /etc/localtime:/etc/localtime:ro

  influxdb:
    image: influxdb:1.8
    restart: always
    ports:
      - "8086:8086"
    volumes:
      - ~/influxdb-data:/var/lib/influxdb
      - ~/influxdb.conf:/etc/influxdb/influxdb.conf:ro
    environment:
      - INFLUXDB_DB=signalk
      - INFLUXDB_HTTP_AUTH_ENABLED=false

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

  watchtower:
    image: containrrr/watchtower
    restart: always
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --cleanup --interval 30
EOF

# Start docker services
echo "Starting services..."
docker-compose up -d

echo "Setup complete! Please reboot your system."
echo "After reboot:"
echo "1. Verify installation with: docker-compose ps"
echo "2. Configure SignalK to store data in InfluxDB:"
echo "   - Visit http://localhost:3000/admin"
echo "   - Install @signalk/signalk-to-influxdb plugin"
echo "   - Configure the plugin with:"
echo "     Host: influxdb"
echo "     Port: 8086"
echo "     Database: signalk"
