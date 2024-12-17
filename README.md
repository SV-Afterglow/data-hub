# Data Hub

Primary vessel data hub and systems interface, based on the SeaBits NMEA 2000 Raspberry Pi implementation. This system manages NMEA2000 network access, hosts SignalK server, and provides data visualization through Grafana with historical data storage in InfluxDB.

## Overview

The Data Hub serves as a central nervous system for vessel data, providing:
- NMEA2000 network connectivity
- Real-time data processing through SignalK
- Time-series data storage in InfluxDB
- Data visualization via Grafana dashboards
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
│   ├── docker-compose.yml
│   ├── signalk/
│   ├── influxdb/
│   └── grafana/
├── config/             # Application configs
│   ├── signalk/
│   ├── influxdb/
│   └── grafana/
└── scripts/           # Maintenance scripts
    ├── backup.sh
    └── restore.sh
```

### Data Flow
1. NMEA2000 data is received through the PICAN-M HAT
2. SignalK processes and normalizes the data
3. Data is stored in InfluxDB for historical analysis
4. Grafana visualizes both real-time and historical data

## Development

1. Local Development
   - Clone repository
   - Make changes
   - Test in local containers
   - Push to GitHub

2. Deployment
   - Merge to main branch
   - Automatic container updates via Watchtower
   - Monitor logs for success

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
