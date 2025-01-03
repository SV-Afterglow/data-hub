# Data Hub

The **Data Hub** is a container-based vessel data hub and systems interface, inspired by the [SeaBits NMEA 2000 Raspberry Pi implementation](https://seabits.com/nmea-2000-powered-raspberry-pi/). This system manages NMEA2000 network access, hosts a SignalK server, and provides data visualization through Grafana with historical data storage in InfluxDB. We also include a **custom update service** to handle updates and rollbacks—**replacing the need for Watchtower**.

---

## Overview

### Key Capabilities

- **NMEA2000 Connectivity**  
  Collect data from onboard sensors and instruments via a PICAN-M HAT or similar.
  
- **SignalK Integration**  
  Normalize real-time vessel data and make it accessible to other systems.
  
- **Time-Series Storage (InfluxDB)**  
  Store historical logs for trend analysis and performance metrics.
  
- **Visualization (Grafana)**  
  Create customizable dashboards for system monitoring and vessel performance.
  
- **System Health & Metrics**  
  Collect, visualize, and alert on CPU usage, memory, disk space, and more.
  
- **Automated Updates (Custom Updater)**  
  Check for new versions, back up configs, apply Docker container updates, and roll back if needed—**replacing Watchtower** with a more robust solution.

---

## Quick Start (Single Push-Button Setup)

1. **Flash Raspberry Pi OS**  
   - We recommend the latest Raspberry Pi OS (Lite) for minimal overhead.

2. **Boot & Run Setup Script**  
   - Once the Pi is up, SSH in (or attach keyboard/monitor) and run:
     ```bash
     curl -fsSL https://raw.githubusercontent.com/YourOrg/data-hub/main/setup_data-hub.sh -o setup_data-hub.sh
     chmod +x setup_data-hub.sh
     ./setup_data-hub.sh
     ```
   - The script can:
     - Install OS dependencies (Docker, Docker Compose)
     - Clone this repo (if desired)
     - Configure the PICAN-M HAT and create the can0 interface
     - Copy pre-configured files so that SignalK automatically writes to Influx
     - Start containers with `docker-compose up -d`
     - Fix any permissions issues for Docker volumes

3. **Reboot or Log Out/In**  
   - After the script finishes, a reboot or log-out/in might be needed to finalize Docker group membership (so you can run Docker without sudo).
   - A **power cycle** also ensures the PICAN-M resets properly.

4. **Open Your Services**  
   - **SignalK**: <http://your-pi-ip:3000>
   - **Grafana**: <http://your-pi-ip:3001>
   - **InfluxDB**: <http://your-pi-ip:8086>
   - You should see vessel data flowing automatically into Influx and visualized in Grafana.

For advanced configuration, see `docs/INSTALLATION.md` and `docs/UPDATES.md`.

Architecture & Directory Structure

data-hub/
├── docker/                  # Docker container configurations (kebab-case folders)
│   ├── compose/            # Docker Compose files
│   │   └── docker-compose.yml
│   ├── grafana/            # Grafana Dockerfile & config
│   ├── influxdb/           # InfluxDB Dockerfile & config
│   ├── signalk/            # SignalK Dockerfile & config
│   └── update-service/     # Custom update service Dockerfile
├── services/               # Python services (snake_case folders)
│   ├── network_monitor/    # (example) Network monitoring service
│   ├── system_metrics/     # System metrics collector
│   └── update_service/     # Python code for the update manager
├── docs/                   # Documentation & proposals
│   ├── proposals/
│   ├── ARCHITECTURE.md
│   ├── INSTALLATION.md
│   ├── REQUIREMENTS.md
│   └── UPDATES.md
├── version.yml             # Tracks current system version for the custom updater
├── scripts/                # Optional scripts (backup, restore, etc.)
└── updates/                # Version update manifests & related files

Data & Config Paths

By default, persistent data and config files reside at ~/.data-hub/. This includes:
	•	~/.data-hub/state/
	•	version: current system version info
	•	updates/: update history
	•	~/.data-hub/config/
	•	Directories for each service’s configs:
	•	influxdb/, grafana/, signalk/, etc.
	•	Additional subfolders for each service (network_monitor/, update_service/, etc.)
	•	~/.data-hub/backups/
	•	Automatic backups before major updates

Data Flow
	1.	NMEA2000 Input
Data arrives via the PICAN-M HAT (or another CAN-enabled interface).
	2.	SignalK Normalization
SignalK processes raw messages and provides a unified data model.
	3.	InfluxDB Storage
Normalized data is stored historically for long-term trend analysis.
	4.	System Metrics
Additional CPU, memory, disk usage, and other metrics also go into InfluxDB.
	5.	Grafana Dashboards
Visualize both real-time and historical data via dashboards (default http://localhost:3001).

Automated Updates (Custom Updater)

We’ve replaced Watchtower with a custom update service that:
	1.	Checks Remote Version
Periodically compares the local version.yml to the remote repo’s version.
	2.	Backs Up System
Creates backups of config/state before applying new updates.
	3.	Applies Manifests
Reads updates/<version>/manifest.yml steps to update config files, Docker Compose, etc.
	4.	Restarts Services
Safely restarts impacted containers.
	5.	Rollbacks if Needed
If verification fails, the updater reverts to the last known good state automatically.
	6.	Logs to InfluxDB
Sends update metrics (success/failure) so you can track changes over time.

For more details, see UPDATES.md.

Development Workflow
	1.	Local Development
	•	Clone the repo and modify Python code in services/<service_name>/.
	•	Optionally, use Docker Compose locally (docker-compose up --build) to test changes.
	2.	Pushing Changes
	•	When you push or merge to main, ensure your GitHub Actions (or other CI) builds/pushes images to your container registry (e.g., GHCR).
	•	Bump version.yml if you want the boat’s custom updater to detect a “new system version.”
	3.	Auto-Update
	•	The custom update service on the device detects version changes, applies updates, and restarts containers as needed.
	•	Logs in InfluxDB help verify a successful rollout.

Adding a New Service
	1.	Create a Python Service
	•	Make a folder under services/ using snake_case (e.g., services/my_new_service/).
	•	Add your Python code, requirements.txt, etc.
	2.	Add a Docker Folder
	•	Create a matching folder under docker/ (kebab-case), e.g., docker/my-new-service/.
	•	Write a Dockerfile that copies code from services/my_new_service/ into the container.
	3.	Update docker-compose.yml
	•	Reference the new service (build context, environment variables, volumes, etc.).
	4.	Add Config (Optional)
	•	If your service needs persistent config or data, place it under ~/.data-hub/config/my_new_service/ (managed by the custom updater).
	5.	Document
	•	Add details in UPDATES.md or a dedicated README explaining how to configure or update the new service.

Configuration Management
	•	All service configs reside in ~/.data-hub/config/.
	•	Updates modify configs via manifest steps, ensuring rollbacks are possible if something fails.
	•	Atomic State Changes happen in ~/.data-hub/state/ (version files, update logs) once an update is verified.

System Persistence
	1.	InfluxDB Data: ~/.data-hub/config/influxdb/
	2.	Grafana Dashboards: ~/.data-hub/config/grafana/
	3.	SignalK Data: ~/.data-hub/config/signalk/
	4.	Service Config: ~/.data-hub/config/<service_name>/ (e.g., update_service, network_monitor)

Support & Troubleshooting

Because this is a private repository, support is handled by the maintainers:
	1.	Check Docs
Consult INSTALLATION.md or UPDATES.md for known issues/solutions.
	2.	Review Logs
	•	Check container logs via docker logs <container_name> or your InfluxDB dashboards.
	3.	Contact Maintainers
	•	File an issue or reach out directly if you’re stuck.

References
	•	[SeaBits NMEA 2000 Guide](https://seabits.com/nmea-2000-powered-raspberry-pi/)
	•	[SignalK Documentation](https://signalk.org/)
	•	[CopperHill PICAN-M Documentation](https://copperhilltech.com/pican-m-nmea-0183-nmea-2000-hat-for-raspberry-pi/)
	•	[InfluxDB Documentation](https://docs.influxdata.com/influxdb/v1.8/)
	•	[Grafana Documentation](https://grafana.com/docs/)



