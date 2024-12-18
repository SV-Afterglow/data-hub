FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    python3-psutil \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY services/update-service/requirements.txt .

# Force pure Python implementation of msgpack
ENV MSGPACK_PUREPYTHON=1

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/update-service/updater.py .

# Make script executable
RUN chmod +x updater.py

CMD ["./updater.py"]
