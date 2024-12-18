# ./docker/signalk/Dockerfile
FROM signalk/signalk-server:latest

WORKDIR /home/node/.signalk

# Copy our custom configuration
# Plugin configurations are managed in settings.json
# Plugin binaries persist in the ~/.signalk volume mount
COPY ./docker/signalk/config/settings.json /home/node/.signalk/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/signalk || exit 1

USER node
