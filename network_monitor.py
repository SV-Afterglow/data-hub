#!/usr/bin/env python3
import os
import time
import socket
import psutil
import logging
from datetime import datetime
from scapy.all import ARP, Ether, srp
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Configuration
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "ViLVYArh1w45FPeMth_hCjKdZfYH-ljFcZ7YkJi635igo8mEojjb8X-fyTzxj6Zy0dv1sEr_aqRn5jznIx7Qrg=="
INFLUX_ORG = "Afterglow"
INFLUX_BUCKET = "network-monitor"

# 15 minutes interval
POLL_INTERVAL = 900

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] network-monitor: %(message)s"
)

def create_bucket_if_missing(client, bucket_name, org):
    """Checks if a bucket exists. If not, create it."""
    buckets_api = client.buckets_api()
    try:
        existing_buckets = buckets_api.find_buckets(name=bucket_name)
        if not existing_buckets or len(existing_buckets.buckets) == 0:
            logging.info(f"Bucket '{bucket_name}' not found. Creating it.")
            buckets_api.create_bucket(
                bucket_name=bucket_name,
                org=org
            )
        else:
            logging.info(f"Bucket '{bucket_name}' exists.")
    except Exception as e:
        logging.error(f"Error checking/creating bucket: {e}")
        raise

def get_network_usage():
    """Gets network I/O statistics."""
    try:
        net_io = psutil.net_io_counters()
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errin': net_io.errin,
            'errout': net_io.errout,
            'dropin': net_io.dropin,
            'dropout': net_io.dropout
        }
    except Exception as e:
        logging.error(f"Error getting network usage: {e}")
        return None

def scan_network():
    """Scans for devices on the local network."""
    try:
        # Create ARP request packet
        arp = ARP(pdst="10.147.17.0/24")  # Adjust network range as needed
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether/arp

        # Send packet and get responses
        result = srp(packet, timeout=3, verbose=0)[0]
        
        devices = []
        for sent, received in result:
            devices.append({
                'ip': received.psrc,
                'mac': received.hwsrc,
                'hostname': socket.getfqdn(received.psrc)
            })
        
        return devices
    except Exception as e:
        logging.error(f"Error scanning network: {e}")
        return []

def main():
    # Get hostname to tag metrics
    host = socket.gethostname()

    # Initialize InfluxDB client
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

    # Ensure our bucket exists
    create_bucket_if_missing(client, INFLUX_BUCKET, INFLUX_ORG)

    write_api = client.write_api(write_options=SYNCHRONOUS)

    logging.info("Starting network-monitor service...")

    while True:
        try:
            # Get network usage metrics
            net_stats = get_network_usage()
            if net_stats:
                point = Point("network_stats") \
                    .tag("host", host) \
                    .field("bytes_sent", net_stats['bytes_sent']) \
                    .field("bytes_recv", net_stats['bytes_recv']) \
                    .field("packets_sent", net_stats['packets_sent']) \
                    .field("packets_recv", net_stats['packets_recv']) \
                    .field("errin", net_stats['errin']) \
                    .field("errout", net_stats['errout']) \
                    .field("dropin", net_stats['dropin']) \
                    .field("dropout", net_stats['dropout']) \
                    .time(datetime.utcnow(), WritePrecision.NS)
                
                write_api.write(bucket=INFLUX_BUCKET, record=point)
                logging.info("Network usage metrics written to InfluxDB.")

            # Scan for devices
            devices = scan_network()
            for device in devices:
                point = Point("network_devices") \
                    .tag("host", host) \
                    .tag("mac", device['mac']) \
                    .tag("hostname", device['hostname']) \
                    .field("ip", device['ip']) \
                    .time(datetime.utcnow(), WritePrecision.NS)
                
                write_api.write(bucket=INFLUX_BUCKET, record=point)
            
            logging.info(f"Found {len(devices)} devices on network.")

        except Exception as e:
            logging.error(f"Error in main loop: {e}")

        # Sleep until next poll
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
