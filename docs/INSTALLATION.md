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
1. PICAN-M HAT Installation
   - Carefully mount HAT on Raspberry Pi GPIO pins
   - Connect to NMEA2000 backbone via Micro-C connector
   - No terminators needed on PICAN-M connection
   - Device is powered directly from NMEA2000 network (12V)

### 3. Automated Setup
After completing the OS installation and physical setup:

1. Boot the Raspberry Pi and log in via SSH:
   ```bash
   ssh admin@data-hub.local
   ```
   When prompted for password, enter your vessel's name

2. Clone this repository and run the setup script:
   ```bash
   git clone https://github.com/SV-Afterglow/data-hub.git
   cd data-hub
   ./setup.sh
   ```
3. Reboot when prompted:
   ```bash
   sudo reboot
   ```

The setup script will automatically handle:
- System updates
- Required package installation
- CAN interface configuration
- Docker setup and configuration
- Service deployment (SignalK, InfluxDB, Grafana)

### 4. Post-Installation Configuration

#### SignalK to InfluxDB Integration
1. Access SignalK admin interface at http://data-hub.local:3000/admin
2. Go to Server -> Plugin Config
3. Find and install "@signalk/signalk-to-influxdb" plugin
4. Configure the plugin:
   - Host: influxdb
   - Port: 8086
   - Database: signalk
   - Batch write: Enabled
   - Write interval: 1000 (1 second)

#### Grafana Data Source Setup
1. Access Grafana at http://data-hub.local:3001
   - Default login: admin/admin
2. Add InfluxDB as data source:
   - Name: SignalK
   - Type: InfluxDB
   - URL: http://influxdb:8086
   - Database: signalk
   - No authentication required

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
   - Web: http://localhost:3000
   - Admin: http://localhost:3000/admin
   - Configure NMEA2000 source in admin panel

#### Grafana Setup
1. Deploy using Docker:
   ```bash
   mkdir -p ~/grafana-data
   docker-compose up -d grafana
   ```

2. Access Grafana:
   - Web: http://localhost:3001
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
   http://localhost:3000/admin
   ```

4. Verify data storage:
   ```bash
   # Check InfluxDB logs
   docker logs influxdb
   
   # Query recent data points
   curl -G 'http://localhost:8086/query?db=signalk' --data-urlencode 'q=SELECT * FROM "signalk" ORDER BY time DESC LIMIT 5'
   ```

## Troubleshooting

### Common Issues
1. CAN Interface Not Starting
   - Check PICAN-M seat on GPIO
   - Verify power from NMEA2000 (12V)
   - Confirm modules loaded: `lsmod | grep can`

2. No NMEA2000 Data
   - Check candump output
   - Verify 250000 bps speed setting
   - Confirm SignalK NMEA2000 source configuration

3. Container Issues
   ```bash
   # Check container status
   docker ps -a
   
   # View container logs
   docker logs signalk
   docker logs influxdb
   docker logs grafana
   ```

4. No Data in InfluxDB
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
