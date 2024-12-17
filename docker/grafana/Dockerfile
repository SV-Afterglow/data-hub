# ./docker/grafana/Dockerfile
FROM grafana/grafana:latest

# Copy our dashboards and datasource configurations
COPY ./docker/grafana/provisioning /etc/grafana/provisioning

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1
    