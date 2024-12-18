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
7. Click **SAVE** and **WRITE**
8. Safely eject the SD card

### 2. Physical Installation

#### PICAN-M HAT Installation
1. Power off your Raspberry Pi completely
2. Carefully align the PICAN-M HAT with all GPIO pins
   - The HAT should sit parallel to the board
   - All pins should be fully inserted without bending
3. Connect to NMEA2000 backbone via Micro-C connector
   - No terminators needed on PICAN-M connection
   - Device is powered directly from NMEA2000 network (12V)

### 3. Software Installation
1. Boot the Raspberry Pi and log in via SSH:
   ```bash
   ssh admin@data-hub.local
   ```

2. Clone and run the setup script:
   ```bash
   sudo apt-get update && sudo apt-get install -y git
   git clone https://github.com/SV-Afterglow/data-hub.git
   cd data-hub
   chmod +x setup.sh
   ./setup.sh
   ```

The setup script will automatically:
- Install and configure all required software
- Set up Docker services
- Configure the PICAN-M HAT and CAN interface
- Create necessary data directories with correct permissions

### 4. Post-Installation Configuration

#### SignalK Plugin Management
SignalK plugins are managed through two mechanisms:
1. **Volume Persistence**: All plugins installed through the admin interface are stored in the `~/.signalk` directory, which is mounted as a Docker volume. This means:
   - Plugins installed via the admin interface persist across container updates
   - Custom plugin configurations are preserved
   - You can safely install, update, or remove plugins through the admin interface

2. **Configuration File**: Core plugin settings are maintained in `settings.json`, ensuring critical integrations (like InfluxDB) are properly configured.

#### SignalK to InfluxDB Integration
1. Access SignalK admin interface at `http://data-hub.local:3000/admin`
2. Go to Server -> Plugin Config
3. Install "@signalk/signalk-to-influxdb" plugin
4. Configure the plugin:
   - Host: influxdb
   - Port: 8086
   - Database: signalk
   - Resolution: 500 (captures changes every 500ms, suitable for most NMEA2000 data)
   - Batch writes interval: 5 (writes data every 5 seconds, balancing real-time access with storage efficiency)

Note: These settings are optimized for marine use - the 500ms resolution catches important changes in navigation data while the 5-second batch interval ensures efficient storage and good system performance.

#### Grafana Setup
Access Grafana at `http://data-hub.local:3001` (default login: admin/admin)

Add InfluxDB as data source:
- Name: SignalK
- Type: InfluxDB
- URL: http://influxdb:8086
- Database: signalk
- No authentication required

## Troubleshooting

### Common Issues

#### 1. Plugin Management Issues
- **Symptom**: Plugin disappeared after container update
  - Check if plugin files exist in ~/.signalk
  - Verify plugin was installed through admin interface
  - Check SignalK logs for plugin loading errors

- **Symptom**: Plugin configuration lost
  - Check settings.json for correct configuration
  - Verify ~/.signalk volume mount in docker-compose logs

#### 2. Permission Issues
- **Symptom**: Grafana can't write to its data directory
  - Verify docker-compose.yaml has correct user:group mapping (472:472)
  - Check ownership of ~/grafana-data directory

- **Symptom**: SignalK can't write to its data directory
  - Check ~/.signalk directory permissions
  - Verify the Docker volume mount in docker-compose.yaml

#### 3. No Data Flow
- Verify SignalK to InfluxDB plugin is installed and configured
- Check container logs:
  ```bash
  docker logs signalk
  docker logs influxdb
  docker logs grafana
  ```
- Verify network connectivity between containers

## Safety Notes
- Always backup before updates
- Monitor system resources
- Keep spare SD card with known working configuration
- Test major changes in development first
