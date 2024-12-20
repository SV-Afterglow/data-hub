# Build stage for wheels
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libiw-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY ./services/network_monitor/requirements.txt .

# Build wheels
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies and build essentials for msgpack
RUN apt-get update && apt-get install -y \
    wireless-tools \
    iw \
    iproute2 \
    libiw-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and requirements
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install packages from wheels
RUN pip install --no-cache /wheels/*

# Copy application code
COPY ./services/network_monitor/network_monitor.py .

# Set permissions
RUN chmod 755 network_monitor.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run application
CMD ["python", "network_monitor.py"]
