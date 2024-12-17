#!/bin/bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Unicode symbols
CHECK_MARK="\xE2\x9C\x94"
CROSS_MARK="\xE2\x9C\x98"
ARROW="\xE2\x9E\xA4"
GEAR="\xE2\x9A\x99"
WARNING="\xE2\x9A\xA0"
ROCKET="\xF0\x9F\x9A\x80"

# Print functions
print_header() {
    echo -e "\n${BLUE}${BOLD}=== $1 ===${NC}\n"
}

print_step() {
    echo -e "${CYAN}${ARROW} $1${NC}"
}

print_success() {
    echo -e "${GREEN}${CHECK_MARK} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
}

print_error() {
    echo -e "${RED}${CROSS_MARK} $1${NC}"
}

print_info() {
    echo -e "${MAGENTA}${GEAR} $1${NC}"
}

# Progress spinner
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# Error handling function
handle_error() {
    print_error "An error occurred during setup!"
    print_error "$1"
    exit 1
}

# Exit immediately if any command fails
set -e

# Print welcome banner
echo -e "\n${BLUE}${BOLD}"
echo "╔═══════════════════════════════════════════╗"
echo "║           Data Hub Setup Wizard           ║"
echo "╚═══════════════════════════════════════════╝${NC}"
echo -e "${CYAN}Preparing your vessel's data infrastructure...${NC}\n"

# Security Check
if [ "$EUID" -eq 0 ]; then 
    print_error "Please don't run as root. Script will use sudo when needed."
    exit 1
fi

# System Updates
print_header "System Update"
print_step "Updating package lists..."
if ! sudo apt update > /dev/null 2>&1; then
    handle_error "Failed to update package lists"
fi
print_success "Package lists updated"

print_step "Upgrading system packages..."
if ! sudo apt upgrade -y > /dev/null 2>&1; then
    handle_error "Failed to upgrade system packages"
fi
print_success "System packages upgraded"

# Package Installation
print_header "Installing Required Packages"
print_step "Installing git, docker, and CAN utilities..."
if ! sudo apt install -y git docker.io docker-compose can-utils > /dev/null 2>&1; then
    handle_error "Failed to install required packages"
fi
print_success "Required packages installed"

# Docker Setup
print_header "Docker Configuration"
print_step "Setting up Docker permissions..."
if ! sudo usermod -aG docker $USER; then
    handle_error "Failed to add user to docker group"
fi
print_success "Docker permissions configured"

print_step "Starting Docker service..."
if ! sudo systemctl start docker; then
    handle_error "Failed to start Docker service"
fi
print_success "Docker service started"

# Hardware Configuration
print_header "Hardware Configuration"
print_step "Enabling SPI interface..."
if ! sudo raspi-config nonint do_spi 0; then
    handle_error "Failed to enable SPI interface"
fi
print_success "SPI interface enabled"

# PICAN-M HAT Check
print_header "PICAN-M HAT Detection"
if ! dmesg | grep -q "mcp251x spi0.0"; then
    print_warning "PICAN-M HAT not detected!"
    echo -e "${YELLOW}This could be because:${NC}"
    echo -e "  ${CYAN}1. The PICAN-M HAT is not installed${NC}"
    echo -e "  ${CYAN}2. The HAT is not properly seated on the GPIO pins${NC}"
    echo -e "  ${CYAN}3. The system needs a reboot after HAT installation${NC}"
    echo ""
    print_info "The script will continue, but CAN functionality won't work until the HAT is properly installed."
    echo ""
    read -p "$(echo -e ${BLUE}Press Enter to continue or Ctrl+C to exit...${NC})"
fi

# CAN Configuration
print_header "CAN Interface Configuration"
print_step "Creating network configuration directory..."
if ! sudo mkdir -p /etc/network/interfaces.d; then
    handle_error "Failed to create network configuration directory"
fi

print_step "Configuring CAN interface..."
if ! sudo tee /etc/network/interfaces.d/can0 > /dev/null << EOF
auto can0
iface can0 inet manual
    pre-up /sbin/ip link set can0 type can bitrate 250000
    up /sbin/ip link set can0 up
    down /sbin/ip link set can0 down
