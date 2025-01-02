#!/bin/bash

# Setup logging
LOG_DIR="$HOME/.data-hub/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/setup-$(date +%Y%m%d-%H%M%S).log"

# Redirect all output to both console and log file
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

# Log system information
echo "=== System Information ===" >> "$LOG_FILE"
echo "Date: $(date)" >> "$LOG_FILE"
echo "User: $USER" >> "$LOG_FILE"
echo "Hostname: $(hostname)" >> "$LOG_FILE"
echo "OS: $(uname -a)" >> "$LOG_FILE"
echo "Docker Version: $(docker --version 2>/dev/null || echo 'Docker not installed')" >> "$LOG_FILE"
echo "=========================" >> "$LOG_FILE"

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

# Print functions with logging
print_header() {
    local message="=== $1 ==="
    echo -e "\n${BLUE}${BOLD}${message}${NC}\n" | tee -a "$LOG_FILE"
}

print_step() {
    local message="${ARROW} $1"
    echo -e "${CYAN}${message}${NC}" | tee -a "$LOG_FILE"
}

print_success() {
    local message="${CHECK_MARK} $1"
    echo -e "${GREEN}${message}${NC}" | tee -a "$LOG_FILE"
}

print_warning() {
    local message="${WARNING} $1"
    echo -e "${YELLOW}${message}${NC}" | tee -a "$LOG_FILE"
}

print_error() {
    local message="${CROSS_MARK} $1"
    echo -e "${RED}${message}${NC}" | tee -a "$LOG_FILE"
}

