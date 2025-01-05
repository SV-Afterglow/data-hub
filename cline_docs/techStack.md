# Technology Stack

## Core Technologies

### Python
- **Version**: Python 3
- **Purpose**: Primary programming language for system services
- **Justification**: 
  - Excellent system integration capabilities
  - Rich ecosystem of libraries
  - Easy to maintain and modify
  - Strong community support

### InfluxDB
- **Version**: Latest from Debian repositories
- **Purpose**: Time-series data storage
- **Justification**:
  - Optimized for time-series data
  - Efficient storage and querying
  - Well-integrated with Grafana
  - Supports multiple data sources

### Grafana
- **Version**: Latest from Debian repositories
- **Purpose**: Data visualization and dashboards
- **Justification**:
  - Powerful visualization capabilities
  - Native InfluxDB support
  - Customizable dashboards
  - Alerting capabilities

### SignalK
- **Version**: Latest from Debian repositories
- **Purpose**: Marine data normalization and distribution
- **Justification**:
  - Marine industry standard
  - NMEA2000 support
  - REST API for data access
  - Plugin ecosystem

## System Integration

### Systemd Services
- **Purpose**: Service management and automation
- **Justification**:
  - Native Linux integration
  - Automatic startup management
  - Dependency handling
  - Logging integration
  - Replaced Docker for simpler architecture

## Python Libraries

### Core Libraries
- **psutil**
  - System metrics collection
  - Cross-platform compatibility
  - Comprehensive system information

- **influxdb-client**
  - InfluxDB API integration
  - Efficient data writing
  - Query capabilities

### Network Monitoring
- **netifaces**
  - Network interface discovery
  - IP address information
  - Cross-platform support

- **scapy**
  - Network scanning
  - Device discovery
  - ARP operations

- **speedtest-cli**
  - Internet speed testing
  - Server selection
  - Comprehensive metrics

## Architecture Decisions

### Service-Based Architecture
- **Decision**: Transition from Docker to native systemd services
- **Rationale**:
  - Simpler deployment
  - Direct system access
  - Reduced overhead
  - Easier maintenance
  - Better system integration

### Data Storage
- **Decision**: Separate InfluxDB buckets per service/data type
- **Rationale**:
  - Better organization
  - Independent retention policies
  - Simplified querying
  - Isolation of concerns

### InfluxDB Buckets
- **data-hub-monitor**
  - Purpose: System metrics storage
  - Data: CPU, memory, disk, temperature
  - Interval: 15 seconds

- **network-monitor**
  - Purpose: Network metrics storage
  - Data: Bandwidth, devices, speed tests
  - Intervals: 15-60 minutes

- **signalk**
  - Purpose: Marine data storage
  - Data: NMEA2000 sensor data
  - Interval: Real-time vessel data

### Monitoring Intervals
- **Decision**: Variable intervals based on metric type
- **Rationale**:
  - System metrics: 15 seconds (low overhead)
  - Network metrics: 15 minutes (balance between detail and resources)
  - Speed tests: 60 minutes (bandwidth consideration)

### Security
- **Decision**: Run services as root
- **Rationale**:
  - Required for network scanning
  - System metric access
  - Hardware monitoring capabilities

## Future Considerations
- Implement metrics aggregation
- Add redundancy for critical services
- Enhance security measures
- Implement backup solutions
- Add remote monitoring capabilities
