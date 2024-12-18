# Data Hub Installation Guide

## Initial Setup

### 1. Operating System Installation
1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Insert SD card into your computer
3. Launch Pi Imager
4. Click **CHOOSE OS**
   - Select "Raspberry Pi OS (other)"
   - Select "Raspberry Pi OS Lite (32-bit)"
5. Click **CHOOSE STORAGE**
   - Select your SD card
6. Click the gear icon ⚙️ (Advanced Options)
   - Set hostname: `data-hub`
   - Enable SSH (password authentication)
   - Set username: `admin`
   - Set password: Your vessel's name
   - Set locale settings
   - Configure wireless network (if needed)
7. Click **SAVE**
8. Click **WRITE**
   - Wait for the process to complete
   - Click **CONTINUE** when done
9. Safely eject the SD card

### 2. Physical Installation

#### PICAN-M HAT Installation
1. Power off your Raspberry Pi completely
2. Carefully align the PICAN-M HAT with all GPIO pins on the Raspberry Pi
   - The HAT should sit parallel to the Raspberry Pi board
   - All pins should be fully inserted without bending
3. Connect to NMEA2000 backbone via Micro-C connector
   - No terminators needed on PICAN-M connection
   - Device is powered directly from NMEA2000 network (12V)
4. Power on the Raspberry Pi
5. Verify HAT detection:
   ```bash
   # Check kernel messages for HAT detection
   dmesg | grep mcp251x
   
   # Expected output should include:
   # mcp251x spi0.0: MCP2515 successfully initialized
   ```

If the HAT is not detected:
1. Power off the Raspberry Pi
2. Check the HAT is properly seated on all GPIO pins
3. Verify 12V power from NMEA2000 network
4. Power on and check again

### 3. Automated Setup
After completing the OS installation and physical setup:

1. Boot the Raspberry Pi and log in via SSH:
   ```bash
   ssh admin@data-hub.local
   ```
   When prompted for password, enter your vessel's name

2. Install git:
   ```bash
   sudo apt-get update
   sudo apt-get install -y git
   ```

3. Clone this repository and prepare for setup:
   ```bash
   git clone https://github.com/SV-Afterglow/data-hub.git
   cd data-hub
   chmod +x setup.sh
   ./setup.sh
   ```

The setup script will:
- Check for PICAN-M HAT presence
- Perform system updates
- Install required packages
- Configure CAN interface
- Set up Docker and services
- Provide guidance if HAT is not detected

4. If the PICAN-M HAT was not detected during setup:
   ```bash
   # After installing HAT and rebooting:
   sudo modprobe mcp251x
   ip link show can0  # Verify CAN interface
   candump can0       # Monitor NMEA2000 traffic
   ```

5. Reboot to complete setup:
   ```bash
   sudo reboot
   ```

### 4. Post-Installation Configuration

#### Network Access
The Data Hub services can be accessed in two ways:
1. Using the hostname: `data-hub.local`
2. Using the IP address (shown at the end of setup)

From another computer on the same network, you cannot use `localhost` - you must use either:
- `http://data-hub.local:[PORT]`
- `http://[IP_ADDRESS]:[PORT]`

Service ports:
- SignalK: 3000
- Grafana: 3001
- InfluxDB: 8086

#### SignalK to InfluxDB Integration
1. Access SignalK admin interface at:
   - `http://data-hub.local:3000/admin` or
   - `http://[IP_ADDRESS]:3000/admin`
2. Go to Server -> Plugin Config
3. Find and install "@signalk/signalk-to-influxdb" plugin
4. Configure the plugin:
   - Host: influxdb (use this exact name, NOT localhost)
   - Port: 8086
   - Database: signalk
   - Batch write: Enabled
   - Write interval: 1000 (1 second)

Note: When configuring the InfluxDB connection in SignalK, use `influxdb` as the hostname. This is the Docker service name and will resolve correctly within the Docker network. Do not use localhost, data-hub.local, or IP addresses for this internal connection.

#### Grafana Data Source Setup
1. Access Grafana at:
   - `http://data-hub.local:3001` or
   - `http://[IP_ADDRESS]:3001`
   - Default login: admin/admin
2. Add InfluxDB as data source:
   - Name: SignalK
   - Type: InfluxDB
   - URL: http://influxdb:8086 (use this exact URL, NOT localhost)
   - Database: signalk
   - No authentication required

Note: When configuring the InfluxDB data source in Grafana, use `http://influxdb:8086` as the URL. This is the Docker service name and will resolve correctly within the Docker network. Do not use localhost, data-hub.local, or IP addresses for this internal connection.

## Manual Installation Reference

The following steps are automated by setup.sh but documented here for reference:

### System Configuration
```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Configure system settings
sudo raspi-config
# Enable:
#   - SPI Interface
#   - Set appropriate timezone
#   - Set locale settings
```

### Required Packages
```bash
sudo apt-get install -y \
    git \
    can-utils \
    docker.io \
    docker-compose
```

### CAN Interface Setup
1. Create CAN interface configuration:
   ```bash
   sudo mkdir -p /etc/network/interfaces.d
   sudo nano /etc/network/interfaces.d/can0
   ```