print_info() {
    local message="${GEAR} $1"
    echo -e "${MAGENTA}${message}${NC}" | tee -a "$LOG_FILE"
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

# Enhanced error handling function
handle_error() {
    local error_msg="$1"
    local error_details="$2"
    
    print_error "An error occurred during setup!"
    print_error "$error_msg"
    
    if [ -n "$error_details" ]; then
        echo -e "\nError Details:" >> "$LOG_FILE"
        echo "$error_details" >> "$LOG_FILE"
    fi
    
    echo -e "\nSetup failed. Please check the log file at: $LOG_FILE"
    exit 1
}

# Get IP address
get_ip_address() {
    hostname -I | cut -d' ' -f1
}

# Check if script is being run with docker group
in_docker_group() {
    groups | grep -q docker
}

# Log command output
log_cmd_output() {
    local cmd="$1"
    local output
    local exit_code
    
    echo "Executing: $cmd" >> "$LOG_FILE"
    output=$($cmd 2>&1)
    exit_code=$?
    
    echo "Exit code: $exit_code" >> "$LOG_FILE"
    echo "Output:" >> "$LOG_FILE"
    echo "$output" >> "$LOG_FILE"
    echo "---" >> "$LOG_FILE"
    
    return $exit_code
}

# Re-execute script with docker group if needed
if [[ -z "${DOCKER_GROUP_HANDLED}" ]] && ! in_docker_group; then
    print_header "Docker Group Setup"
    print_step "Adding user to docker group..."
    if ! log_cmd_output "sudo usermod -aG docker $USER"; then
        handle_error "Failed to add user to docker group" "$(tail -n 20 "$LOG_FILE")"
    fi
    print_success "User added to docker group"
    
    print_step "Applying group changes..."
    export DOCKER_GROUP_HANDLED=1
    exec sg docker -c "$0 $*"
    exit 0
fi

# Exit immediately if any command fails
set -e

# Print welcome banner
echo -e "\n${BLUE}${BOLD}"
echo "╔═══════════════════════════════════════════╗"
echo "║           Data Hub Setup Wizard           ║"
echo "╚═══════════════════════════════════════════╝${NC}"
echo -e "${CYAN}Preparing your vessel's data infrastructure...${NC}\n"

# Log file location notice
print_info "Setup log file: $LOG_FILE"
echo ""

# Security Check
if [ "$EUID" -eq 0 ]; then 
    handle_error "Please don't run as root. Script will use sudo when needed."
fi

# System Updates
print_header "System Update"
print_step "Updating package lists..."
if ! log_cmd_output "sudo apt update"; then
    handle_error "Failed to update package lists" "$(tail -n 20 "$LOG_FILE")"
fi
print_success "Package lists updated"

print_step "Upgrading system packages..."
if ! log_cmd_output "sudo apt upgrade -y"; then
    handle_error "Failed to upgrade system packages" "$(tail -n 20 "$LOG_FILE")"
fi
print_success "System packages upgraded"

# Package Installation
print_header "Installing Required Packages"
print_step "Installing git, docker, and CAN utilities..."
if ! log_cmd_output "sudo apt install -y git docker.io docker-compose can-utils"; then
    handle_error "Failed to install required packages" "$(tail -n 20 "$LOG_FILE")"
fi
print_success "Required packages installed"

# Docker Setup
print_header "Docker Configuration"
print_step "Starting Docker service..."
if ! log_cmd_output "sudo systemctl start docker"; then
    handle_error "Failed to start Docker service" "$(tail -n 20 "$LOG_FILE")"
fi
print_success "Docker service started"

# Hardware Configuration
print_header "Hardware Configuration"
print_step "Enabling SPI interface..."
if ! log_cmd_output "sudo raspi-config nonint do_spi 0"; then
    handle_error "Failed to enable SPI interface" "$(tail -n 20 "$LOG_FILE")"
fi
print_success "SPI interface enabled"

# PICAN-M HAT Check
print_header "PICAN-M HAT Detection"
log_cmd_output "dmesg | grep mcp251x" || true
if ! dmesg | grep -q "mcp251x spi0.0"; then
    print_warning "PICAN-M HAT not detected!"
    echo -e "${YELLOW}This could be because:${NC}"
    echo -e "  ${CYAN}1. The PICAN-M HAT is not installed${NC}"
    echo -e "  ${CYAN}2. The HAT is not properly seated on the GPIO pins${NC}"
    echo -e "  ${CYAN}3. The system needs a reboot after HAT installation${NC}"
    echo ""
    print_info "The script will continue, but CAN functionality won't work until the HAT is properly installed."
    echo ""
fi

# CAN Configuration
print_header "CAN Interface Configuration"
print_step "Creating network configuration directory..."
if ! log_cmd_output "sudo mkdir -p /etc/network/interfaces.d"; then
    handle_error "Failed to create network configuration directory" "$(tail -n 20 "$LOG_FILE")"
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
    handle_error "Failed to configure CAN interface" "$(tail -n 20 "$LOG_FILE")"
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
    handle_error "Failed to configure kernel modules" "$(tail -n 20 "$LOG_FILE")"
fi
fi
print_success "Kernel modules configured"

# Data Hub Directory Structure
print_header "Creating Data Hub Directory Structure"
print_step "Setting up data hub directories..."

DATA_DIR="$HOME/.data-hub"
GRAFANA_DIR="$HOME/grafana-data"
SIGNALK_DIR="$HOME/.signalk"

# Create data hub directories
mkdir -p "$DATA_DIR/state"
mkdir -p "$DATA_DIR/config/update_service"
mkdir -p "$DATA_DIR/config/system_metrics"
mkdir -p "$DATA_DIR/config/network_monitor"
mkdir -p "$DATA_DIR/backups"

# Create service data directories
mkdir -p "$GRAFANA_DIR"
mkdir -p "$SIGNALK_DIR"

# Copy initial service configurations
print_step "Copying initial service configurations..."
cp services/update_service/settings.yml "$DATA_DIR/config/update_service/"
cp services/system_metrics/settings.yml "$DATA_DIR/config/system_metrics/"
cp services/network_monitor/settings.yml "$DATA_DIR/config/network_monitor/"

# Initialize version state
print_step "Initializing version state..."
if [ -f "version.yml" ]; then
    cp version.yml "$DATA_DIR/state/version"
else
    echo "version: \"1.0.0\"" > "$DATA_DIR/state/version"
fi

# Set base permissions
print_step "Setting base permissions..."
if ! log_cmd_output "sudo chown -R $USER:$USER $DATA_DIR"; then
    handle_error "Failed to set base permissions" "$(tail -n 20 "$LOG_FILE")"
fi
if ! log_cmd_output "sudo chmod -R 755 $DATA_DIR"; then
    handle_error "Failed to set directory permissions" "$(tail -n 20 "$LOG_FILE")"
fi

# Set service-specific permissions
print_step "Setting service permissions..."
if ! log_cmd_output "sudo chown -R 472:472 $GRAFANA_DIR"; then
    handle_error "Failed to set Grafana permissions" "$(tail -n 20 "$LOG_FILE")"
fi
if ! log_cmd_output "sudo chown -R 1000:1000 $SIGNALK_DIR"; then
    handle_error "Failed to set SignalK permissions" "$(tail -n 20 "$LOG_FILE")"
fi

print_success "Data Hub directory structure initialized"

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
    handle_error "Failed to create InfluxDB configuration" "$(tail -n 20 "$LOG_FILE")"
fi
print_success "InfluxDB configured"

# Docker Compose
print_header "Docker Services Configuration"
print_step "Creating docker-compose configuration..."
if ! cat > docker-compose.yml << EOF
version: '3'
services:
  signalk:
    image: ghcr.io/sv-afterglow/data-hub/signalk:latest
    restart: always
    network_mode: host
    volumes:
      - ~/.signalk:/home/node/.signalk
      - /etc/localtime:/etc/localtime:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/signalk"]
      interval: 30s
      timeout: 10s
      retries: 3

  influxdb:
    image: ghcr.io/sv-afterglow/data-hub/influxdb:latest
    restart: always
    ports:
      - "8086:8086"
    volumes:
      - ~/influxdb-data:/var/lib/influxdb
      - ~/influxdb.conf:/etc/influxdb/influxdb.conf:ro
    environment:
      - INFLUXDB_HTTP_AUTH_ENABLED=false
    user: "999:999"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8086/ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  grafana:
    image: ghcr.io/sv-afterglow/data-hub/grafana:latest
    restart: always
    ports:
      - "3001:3000"
    volumes:
      - ~/grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_PATHS_DATA=/var/lib/grafana
      - GF_USERS_ALLOW_SIGN_UP=false
    user: "472:472"
    depends_on:
      - influxdb
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3001/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  system_metrics:
    build:
      context: .
      dockerfile: docker/system_metrics/Dockerfile
    image: ghcr.io/sv-afterglow/data-hub/system_metrics:latest
    restart: always
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /sys/class/thermal:/sys/class/thermal:ro
      - ~/.data-hub/config/system_metrics:/data/config/system_metrics:ro
    depends_on:
      - influxdb

  network_monitor:
    image: ghcr.io/sv-afterglow/data-hub/network_monitor:latest
    restart: always
    network_mode: host
    volumes:
      - ~/.data-hub/config/network_monitor:/data/config/network_monitor:ro
    depends_on:
      - influxdb
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  update_service:
    build:
      context: .
      dockerfile: docker/update_service/Dockerfile
    image: ghcr.io/sv-afterglow/data-hub/update_service:latest
    restart: always
    volumes:
      - ~/.data-hub/config/update_service:/data/config/update_service:ro
      - ~/.data-hub/state:/data/state
      - /var/run/docker.sock:/var/run/docker.sock
    depends_on:
      - influxdb

  watchtower:
    image: containrrr/watchtower
    restart: always
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --cleanup --interval 30
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/v1/metrics"]
      interval: 30s
      timeout: 10s
      retries: 3
EOF
then
    handle_error "Failed to create docker-compose configuration" "$(tail -n 20 "$LOG_FILE")"
fi
print_success "Docker services configured"

# Start Services
print_header "Starting Services"
print_step "Launching Docker containers..."

# Ensure Docker socket has correct permissions
if ! log_cmd_output "sudo chmod 666 /var/run/docker.sock"; then
    handle_error "Failed to set Docker socket permissions" "$(tail -n 20 "$LOG_FILE")"
fi

# Pull images first
print_info "Pulling Docker images (this may take a few minutes)..."
if ! log_cmd_output "docker-compose pull"; then
    handle_error "Failed to pull Docker images" "$(tail -n 20 "$LOG_FILE")"
fi

# Start services
if ! log_cmd_output "docker-compose up -d"; then
    handle_error "Failed to start Docker services" "$(tail -n 20 "$LOG_FILE")"
fi
print_success "Services started successfully"

# Get IP address for instructions
IP_ADDRESS=$(get_ip_address)

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

print_header "Access Information"
echo -e "${CYAN}Your Data Hub is accessible at:${NC}"
echo -e "  ${MAGENTA}Hostname: ${BOLD}data-hub.local${NC}"
echo -e "  ${MAGENTA}IP Address: ${BOLD}${IP_ADDRESS}${NC}"
echo ""
echo -e "${CYAN}Service URLs:${NC}"
echo -e "  ${MAGENTA}SignalK:${NC}"
echo -e "    ${BOLD}http://data-hub.local:3000${NC}"
echo -e "    ${BOLD}http://${IP_ADDRESS}:3000${NC}"
echo ""
echo -e "  ${MAGENTA}Grafana:${NC}"
echo -e "    ${BOLD}http://data-hub.local:3001${NC}"
echo -e "    ${BOLD}http://${IP_ADDRESS}:3001${NC}"
echo ""
echo -e "  ${MAGENTA}InfluxDB:${NC}"
echo -e "    ${BOLD}http://data-hub.local:8086${NC}"
echo -e "    ${BOLD}http://${IP_ADDRESS}:8086${NC}"
echo ""

print_header "Next Steps"
echo -e "${CYAN}1. Verify installation:${NC}"
echo -e "   ${BOLD}docker-compose ps${NC}"
echo -e "${CYAN}2. Configure SignalK to store data in InfluxDB:${NC}"
echo -e "   ${MAGENTA}- Visit ${BOLD}http://data-hub.local:3000/admin${NC}"
echo -e "   ${MAGENTA}- Install ${BOLD}@signalk/signalk-to-influxdb${NC}${MAGENTA} plugin${NC}"
echo -e "   ${MAGENTA}- Configure with:${NC}"
echo -e "     ${BOLD}Host: influxdb${NC}"
echo -e "     ${BOLD}Port: 8086${NC}"
echo -e "     ${BOLD}Database: signalk${NC}"
echo -e "${CYAN}3. View System Metrics:${NC}"
echo -e "   ${MAGENTA}- Visit ${BOLD}http://data-hub.local:3001${NC}"
echo -e "   ${MAGENTA}- Navigate to the System Metrics dashboard${NC}"
echo -e "   ${MAGENTA}- Monitor CPU, Memory, and System Load${NC}"
echo ""
print_warning "Please reboot your system to complete the setup."
echo ""

print_info "Setup completed. Full logs available at: $LOG_FILE"
