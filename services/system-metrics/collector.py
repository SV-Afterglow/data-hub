#!/usr/bin/env python3

import os
import time
import psutil
import logging
import sys
from influxdb import InfluxDBClient

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger('system-metrics')

# InfluxDB configuration
INFLUX_URL = os.getenv('INFLUX_URL', 'http://influxdb:8086')
INFLUX_DB = "system_metrics"

# Collection interval in seconds
INTERVAL = int(os.getenv('COLLECTION_INTERVAL', '10'))

def get_system_metrics():
    """Collect system metrics."""
    logger.debug("Collecting system metrics...")
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
    except Exception as e:
        logger.warning(f"Could not read CPU temperature: {e}")
        metrics['cpu_temperature'] = 0
        
    logger.debug(f"Collected metrics: {metrics}")
    return metrics

def write_metrics(client, metrics):
    """Write metrics to InfluxDB."""
    json_body = [
        {
            "measurement": "system_metrics",
            "fields": metrics
        }
    ]
    
    try:
        client.write_points(json_body)
        logger.info(f"Successfully wrote metrics to InfluxDB: {metrics}")
    except Exception as e:
        logger.error(f"Error writing to InfluxDB: {e}", exc_info=True)

def main():
    """Main collection loop."""
    logger.info("Starting system metrics collector...")
    logger.info(f"InfluxDB URL: {INFLUX_URL}")
    logger.info(f"Collection interval: {INTERVAL} seconds")
    
    try:
        # Create InfluxDB client
        logger.debug("Creating InfluxDB client...")
        client = InfluxDBClient(host='influxdb', port=8086)
        
        # Ensure database exists
        logger.debug("Checking databases...")
        databases = client.get_list_database()
        logger.debug(f"Found databases: {databases}")
        
        if INFLUX_DB not in [db['name'] for db in databases]:
            logger.info(f"Creating database: {INFLUX_DB}")
            client.create_database(INFLUX_DB)
        
        client.switch_database(INFLUX_DB)
        logger.info(f"Connected to database: {INFLUX_DB}")
        
        # Main collection loop
        while True:
            try:
                metrics = get_system_metrics()
                write_metrics(client, metrics)
            except Exception as e:
                logger.error(f"Error in collection loop: {e}", exc_info=True)
            
            time.sleep(INTERVAL)
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
