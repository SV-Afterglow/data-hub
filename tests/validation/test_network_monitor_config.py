#!/usr/bin/env python3

import os
import yaml
import pytest
from pathlib import Path

class TestNetworkMonitorConfig:
    """Validate Network Monitor configuration and setup."""

    def test_dockerfile_structure(self):
        """Validate Dockerfile follows best practices."""
        dockerfile_path = Path(__file__).parent.parent.parent / "docker/network_monitor/Dockerfile"
        assert dockerfile_path.exists(), "Dockerfile not found"
        
        with open(dockerfile_path) as f:
            content = f.read().lower()
            
            # Check multi-stage build
            assert content.count("from") >= 2, "Should use multi-stage build"
            
            # Check base image
            assert "python:3.11-slim" in content, "Should use slim Python image"
            
            # Check security practices
            assert "user" in content, "Should set non-root user"
            assert "healthcheck" in content, "Should include health check"
            
            # Check dependencies
            assert "wireless-tools" in content, "Missing wireless-tools package"
            assert "requirements.txt" in content, "Should install from requirements.txt"

    def test_compose_configuration(self):
        """Validate docker-compose service configuration."""
        compose_path = Path(__file__).parent.parent.parent / "docker/compose/docker-compose.yaml"
        assert compose_path.exists(), "docker-compose.yaml not found"
        
        with open(compose_path) as f:
            config = yaml.safe_load(f)
            
            # Check service exists
            assert "network_monitor" in config["services"], "Service not defined"
            service = config["services"]["network_monitor"]
            
            # Check required configuration
            assert service.get("network_mode") == "host", "Requires host network"
            assert service.get("privileged") is True, "Requires privileged mode"
            
            # Check volumes
            volumes = service.get("volumes", [])
            required_mounts = [
                "/etc/localtime",
                "/proc/net/dev",
                "/sys/class/net",
                "~/.data-hub"
            ]
            for mount in required_mounts:
                assert any(mount in v for v in volumes), f"Missing volume: {mount}"
            
            # Check environment
            env = service.get("environment", [])
            required_vars = {
                "NETWORK_INTERFACE": "wlan0",
                "SPEED_TEST_INTERVAL": "3600",
                "WIFI_CHECK_INTERVAL": "30",
                "INFLUX_URL": "http://influxdb:8086"
            }
            for var, expected_value in required_vars.items():
                env_var = f"{var}={expected_value}"
                assert env_var in env, f"Missing or incorrect environment variable: {var}"
            
            # Check dependencies
            assert "influxdb" in service.get("depends_on", []), "Missing InfluxDB dependency"
            
            # Check labels
            labels = service.get("labels", [])
            assert "com.centurylinklabs.watchtower.enable=false" in labels, "Missing Watchtower label"

    def test_python_requirements(self):
        """Validate Python package requirements."""
        req_path = Path(__file__).parent.parent.parent / "services/network_monitor/requirements.txt"
        assert req_path.exists(), "requirements.txt not found"
        
        with open(req_path) as f:
            requirements = f.read()
            
            # Check required packages
            required_packages = [
                "speedtest-cli",
                "influxdb-client",
                "python-wifi",
                "iwlib",
                "schedule"
            ]
            for package in required_packages:
                assert package in requirements, f"Missing requirement: {package}"

    def test_service_permissions(self):
        """Validate file permissions."""
        service_dir = Path(__file__).parent.parent.parent / "services/network_monitor"
        
        # Check executable permissions
        monitor_script = service_dir / "network_monitor.py"
        assert monitor_script.exists(), "Service script not found"
        assert oct(monitor_script.stat().st_mode)[-3:] == "755", "Incorrect script permissions"
        
        # Check config permissions
        req_file = service_dir / "requirements.txt"
        assert req_file.exists(), "requirements.txt not found"
        assert oct(req_file.stat().st_mode)[-3:] in ["644", "664"], "Incorrect requirements.txt permissions"

    def test_update_manifest(self):
        """Validate update manifest."""
        manifest_path = Path(__file__).parent.parent.parent / "updates/1.2.0/manifest.yml"
        assert manifest_path.exists(), "Update manifest not found"
        
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
            
            # Check version info
            assert "version" in manifest, "Missing version"
            assert "requires" in manifest, "Missing version requirement"
            
            # Check steps
            steps = manifest.get("steps", [])
            required_steps = [
                "network_monitor.py",
                "requirements.txt",
                "Dockerfile"
            ]
            step_files = [s.get("path", "").split("/")[-1] for s in steps]
            for req_file in required_steps:
                assert any(req_file in f for f in step_files), f"Missing step for: {req_file}"
            
            # Check permissions
            for step in steps:
                if step.get("path", "").endswith(".py"):
                    assert step.get("permissions") == "755", "Incorrect Python file permissions"
                else:
                    assert step.get("permissions") in ["644", None], "Incorrect file permissions"
            
            # Check rollback
            assert manifest.get("rollback", {}).get("supported") is True, "Rollback not supported"

if __name__ == '__main__':
    pytest.main([__file__])
