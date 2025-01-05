#!/usr/bin/env python3
import os
import time
import json
import socket
import psutil
import logging
import subprocess
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
        # Get default interface
        import netifaces
        default_iface = netifaces.gateways()['default'][netifaces.AF_INET][1]
        ip = netifaces.ifaddresses(default_iface)[netifaces.AF_INET][0]
        network = '.'.join(ip['addr'].split('.')[:-1] + ['0/24'])

        # Create ARP request packet
        arp = ARP(pdst=network)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether/arp

        # Send packet and get responses
        result = srp(packet, timeout=3, verbose=0, iface=default_iface)[0]
        
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

def run_speed_test():
    """Runs a speed test using the official Ookla speedtest CLI."""
    try:
        logging.info("Starting speed test...")
        result = subprocess.run(
            ['speedtest', '--accept-license', '-f', 'json'],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        logging.info("Speed test completed successfully.")
        return {
            'download': data['download']['bandwidth'] * 8 / 1_000_000,  # Convert bytes/s to Mbps
            'upload': data['upload']['bandwidth'] * 8 / 1_000_000,      # Convert bytes/s to Mbps
            'ping': data['ping']['latency'],
            'jitter': data['ping']['jitter'],
            'packet_loss': data['packetLoss'],
            'server_name': data['server']['name'],
            'server_location': f"{data['server']['location']}, {data['server']['country']}"
        }
    except Exception as e:
        logging.error(f"Error running speed test: {e}")
        return None

def main():
    # Get hostname to tag metrics
    host = socket.gethostname()

    # Initialize InfluxDB client
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

    # Ensure our bucket exists
    create_bucket_if_missing(client, INFLUX_BUCKET, INFLUX_ORG)

    write_api = client.write_api(write_options=SYNCHRONOUS)

    logging.info("Starting network-monitor service...")

    last_speed_test = 0
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

            # Run speed test if interval has elapsed
            current_time = time.time()
            if current_time - last_speed_test >= 3600:  # Every hour
                speed_data = run_speed_test()
                if speed_data:
                    point = Point("speed_test") \
                        .tag("host", host) \
                        .tag("server_name", speed_data['server_name']) \
                        .tag("server_location", speed_data['server_location']) \
                        .field("download_mbps", speed_data['download']) \
                        .field("upload_mbps", speed_data['upload']) \
                        .field("ping_ms", speed_data['ping']) \
                        .field("jitter_ms", speed_data['jitter']) \
                        .field("packet_loss_percent", speed_data['packet_loss']) \
                        .time(datetime.utcnow(), WritePrecision.NS)
                    
                    write_api.write(bucket=INFLUX_BUCKET, record=point)
                    logging.info(f"Speed test results written to InfluxDB: {speed_data['download']:.1f} Mbps down, {speed_data['upload']:.1f} Mbps up, {speed_data['ping']:.1f} ms ping")
                    last_speed_test = current_time

        except Exception as e:
            logging.error(f"Error in main loop: {e}")

        # Sleep until next poll
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
