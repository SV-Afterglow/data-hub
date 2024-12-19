# Build stage
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements
COPY services/network_monitor/requirements.txt .

# Install dependencies
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Final stage
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -r -u 1000 monitor

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    wireless-tools \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels

# Copy application
COPY services/network_monitor/ .

# Install dependencies
RUN pip install --no-cache /wheels/*

# Set permissions
RUN chmod 755 network_monitor.py && \
    chown -R monitor:monitor /app

# Switch to non-root user
USER monitor

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "from network_monitor import NetworkMonitor; monitor = NetworkMonitor(); healthy, _ = monitor.check_health(); exit(0 if healthy else 1)"

# Run application
CMD ["python3", "network_monitor.py"]
