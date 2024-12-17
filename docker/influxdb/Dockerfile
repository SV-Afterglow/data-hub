# ./docker/influxdb/Dockerfile
FROM influxdb:1.8

# Copy custom configuration
COPY ./docker/influxdb/config/influxdb.conf /etc/influxdb/influxdb.conf

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8086/ping || exit 1