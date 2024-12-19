#!/usr/bin/env python3

import os
import yaml
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the UpdateService class
from services.update_service.updater import UpdateService, compare_versions

@pytest.fixture
def update_service():
    """Create an UpdateService instance with mocked clients."""
    with patch('docker.from_env') as mock_docker, \
         patch('influxdb.InfluxDBClient') as mock_influx:
        service = UpdateService()
        service.docker_client = mock_docker
        service.influx_client = mock_influx
        yield service

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)

class TestVersionValidation:
    """Test version comparison and validation."""
    
    def test_compare_versions(self):
        """Test version comparison logic."""
        assert compare_versions("1.1.0", "1.0.0") == True
        assert compare_versions("1.0.0", "1.1.0") == False
        assert compare_versions("1.0.0", "1.0.0") == False
        assert compare_versions("2.0.0", "1.9.9") == True

    def test_version_requirement_validation(self, update_service, temp_dir):
        """Test manifest version requirement validation."""
        manifest = {
            'version': '1.1.0',
            'requires': '1.0.0'
        }
        
        # Test when current version meets requirement
        with patch.object(update_service, 'get_current_version', return_value='1.0.0'):
            # Should not raise exception
            update_service.apply_update('1.1.0')

        # Test when current version doesn't meet requirement
        with patch.object(update_service, 'get_current_version', return_value='0.9.0'):
            with pytest.raises(Exception) as exc:
                update_service.apply_update('1.1.0')
            assert "does not meet required version" in str(exc.value)

class TestFilePermissions:
    """Test file permission handling."""

    def test_permission_setting(self, update_service, temp_dir):
        """Test setting file permissions from manifest."""
        test_file = temp_dir / "test.py"
        test_file.touch()

        step = {
            'type': 'service_config',
            'path': 'test.py',
            'target': str(test_file),
            'permissions': '755'
        }

        # Mock the file write operation
        with patch('builtins.open', MagicMock()), \
             patch('requests.get') as mock_get:
            mock_get.return_value.text = "test content"
            update_service.apply_update_step(step)

        assert oct(test_file.stat().st_mode)[-3:] == '755'

class TestServiceRestarts:
    """Test service-specific restart handling."""

    def test_specific_service_restart(self, update_service):
        """Test restarting specific services."""
        manifest = {
            'steps': [{
                'type': 'docker_compose',
                'service': 'test-service',
                'action': 'restart'
            }]
        }

        with patch.object(update_service, 'restart_services') as mock_restart:
            update_service.apply_update('1.0.0')
            mock_restart.assert_called_once_with({'test-service'})

    def test_all_services_restart(self, update_service):
        """Test restarting all services."""
        manifest = {
            'steps': [{
                'type': 'docker_compose',
                'action': 'restart'
            }]
        }

        expected_services = {'service1', 'service2'} - {'update-service', 'watchtower'}
        
        with patch.object(update_service, 'get_expected_services', return_value=expected_services), \
             patch.object(update_service, 'restart_services') as mock_restart:
            update_service.apply_update('1.0.0')
            mock_restart.assert_called_once_with(expected_services)

class TestManifestProcessing:
    """Test manifest processing and validation."""

    def test_valid_manifest(self, update_service):
        """Test processing a valid manifest."""
        manifest = {
            'version': '1.1.0',
            'requires': '1.0.0',
            'steps': [
                {
                    'type': 'service_config',
                    'path': 'test.py',
                    'target': '/data/test.py',
                    'permissions': '755'
                },
                {
                    'type': 'docker_compose',
                    'service': 'test-service',
                    'action': 'restart'
                }
            ]
        }

        with patch('requests.get') as mock_get, \
             patch.object(update_service, 'restart_services'), \
             patch('builtins.open', MagicMock()):
            mock_get.return_value.text = yaml.dump(manifest)
            mock_get.return_value.raise_for_status = MagicMock()
            
            # Should not raise exception
            update_service.apply_update('1.1.0')

    def test_invalid_manifest(self, update_service):
        """Test handling invalid manifest."""
        manifest = {
            'version': '1.1.0',
            'steps': [
                {
                    'type': 'invalid_type',
                    'path': 'test.py'
                }
            ]
        }

        with patch('requests.get') as mock_get, \
             patch.object(update_service, 'rollback_update'):
            mock_get.return_value.text = yaml.dump(manifest)
            mock_get.return_value.raise_for_status = MagicMock()
            
            # Should fail and trigger rollback
            assert update_service.apply_update('1.1.0') == False

if __name__ == '__main__':
    pytest.main([__file__])
