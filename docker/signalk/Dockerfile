# ./docker/signalk/Dockerfile
FROM signalk/signalk-server:latest

WORKDIR /home/node/.signalk

# Install required plugins
RUN npm install --unsafe-perm \
    @signalk/nmea2000-reader \
    @signalk/signalk-to-influxdb

# Copy our custom configuration
COPY ./docker/signalk/config/settings.json /home/node/.signalk/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/signalk || exit 1

USER node