2. Add configuration:
   ```
   auto can0
   iface can0 inet manual
       pre-up /sbin/ip link set can0 type can bitrate 250000
       up /sbin/ip link set can0 up
       down /sbin/ip link set can0 down
   ```

3. Configure modules:
   ```bash
   sudo nano /etc/modules
   ```
   Add lines:
   ```
   mcp251x
   can_dev
   can
   can_raw
   ```

### Docker Services Setup

#### InfluxDB Setup
1. Create data directory and configuration:
   ```bash
   mkdir -p ~/influxdb-data
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
   ```

#### SignalK Installation
1. Using Docker for consistent deployment:
   ```bash
   mkdir -p ~/.signalk
   docker-compose up -d signalk
   ```

2. Access SignalK:
   - Web: http://data-hub.local:3000
   - Admin: http://data-hub.local:3000/admin
   - Configure NMEA2000 source in admin panel

#### Grafana Setup
1. Deploy using Docker:
   ```bash
   mkdir -p ~/grafana-data
   docker-compose up -d grafana
   ```

2. Access Grafana:
   - Web: http://data-hub.local:3001
   - Default login: admin/admin
   - Add SignalK InfluxDB as data source

### Automated Updates

1. Watchtower Setup
   ```bash
   docker run -d \
     --name watchtower \
     --restart always \
     -v /var/run/docker.sock:/var/run/docker.sock \
     containrrr/watchtower \
     --cleanup --interval 30
   ```

## Testing NMEA2000 Connection

1. Check CAN interface:
   ```bash
   ip link show can0
   ```

2. Monitor NMEA2000 traffic:
   ```bash
   candump can0
   ```

3. View SignalK data:
   ```bash
   # View logs
   docker logs signalk
   
   # Monitor NMEA2000 data in SignalK
   http://data-hub.local:3000/admin
   ```

4. Verify data storage:
   ```bash
   # Check InfluxDB logs
   docker logs influxdb
   
   # Query recent data points
   curl -G 'http://data-hub.local:8086/query?db=signalk' --data-urlencode 'q=SELECT * FROM "signalk" ORDER BY time DESC LIMIT 5'
   ```

## Networking Notes

### Internal vs External Access

#### Internal Docker Communication
Services within the Docker network should use the service names for communication:
- SignalK → InfluxDB: Use `influxdb:8086`
- Grafana → InfluxDB: Use `influxdb:8086`

#### External Access
Computers on your network should use:
1. Hostname (recommended):
   - SignalK: `http://data-hub.local:3000`
   - Grafana: `http://data-hub.local:3001`
   - InfluxDB: `http://data-hub.local:8086`

2. IP Address (alternative):
   - SignalK: `http://[IP_ADDRESS]:3000`
   - Grafana: `http://[IP_ADDRESS]:3001`
   - InfluxDB: `http://[IP_ADDRESS]:8086`

Do not use `localhost` when accessing from another computer - it will not work.

### Troubleshooting Network Access

1. Cannot access using hostname:
   ```bash
   # On your computer, try to ping the Data Hub
   ping data-hub.local
   
   # If this fails, try using the IP address instead
   ping [IP_ADDRESS]
   ```

2. Cannot access using IP:
   - Verify both devices are on the same network
   - Check firewall settings on the Data Hub:
     ```bash
     sudo ufw status
     ```
   - Verify services are running:
     ```bash
     docker-compose ps
     ```

3. Services can't communicate:
   - Verify you're using service names (e.g., `influxdb`) not `localhost`
   - Check Docker network:
     ```bash
     docker network ls
     docker network inspect data-hub_default
     ```

## Troubleshooting

### Common Issues

#### 1. PICAN-M HAT Not Detected
- **Symptoms:**
  - No `can0` interface
  - No "mcp251x" in `dmesg` output
  - SignalK shows no NMEA2000 data
- **Solutions:**
  1. Check physical installation:
     - Power off Raspberry Pi
     - Verify HAT is properly seated on all GPIO pins
     - Check for bent pins
     - Power on and check `dmesg` again
  2. Verify power:
     - Confirm 12V from NMEA2000 network
     - Check voltage at HAT power points
  3. Check kernel modules:
     ```bash
     lsmod | grep can    # Should show CAN modules
     lsmod | grep mcp251x  # Should show MCP driver
     sudo modprobe mcp251x  # Load driver if missing
     ```
  4. Verify SPI interface:
     ```bash
     ls /dev/spidev*  # Should show SPI devices
     sudo raspi-config  # Enable SPI if needed
     ```

#### 2. No NMEA2000 Data
- Check candump output
- Verify 250000 bps speed setting
- Confirm SignalK NMEA2000 source configuration

#### 3. Container Issues
```bash
# Check container status
docker ps -a

# View container logs
docker logs signalk
docker logs influxdb
docker logs grafana
```

#### 4. No Data in InfluxDB
- Verify SignalK to InfluxDB plugin is installed and configured
- Check InfluxDB logs for write errors
- Verify network connectivity between containers

## Backup and Recovery

### Backup
```bash
# Backup configurations and data
./scripts/backup.sh
```

### Restore
```bash
# Restore from backup
./scripts/restore.sh backup_file.tar.gz
```

## Safety Notes

- Always backup before updates
- Monitor system resources
- Keep spare SD card with known working configuration
- Test major changes in development first
- Regularly check InfluxDB storage usage
