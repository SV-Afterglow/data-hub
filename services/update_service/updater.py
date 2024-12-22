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
from packaging.version import parse as parse_version
from influxdb import InfluxDBClient

# Base paths from environment variables
DATA_DIR = Path(os.getenv('DATA_DIR', '/data/state'))  # Points to state directory
CONFIG_DIR = Path(os.getenv('CONFIG_DIR', '/config'))  # Update service config
REPO_ROOT = Path('/app/repo')  # Repository root path
COMPOSE_FILE = REPO_ROOT / 'docker/compose/docker-compose.yaml'
INFLUX_URL = os.getenv('INFLUX_URL', 'http://influxdb:8086')
PROJECT_NAME = 'compose'
NETWORK_NAME = f'{PROJECT_NAME}_data-hub'

# State file paths
VERSION_FILE = DATA_DIR / 'version'
UPDATES_DIR = DATA_DIR / 'updates'

def load_settings():
    """Load settings from config file."""
    try:
        with open(CONFIG_DIR / 'settings.yml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading settings: {e}")
        return {
            'github': {
                'repo': 'sv-afterglow/data-hub',
                'branch': 'main'
            },
            'intervals': {
                'update_check': 3600,
                'metrics_flush': 300
            },
            'logging': {
                'level': 'DEBUG',
                'file': 'history.log',
                'max_size': '10MB',
                'backup_count': 5
            },
            'metrics': {
                'database': 'update_service',
                'retention': '30d'
            }
        }

# Load settings
settings = load_settings()
GITHUB_REPO = settings['github']['repo']
GITHUB_BRANCH = settings['github']['branch']
CHECK_INTERVAL = settings['intervals']['update_check']
INFLUX_DB = settings['metrics']['database']

# Setup logging
log_file = CONFIG_DIR / settings['logging']['file']
log_level = getattr(logging, settings['logging']['level'].upper())
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('update-service')

def compare_versions(v1, v2):
    """Compare two version strings."""
    try:
        return parse_version(v1) > parse_version(v2)
    except Exception as e:
        logger.error(f"Version comparison error: {e}")
        return False

class UpdateService:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.influx_client = InfluxDBClient(host='influxdb', port=8086)
        self.backup_dir = Path('/data/backups')  # Keep backups in data dir
        self.ensure_directories()
        self.setup_influxdb()

    def ensure_directories(self):
        """Ensure required directories exist."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

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

    def ensure_network(self):
        """Ensure the Docker network exists."""
        try:
            networks = self.docker_client.networks.list(names=[NETWORK_NAME])
            if not networks:
                logger.debug(f"Creating network {NETWORK_NAME}")
                self.docker_client.networks.create(NETWORK_NAME, driver='bridge')
            else:
                logger.debug(f"Network {NETWORK_NAME} already exists")
        except Exception as e:
            logger.error(f"Failed to ensure network: {e}")
            raise

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
            if VERSION_FILE.exists():
                with open(VERSION_FILE, 'r') as f:
                    data = yaml.safe_load(f)
                    version = data.get('version')
                    if version:
                        return version
            logger.error("No valid version file found")
            return '0.0.0'
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
            # Create backup directories
            backup_path.mkdir(parents=True, exist_ok=True)
            (backup_path / 'state').mkdir(exist_ok=True)
            (backup_path / 'config').mkdir(exist_ok=True)

            # Backup state
            if VERSION_FILE.exists():
                subprocess.run(['cp', '-r', str(VERSION_FILE), str(backup_path / 'state')])

            # Backup configs
            if CONFIG_DIR.exists():
                subprocess.run(['cp', '-r', str(CONFIG_DIR), str(backup_path)])

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

            # Don't check for services we haven't built yet
            required_services = {'influxdb', 'update_service'}  # Use consistent service name
            missing_services = required_services - running_services

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

    def restart_services(self, services_to_restart=None):
        """Restart specified services using docker commands."""
        try:
            logger.debug("Reading docker-compose.yml")
            with open(COMPOSE_FILE, 'r') as f:
                compose_data = yaml.safe_load(f)
                available_services = compose_data.get('services', {}).keys()

            logger.debug(f"Found services: {available_services}")

            # If no services specified, restart all except ourselves and watchtower
            if services_to_restart is None:
                services_to_restart = set(available_services) - {'update_service', 'watchtower'}
            else:
                # Validate specified services exist
                invalid_services = services_to_restart - set(available_services)
                if invalid_services:
                    raise Exception(f"Invalid services specified: {invalid_services}")

            logger.debug(f"Services to restart: {services_to_restart}")

            # Ensure network exists
            self.ensure_network()

            # Stop and remove existing containers
            for service in services_to_restart:
                container_name = f"{PROJECT_NAME}_{service}_1"
                try:
                    logger.debug(f"Stopping container {container_name}")
                    container = self.docker_client.containers.get(container_name)
                    container.stop()
                    container.remove()
                except docker.errors.NotFound:
                    logger.debug(f"Container {container_name} not found")
                    pass  # Container doesn't exist which is fine

            # Start services using docker-compose
            try:
                # First stop all services to release ports
                stop_cmd = ['docker-compose', '-f', str(COMPOSE_FILE), 'stop']
                stop_cmd.extend(list(services_to_restart))
                stop_result = subprocess.run(stop_cmd, check=True, capture_output=True, text=True)
                logger.debug(f"docker-compose stop output: {stop_result.stdout}")

                # Remove containers to ensure clean state
                rm_cmd = ['docker-compose', '-f', str(COMPOSE_FILE), 'rm', '-f']
                rm_cmd.extend(list(services_to_restart))
                rm_result = subprocess.run(rm_cmd, check=True, capture_output=True, text=True)
                logger.debug(f"docker-compose rm output: {rm_result.stdout}")

                # Start services
                up_cmd = ['docker-compose', '-f', str(COMPOSE_FILE), 'up', '-d']
                up_cmd.extend(list(services_to_restart))
                up_result = subprocess.run(up_cmd, check=True, capture_output=True, text=True)
                logger.debug(f"docker-compose up output: {up_result.stdout}")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to start services: {e}\nOutput: {e.stdout}\nError: {e.stderr}")
                raise

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

            # Restore state
            state_backup = Path(backup_path) / 'state'
            if state_backup.exists():
                subprocess.run(['cp', '-r', str(state_backup), str(DATA_DIR)])

            # Restore configs
            config_backup = Path(backup_path) / 'config'
            if config_backup.exists():
                subprocess.run(['cp', '-r', str(config_backup), str(CONFIG_DIR)])

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

        # Initialize step tracking
        completed_steps = 0
        total_steps = 0

        # Create backup
        backup_path = self.backup_system()
        if not backup_path:
            logger.error("Backup failed, aborting update")
            return False

        try:
            # Download update manifest
            url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/updates/{version}/manifest.yml"
            logger.debug(f"Downloading manifest from {url}")
            response = requests.get(url)
            response.raise_for_status()
            manifest = yaml.safe_load(response.text)
            logger.debug(f"Manifest content: {manifest}")

            # Validate version requirement
            if 'requires' in manifest:
                current = self.get_current_version()
                required = manifest['requires']
                if parse_version(current) < parse_version(required):
                    raise Exception(f"Current version {current} does not meet required version {required}")
                logger.debug(f"Version requirement satisfied: {current} >= {required}")

            # Track step completion
            total_steps = len(manifest.get('steps', []))
            completed_steps = 0

            # Apply updates in order
            for step in manifest.get('steps', []):
                step_start = time.time()
                step_type = step['type']
                logger.debug(f"Processing step {completed_steps + 1}/{total_steps}: {step_type}")
                try:
                    if step_type == 'service_config':
                        # Update service configuration
                        config_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{step['path']}"
                        logger.debug(f"Downloading config from {config_url}")
                        response = requests.get(config_url)
                        response.raise_for_status()
                        # Handle both absolute and relative paths
                        target = step['target']
                        if target.startswith('/data/config/'):
                            target = target.lstrip('/data/config/')
                        target_path = CONFIG_DIR / target
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with open(target_path, 'w') as f:
                            f.write(response.text)

                        # Set file permissions if specified
                        if 'permissions' in step:
                            mode = int(step['permissions'], 8)  # Convert octal string to int
                            os.chmod(str(target_path), mode)  # Convert Path to string for chmod
                            logger.debug(f"Set permissions {step['permissions']} on {target_path}")
                    elif step_type == 'docker_compose':
                        # Update docker-compose.yml from the template in docker/compose/
                        compose_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/docker/compose/docker-compose.yaml"
                        logger.debug(f"Downloading compose file from {compose_url}")
                        response = requests.get(compose_url)
                        response.raise_for_status()
                        with open(COMPOSE_FILE, 'w') as f:
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
            logger.debug("Updating version file")
            with open(VERSION_FILE, 'w') as f:
                yaml.dump({'version': version}, f)

            # Handle service restarts
            services_to_restart = set()
            for step in manifest.get('steps', []):
                if step['type'] == 'docker_compose' and step.get('action') == 'restart':
                    if 'service' in step:
                        services_to_restart.add(step['service'])
                    else:
                        # If no specific service, restart all
                        services_to_restart = self.get_expected_services() - {'update_service', 'watchtower'}
                        break

            if services_to_restart:
                logger.debug(f"Restarting services: {services_to_restart}")
                if not self.restart_services(services_to_restart):
                    raise Exception("Failed to restart services")

            # Verify update
            logger.debug("Verifying update")
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
