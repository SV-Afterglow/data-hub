#!/usr/bin/env python3

import os
import time
import yaml
import docker
import requests
import logging
from pathlib import Path
from datetime import datetime
from packaging import version
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Configuration from environment variables
GITHUB_REPO = os.getenv('GITHUB_REPO', 'sv-afterglow/data-hub')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')
CHECK_INTERVAL = int(os.getenv('UPDATE_CHECK_INTERVAL', '3600'))  # Default 1 hour
DATA_DIR = Path(os.getenv('DATA_DIR', '/data'))
COMPOSE_DIR = Path('/data/docker/compose')  # Fixed path for compose files
INFLUX_URL = os.getenv('INFLUX_URL', 'http://influxdb:8086')
INFLUX_BUCKET = "system_updates"

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
        self.influx_client = InfluxDBClient(url=INFLUX_URL)
        self.version_file = DATA_DIR / 'version.yml'
        self.backup_dir = DATA_DIR / 'backups'
        self.compose_file = COMPOSE_DIR / 'docker-compose.yaml'  # Updated path
        self.ensure_directories()
        self.setup_influxdb()

    def ensure_directories(self):
        """Ensure required directories exist."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        COMPOSE_DIR.mkdir(parents=True, exist_ok=True)

    def setup_influxdb(self):
        """Setup InfluxDB bucket for update metrics."""
        try:
            buckets_api = self.influx_client.buckets_api()
            if INFLUX_BUCKET not in [bucket.name for bucket in buckets_api.find_buckets()]:
                buckets_api.create_bucket(bucket_name=INFLUX_BUCKET)
                logger.info(f"Created InfluxDB bucket: {INFLUX_BUCKET}")
        except Exception as e:
            logger.error(f"Error setting up InfluxDB: {e}")

    def log_metric(self, measurement, fields, tags=None):
        """Log a metric to InfluxDB."""
        try:
            write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            point = Point(measurement)
            
            if tags:
                for key, value in tags.items():
                    point = point.tag(key, str(value))
            
            for key, value in fields.items():
                if isinstance(value, bool):
                    point = point.field(key, value)
                elif isinstance(value, (int, float)):
                    point = point.field(key, value)
                else:
                    point = point.field(key, str(value))
            
            write_api.write(bucket=INFLUX_BUCKET, record=point)
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
            if self.compose_file.exists():
                with open(self.compose_file, 'r') as f:
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
            compose_backup = backup_path / 'docker-compose.yaml'  # Updated extension
            compose_backup.parent.mkdir(parents=True, exist_ok=True)
            if self.compose_file.exists():
                with open(self.compose_file, 'r') as src:
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
            running_services = {c.name.split('_')[-1] for c in containers}
            
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

    def rollback_update(self, backup_path):
        """Rollback system to previous state."""
        if not backup_path or not Path(backup_path).exists():
            logger.error("No backup path provided or backup not found")
            return False

        try:
            start_time = time.time()
            
            # Restore docker-compose config
            compose_backup = Path(backup_path) / 'docker-compose.yaml'  # Updated extension
            if compose_backup.exists():
                with open(compose_backup, 'r') as src:
                    with open(self.compose_file, 'w') as dst:
                        dst.write(src.read())

            # Restore service configurations
            config_backup = Path(backup_path) / 'configs'
            if config_backup.exists():
                # Add specific config restore logic here
                pass

            # Restart services using the correct compose file path
            os.system(f'docker-compose -f {self.compose_file} up -d')
            
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
                    if step_type == 'system_package':
                        os.system(f"apt-get install -y {step['package']}")
                    elif step_type == 'docker_compose':
                        # Update docker-compose.yml
                        compose_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/docker/compose/docker-compose.yaml"
                        response = requests.get(compose_url)
                        response.raise_for_status()
                        with open(self.compose_file, 'w') as f:
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

            # Restart services using the correct compose file path
            os.system(f'docker-compose -f {self.compose_file} up -d')

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
