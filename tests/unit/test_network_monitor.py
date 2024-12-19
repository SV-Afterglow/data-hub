#!/usr/bin/env python3

import os
import sys
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from influxdb_client import Point

# Mock the iwlib module since it requires system dependencies
sys.modules['iwlib'] = MagicMock()
sys.modules['python_wifi'] = MagicMock()

from services.network_monitor.network_monitor import NetworkMonitor

@pytest.fixture
def network_monitor():
    """Create a NetworkMonitor instance with mocked clients."""
    with patch('services.network_monitor.network_monitor.InfluxDBClient') as mock_influx, \
         patch('speedtest.Speedtest') as mock_speedtest:
        # Mock the bucket API
        mock_bucket = Mock()
        mock_bucket.name = "network_metrics"
        mock_bucket_api = Mock()
        mock_bucket_api.find_buckets.return_value = [mock_bucket]
        mock_influx.buckets_api.return_value = mock_bucket_api

        # Mock write API
        mock_write_api = Mock()
        mock_influx.write_api.return_value = mock_write_api

        # Mock ping method
        mock_influx.ping.return_value = True

        # Create monitor with mocked clients
        with patch.dict('os.environ', {'INFLUX_URL': 'http://mock:8086'}):
            monitor = NetworkMonitor()
            monitor.speedtest_client = mock_speedtest
            yield monitor

class TestWiFiStatus:
    """Test WiFi status monitoring functionality."""

    def test_parse_connected_wifi(self, network_monitor):
        """Test parsing iwconfig output when connected."""
        mock_output = """
        wlan0     IEEE 802.11  ESSID:"Test Network"  
                  Mode:Managed  Frequency:2.412 GHz  Access Point: 00:11:22:33:44:55   
                  Bit Rate=72.2 Mb/s   Tx-Power=20 dBm   
                  Retry short limit:7   RTS thr:off   Fragment thr:off
                  Power Management:on
                  Link Quality=70/70  Signal level=-50 dBm  
                  Rx invalid nwid:0  Rx invalid crypt:0  Rx invalid frag:0
                  Tx excessive retries:0  Invalid misc:0   Missed beacon:0
        """
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = mock_output
            mock_run.return_value.returncode = 0
            
            status = network_monitor.get_wifi_status()
            
            assert status['connected'] == True
            assert status['ssid'] == "Test Network"
            assert status['frequency'] == 2.412
            assert status['rssi'] == -50
            assert status['quality'] == 100.0

    def test_parse_disconnected_wifi(self, network_monitor):
        """Test parsing iwconfig output when disconnected."""
        mock_output = """
        wlan0     IEEE 802.11  ESSID:off/any  
                  Mode:Managed  Access Point: Not-Associated   
                  Retry short limit:7   RTS thr:off   Fragment thr:off
                  Power Management:on
        """
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = mock_output
            mock_run.return_value.returncode = 0
            
            status = network_monitor.get_wifi_status()
            
            assert status['connected'] == False
            assert status['ssid'] is None
            assert status['frequency'] is None
            assert status['rssi'] is None
            assert status['quality'] is None

    def test_iwconfig_failure(self, network_monitor):
        """Test handling of iwconfig command failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Device not found"
            
            with pytest.raises(Exception) as exc:
                network_monitor.get_wifi_status()
            # Check the original exception message inside the RetryError
            assert "iwconfig failed" in str(exc.value.last_attempt.exception())

class TestSpeedTest:
    """Test network speed testing functionality."""

    def test_successful_speed_test(self, network_monitor):
        """Test successful speed test execution."""
        # Mock speedtest results
        network_monitor.speedtest_client.download.return_value = 50_000_000  # 50 Mbps
        network_monitor.speedtest_client.upload.return_value = 20_000_000   # 20 Mbps
        network_monitor.speedtest_client.results = Mock(
            ping=20,
            server={'host': 'test.speedtest.net'}
        )
        
        # Run speed test
        network_monitor.run_speed_test()
        
        # Verify metrics were logged
        write_api = network_monitor.influx_client.write_api.return_value
        assert write_api.write.called
        
        # Verify correct values
        point = write_api.write.call_args[1]['record']
        assert isinstance(point, Point)
        assert point._fields['download_mbps'] == 50.0
        assert point._fields['upload_mbps'] == 20.0
        assert point._fields['latency_ms'] == 20

    def test_speed_test_throttling(self, network_monitor):
        """Test speed test throttling."""
        # Set last test time to recent
        network_monitor.last_speed_test = time.time()
        
        # Attempt speed test
        network_monitor.run_speed_test()
        
        # Verify no test was run
        assert not network_monitor.speedtest_client.download.called
        assert not network_monitor.speedtest_client.upload.called

class TestMetricsLogging:
    """Test InfluxDB metrics logging."""

    def test_wifi_status_logging(self, network_monitor):
        """Test logging of WiFi status metrics."""
        status = {
            'connected': True,
            'ssid': 'Test Network',
            'frequency': 2.4,
            'rssi': -65,
            'quality': 80
        }
        
        network_monitor.log_wifi_status(status)
        
        write_api = network_monitor.influx_client.write_api.return_value
        point = write_api.write.call_args[1]['record']
        
        assert point._fields['connected'] == True
        assert point._fields['ssid'] == 'Test Network'
        assert point._fields['rssi'] == -65
        assert point._fields['quality'] == 80

    def test_connection_event_logging(self, network_monitor):
        """Test logging of connection state changes."""
        old_status = {
            'connected': True,
            'ssid': 'Old Network'
        }
        new_status = {
            'connected': True,
            'ssid': 'New Network'
        }
        
        # Set initial status
        network_monitor.last_wifi_status = old_status
        
        # Log new status
        network_monitor.log_wifi_status(new_status)
        
        # Verify event was logged
        write_api = network_monitor.influx_client.write_api.return_value
        calls = write_api.write.call_args_list
        
        # Should have two writes: status and event
        assert len(calls) == 2
        
        # Verify event fields
        event_point = calls[1][1]['record']
        assert event_point._fields['event_type'] == 'connect'
        assert event_point._fields['previous_ssid'] == 'Old Network'
        assert event_point._fields['new_ssid'] == 'New Network'

class TestHealthCheck:
    """Test service health checking."""

    def test_healthy_service(self, network_monitor):
        """Test health check when service is healthy."""
        with patch('os.path.exists', return_value=True):
            healthy, message = network_monitor.check_health()
            assert healthy == True
            assert "healthy" in message

    def test_missing_interface(self, network_monitor):
        """Test health check with missing network interface."""
        with patch('os.path.exists', return_value=False):
            healthy, message = network_monitor.check_health()
            assert healthy == False
            assert "Interface" in message

    def test_influxdb_failure(self, network_monitor):
        """Test health check with InfluxDB connection failure."""
        network_monitor.influx_client.ping.side_effect = Exception("Connection failed")
        
        with patch('os.path.exists', return_value=True):
            healthy, message = network_monitor.check_health()
            assert healthy == False
            assert "Connection failed" in message

if __name__ == '__main__':
    pytest.main([__file__, "--asyncio-default-fixture-loop-scope=function"])
