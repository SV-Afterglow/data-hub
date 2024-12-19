# Network Monitor Service

## Overview
The Network Monitor service tracks vessel network connectivity, providing real-time metrics about WiFi connections, signal strength, and internet speeds. This data helps monitor network reliability and performance while underway.

## Features
- WiFi connection monitoring
- Signal strength (RSSI) tracking
- Network speed measurements
- Connection state changes
- Network availability mapping

## Metrics Organization

### WiFi Status
**Measurement:** `wifi_status`
- **Fields:**
  - `connected`: Boolean connection state
  - `ssid`: Network name
  - `rssi`: Signal strength in dBm
  - `frequency`: Network frequency in MHz
  - `encryption`: Security type (WPA2, etc.)
- **Tags:**
  - `interface`: Network interface name
  - `connection_type`: "wifi"

### Network Speed
**Measurement:** `network_speed`
- **Fields:**
  - `download_mbps`: Download speed in Mbps
  - `upload_mbps`: Upload speed in Mbps
  - `latency_ms`: Ping latency in milliseconds
  - `jitter_ms`: Connection jitter in milliseconds
  - `packet_loss`: Packet loss percentage
- **Tags:**
  - `test_server`: Speed test server used
  - `connection_type`: Network type

### Connection Events
**Measurement:** `network_events`
- **Fields:**
  - `event_type`: Connection event type
  - `previous_ssid`: Previous network name
  - `new_ssid`: New network name
  - `duration`: Connection duration in seconds
- **Tags:**
  - `interface`: Network interface
  - `event_category`: "connection"

## Configuration
The service is configurable through environment variables:
```yaml
NETWORK_INTERFACE: "wlan0"           # Network interface to monitor
SPEED_TEST_INTERVAL: "3600"          # Speed test interval in seconds (default: 1 hour)
WIFI_CHECK_INTERVAL: "30"            # WiFi status check interval in seconds
SPEED_TEST_SERVER: ""                # Preferred speed test server (optional)
INFLUX_URL: "http://influxdb:8086"   # InfluxDB connection URL
MIN_SPEED_TEST_INTERVAL: "600"       # Minimum time between speed tests (10 minutes)
```

## Dependencies
- `speedtest-cli`: Network speed testing
- `iwconfig`/`iwlib`: WiFi interface monitoring
- `influxdb-client`: Metrics storage
- Docker with host network access

## Development

### Setup
1. Install system dependencies:
   ```bash
   apt-get update && apt-get install -y \
       wireless-tools \
       python3-dev \
       gcc
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Building
```bash
docker build -t data-hub/network-monitor .
```

### Testing
1. Unit Tests:
   ```bash
   pytest tests/unit/
   ```

2. Integration Tests:
   ```bash
   pytest tests/integration/
   ```

3. Manual Testing:
   ```bash
   python network_monitor.py --debug
   ```

## Grafana Integration

### Dashboards
1. **Network Overview**
   - Current connection status
   - Signal strength history
   - Speed test results
   - Connection events

2. **Performance Metrics**
   - Speed trends over time
   - Signal strength heatmap
   - Latency tracking
   - Packet loss monitoring

### Alerts
- Signal strength below threshold
- Network disconnection
- Speed degradation
- High latency/packet loss

## Maintenance

### Logs
The service logs to both stdout (for Docker) and InfluxDB:
- Connection state changes
- Speed test results
- Error conditions
- Configuration updates

### Updates
Version updates through the Data Hub update service:
- Configuration changes
- Speed test parameters
- Monitoring thresholds
- New metrics collection

### Troubleshooting

#### Common Issues
1. **No WiFi Data**
   - Check interface name
   - Verify interface permissions
   - Check wireless tools installation

2. **Speed Test Failures**
   - Check internet connectivity
   - Verify speed test server access
   - Check rate limiting settings

3. **Missing Metrics**
   - Verify InfluxDB connection
   - Check metric collection intervals
   - Review error logs

## Security
- Network interface access restricted
- Speed test server validation
- No sensitive data storage
- Encrypted InfluxDB communication

## Future Enhancements
1. Multiple interface support
2. Cellular failover monitoring
3. Geographic network mapping
4. Historical performance analysis
5. Automated network selection
