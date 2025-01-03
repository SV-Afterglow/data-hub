#!/usr/bin/env bash
#
# setup_data-hub.sh
#
# Host-level setup for a Raspberry Pi environment:
#   - Wi-Fi & SSH (optional)
#   - OS updates, hostname
#   - PICAN-M HAT overlay for can0
#   - Docker & Docker Compose install
#   - Clone the data-hub repo (if not present)
#   - Copy pre-configured files (SignalK settings, etc.)
#   - Start containers with docker-compose
#   - Fix permissions to avoid EACCES errors for container volumes
#
# ------------------------------------------------------------------------------

GREEN="\033[0;32m"
BLUE="\033[0;34m"
BOLD="\033[1m"
RESET="\033[0m"

if [ -z "$BASH_VERSION" ]; then
  echo "Please run this script with bash!"
  exit 1
fi

CURRENT_USER="$(whoami)"
if [ "$CURRENT_USER" == "root" ]; then
  echo -e "${BLUE}[INFO]${RESET} Running as root. Docker group modifications may require manual checks."
fi

cat << "EOF"

██████╗  █████╗ ████████╗ █████╗     ██╗  ██╗██╗   ██╗██████╗ 
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗    ██║  ██║██║   ██║██╔══██╗
██║  ██║███████║   ██║   ███████║    ███████║██║   ██║██████╔╝
██║  ██║██╔══██║   ██║   ██╔══██║    ██╔══██║██║   ██║██╔══██╗
██████╔╝██║  ██║   ██║   ██║  ██║    ██║  ██║╚██████╔╝██████╔╝
╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ 

  HOST-LEVEL SETUP FOR DOCKER-BASED SIGNALK/INFLUX/GRAFANA
-----------------------------------------------------------
EOF

# ------------------------------------------------------------------------------
# 1. (Optional) Wi-Fi & SSH
# ------------------------------------------------------------------------------
read -rp "Enter 2-letter Wi-Fi country code (e.g., US). Leave blank to skip: " WIFI_COUNTRY
if [ -n "$WIFI_COUNTRY" ]; then
  echo -e "${BLUE}[STEP 1A]${RESET} Setting Wi-Fi country to ${WIFI_COUNTRY}..."
  sudo tee /boot/wpa_supplicant.conf >/dev/null <<EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=${WIFI_COUNTRY}

network={
  ssid="<Your_SSID>"
  psk="<Your_Password>"
}
EOF
  echo -e "${GREEN}[OK]${RESET} wpa_supplicant.conf updated. Reboot or re-flash may be needed."
fi

read -rp "Enable SSH? (y/n): " ENABLE_SSH
if [[ "$ENABLE_SSH" =~ ^[Yy]$ ]]; then
  echo -e "${BLUE}[STEP 1B]${RESET} Enabling SSH by creating /boot/ssh file..."
  sudo touch /boot/ssh
  echo -e "${GREEN}[OK]${RESET} SSH enabled."
fi

# ------------------------------------------------------------------------------
# 2. OS Update & Basic Config
# ------------------------------------------------------------------------------
echo -e "${BLUE}[STEP 2]${RESET} Updating and configuring system packages..."
sudo apt-get update -y && sudo apt-get upgrade -y

read -rp "Enter a hostname (default: data-hub). Leave blank to skip: " NEW_HOSTNAME
NEW_HOSTNAME="${NEW_HOSTNAME:-data-hub}"
echo -e "${BLUE}[INFO]${RESET} Setting hostname to '${NEW_HOSTNAME}'..."
sudo hostnamectl set-hostname "$NEW_HOSTNAME"
sudo sed -i "/127.0.1.1/d" /etc/hosts
echo "127.0.1.1       $NEW_HOSTNAME" | sudo tee -a /etc/hosts

read -rp "Reconfigure timezone interactively? (y/n): " SET_TZ
if [[ "$SET_TZ" =~ ^[Yy]$ ]]; then
  sudo dpkg-reconfigure tzdata
fi

# ------------------------------------------------------------------------------
# 3. PICAN-M CAN bus setup
# ------------------------------------------------------------------------------
echo -e "${BLUE}[STEP 3]${RESET} Setting up PICAN-M (mcp2515) overlay & can-utils"
CONFIG_FILE="/boot/firmware/config.txt"
if [ ! -f "$CONFIG_FILE" ]; then
  # Some Pi OS versions might be using /boot/config.txt instead
  CONFIG_FILE="/boot/config.txt"
fi

if ! grep -q "dtoverlay=mcp2515-can0" "$CONFIG_FILE"; then
  echo -e "${BLUE}[INFO]${RESET} Appending MCP2515 overlay lines to ${CONFIG_FILE}..."
  sudo tee -a "$CONFIG_FILE" <<EOF

# --- PICAN-M Overlays ---
enable_uart=1
dtparam=i2c_arm=on
dtparam=spi=on
dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25
dtoverlay=spi-bcm2835-overlay
EOF
else
  echo -e "${BLUE}[INFO]${RESET} Overlays already present, skipping..."
fi

sudo apt-get install -y can-utils

