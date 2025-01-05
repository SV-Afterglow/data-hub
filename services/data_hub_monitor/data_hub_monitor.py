#!/usr/bin/env python3
import os
import time
import socket
import psutil
import logging
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.buckets_api import BucketsApi, Bucket
from influxdb_client.rest import ApiException

# ----------------------------
# User Configurable Constants
# ----------------------------
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "ViLVYArh1w45FPeMth_hCjKdZfYH-ljFcZ7YkJi635igo8mEojjb8X-fyTzxj6Zy0dv1sEr_aqRn5jznIx7Qrg=="  # Replace with your token
INFLUX_ORG = "Afterglow"
INFLUX_BUCKET = "data-hub-monitor"

# Polling interval in seconds
POLL_INTERVAL = 15

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] data-hub-monitor: %(message)s"
)

def create_bucket_if_missing(client, bucket_name, org):
    """
    Checks if a bucket exists. If not, create it.
    """
    buckets_api = client.buckets_api()
    try:
        # Attempt to retrieve existing bucket
        existing_buckets = buckets_api.find_buckets(name=bucket_name)
        if not existing_buckets or len(existing_buckets.buckets) == 0:
            logging.info(f"Bucket '{bucket_name}' not found. Creating it.")
            buckets_api.create_bucket(
                bucket_name=bucket_name,
                org=org
            )
        else:
            logging.info(f"Bucket '{bucket_name}' exists. No need to create.")
    except ApiException as e:
        logging.error(f"Error checking/creating bucket: {e}")
        raise

def get_temperature_celsius():
    """
    Gets CPU temperature in Celsius.
    This may differ depending on your hardware/OS. 
    For Raspberry Pi, you can often read from /sys/class/thermal/thermal_zone0/temp.
    """
    temp_path = "/sys/class/thermal/thermal_zone0/temp"
    try:
        with open(temp_path, "r") as f:
            temp_str = f.read().strip()
            # The file typically returns temp in millidegrees Celsius
            return float(temp_str) / 1000.0
    except FileNotFoundError:
        logging.warning("Temperature file not found. Returning 0 as fallback.")
        return 0.0
    except Exception as e:
        logging.error(f"Error reading temperature: {e}")
        return 0.0

def get_uptime_seconds():
    """
    Reads system uptime from /proc/uptime (Linux).
    """
    try:
        with open("/proc/uptime", "r") as f:
            contents = f.read().strip().split()
            return float(contents[0])
    except Exception as e:
        logging.error(f"Error reading uptime: {e}")
        return 0.0

def main():
    # Get hostname to tag metrics
    host = socket.gethostname()

    # Initialize InfluxDB client
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

    # Ensure our bucket exists (create if missing)
    create_bucket_if_missing(client, INFLUX_BUCKET, INFLUX_ORG)

    write_api = client.write_api(write_options=SYNCHRONOUS)

    logging.info("Starting data-hub-monitor service...")

    while True:
        # Gather metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        mem_info = psutil.virtual_memory()  # total, available, percent, etc.
        disk_info = psutil.disk_usage("/")  # total, used, free, etc.
        temperature_c = get_temperature_celsius()
        uptime_sec = get_uptime_seconds()

        # Create InfluxDB point
        # Influx best practices: measurement name is something generic like "system_stats"
        # Use fields for numeric data, tags for identifying metadata (like hostname).
        # Timestamp is auto-generated using system time.
        point = (
            Point("system_stats")
            .tag("host", host)
            .field("cpu_usage_percent", cpu_percent)
            .field("mem_usage_percent", mem_info.percent)
            .field("disk_usage_percent", disk_info.percent)
            .field("mem_available_bytes", mem_info.available)
            .field("disk_free_bytes", disk_info.free)
            .field("temperature_c", temperature_c)
            .field("uptime_seconds", uptime_sec)
            .time(datetime.utcnow(), WritePrecision.NS)
        )

        # Write to InfluxDB
        try:
            write_api.write(bucket=INFLUX_BUCKET, record=point)
            logging.info("Metrics written to InfluxDB.")
        except Exception as e:
            logging.error(f"Failed to write metrics: {e}")

        # Sleep until next poll
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()