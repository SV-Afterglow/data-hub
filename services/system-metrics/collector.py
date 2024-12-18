#!/usr/bin/env python3

import os
import time
import psutil
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# InfluxDB configuration
INFLUX_URL = os.getenv('INFLUX_URL', 'http://influxdb:8086')
INFLUX_TOKEN = os.getenv('INFLUX_TOKEN', '')  # Not needed if auth is disabled
INFLUX_ORG = os.getenv('INFLUX_ORG', '')     # Not needed if auth is disabled
INFLUX_BUCKET = "system_metrics"

# Collection interval in seconds
INTERVAL = int(os.getenv('COLLECTION_INTERVAL', '10'))

def get_system_metrics():
    """Collect system metrics."""
    metrics = {
        # CPU metrics
        'cpu_percent': psutil.cpu_percent(interval=1),
        'cpu_freq': psutil.cpu_freq().current if psutil.cpu_freq() else 0,
        'load_1min': psutil.getloadavg()[0],
        'load_5min': psutil.getloadavg()[1],
        'load_15min': psutil.getloadavg()[2],
        
        # Memory metrics
        'memory_total': psutil.virtual_memory().total,
        'memory_available': psutil.virtual_memory().available,
        'memory_used': psutil.virtual_memory().used,
        'memory_percent': psutil.virtual_memory().percent,
        
        # Disk metrics
        'disk_total': psutil.disk_usage('/').total,
        'disk_used': psutil.disk_usage('/').used,
        'disk_free': psutil.disk_usage('/').free,
        'disk_percent': psutil.disk_usage('/').percent,
    }
    
    # Get CPU temperature on Raspberry Pi
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read().strip()) / 1000.0
            metrics['cpu_temperature'] = temp
    except:
        metrics['cpu_temperature'] = 0
        
    return metrics

def write_metrics(client, metrics):
    """Write metrics to InfluxDB."""
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    point = Point("system_metrics")
    
    # Add all metrics as fields
    for key, value in metrics.items():
        point.field(key, value)
    
    try:
        write_api.write(bucket=INFLUX_BUCKET, record=point)
        print(f"Successfully wrote metrics to InfluxDB: {metrics}")
    except Exception as e:
        print(f"Error writing to InfluxDB: {e}")

def main():
    """Main collection loop."""
    print(f"Starting system metrics collector...")
    print(f"InfluxDB URL: {INFLUX_URL}")
    print(f"Collection interval: {INTERVAL} seconds")
    
    # Create InfluxDB client
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    
    # Ensure bucket exists
    try:
        buckets_api = client.buckets_api()
        if INFLUX_BUCKET not in [bucket.name for bucket in buckets_api.find_buckets()]:
            buckets_api.create_bucket(bucket_name=INFLUX_BUCKET)
            print(f"Created bucket: {INFLUX_BUCKET}")
    except Exception as e:
        print(f"Error checking/creating bucket: {e}")
    
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
