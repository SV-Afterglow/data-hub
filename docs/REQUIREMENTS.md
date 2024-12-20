# System Requirements

## Hardware Components
- Raspberry Pi 4 (4GB RAM recommended)
- PICAN-M HAT for NMEA2000 connectivity
- 32GB+ high-quality microSD card
- Optional but recommended:
  - Case with cooling
  - Ethernet cable for reliable network connection

## Operating System
- Raspberry Pi OS Lite (32-bit)
- Current tested version: 2023-10-10 release
- No desktop environment needed

## Network Requirements
- Static IP recommended for reliable access
- Network connectivity to NMEA2000 backbone
- Internet connection for updates (can be intermittent)

## Software Dependencies
### Base System
- Python 3.7+
- Git
- Docker
- Docker Compose

### Marine Software
- SignalK Server
  - Plugin system with persistent storage
  - Volume mount permissions for ~/.signalk
- Grafana
  - Volume mount permissions for data directory (uid:gid 472:472)
- CAN utils for NMEA2000

## Resource Requirements
### Storage
- Base system: ~2GB
- SignalK + Plugins: ~2GB
  - Core system: ~1GB
  - Plugin storage: ~1GB recommended
- Grafana: ~1GB
- Data storage: 10GB+ recommended
- Log storage: 1GB+ recommended

### Memory
- Minimum: 512MB available RAM
- Recommended: 1GB+ available RAM
  - SignalK + Plugins: ~256MB
  - Grafana: ~256MB
  - System: ~512MB

### Power
- Input voltage: 12V DC (from NMEA2000)
- Power consumption: ~2.5W typical

### File System
- Read/write access for Docker volume mounts:
  - ~/.signalk for SignalK data
  - ~/grafana-data for Grafana
  - ~/influxdb-data for InfluxDB

## Development Requirements
### Local Development
- Git
- VS Code with recommended extensions
- Python 3.7+
- Docker & Docker Compose
- Understanding of:
  - Docker volume permissions
  - SignalK plugin system
  - Container user mapping

### Remote Access
- SSH access
- Network connectivity to vessel
- GitHub access for deployments

### Permissions
- Docker group membership for development
- Access to Docker socket
- Ability to manage volume mount permissions
