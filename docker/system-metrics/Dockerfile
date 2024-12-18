FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY services/system-metrics/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Note: collector.py will be mounted from ~/.data-hub/services/system-metrics/
# Copy a default version for initial build
COPY services/system-metrics/collector.py .

# Make script executable
RUN chmod +x collector.py

# Use the mounted collector.py if it exists, otherwise use the built-in one
CMD ["sh", "-c", "[ -f /data/services/system-metrics/collector.py ] && cp /data/services/system-metrics/collector.py . && chmod +x collector.py; ./collector.py"]
