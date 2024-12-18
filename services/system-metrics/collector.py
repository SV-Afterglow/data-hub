#!/usr/bin/env python3

import os
import time
import psutil
import socket
from influxdb import InfluxDBClient

# InfluxDB configuration
INFLUX_URL = os.getenv('INFLUX_URL', 'http://influxdb:8086')
INFLUX_DB = "system_metrics"

# Collection interval in seconds
INTERVAL = int(os.getenv('COLLECTION_INTERVAL', '10'))

def get_system_metrics():
    """Collect system metrics."""
    hostname = socket.gethostname()
    timestamp = int(time.time() * 1e9)  # Convert to nanoseconds for InfluxDB
    
    metrics = []
    
    # CPU metrics
    cpu_metrics = {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'cpu_freq': psutil.cpu_freq().current if psutil.cpu_freq() else 0,
    }
    metrics.append({
        "measurement": "cpu",
        "tags": {
            "host": hostname,
            "metric_type": "usage"
        },
        "time": timestamp,
        "fields": cpu_metrics
    })
    
    # Load average metrics
    load_metrics = {
        'load_1min': psutil.getloadavg()[0],
        'load_5min': psutil.getloadavg()[1],
        'load_15min': psutil.getloadavg()[2]
    }
    metrics.append({
        "measurement": "system_load",
        "tags": {
            "host": hostname,
            "metric_type": "load_average"
        },
        "time": timestamp,
        "fields": load_metrics
    })
    
    # Memory metrics
    memory = psutil.virtual_memory()
    memory_metrics = {
        'total': memory.total,
        'available': memory.available,
        'used': memory.used,
        'percent': memory.percent
    }
    metrics.append({
        "measurement": "memory",
        "tags": {
            "host": hostname,
            "metric_type": "usage"
        },
        "time": timestamp,
        "fields": memory_metrics
    })
    
    # Disk metrics
    disk = psutil.disk_usage('/')
    disk_metrics = {
        'total': disk.total,
        'used': disk.used,
        'free': disk.free,
        'percent': disk.percent
    }
    metrics.append({
        "measurement": "disk",
        "tags": {
            "host": hostname,
            "device": "/",
            "metric_type": "usage"
        },
        "time": timestamp,
        "fields": disk_metrics
    })
    
    # CPU temperature (Raspberry Pi)
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read().strip()) / 1000.0
            metrics.append({
                "measurement": "temperature",
                "tags": {
                    "host": hostname,
                    "sensor": "cpu",
                    "metric_type": "temperature"
                },
                "time": timestamp,
                "fields": {
                    "celsius": temp
                }
            })
    except:
        pass
        
    return metrics

def write_metrics(client, metrics):
    """Write metrics to InfluxDB."""
    try:
        client.write_points(metrics)
        print(f"Successfully wrote {len(metrics)} metrics to InfluxDB")
    except Exception as e:
        print(f"Error writing to InfluxDB: {e}")

def main():
    """Main collection loop."""
    print(f"Starting system metrics collector...")
    print(f"InfluxDB URL: {INFLUX_URL}")
    print(f"Collection interval: {INTERVAL} seconds")
    
    # Create InfluxDB client
    client = InfluxDBClient(host='influxdb', port=8086)
    
    # Ensure database exists
    databases = client.get_list_database()
    if INFLUX_DB not in [db['name'] for db in databases]:
        client.create_database(INFLUX_DB)
        print(f"Created database: {INFLUX_DB}")
    
    client.switch_database(INFLUX_DB)
    print(f"Connected to database: {INFLUX_DB}")
    
    # Main collection loop
    while True:
        try:
            metrics = get_system_metrics()
            write_metrics(client, metrics)
        except Exception as e:
            print(f"Error collecting metrics: {e}")
        
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