EOF
then
    handle_error "Failed to configure CAN interface"
fi
print_success "CAN interface configured"

# Kernel Modules
print_header "Kernel Module Configuration"
print_step "Setting up CAN kernel modules..."
if ! grep -q "mcp251x" /etc/modules; then
    if ! sudo tee -a /etc/modules > /dev/null << EOF
mcp251x
can_dev
can
can_raw
EOF
then
    handle_error "Failed to configure kernel modules"
fi
fi
print_success "Kernel modules configured"

# Data Directories
print_header "Creating Data Directories"
print_step "Setting up service directories..."
mkdir -p ~/influxdb-data ~/.signalk ~/grafana-data || handle_error "Failed to create data directories"
print_success "Data directories created"

# InfluxDB Configuration
print_header "InfluxDB Configuration"
print_step "Creating InfluxDB configuration..."
if ! cat > ~/influxdb.conf << EOF
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
then
    handle_error "Failed to create InfluxDB configuration"
fi
print_success "InfluxDB configured"

# Docker Compose
print_header "Docker Services Configuration"
print_step "Creating docker-compose configuration..."
if ! cat > docker-compose.yml << EOF
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
then
    handle_error "Failed to create docker-compose configuration"
fi
print_success "Docker services configured"

# Start Services
print_header "Starting Services"
print_step "Launching Docker containers..."

# Ensure Docker socket has correct permissions
sudo chmod 666 /var/run/docker.sock || handle_error "Failed to set Docker socket permissions"

# Pull images first
print_info "Pulling Docker images (this may take a few minutes)..."
if ! docker-compose pull > /dev/null 2>&1; then
    handle_error "Failed to pull Docker images"
fi

# Start services
if ! docker-compose up -d > /dev/null 2>&1; then
    handle_error "Failed to start Docker services"
fi
print_success "Services started successfully"

# Setup Complete
echo -e "\n${GREEN}${BOLD}╔═══════════════════════════════════════════╗"
echo "║           Setup Complete! ${ROCKET}              ║"
echo -e "╚═══════════════════════════════════════════╝${NC}\n"

if ! dmesg | grep -q "mcp251x spi0.0"; then
    print_header "PICAN-M HAT Installation Instructions"
    echo -e "${YELLOW}${BOLD}The PICAN-M HAT was not detected during setup!${NC}"
    echo -e "${CYAN}After installing the HAT:${NC}"
    echo -e "  ${MAGENTA}1. Power off the Raspberry Pi${NC}"
    echo -e "  ${MAGENTA}2. Install the PICAN-M HAT on the GPIO pins${NC}"
    echo -e "  ${MAGENTA}3. Power on and wait for boot${NC}"
    echo -e "  ${MAGENTA}4. Run: ${BOLD}sudo modprobe mcp251x${NC}"
    echo -e "  ${MAGENTA}5. Check CAN interface: ${BOLD}ip link show can0${NC}"
    echo -e "  ${MAGENTA}6. Monitor NMEA2000 traffic: ${BOLD}candump can0${NC}"
    echo ""
fi

print_header "Next Steps"
echo -e "${CYAN}1. Verify installation:${NC}"
echo -e "   ${BOLD}docker-compose ps${NC}"
echo -e "${CYAN}2. Configure SignalK to store data in InfluxDB:${NC}"
echo -e "   ${MAGENTA}- Visit ${BOLD}http://localhost:3000/admin${NC}"
echo -e "   ${MAGENTA}- Install ${BOLD}@signalk/signalk-to-influxdb${NC}${MAGENTA} plugin${NC}"
echo -e "   ${MAGENTA}- Configure with:${NC}"
echo -e "     ${BOLD}Host: influxdb${NC}"
echo -e "     ${BOLD}Port: 8086${NC}"
echo -e "     ${BOLD}Database: signalk${NC}"
echo ""
print_warning "Please reboot your system to complete the setup."
echo ""
