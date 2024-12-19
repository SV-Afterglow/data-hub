#!/usr/bin/env python3

import os
import time
import pytest
import docker
import requests
from pathlib import Path
from influxdb import InfluxDBClient

class TestServiceInteractions:
    """Test interactions between services."""

    @pytest.fixture(scope="class")
    def docker_client(self):
        """Create Docker client."""
        return docker.from_env()

    @pytest.fixture(scope="class")
    def influx_client(self):
        """Create InfluxDB client."""
        client = InfluxDBClient(host='localhost', port=8086)
        # Wait for InfluxDB to be ready
        for _ in range(30):
            try:
                client.ping()
                break
            except:
                time.sleep(1)
        return client

    def test_service_startup_order(self, docker_client):
        """Test services start in correct order with dependencies."""
        # Get all running containers
        containers = docker_client.containers.list()
        
        # Get container start times
        start_times = {
            c.name: c.attrs['State']['StartedAt']
            for c in containers
            if 'data-hub' in c.name
        }
        
        # Verify InfluxDB starts before dependent services
        influx_start = start_times.get('data-hub_influxdb_1')
        assert influx_start is not None, "InfluxDB not running"
        
        for name, start_time in start_times.items():
            if 'influxdb' not in name:
                assert start_time > influx_start, f"{name} started before InfluxDB"

    def test_influxdb_data_persistence(self, influx_client, docker_client):
        """Test data persists across service restarts."""
        # Write test data
        test_data = [{
            "measurement": "test_measurement",
            "tags": {"test": "persistence"},
            "fields": {"value": 123}
        }]
        
        db_name = "test_persistence"
        influx_client.create_database(db_name)
        influx_client.switch_database(db_name)
        influx_client.write_points(test_data)
        
        # Restart InfluxDB container
        container = docker_client.containers.get('data-hub_influxdb_1')
        container.restart()
        
        # Wait for container to be ready
        time.sleep(5)
        
        # Verify data still exists
        result = influx_client.query('SELECT * FROM test_measurement')
        points = list(result.get_points())
        assert len(points) == 1
        assert points[0]['value'] == 123

    def test_metrics_collection(self, influx_client):
        """Test system metrics are being collected."""
        # Wait for metrics to be collected
        time.sleep(15)
        
        # Check each metric type
        metrics = ['cpu', 'memory', 'disk', 'system_load']
        for metric in metrics:
            result = influx_client.query(f'SELECT * FROM {metric} LIMIT 1')
            points = list(result.get_points())
            assert len(points) > 0, f"No {metric} metrics found"

    def test_update_service_monitoring(self, influx_client):
        """Test update service logs updates to InfluxDB."""
        # Query update metrics
        result = influx_client.query('''
            SELECT * FROM system_update 
            WHERE time > now() - 1h 
            ORDER BY time DESC 
            LIMIT 1
        ''')
        points = list(result.get_points())
        
        # Verify update metrics exist
        assert len(points) > 0, "No update metrics found"
        assert 'success' in points[0], "Update status not logged"

    def test_service_health_checks(self, docker_client):
        """Test service health checks are working."""
        containers = docker_client.containers.list()
        for container in containers:
            if 'data-hub' in container.name:
                health = container.attrs['State'].get('Health', {})
                status = health.get('Status', 'none')
                assert status in ['healthy', 'none'], \
                    f"Container {container.name} health check failed: {status}"

class TestDataPersistence:
    """Test data persistence across updates."""

    @pytest.fixture(scope="class")
    def test_data_dir(self):
        """Create test data directory."""
        data_dir = Path.home() / '.data-hub' / 'test'
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def test_config_persistence(self, test_data_dir):
        """Test configuration files persist across updates."""
        # Create test config
        config_file = test_data_dir / 'test_config.yml'
        config_file.write_text('test: value')
        
        # Simulate update
        from services.update_service.updater import UpdateService
        service = UpdateService()
        service.backup_system()
        
        # Verify config persists
        assert config_file.exists()
        assert config_file.read_text() == 'test: value'

    def test_volume_persistence(self, docker_client):
        """Test Docker volume data persists."""
        # Get volume information
        volumes = docker_client.volumes.list(
            filters={'name': 'data-hub'}
        )
        
        for volume in volumes:
            # Verify volume exists and is in use
            assert volume.attrs['Status']['Status'] == 'in-use'
            
            # Verify mount points are accessible
            mount_point = volume.attrs['Mountpoint']
            assert os.path.exists(mount_point)
            assert os.access(mount_point, os.R_OK | os.W_OK)

if __name__ == '__main__':
    pytest.main([__file__])
