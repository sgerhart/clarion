# Clarion pxGrid Service
# Container for ISE pxGrid integration with certificate authentication

FROM python:3.11-slim

LABEL maintainer="Clarion Development Team"
LABEL description="Clarion TrustSec Policy Copilot - pxGrid Integration Service"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies (including pxGrid-specific dependencies)
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir websocket-client>=1.6.0

# Copy application code (shared codebase)
COPY src/ ./src/
COPY services/pxgrid/pxgrid_service.py ./pxgrid_service.py

# Create directories for certificates and data
RUN mkdir -p /app/certs /app/data && \
    chmod 700 /app/certs

# Set environment variables
ENV PYTHONPATH=/app/src
ENV CLARION_DB_PATH=/app/data/clarion.db
ENV PXGRID_CERT_DIR=/app/certs
ENV PORT=9000

# Expose status API port (optional)
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:9000/health')" || exit 1

# Run the pxGrid subscriber service
CMD ["python", "/app/pxgrid_service.py"]

