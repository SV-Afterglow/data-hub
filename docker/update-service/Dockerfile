FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    docker-compose \
    && apt-get clean

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY services/update-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/update-service/updater.py .

# Make script executable
RUN chmod +x updater.py

CMD ["./updater.py"]
