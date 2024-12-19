#!/usr/bin/env python3

import os
import yaml
import json
import pytest
import docker
from pathlib import Path
from jsonschema import validate

class TestManifestValidation:
    """Validate update manifest files."""

    # Schema for manifest validation
    MANIFEST_SCHEMA = {
        "type": "object",
        "required": ["version", "steps"],
        "properties": {
            "version": {"type": "string"},
            "requires": {"type": "string"},
            "release_date": {"type": "string"},
            "description": {"type": "string"},
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type"],
                    "properties": {
                        "type": {"enum": ["service_config", "docker_compose", "system_package"]},
                        "path": {"type": "string"},
                        "target": {"type": "string"},
                        "description": {"type": "string"},
                        "permissions": {"pattern": "^[0-7]{3}$"},
                        "service": {"type": "string"},
                        "action": {"enum": ["restart", "recreate"]}
                    }
                }
            },
            "rollback": {
                "type": "object",
                "properties": {
                    "supported": {"type": "boolean"},
                    "steps": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    }

    def test_manifest_files(self):
        """Test all manifest files are valid."""
        updates_dir = Path("../updates")
        if not updates_dir.exists():
            pytest.skip("No updates directory found")

        for version_dir in updates_dir.iterdir():
            if version_dir.is_dir():
                manifest_file = version_dir / "manifest.yml"
                if manifest_file.exists():
                    with open(manifest_file) as f:
                        manifest = yaml.safe_load(f)
                        validate(instance=manifest, schema=self.MANIFEST_SCHEMA)

class TestDockerConfiguration:
    """Validate Docker configurations."""

    def test_dockerfile_best_practices(self):
        """Test Dockerfiles follow best practices."""
        docker_dir = Path("../docker")
        if not docker_dir.exists():
            pytest.skip("No docker directory found")

        for dockerfile in docker_dir.rglob("Dockerfile"):
            with open(dockerfile) as f:
                content = f.read().lower()
                
                # Check for multi-stage builds
                assert "from" in content, f"{dockerfile} should use FROM instruction"
                
                # Check for proper base image
                assert "alpine" in content or "slim" in content, \
                    f"{dockerfile} should use slim or Alpine base image"
                
                # Check for non-root user
                assert "user" in content, f"{dockerfile} should set non-root user"
                
                # Check for health check
                assert "healthcheck" in content, f"{dockerfile} should include HEALTHCHECK"

    def test_compose_configuration(self):
        """Test docker-compose configuration."""
        compose_file = Path("../docker/compose/docker-compose.yaml")
        if not compose_file.exists():
            pytest.skip("No docker-compose.yaml found")

        with open(compose_file) as f:
            config = yaml.safe_load(f)
            
            assert "version" in config, "Compose file should specify version"
            assert "services" in config, "Compose file should define services"
            assert "networks" in config, "Compose file should define networks"
            
            for service_name, service in config["services"].items():
                # Check for required fields
                assert "image" in service or "build" in service, \
                    f"{service_name} should specify image or build"
                
                # Check for restart policy
                assert service.get("restart") == "always", \
                    f"{service_name} should have restart: always"
                
                # Check for health checks
                assert "healthcheck" in service, \
                    f"{service_name} should have health check"
                
                # Check for proper labels
                if "watchtower" not in service_name:
                    assert "labels" in service and \
                           "com.centurylinklabs.watchtower.enable=false" in \
                           service["labels"], \
                           f"{service_name} should disable Watchtower"

class TestFilePermissions:
    """Validate file permissions."""

    def test_executable_permissions(self):
        """Test executable files have correct permissions."""
        executables = [
            "services/update-service/updater.py",
            "services/system-metrics/collector.py",
            "scripts/backup.sh",
            "scripts/restore.sh"
        ]
        
        for exe in executables:
            path = Path("..") / exe
            if path.exists():
                mode = oct(path.stat().st_mode)[-3:]
                assert mode == "755", \
                    f"{exe} should have 755 permissions, has {mode}"

    def test_config_permissions(self):
        """Test configuration files have correct permissions."""
        config_dirs = ["config", "docker/compose"]
        
        for config_dir in config_dirs:
            path = Path("..") / config_dir
            if path.exists():
                for config_file in path.rglob("*"):
                    if config_file.is_file():
                        mode = oct(config_file.stat().st_mode)[-3:]
                        assert mode in ["644", "640"], \
                            f"{config_file} has incorrect permissions: {mode}"

    def test_directory_permissions(self):
        """Test directory permissions."""
        dirs = {
            "services": "755",  # Executable for all
            "config": "750",    # Restricted access
            "data": "750"       # Restricted access
        }
        
        for dir_name, expected_mode in dirs.items():
            path = Path("..") / dir_name
            if path.exists():
                mode = oct(path.stat().st_mode)[-3:]
                assert mode == expected_mode, \
                    f"{dir_name} should have {expected_mode} permissions, has {mode}"

class TestNetworkSecurity:
    """Validate network security configurations."""

    @pytest.fixture(scope="class")
    def docker_client(self):
        """Create Docker client."""
        return docker.from_env()

    def test_network_isolation(self, docker_client):
        """Test network isolation between services."""
        networks = docker_client.networks.list(
            filters={"name": "data-hub"}
        )
        
        assert len(networks) > 0, "Data hub network not found"
        
        network = networks[0]
        containers = network.attrs["Containers"]
        
        # Verify SignalK is isolated
        signalk_containers = [c for c in containers.values() 
                            if "signalk" in c["Name"]]
        if signalk_containers:
            assert signalk_containers[0]["NetworkSettings"]["NetworkMode"] == "host", \
                "SignalK should use host network mode"
        
        # Verify other services use internal network
        for container in containers.values():
            if "signalk" not in container["Name"]:
                assert container["NetworkSettings"]["NetworkMode"] != "host", \
                    f"{container['Name']} should not use host network mode"

if __name__ == '__main__':
    pytest.main([__file__])
