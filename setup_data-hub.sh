#!/usr/bin/env bash
#
# setup_data-hub.sh
#
# This script automates the initial setup of the "Data Hub" environment on a fresh Raspberry Pi OS Lite
# (or similar Debian-based system). It installs Docker, Docker Compose, creates necessary directories,
# and updates user permissions so you can run "data-hub" services smoothly.
#
# OVERVIEW
# -----------------------------------------------------------------------------
# 1. Updates System Packages
#    - Performs apt-get update & upgrade (optional, but recommended).
# 2. Installs Docker & Docker Compose
#    - Fetches Docker using the official convenience script.
#    - Installs Docker Compose (if not present), or upgrades it if older.
#    - Adds the "pi" (or current) user to the "docker" group for passwordless usage.
# 3. Creates Data Hub Directories (~/.data-hub)
#    - config/    - Holds service configs (SignalK, InfluxDB, Grafana, etc.).
#    - state/     - Tracks version state, updates history, etc.
#    - backups/   - Stores backup archives before major updates.
# 4. (Optional) Additional customizations or placeholders for future expansions.
#
# NOTE: This script is meant as a temporary measure if you're not using a
#       fully custom Pi image. In production, consider building a pre-configured
#       OS image instead.
#
# ------------------------------------------------------------------------------
# COLOR CODING FOR GORGEOUS TERMINAL OUTPUT
GREEN="\033[0;32m"
BLUE="\033[0;34m"
BOLD="\033[1m"
RESET="\033[0m"

# Ensure this script is run with bash
if [ -z "$BASH_VERSION" ]; then
  echo "Please run this script with bash!"
  exit 1
fi

# Detect current user (often 'pi' on Raspberry Pi OS)
CURRENT_USER="$(whoami)"
if [ "$CURRENT_USER" == "root" ]; then
  echo -e "${BLUE}[INFO]${RESET} Running as root. We'll still proceed, but remember to adjust 'usermod' calls if needed."
fi

# ASCII Art Header (Make it gorgeous!)
cat << "EOF"

██████╗  █████╗ ████████╗ █████╗     ██╗  ██╗██╗   ██╗██████╗ 
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗    ██║  ██║██║   ██║██╔══██╗
██║  ██║███████║   ██║   ███████║    ███████║██║   ██║██████╔╝
██║  ██║██╔══██║   ██║   ██╔══██║    ██╔══██║██║   ██║██╔══██╗
██████╔╝██║  ██║   ██║   ██║  ██║    ██║  ██║╚██████╔╝██████╔╝
╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ 

        DATA HUB QUICK SETUP SCRIPT
------------------------------------------------------------
EOF

echo -e "${BOLD}Welcome to the Data Hub Setup Script!${RESET}"
echo -e "We'll now ensure your Raspberry Pi (or Debian system) is prepared to run Data Hub containers.\n"

# ------------------------------------------------------------------------------
# STEP 1: SYSTEM UPDATE & UPGRADE (Optional, but recommended)
# ------------------------------------------------------------------------------
echo -e "${BLUE}[STEP 1]${RESET} Updating system packages (apt-get update & upgrade)..."
sudo apt-get update -y && sudo apt-get upgrade -y
echo -e "${GREEN}[OK]${RESET} System packages updated.\n"

# ------------------------------------------------------------------------------
# STEP 2: INSTALL DOCKER
# ------------------------------------------------------------------------------
echo -e "${BLUE}[STEP 2]${RESET} Installing Docker..."
curl -fsSL https://get.docker.com | sudo sh

echo -e "${BLUE}[INFO]${RESET} Adding the current user (${CURRENT_USER}) to the 'docker' group..."
sudo usermod -aG docker "${CURRENT_USER}"

echo -e "${GREEN}[OK]${RESET} Docker installed and user permissions set.\n"

# ------------------------------------------------------------------------------
# STEP 3: INSTALL / UPGRADE DOCKER COMPOSE
# ------------------------------------------------------------------------------
echo -e "${BLUE}[STEP 3]${RESET} Checking Docker Compose installation..."

if ! command -v docker-compose &> /dev/null; then
  echo -e "${BLUE}[INFO]${RESET} Docker Compose not found. Installing via apt..."
  sudo apt-get install -y docker-compose
else
  echo -e "${BLUE}[INFO]${RESET} Docker Compose is already installed. Upgrading (if needed)..."
  sudo apt-get install -y docker-compose
fi

echo -e "${GREEN}[OK]${RESET} Docker Compose installation/upgrade complete.\n"

# ------------------------------------------------------------------------------
# STEP 4: CREATE DATA HUB DIRECTORIES
# ------------------------------------------------------------------------------
echo -e "${BLUE}[STEP 4]${RESET} Creating data-hub directories in your home (~/.data-hub)..."

DATA_HUB_DIR="${HOME}/.data-hub"
CONFIG_DIR="${DATA_HUB_DIR}/config"
STATE_DIR="${DATA_HUB_DIR}/state"
BACKUPS_DIR="${DATA_HUB_DIR}/backups"

mkdir -p "${CONFIG_DIR}" "${STATE_DIR}" "${BACKUPS_DIR}"

echo -e "${BLUE}[INFO]${RESET} Created directories:"
echo "  - ${CONFIG_DIR}"
echo "  - ${STATE_DIR}"
echo "  - ${BACKUPS_DIR}"

echo -e "${GREEN}[OK]${RESET} Data Hub directory structure is in place.\n"

# ------------------------------------------------------------------------------
# STEP 5: WRAP UP
# ------------------------------------------------------------------------------
echo -e "${BOLD}Setup Complete!${RESET}"
echo -e "You should now reboot or log out/log in to ensure your user membership (in 'docker' group) is refreshed.\n"

echo -e "${BLUE}--------------------------------------------------${RESET}"
echo -e "Final Steps:"
echo -e "  1. (Optional) Reboot your Raspberry Pi: ${BOLD}sudo reboot${RESET}"
echo -e "  2. Clone and run the data-hub repository containers:"
echo -e "     ${BOLD}git clone https://github.com/<yourusername>/data-hub.git${RESET}"
echo -e "     ${BOLD}cd data-hub/docker/compose && docker-compose up -d${RESET}"
echo -e "  3. Access your services via InfluxDB/Grafana/SignalK ports."
echo -e "--------------------------------------------------\n"

echo -e "${GREEN}[DONE]${RESET} Your Pi is now ready to run Data Hub!"
