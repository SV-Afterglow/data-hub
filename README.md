Below is an updated README reflecting our new naming conventions and the custom update service approach (instead of Watchtower). It also highlights the high-level features, folder structure, and recommended workflow. Feel free to adjust any wording to match your style or repo specifics!

Data Hub

Overview

The Data Hub serves as the primary vessel data hub and systems interface, originally inspired by the SeaBits NMEA 2000 Raspberry Pi implementation. This system manages NMEA2000 network access, hosts a SignalK server, and provides data visualization through Grafana with historical data storage in InfluxDB.

Key Capabilities
	•	NMEA2000 Connectivity: Collect data from onboard sensors and instruments.
	•	SignalK Integration: Normalize real-time data and make it accessible to other vessel systems.
	•	Time-Series Storage (InfluxDB): Store historical data for trend analysis.
	•	Visualization (Grafana): Create customized dashboards for monitoring vessel performance.
	•	data-hub system Health & Metrics: Collect and display CPU, memory, disk usage, and more.
	•	Automated Updates (Custom Updater): Check for new versions, back up configs, apply updates, and roll back if needed.

Quick Start
	1.	Clone the Repository

git clone https://github.com/<yourusername>/data-hub.git
cd data-hub


	2.	Review Hardware Requirements
See Requirements to confirm hardware compatibility (e.g., Raspberry Pi with a PICAN-M HAT).
	3.	Run Setup (Optional)

./setup.sh

	Depending on your environment, this script may install prerequisites and configure basic settings.

	4.	Boot or Reboot
If prompted, reboot your system or restart services.
	5.	Access Your Services (default ports shown below; adjust as needed):
	•	SignalK: http://localhost:3000
	•	Grafana: http://localhost:3001
	•	InfluxDB: http://localhost:8086

For detailed manual installation steps and troubleshooting, see the Installation Guide.

Architecture & Directory Structure

data-hub/
├── docker/                # Docker container configurations (kebab-case folders)
│   ├── compose/           # Docker Compose files
│   │   └── docker-compose.yml
│   ├── grafana/           # Grafana Dockerfile & config
│   ├── influxdb/          # InfluxDB Dockerfile & config
│   ├── signalk/           # SignalK Dockerfile & config
│   └── update-service/    # Custom update service Dockerfile
├── services/              # Python services (snake_case folders)
│   ├── network_monitor/   # (example) Network monitoring service
│   ├── system_metrics/    # System metrics collector
│   └── update_service/    # Python code for the update manager
├── docs/                  # Documentation & proposals
│   ├── proposals/
│   ├── ARCHITECTURE.md
│   ├── INSTALLATION.md
│   ├── REQUIREMENTS.md
│   └── UPDATES.md
├── version.yml            # Tracks current system version for the custom updater
├── scripts/               # Optional scripts (backup, restore, etc.)
└── updates/               # Version update manifests & related files

Data & Config Paths

By default, persistent data and config files reside at ~/.data-hub/. This includes:
	•	~/.data-hub/state/
	•	version: current system version info
	•	updates/: history of applied updates
	•	~/.data-hub/config/
	•	influxdb/, grafana/, signalk/, etc.
	•	Additional subfolders for each service’s configs (network_monitor, update_service, etc.)
	•	~/.data-hub/backups/
	•	Automatic backups before major updates

Data Flow
	1.	NMEA2000 Input: Data arrives via the PICAN-M HAT (or other interface).
	2.	SignalK Normalization: SignalK processes raw messages and provides a unified data model.
	3.	InfluxDB Storage: The normalized data is stored historically for trend analysis.
	4.	System Metrics: Additional CPU, memory, disk usage, and other metrics also go into InfluxDB.
	5.	Grafana Dashboards: Visualize real-time and historical data via dashboards on port 3001.

Automated Updates (Custom Updater)

We have replaced Watchtower with a custom update service that:
	1.	Checks Remote Version: Periodically compares the local version.yml to the remote repo’s version.
	2.	Backs Up System: Creates backups of config/state before applying new updates.
	3.	Applies Manifests: Uses updates/<version>/manifest.yml steps to update config files, Docker Compose, etc.
	4.	Restarts Services: Safely restarts impacted containers.
	5.	Rollbacks if Needed: If verification fails, the updater automatically reverts to the last known good state.
	6.	Logs to InfluxDB: Sends update metrics (success/failure) so you can track system changes over time.

For more details, see UPDATES.md.

Development Workflow
	1.	Local Development
	•	Clone the repo and modify Python code in services/<service_name>/.
	•	Optionally, use Docker Compose locally (docker-compose up --build) to test changes.
	2.	Pushing Changes
	•	When you push or merge to main, ensure your GitHub Actions (or other CI) builds/pushes images to your container registry (e.g., GHCR).
	•	Bump version.yml if you want the boat’s custom updater to notice a “new system version.”
	3.	Auto-Update
	•	The custom update service on the device will detect the version change, apply updates, and restart containers as needed.
	•	Logs in InfluxDB help you verify a successful rollout.

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
	•	If your service needs persistent config or data, place it under ~/.data-hub/config/my_new_service/ (the custom updater can manage this during updates).
	5.	Document
	•	Add details in UPDATES.md or a dedicated README explaining how to configure or update the new service.

Configuration Management
	•	All service configs live in ~/.data-hub/config/.
	•	Updates modify config files via manifest steps, ensuring you can roll back if something goes wrong.
	•	Atomic State Changes: The update service updates ~/.data-hub/state/ only after a successful operation.

System Persistence
	1.	InfluxDB Data: ~/.data-hub/config/influxdb/
	2.	Grafana Dashboards: ~/.data-hub/config/grafana/
	3.	SignalK Data: ~/.data-hub/config/signalk/
	4.	Service Config: ~/.data-hub/config/<service_name>/ (e.g., update_service, network_monitor, etc.)

Support & Troubleshooting

Because this is a private repository, support is handled by the maintainers:
	1.	Check Docs: Consult INSTALLATION.md or UPDATES.md for known issues/solutions.
	2.	Review Logs: Check container logs via docker logs <container_name> or your InfluxDB dashboards.
	3.	Contact Maintainers: File an issue or reach out directly if you’re stuck.

References
	•	[SeaBits NMEA 2000 Guide](https://seabits.com/nmea-2000-powered-raspberry-pi/)
	•	[SignalK Documentation](https://signalk.org/)
	•	[CopperHill PICAN-M Documentation](https://copperhilltech.com/pican-m-nmea-0183-nmea-2000-hat-for-raspberry-pi/)
	•	[InfluxDB Documentation](https://docs.influxdata.com/influxdb/v1.8/)
	•	[Grafana Documentation](https://grafana.com/docs/)

Feedback or Suggestions?

Feel free to submit a PR or open a discussion in the repo. We welcome improvements to documentation, code, and overall architecture!

Happy Sailing!
– The Data Hub Development Team