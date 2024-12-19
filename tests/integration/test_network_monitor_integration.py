#!/usr/bin/env python3

import os
import time
import pytest
import docker
from pathlib import Path
from influxdb_client import InfluxDBClient

# Import the NetworkMonitor class
from services.network_monitor.network_monitor import NetworkMonitor

class TestNetworkMonitorIntegration:
    """Integration tests for NetworkMonitor service."""

    @pytest.fixture(scope="class")
    def docker_client(self):
        """Create Docker client."""
        return docker.from_env()

    @pytest.fixture(scope="class")
    def influx_client(self):
        """Create InfluxDB client."""
        client = InfluxDBClient(url="http://localhost:8086")
        # Wait for InfluxDB to be ready
        for _ in range(30):
            try:
                client.ping()
                break
            except:
                time.sleep(1)
        return client

    @pytest.fixture(scope="class")
    def network_monitor(self, influx_client):
        """Create NetworkMonitor instance."""
        monitor = NetworkMonitor()
        # Override interface for testing
        os.environ['NETWORK_INTERFACE'] = 'test0'
        yield monitor
        # Cleanup
        del os.environ['NETWORK_INTERFACE']

    def test_influxdb_connection(self, network_monitor):
        """Test InfluxDB connection and bucket creation."""
        # Setup should create the bucket
        network_monitor.setup_influxdb()
        
        # Verify bucket exists
        buckets = network_monitor.influx_client.buckets_api().find_buckets()
        bucket_names = [b.name for b in buckets]
        assert "network_metrics" in bucket_names

    def test_metric_writing(self, network_monitor, influx_client):
        """Test writing and reading metrics."""
        # Write test metric
        test_status = {
            'connected': True,
            'ssid': 'Test Network',
            'frequency': 2.4,
            'rssi': -65,
            'quality': 80
        }
        network_monitor.log_wifi_status(test_status)
        
        # Wait for write to complete
        time.sleep(1)
        
        # Query metric
        query = '''
            from(bucket: "network_metrics")
                |> range(start: -1m)
                |> filter(fn: (r) => r["_measurement"] == "wifi_status")
                |> last()
        '''
        result = influx_client.query_api().query(query)
        
        # Verify metric values
        assert len(result) > 0
        record = result[0].records[0]
        assert record.values["connected"] == True
        assert record.values["ssid"] == "Test Network"
        assert record.values["rssi"] == -65

    def test_event_logging(self, network_monitor, influx_client):
        """Test connection event logging."""
        # Log connection change event
        old_status = {'connected': True, 'ssid': 'Old Network'}
        new_status = {'connected': True, 'ssid': 'New Network'}
        
        network_monitor.last_wifi_status = old_status
        network_monitor.log_wifi_status(new_status)
        
        # Wait for write to complete
        time.sleep(1)
        
        # Query events
        query = '''
            from(bucket: "network_metrics")
                |> range(start: -1m)
                |> filter(fn: (r) => r["_measurement"] == "network_events")
                |> last()
        '''
        result = influx_client.query_api().query(query)
        
        # Verify event was logged
        assert len(result) > 0
        record = result[0].records[0]
        assert record.values["event_type"] == "connect"
        assert record.values["previous_ssid"] == "Old Network"
        assert record.values["new_ssid"] == "New Network"

    def test_service_container(self, docker_client):
        """Test network monitor service container."""
        # Start the service
        container = docker_client.containers.run(
            "data-hub/network-monitor:latest",
            detach=True,
            network_mode="host",
            environment={
                "NETWORK_INTERFACE": "test0",
                "SPEED_TEST_INTERVAL": "3600",
                "WIFI_CHECK_INTERVAL": "30",
                "INFLUX_URL": "http://localhost:8086"
            },
            privileged=True
        )
        
        try:
            # Wait for container to be ready
            time.sleep(5)
            
            # Check container is running
            container.reload()
            assert container.status == "running"
            
            # Check logs for expected startup messages
            logs = container.logs().decode('utf-8')
            assert "Starting network monitor" in logs
            assert "Created InfluxDB bucket" in logs
            
            # Check health status
            health = container.attrs['State'].get('Health', {})
            assert health.get('Status') == 'healthy'
        
        finally:
            # Cleanup
            container.remove(force=True)

    def test_data_persistence(self, network_monitor, docker_client):
        """Test data persistence across service restarts."""
        # Write test data
        test_status = {
            'connected': True,
            'ssid': 'Persistence Test',
            'frequency': 5.0,
            'rssi': -70,
            'quality': 75
        }
        network_monitor.log_wifi_status(test_status)
        
        # Restart InfluxDB container
        container = docker_client.containers.get('data-hub_influxdb_1')
        container.restart()
        
        # Wait for container to be ready
        time.sleep(5)
        
        # Query data after restart
        query = '''
            from(bucket: "network_metrics")
                |> range(start: -5m)
                |> filter(fn: (r) => r["_measurement"] == "wifi_status")
                |> filter(fn: (r) => r["ssid"] == "Persistence Test")
                |> last()
        '''
        result = network_monitor.influx_client.query_api().query(query)
        
        # Verify data persisted
        assert len(result) > 0
        record = result[0].records[0]
        assert record.values["ssid"] == "Persistence Test"
        assert record.values["rssi"] == -70

if __name__ == '__main__':
    pytest.main([__file__])
