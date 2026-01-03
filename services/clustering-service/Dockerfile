FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared source code
COPY ../../src /app/src
COPY ../../requirements.txt /app/requirements-shared.txt
RUN pip install --no-cache-dir -r requirements-shared.txt

# Copy service code
COPY main.py .

# Expose port
EXPOSE 8003

# Run service
CMD ["python", "main.py"]

