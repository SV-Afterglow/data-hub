# Codebase Summary

## Key Components

### System Services
1. **data_hub_monitor**
   - Location: /usr/local/bin/data_hub_monitor.py
   - Purpose: System metrics collection
   - Dependencies: psutil, influxdb-client
   - Data Flow: System → InfluxDB → Grafana

2. **network_monitor**
   - Location: /usr/local/bin/network_monitor.py
   - Purpose: Network monitoring and speed testing
   - Dependencies: psutil, netifaces, scapy, speedtest-cli, influxdb-client
   - Data Flow: Network → InfluxDB → Grafana

### External Services
1. **SignalK**
   - Purpose: Marine data handling
   - Integration: Writes to InfluxDB
   - Access: Port 3000

2. **InfluxDB**
   - Purpose: Time-series data storage
   - Buckets:
     - data-hub-monitor: System metrics (15s intervals)
     - network-monitor: Network metrics (15-60m intervals)
     - signalk: Marine sensor data (real-time)
   - Access: Port 8086

3. **Grafana**
   - Purpose: Data visualization
   - Data Sources: InfluxDB
   - Access: Port 3001

## Data Flow

### System Metrics Flow
1. data_hub_monitor collects system metrics
2. Metrics written to data-hub-monitor bucket
3. Grafana queries and displays metrics

### Network Metrics Flow
1. network_monitor collects:
   - Bandwidth usage (15-minute intervals)
   - Connected devices (15-minute intervals)
   - Speed test results (60-minute intervals)
2. Metrics written to network-monitor bucket
3. Grafana queries and displays metrics

### Marine Data Flow
1. NMEA2000 data received via PICAN-M
2. SignalK processes and normalizes data
3. Data written to InfluxDB
4. Grafana visualizes marine data

## External Dependencies
- Python 3.x and pip
- Debian package repositories
- System utilities (speedtest-cli)
- Hardware dependencies (PICAN-M HAT)

## Recent Significant Changes
1. Transitioned from Docker to systemd services
   - Removed Docker containers
   - Implemented native system services
   - Updated documentation

2. Added network monitoring service
   - Implemented bandwidth tracking
   - Added device discovery
   - Integrated speed testing
   - Created new InfluxDB bucket

3. Updated project structure
   - Reorganized services directory
   - Created cline_docs documentation
   - Updated README

## User Feedback Integration
- Hourly speed tests confirmed acceptable
- Data usage documented (~33MB per speed test)
- Service installation process simplified

## Active Development Areas
1. Grafana Dashboards
   - Network performance visualization
   - Device tracking interface
   - System health monitoring

2. Alert System
   - Threshold configuration
   - Notification system
   - Integration planning

## Additional Documentation
- README.md: Main project documentation
- INSTALLATION.md: Installation guide
- ARCHITECTURE.md: System architecture details
- REQUIREMENTS.md: System requirements
- cline_docs/: Development documentation
