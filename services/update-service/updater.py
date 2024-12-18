#!/usr/bin/env python3

import os
import time
import yaml
import docker
import requests
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from packaging import version
from influxdb import InfluxDBClient  # Changed to use InfluxDB 1.8 client

# Configuration from environment variables
GITHUB_REPO = os.getenv('GITHUB_REPO', 'sv-afterglow/data-hub')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')
CHECK_INTERVAL = int(os.getenv('UPDATE_CHECK_INTERVAL', '3600'))  # Default 1 hour
DATA_DIR = Path(os.getenv('DATA_DIR', '/data'))
HOME_DIR = Path(os.path.expanduser('~'))
COMPOSE_FILE = HOME_DIR / 'data-hub/docker-compose.yml'  # Main compose file
INFLUX_URL = os.getenv('INFLUX_URL', 'http://influxdb:8086')
INFLUX_DB = "system_updates"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('update-service')

def compare_versions(v1, v2):
    """Compare two version strings."""
    try:
        return version.parse(v1) > version.parse(v2)
    except Exception as e:
        logger.error(f"Version comparison error: {e}")
        return False

class UpdateService:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.influx_client = InfluxDBClient(host='influxdb', port=8086)
        self.version_file = DATA_DIR / 'version.yml'
        self.backup_dir = DATA_DIR / 'backups'
        self.ensure_directories()
        self.setup_influxdb()

    def ensure_directories(self):
        """Ensure required directories exist."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        COMPOSE_FILE.parent.mkdir(parents=True, exist_ok=True)

    def setup_influxdb(self):
        """Setup InfluxDB database for update metrics."""
        try:
            databases = self.influx_client.get_list_database()
            if INFLUX_DB not in [db['name'] for db in databases]:
                self.influx_client.create_database(INFLUX_DB)
                logger.info(f"Created InfluxDB database: {INFLUX_DB}")
            self.influx_client.switch_database(INFLUX_DB)
        except Exception as e:
            logger.error(f"Error setting up InfluxDB: {e}")

    def log_metric(self, measurement, fields, tags=None):
        """Log a metric to InfluxDB."""
        try:
            point = {
                "measurement": measurement,
                "tags": tags or {},
                "fields": fields,
                "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            self.influx_client.write_points([point])
        except Exception as e:
            logger.error(f"Failed to log metric: {e}")

    def get_current_version(self):
        """Get current system version from version file."""
        try:
            if self.version_file.exists():
                with open(self.version_file, 'r') as f:
                    data = yaml.safe_load(f)
                    return data.get('version', '0.0.0')
        except Exception as e:
            logger.error(f"Error reading version file: {e}")
        return '0.0.0'

    def get_latest_version(self):
        """Get latest version from GitHub."""
        try:
            url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/version.yml"
            response = requests.get(url)
            response.raise_for_status()
            data = yaml.safe_load(response.text)
            return data.get('version')
        except Exception as e:
            logger.error(f"Error fetching latest version: {e}")
            return None

    def get_expected_services(self):
        """Get list of expected services from docker-compose.yml."""
        try:
            if COMPOSE_FILE.exists():
                with open(COMPOSE_FILE, 'r') as f:
                    compose_data = yaml.safe_load(f)
                    return set(compose_data.get('services', {}).keys())
            return set()
        except Exception as e:
            logger.error(f"Error reading docker-compose.yml: {e}")
            return set()

    def backup_system(self):
        """Create system backup before updates."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"backup_{timestamp}"
        
        try:
            # Backup docker-compose config
            compose_backup = backup_path / 'docker-compose.yaml'
            compose_backup.parent.mkdir(parents=True, exist_ok=True)
            if COMPOSE_FILE.exists():
                with open(COMPOSE_FILE, 'r') as src:
                    with open(compose_backup, 'w') as dst:
                        dst.write(src.read())

            # Backup service configurations
            config_backup = backup_path / 'configs'
            config_backup.mkdir(parents=True, exist_ok=True)
            
            self.log_metric("system_backup", 
                          {"success": True, "path": str(backup_path)},
                          {"type": "pre_update"})
            
            logger.info(f"System backup created at {backup_path}")
            return str(backup_path)
        except Exception as e:
            self.log_metric("system_backup", 
                          {"success": False, "error": str(e)},
                          {"type": "pre_update"})
            logger.error(f"Backup failed: {e}")
            return None

    def verify_update(self, version):
        """Verify system state after update."""
        try:
            # Get expected services from docker-compose.yml
            expected_services = self.get_expected_services()
            if not expected_services:
                logger.error("No services found in docker-compose.yml")
                return False

            # Check all expected containers are running
            containers = self.docker_client.containers.list()
            running_services = {c.name.split('_')[1] for c in containers}
            
            missing_services = expected_services - running_services
            if missing_services:
                logger.error(f"Services not running after update: {missing_services}")
                self.log_metric("update_verification",
                              {"success": False, 
                               "error": f"Missing services: {missing_services}"},
                              {"version": version})
                return False

            # Verify version file was updated
            current = self.get_current_version()
            if current != version:
                logger.error(f"Version mismatch after update: {current} != {version}")
                self.log_metric("update_verification",
                              {"success": False,
                               "error": "Version mismatch"},
                              {"version": version})
                return False

            self.log_metric("update_verification",
                          {"success": True},
                          {"version": version})
            return True
        except Exception as e:
            self.log_metric("update_verification",
                          {"success": False, "error": str(e)},
                          {"version": version})
            logger.error(f"Update verification failed: {e}")
            return False

    def restart_services(self):
        """Restart all services using docker commands."""
        try:
            # Get list of services from compose file
            with open(COMPOSE_FILE, 'r') as f:
                compose_data = yaml.safe_load(f)
                services = compose_data.get('services', {}).keys()

            # Stop and remove existing containers
            for service in services:
                container_name = f"data-hub_{service}_1"
                try:
                    container = self.docker_client.containers.get(container_name)
                    container.stop()
                    container.remove()
                except docker.errors.NotFound:
                    pass  # Container doesn't exist, which is fine

            # Pull latest images
            for service in services:
                image_name = compose_data['services'][service].get('image')
                if image_name:
                    try:
                        self.docker_client.images.pull(image_name)
                    except Exception as e:
                        logger.error(f"Failed to pull image for {service}: {e}")

            # Start services using docker run
            for service_name, service_config in compose_data['services'].items():
                container_name = f"data-hub_{service_name}_1"
                
                # Basic configuration
                run_kwargs = {
                    'name': container_name,
                    'detach': True,
                    'restart_policy': {"Name": "always"},
                }

                # Add environment variables
                if 'environment' in service_config:
                    run_kwargs['environment'] = service_config['environment']

                # Add volumes
                if 'volumes' in service_config:
                    run_kwargs['volumes'] = service_config['volumes']

                # Add ports
                if 'ports' in service_config:
                    ports = {}
                    for port_mapping in service_config['ports']:
                        host_port, container_port = port_mapping.split(':')
                        ports[container_port] = host_port
                    run_kwargs['ports'] = ports

                # Add network mode if specified
                if 'network_mode' in service_config:
                    run_kwargs['network_mode'] = service_config['network_mode']
                elif 'networks' in service_config:
                    run_kwargs['network'] = 'data-hub_data-hub'

                # Add command if specified
                if 'command' in service_config:
                    run_kwargs['command'] = service_config['command']

                try:
                    if 'build' in service_config:
                        # Build the image locally
                        context = service_config['build'].get('context', '.')
                        dockerfile = service_config['build'].get('dockerfile')
                        tag = f"data-hub_{service_name}:latest"
                        
                        self.docker_client.images.build(
                            path=str(COMPOSE_FILE.parent / context),
                            dockerfile=str(COMPOSE_FILE.parent / dockerfile) if dockerfile else None,
                            tag=tag
                        )
                        run_kwargs['image'] = tag
                    else:
                        run_kwargs['image'] = service_config['image']

                    self.docker_client.containers.run(**run_kwargs)
                except Exception as e:
                    logger.error(f"Failed to start {service_name}: {e}")
                    raise

            return True
        except Exception as e:
            logger.error(f"Failed to restart services: {e}")
            return False

    def rollback_update(self, backup_path):
        """Rollback system to previous state."""
        if not backup_path or not Path(backup_path).exists():
            logger.error("No backup path provided or backup not found")
            return False

        try:
            start_time = time.time()
            
            # Restore docker-compose config
            compose_backup = Path(backup_path) / 'docker-compose.yaml'
            if compose_backup.exists():
                with open(compose_backup, 'r') as src:
                    with open(COMPOSE_FILE, 'w') as dst:
                        dst.write(src.read())

            # Restore service configurations
            config_backup = Path(backup_path) / 'configs'
            if config_backup.exists():
                # Add specific config restore logic here
                pass

            # Restart services
            if not self.restart_services():
                raise Exception("Failed to restart services during rollback")
            
            duration = time.time() - start_time
            self.log_metric("rollback",
                          {"success": True,
                           "duration_seconds": duration},
                          {"backup_path": str(backup_path)})
            
            logger.info("System rollback completed")
            return True
        except Exception as e:
            self.log_metric("rollback",
                          {"success": False,
                           "error": str(e)},
                          {"backup_path": str(backup_path)})
            logger.error(f"Rollback failed: {e}")
            return False

    def apply_update(self, version):
        """Apply system update to specified version."""
        logger.info(f"Starting update to version {version}")
        start_time = time.time()
        
        # Create backup
        backup_path = self.backup_system()
        if not backup_path:
            logger.error("Backup failed, aborting update")
            return False

        try:
            # Download update manifest
            url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/updates/{version}/manifest.yml"
            response = requests.get(url)
            response.raise_for_status()
            manifest = yaml.safe_load(response.text)

            # Track step completion
            total_steps = len(manifest.get('steps', []))
            completed_steps = 0

            # Apply updates in order
            for step in manifest.get('steps', []):
                step_start = time.time()
                step_type = step['type']
                try:
                    if step_type == 'docker_compose':
                        # Update docker-compose.yml from the template in docker/compose/
                        compose_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/docker/compose/docker-compose.yaml"
                        response = requests.get(compose_url)
                        response.raise_for_status()
                        with open(COMPOSE_FILE, 'w') as f:
                            f.write(response.text)
                    elif step_type == 'service_config':
                        # Update service configuration
                        config_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{step['path']}"
                        response = requests.get(config_url)
                        response.raise_for_status()
                        target_path = DATA_DIR / step['target'].lstrip('/data/')
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with open(target_path, 'w') as f:
                            f.write(response.text)
                    elif step_type == 'system_package':
                        # Skip system package installation since we handle it in Dockerfile
                        logger.info(f"Skipping system package installation of {step['package']} (handled by Dockerfile)")

                    completed_steps += 1
                    step_duration = time.time() - step_start
                    
                    self.log_metric("update_step",
                                  {"success": True,
                                   "duration_seconds": step_duration},
                                  {"version": version,
                                   "step_type": step_type,
                                   "step_number": completed_steps,
                                   "total_steps": total_steps})
                
                except Exception as e:
                    self.log_metric("update_step",
                                  {"success": False,
                                   "error": str(e)},
                                  {"version": version,
                                   "step_type": step_type,
                                   "step_number": completed_steps + 1,
                                   "total_steps": total_steps})
                    raise

            # Update version file
            with open(self.version_file, 'w') as f:
                yaml.dump({'version': version}, f)

            # Restart services
            if not self.restart_services():
                raise Exception("Failed to restart services")

            # Verify update
            if not self.verify_update(version):
                logger.error("Update verification failed, rolling back")
                self.rollback_update(backup_path)
                return False

            duration = time.time() - start_time
            self.log_metric("system_update",
                          {"success": True,
                           "duration_seconds": duration,
                           "steps_completed": completed_steps,
                           "total_steps": total_steps},
                          {"from_version": self.get_current_version(),
                           "to_version": version})

            logger.info(f"Update to version {version} completed successfully")
            return True

        except Exception as e:
            duration = time.time() - start_time
            self.log_metric("system_update",
                          {"success": False,
                           "duration_seconds": duration,
                           "error": str(e),
                           "steps_completed": completed_steps},
                          {"from_version": self.get_current_version(),
                           "to_version": version})
            
            logger.error(f"Update failed: {e}")
            self.rollback_update(backup_path)
            return False

    def run(self):
        """Main update service loop."""
        logger.info("Starting update service")
        
        while True:
            try:
                current_version = self.get_current_version()
                latest_version = self.get_latest_version()

                self.log_metric("version_check",
                              {"current_version": current_version,
                               "latest_version": latest_version or "unknown",
                               "update_available": bool(latest_version and 
                                   compare_versions(latest_version, current_version))})

                if latest_version and compare_versions(latest_version, current_version):
                    logger.info(f"Update available: {current_version} -> {latest_version}")
                    
                    if self.apply_update(latest_version):
                        logger.info(f"Successfully updated to version {latest_version}")
                    else:
                        logger.error(f"Failed to update to version {latest_version}")
                else:
                    logger.info(f"System is up to date (version {current_version})")

            except Exception as e:
                self.log_metric("update_check",
                              {"success": False,
                               "error": str(e)})
                logger.error(f"Error in update check: {e}")

            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    service = UpdateService()
    service.run()
