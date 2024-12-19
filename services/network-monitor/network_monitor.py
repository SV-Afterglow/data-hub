#!/usr/bin/env python3

import os
import time
import json
import logging
import schedule
import subprocess
import speedtest
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from tenacity import retry, stop_after_attempt, wait_exponential

# Configuration from environment variables
NETWORK_INTERFACE = os.getenv('NETWORK_INTERFACE', 'wlan0')
SPEED_TEST_INTERVAL = int(os.getenv('SPEED_TEST_INTERVAL', '3600'))
WIFI_CHECK_INTERVAL = int(os.getenv('WIFI_CHECK_INTERVAL', '30'))
INFLUX_URL = os.getenv('INFLUX_URL', 'http://influxdb:8086')
MIN_SPEED_TEST_INTERVAL = int(os.getenv('MIN_SPEED_TEST_INTERVAL', '600'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('network-monitor')

class NetworkMonitor:
    def __init__(self):
        """Initialize the network monitor."""
        self.influx_client = InfluxDBClient(url=INFLUX_URL)
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        self.speedtest_client = speedtest.Speedtest()
        self.last_wifi_status = None
        self.last_speed_test = 0
        self.setup_influxdb()

    def setup_influxdb(self):
        """Ensure InfluxDB is properly configured."""
        try:
            bucket_api = self.influx_client.buckets_api()
            if "network_metrics" not in [b.name for b in bucket_api.find_buckets()]:
                bucket_api.create_bucket(bucket_name="network_metrics")
                logger.info("Created InfluxDB bucket: network_metrics")
        except Exception as e:
            logger.error(f"Error setting up InfluxDB: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_wifi_status(self):
        """Get current WiFi connection status."""
        try:
            # Get interface info using iwconfig
            iwconfig = subprocess.run(
                ['iwconfig', NETWORK_INTERFACE],
                capture_output=True,
                text=True
            )
            
            if iwconfig.returncode != 0:
                raise Exception(f"iwconfig failed: {iwconfig.stderr}")

            output = iwconfig.stdout
            
            # Parse iwconfig output
            status = {
                'connected': 'ESSID:' in output and 'ESSID:"off/any"' not in output,
                'ssid': None,
                'frequency': None,
                'rssi': None,
                'quality': None
            }

            # Extract values if connected
            if status['connected']:
                try:
                    # Extract SSID
                    if 'ESSID:' in output:
                        status['ssid'] = output.split('ESSID:"')[1].split('"')[0]

                    # Extract frequency
                    if 'Frequency:' in output:
                        freq = output.split('Frequency:')[1].split(' ')[0]
                        status['frequency'] = float(freq)

                    # Extract signal level
                    if 'Signal level=' in output:
                        signal = output.split('Signal level=')[1].split(' ')[0]
                        status['rssi'] = int(signal)

                    # Extract link quality
                    if 'Link Quality=' in output:
                        quality = output.split('Link Quality=')[1].split(' ')[0]
                        num, den = quality.split('/')
                        status['quality'] = (int(num) / int(den)) * 100
                except Exception as e:
                    logger.error(f"Error parsing WiFi status: {e}")
                    status['connected'] = False

            return status

        except Exception as e:
            logger.error(f"Error getting WiFi status: {e}")
            if "iwconfig failed" in str(e):
                raise
            status = {
                'connected': False,
                'ssid': None,
                'frequency': None,
                'rssi': None,
                'quality': None
            }
            return status

    def log_wifi_status(self, status):
        """Log WiFi status to InfluxDB."""
        try:
            # Create status point with required fields
            point = Point("wifi_status") \
                .tag("interface", NETWORK_INTERFACE) \
                .tag("connection_type", "wifi") \
                .field("connected", status['connected'])

            # Add optional fields if present
            if status['connected']:
                if status.get('ssid'):
                    point = point.field("ssid", status['ssid'])
                if status.get('frequency'):
                    point = point.field("frequency", status['frequency'])
                if status.get('rssi'):
                    point = point.field("rssi", status['rssi'])
                if status.get('quality'):
                    point = point.field("quality", status['quality'])

            self.write_api.write(bucket="network_metrics", record=point)
            
            # Log connection state changes
            if self.last_wifi_status is None:
                self.last_wifi_status = status.copy()
            elif self.last_wifi_status['connected'] != status['connected'] or \
                 (status['connected'] and self.last_wifi_status.get('ssid') != status.get('ssid')):
                event = Point("network_events") \
                    .tag("interface", NETWORK_INTERFACE) \
                    .tag("event_category", "connection") \
                    .field("event_type", "connect" if status['connected'] else "disconnect") \
                    .field("previous_ssid", self.last_wifi_status.get('ssid')) \
                    .field("new_ssid", status.get('ssid'))
                self.write_api.write(bucket="network_metrics", record=event)
                self.last_wifi_status = status.copy()

        except Exception as e:
            logger.error(f"Error logging WiFi status: {e}")

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=4, max=10))
    def run_speed_test(self):
        """Run network speed test."""
        try:
            # Check if enough time has passed since last test
            now = time.time()
            if now - self.last_speed_test < MIN_SPEED_TEST_INTERVAL:
                logger.info("Skipping speed test - minimum interval not reached")
                return

            logger.info("Starting speed test")
            
            # Get best server
            self.speedtest_client.get_best_server()
            
            # Run tests
            download_speed = self.speedtest_client.download() / 1_000_000  # Convert to Mbps
            upload_speed = self.speedtest_client.upload() / 1_000_000      # Convert to Mbps
            ping = self.speedtest_client.results.ping
            
            # Log results
            point = Point("network_speed") \
                .tag("interface", NETWORK_INTERFACE) \
                .tag("test_server", self.speedtest_client.results.server['host']) \
                .field("download_mbps", download_speed) \
                .field("upload_mbps", upload_speed) \
                .field("latency_ms", ping)

            self.write_api.write(bucket="network_metrics", record=point)
            
            self.last_speed_test = now
            logger.info(f"Speed test complete - Down: {download_speed:.1f} Mbps, Up: {upload_speed:.1f} Mbps, Ping: {ping:.0f}ms")

        except Exception as e:
            logger.error(f"Error running speed test: {e}")
            raise

    def check_health(self):
        """Check service health."""
        try:
            # Verify WiFi interface exists
            if not os.path.exists(f"/sys/class/net/{NETWORK_INTERFACE}"):
                return False, f"Interface {NETWORK_INTERFACE} not found"

            # Verify InfluxDB connection
            self.influx_client.ping()

            return True, "Service healthy"
        except Exception as e:
            return False, str(e)

    def run(self):
        """Main monitoring loop."""
        logger.info(f"Starting network monitor for interface {NETWORK_INTERFACE}")
        
        # Schedule regular checks
        schedule.every(WIFI_CHECK_INTERVAL).seconds.do(
            lambda: self.log_wifi_status(self.get_wifi_status())
        )
        schedule.every(SPEED_TEST_INTERVAL).seconds.do(self.run_speed_test)

        # Initial checks
        self.log_wifi_status(self.get_wifi_status())
        self.run_speed_test()

        # Main loop
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    monitor = NetworkMonitor()
    monitor.run()
