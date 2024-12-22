# Data Hub

Primary vessel data hub and systems interface, based on the SeaBits NMEA 2000 Raspberry Pi implementation. This system manages NMEA2000 network access, hosts SignalK server, and provides data visualization through Grafana with historical data storage in InfluxDB.

## Overview

The Data Hub serves as a central nervous system for vessel data, providing:
- NMEA2000 network connectivity
- Real-time data processing through SignalK
- Time-series data storage in InfluxDB
- Data visualization via Grafana dashboards
- System performance monitoring
- Automated updates and maintenance

## Quick Start

1. Check the [Requirements](docs/REQUIREMENTS.md) to ensure your hardware is compatible
2. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/data-hub.git
   cd data-hub
   ```
3. Run the setup script:
   ```bash
   ./setup.sh
   ```
4. Reboot your system when prompted
5. Access your services:
   - SignalK: http://localhost:3000
   - Grafana: http://localhost:3001
   - InfluxDB: http://localhost:8086

For detailed manual installation steps and troubleshooting, see the [Installation Guide](docs/INSTALLATION.md).

## Architecture

```
data-hub/
├── docker/              # Container configurations
│   ├── compose/        # Docker compose files
│   ├── signalk/       # SignalK server configuration
│   ├── influxdb/      # InfluxDB configuration
│   ├── grafana/       # Grafana configuration
│   ├── system_metrics/ # System metrics collector
│   └── update_service/ # Automated update service
├── services/           # Application services
│   ├── system_metrics/ # System metrics collector service
│   └── update_service/ # Update management service
├── updates/           # Version updates and manifests
├── config/            # Application configs
│   ├── signalk/
│   ├── influxdb/
│   └── grafana/
└── scripts/           # Maintenance scripts
    ├── backup.sh
    └── restore.sh
```

### Directory Structure

```
~/.data-hub/          # Main data directory
├── state/            # System state
│   ├── version      # Current version
│   └── updates/     # Update history
├── config/          # Service configurations
│   ├── influxdb/    # InfluxDB data and config
│   ├── grafana/     # Grafana dashboards and settings
│   ├── signalk/     # SignalK configuration
│   ├── network_monitor/    # Network monitoring service
│   ├── update_service/     # Update management service
│   └── system_metrics/     # System metrics service
└── backups/         # System backups
```

### Data Flow
1. NMEA2000 data is received through the PICAN-M HAT
2. SignalK processes and normalizes the data
3. Data is stored in InfluxDB for historical analysis
4. System metrics are collected and stored in InfluxDB
5. Grafana visualizes both real-time and historical data

### Update Flow
1. Update service checks for new versions periodically
2. New versions are detected via version.yml and manifest files
3. System state and configs are backed up
4. Updates are downloaded and applied to the correct locations:
   - Service configs go to ~/.data-hub/config/
   - Version state is updated in ~/.data-hub/state/
   - Update history is tracked in ~/.data-hub/state/updates/
5. Services are restarted as needed
6. Update status is logged to InfluxDB

## Features

### Marine Data
- NMEA2000 network integration
- Real-time data processing via SignalK
- Historical data storage in InfluxDB
- Customizable Grafana dashboards

### System Monitoring
- CPU usage and temperature
- Memory utilization
- Disk space monitoring
- System load averages
- Real-time performance graphs
- Historical trend analysis

### Automated Updates
- Version-controlled updates
- Automatic detection of new versions
- Safe update application
- Rollback capability
- Update status monitoring

## Development

1. Local Development
   - Clone repository
   - Make changes
   - Test in local containers
   - Push to GitHub

2. Deployment
   - Merge to main branch
   - Automatic container updates via update service and Watchtower
   - Monitor logs for success

### Adding New Services
1. Create service directory in services/
2. Add Dockerfile in docker/service-name/
3. Update docker-compose.yaml
4. Add service configuration to ~/.data-hub/config/
5. Add service to update manifests
6. Document in appropriate README

### Configuration Management
1. Service Configurations
   - All service configs live in ~/.data-hub/config/
   - Updates modify configs through manifest steps
   - Backups preserve configs for rollback

2. System State
   - Version info stored in ~/.data-hub/state/version
   - Update history in ~/.data-hub/state/updates/
   - State changes are atomic and backed up

3. Data Persistence
   - InfluxDB data: ~/.data-hub/config/influxdb/
   - Grafana data: ~/.data-hub/config/grafana/
   - SignalK data: ~/.data-hub/config/signalk/
   - Update service: ~/.data-hub/config/update_service/
     - settings.yml: GitHub repo, branch, intervals
     - history.log: Detailed update logs
     - metrics.db: Update metrics and status
   - System metrics: ~/.data-hub/config/system_metrics/
     - settings.yml: Collection intervals, thresholds
     - collector.log: Metrics collection logs
   - Network monitor: ~/.data-hub/config/network_monitor/
     - settings.yml: Network interfaces, intervals
     - monitor.log: Network status logs

## Support

This is a private repository. For support:
1. Check the troubleshooting section in the [Installation Guide](docs/INSTALLATION.md)
2. Review system logs
3. Contact repository maintainers

## References

- [SeaBits NMEA 2000 Guide](https://seabits.com/nmea-2000-powered-raspberry-pi/)
- [SignalK Documentation](https://signalk.org/)
- [CopperHill PICAN-M Documentation](https://copperhilltech.com/pican-m-nmea-0183-nmea-2000-hat-for-raspberry-pi/)
- [InfluxDB Documentation](https://docs.influxdata.com/influxdb/v1.8/)
- [Grafana Documentation](https://grafana.com/docs/)
