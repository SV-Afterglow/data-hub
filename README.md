# Data Hub

The **Data Hub** is a systemd service-based vessel data hub and systems interface, inspired by the [SeaBits NMEA 2000 Raspberry Pi implementation](https://seabits.com/nmea-2000-powered-raspberry-pi/). This system manages NMEA2000 network access, hosts a SignalK server, and provides data visualization through Grafana with historical data storage in InfluxDB.

---

## Overview

### Key Capabilities

- **NMEA2000 Connectivity**  
  Collect data from onboard sensors and instruments via a PICAN-M HAT or similar.
  
- **SignalK Integration**  
  Normalize real-time vessel data and make it accessible to other systems.
  
- **Time-Series Storage (InfluxDB)**  
  Store historical logs for trend analysis and performance metrics.
  
- **Visualization (Grafana)**  
  Create customizable dashboards for system monitoring and vessel performance.
  
- **System Health & Metrics**  
  Collect, visualize, and alert on CPU usage, memory, disk space, and more through the data_hub_monitor service.
  
- **Network Monitoring**  
  Track network performance, connected devices, and internet speeds through the network_monitor service.

---

## Installation

1. **Flash Raspberry Pi OS**  
   - We recommend the latest Raspberry Pi OS (Lite) for minimal overhead.

2. **Install Dependencies**
   ```bash
   # Update system
   sudo apt-get update && sudo apt-get upgrade -y

   # Install required packages
   sudo apt-get install -y \
     python3 python3-pip \
     influxdb influxdb-client \
     grafana \
     signalk \
     python3-psutil python3-netifaces python3-scapy \
     speedtest-cli
   ```

3. **Configure Services**
   - Install monitoring services:
     ```bash
     # Copy service files
     sudo cp services/data_hub_monitor/data_hub_monitor.py /usr/local/bin/
     sudo cp services/network_monitor/network_monitor.py /usr/local/bin/
     
     # Make executable
     sudo chmod +x /usr/local/bin/data_hub_monitor.py
     sudo chmod +x /usr/local/bin/network_monitor.py
     
     # Install systemd services
     sudo cp services/data_hub_monitor/data_hub_monitor.service /etc/systemd/system/
     sudo cp services/network_monitor/network_monitor.service /etc/systemd/system/
     
     # Enable and start services
     sudo systemctl daemon-reload
     sudo systemctl enable data_hub_monitor.service network_monitor.service
     sudo systemctl start data_hub_monitor.service network_monitor.service
     ```

   - Configure SignalK to write to InfluxDB
   - Set up Grafana dashboards for visualization

4. **Access Your Services**
   - **SignalK**: <http://your-pi-ip:3000>
   - **Grafana**: <http://your-pi-ip:3001>
   - **InfluxDB**: <http://your-pi-ip:8086>
   - You should see vessel data flowing automatically into Influx and visualized in Grafana.

For advanced configuration, see `docs/INSTALLATION.md`.

## Architecture & Directory Structure

```
data-hub/
├── services/               # Python services (snake_case)
│   ├── __init__.py
│   ├── data_hub_monitor/  # System monitoring service
│   └── network_monitor/   # Network monitoring service
├── docs/                  # Documentation & proposals
│   ├── proposals/
│   ├── ARCHITECTURE.md
│   ├── INSTALLATION.md
│   └── REQUIREMENTS.md
└── version.yml           # Tracks current system version

```

## System Services

### data_hub_monitor
- Collects system metrics every 15 seconds:
  - CPU usage
  - Memory usage
  - Disk usage
  - Temperature
  - System uptime
- Writes metrics to InfluxDB for visualization in Grafana

### network_monitor
- Collects network metrics every 15 minutes:
  - Bandwidth usage (bytes sent/received)
  - Network errors and packet drops
  - Connected devices (IP, MAC, hostname)
- Performs speed tests every hour:
  - Download speed
  - Upload speed
  - Latency
  - Uses ~33MB per test (~792MB per day)
- Writes all metrics to InfluxDB for visualization in Grafana

## Data Flow
1. **NMEA2000 Input**  
   Data arrives via the PICAN-M HAT (or another CAN-enabled interface).
2. **SignalK Normalization**  
   SignalK processes raw messages and provides a unified data model.
3. **InfluxDB Storage**  
   - Normalized vessel data is stored for long-term trend analysis
   - System metrics from data_hub_monitor
   - Network metrics from network_monitor
4. **Grafana Dashboards**  
   Visualize both real-time and historical data via dashboards (default http://localhost:3001).

## Development Workflow
1. **Local Development**
   - Clone the repo and modify Python code in services/
   - Test changes locally before deploying
2. **Version Control**
   - Create feature branches for new development (e.g., feature/network-monitoring)
   - Submit pull requests for review
   - Merge to main when approved
3. **Deployment**
   - Copy service files to target system
   - Install and configure systemd services
   - Test and verify functionality

## Adding a New Service
1. Create a Python service in services/
2. Create a systemd service file in services/your_service/
3. Install dependencies and service files on target system
4. Document installation steps in INSTALLATION.md

## Configuration
- Service files are installed in /usr/local/bin/
- Systemd service files are in /etc/systemd/system/
- Logs are available through journalctl
- Each service has its own InfluxDB bucket for metrics

## Support & Troubleshooting

1. **Check Logs**
   ```bash
   journalctl -u data_hub_monitor.service
   journalctl -u network_monitor.service
   ```
2. **Review Metrics**
   - Check Grafana dashboards for system and network performance
3. **Contact Maintainers**
   - File an issue or reach out directly if you're stuck

## References
- [SeaBits NMEA 2000 Guide](https://seabits.com/nmea-2000-powered-raspberry-pi/)
- [SignalK Documentation](https://signalk.org/)
- [CopperHill PICAN-M Documentation](https://copperhilltech.com/pican-m-nmea-0183-nmea-2000-hat-for-raspberry-pi/)
- [InfluxDB Documentation](https://docs.influxdata.com/)
- [Grafana Documentation](https://grafana.com/docs/)
