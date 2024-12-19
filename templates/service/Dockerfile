# Build stage
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /build

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Create non-root user
RUN useradd -r -s /bin/false serviceuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    # Add required runtime packages here \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/

# Copy application code
COPY . .

# Set correct permissions
RUN chown -R serviceuser:serviceuser /app && \
    chmod -R 755 /app

# Set environment variables
ENV SERVICE_VAR1=default_value \
    SERVICE_VAR2=default_value \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER serviceuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Start application
CMD ["python", "service.py"]
