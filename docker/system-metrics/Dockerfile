FROM python:3.9-slim

# Install system utilities
RUN apt-get update && apt-get install -y \
    sysstat \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY services/system-metrics/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy collector script
COPY services/system-metrics/collector.py .

# Make the collector script executable
RUN chmod +x collector.py

CMD ["./collector.py"]
