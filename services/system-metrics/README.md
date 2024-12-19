# System Metrics Service

## Overview
The system metrics service collects and stores system performance data in InfluxDB for monitoring and analysis through Grafana dashboards.

## Metrics Organization

The collector organizes data into separate measurements for better querying and visualization:

### 1. CPU Metrics
**Measurement:** `cpu`
- **Fields:**
  - `cpu_percent`: CPU usage percentage
  - `cpu_freq`: CPU frequency
- **Tags:**
  - `host`: System hostname
  - `metric_type`: "usage"

### 2. System Load
**Measurement:** `system_load`
- **Fields:**
  - `load_1min`: 1-minute load average
  - `load_5min`: 5-minute load average
  - `load_15min`: 15-minute load average
- **Tags:**
  - `host`: System hostname
  - `metric_type`: "load_average"

### 3. Memory Usage
**Measurement:** `memory`
- **Fields:**
  - `total`: Total memory
  - `available`: Available memory
  - `used`: Used memory
  - `percent`: Usage percentage
- **Tags:**
  - `host`: System hostname
  - `metric_type`: "usage"

### 4. Disk Space
**Measurement:** `disk`
- **Fields:**
  - `total`: Total space
  - `used`: Used space
  - `free`: Free space
  - `percent`: Usage percentage
- **Tags:**
  - `host`: System hostname
  - `device`: Mount point (e.g., "/")
  - `metric_type`: "usage"

### 5. Temperature
**Measurement:** `temperature`
- **Fields:**
  - `celsius`: CPU temperature in Celsius
- **Tags:**
  - `host`: System hostname
  - `sensor`: "cpu"
  - `metric_type`: "temperature"

## InfluxDB Structure
- **Database:** system_metrics
- **Retention:** Default (infinite)
- **Measurements:** Separated by metric type
- **Tags:** Used for filtering and grouping
- **Fields:** Actual metric values
- **Timestamp:** Nanosecond precision

## Configuration
The service is configurable through environment variables:
- `INFLUX_URL`: InfluxDB URL (default: http://influxdb:8086)
- `COLLECTION_INTERVAL`: Metrics collection interval in seconds (default: 10)

## Example Queries

### CPU Usage Over Last Hour
```sql
SELECT mean("cpu_percent") 
FROM "cpu" 
WHERE time > now() - 1h 
GROUP BY time(1m)
```

### Memory Usage by Host
```sql
SELECT last("percent") 
FROM "memory" 
GROUP BY "host"
```

### High Temperature Alerts
```sql
SELECT "celsius" 
FROM "temperature" 
WHERE "celsius" > 70
```

## Grafana Integration
The metrics are designed to work with Grafana dashboards:
- Real-time performance monitoring
- Historical trend analysis
- Pre-configured dashboards available
- Customizable alerts based on thresholds

## Development

### Adding New Metrics
1. Add collection logic in `collector.py`
2. Define measurement structure:
   - Choose appropriate measurement name
   - Define relevant tags
   - Define fields for values
3. Update documentation
4. Update Grafana dashboards

### Testing
1. Run collector locally
2. Verify metrics in InfluxDB
3. Check Grafana visualization
4. Test error conditions

## Troubleshooting

### Common Issues
1. **No Data in InfluxDB**
   - Check InfluxDB connection
   - Verify database exists
   - Check collector logs

2. **Missing Metrics**
   - Verify sensor availability
   - Check permissions
   - Review error logs

3. **Performance Impact**
   - Adjust collection interval
   - Review metric volume
   - Check resource usage
