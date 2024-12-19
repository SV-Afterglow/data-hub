FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create data directory structure
RUN mkdir -p /data/services/system_metrics

# Copy requirements first for better caching
COPY services/system_metrics/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Note: collector.py will be mounted from ~/.data-hub/services/system-metrics/
# Copy a default version for initial build
COPY services/system_metrics/collector.py ./collector.py.default

# Make script executable
RUN chmod +x collector.py.default

# Use the mounted collector.py if it exists, otherwise use default
CMD ["sh", "-c", "\
    if [ -f /data/services/system_metrics/collector.py ]; then \
        echo 'Found mounted collector.py, using it...'; \
        cp /data/services/system-metrics/collector.py ./collector.py; \
        chmod +x ./collector.py; \
    else \
        echo 'No mounted collector.py found, using default...'; \
        cp ./collector.py.default ./collector.py; \
    fi; \
    echo 'Contents of collector.py:'; \
    cat ./collector.py; \
    echo 'Starting collector...'; \
    ./collector.py"]