echo -e "${BLUE}[INFO]${RESET} Creating socketcan-interface systemd service..."
sudo bash -c "cat << 'EOF' > /etc/systemd/system/socketcan-interface.service
[Unit]
Description=SocketCAN interface can0 with a baudrate of 250000
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/sbin/ip link set can0 type can bitrate 250000 ; /sbin/ifconfig can0 up
ExecReload=/sbin/ifconfig can0 down ; /sbin/ip link set can0 type can bitrate 250000 ; /sbin/ifconfig can0 up
ExecStop=/sbin/ifconfig can0 down

[Install]
WantedBy=multi-user.target
EOF"
sudo chmod 644 /etc/systemd/system/socketcan-interface.service
sudo systemctl enable socketcan-interface.service

echo -e "${GREEN}[OK]${RESET} PICAN-M setup done. A full power cycle is recommended."

# ------------------------------------------------------------------------------
# 4. Docker & Docker Compose
# ------------------------------------------------------------------------------
echo -e "${BLUE}[STEP 4]${RESET} Installing Docker & Docker Compose..."
if ! command -v docker &> /dev/null; then
  echo -e "${BLUE}[INFO]${RESET} Installing Docker from official script..."
  curl -fsSL https://get.docker.com | sudo sh
fi

echo -e "${BLUE}[INFO]${RESET} Adding ${CURRENT_USER} to docker group..."
sudo usermod -aG docker "$CURRENT_USER"

if ! command -v docker-compose &> /dev/null; then
  echo -e "${BLUE}[INFO]${RESET} Installing docker-compose..."
  sudo apt-get install -y docker-compose
fi

# ------------------------------------------------------------------------------
# 5. Clone data-hub Repo (if not present)
# ------------------------------------------------------------------------------
DHUB_DIR="/home/${CURRENT_USER}/data-hub"
if [ ! -d "$DHUB_DIR" ]; then
  read -rp "Clone the data-hub repository? (y/n): " CLONE_REPO
  if [[ "$CLONE_REPO" =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}[STEP 5]${RESET} Cloning the data-hub repo to $DHUB_DIR..."
    git clone https://github.com/SV-Afterglow/data-hub.git "$DHUB_DIR"
  fi
fi

# ------------------------------------------------------------------------------
# 6. Copy Pre-Configured Settings, Fix Permissions
# ------------------------------------------------------------------------------
# Example: if you have a preconfigured folder inside the repo at:
# data-hub/docker/signalk/config/settings.json
# And you want to mount it at /home/node/.signalk in the container.

if [ -d "$DHUB_DIR/docker/signalk/config" ]; then
  echo -e "${BLUE}[STEP 6]${RESET} Preparing SignalK config for container..."
  # Copy to a hidden dir in ~, or you might directly use volumes from the repo
  mkdir -p "${HOME}/.data-hub/signalk-settings"
  cp -r "$DHUB_DIR/docker/signalk/config/." "${HOME}/.data-hub/signalk-settings/"

  # Fix ownership so the 'node' user inside container can write
  # Typically 'node' user has UID 1000, but confirm with official signalk Dockerfile
  sudo chown -R 1000:1000 "${HOME}/.data-hub/signalk-settings"
fi

# If you also have provisioning for Influx/Grafana, do similar steps here:
# mkdir -p "${HOME}/.data-hub/grafana-provisioning"
# cp -r "$DHUB_DIR/docker/grafana/provisioning/." "${HOME}/.data-hub/grafana-provisioning/"
# sudo chown -R 472:472 "${HOME}/.data-hub/grafana-provisioning"  # 472 is often the grafana user

# ------------------------------------------------------------------------------
# 7. Start Docker Containers
# ------------------------------------------------------------------------------
if [ -f "$DHUB_DIR/docker/compose/docker-compose.yml" ]; then
  echo -e "${BLUE}[STEP 7]${RESET} Starting Docker containers with docker-compose..."
  cd "$DHUB_DIR/docker/compose" || exit 1
  docker-compose up -d
  echo -e "${GREEN}[OK]${RESET} Containers are starting. Check logs with 'docker-compose logs -f'."
else
  echo -e "${BLUE}[INFO]${RESET} No docker-compose.yml found at $DHUB_DIR/docker/compose."
fi

# ------------------------------------------------------------------------------
# 8. Wrap Up
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}Setup Complete!${RESET}"
echo -e "Recommended next steps:"
echo -e "  1. Power-cycle the Pi (unplug/replug) for PICAN-M to fully reset."
echo -e "  2. Re-log or reboot to finalize Docker group membership for '${CURRENT_USER}'."
echo -e "  3. Validate can0 with 'candump can0' after reboot."
echo -e "  4. Access services:"
echo -e "     - SignalK  : http://<your-pi-ip>:3000"
echo -e "     - Grafana  : http://<your-pi-ip>:3001"
echo -e "     - InfluxDB : http://<your-pi-ip>:8086"
echo -e "\n${BLUE}--------------------------------------------------${RESET}"
echo -e "If you enabled SSH or changed Wi-Fi, a reboot may be required."
echo -e "${BLUE}--------------------------------------------------${RESET}"