# Clarion Main API Service
# Container for the FastAPI backend application

FROM python:3.11-slim

LABEL maintainer="Clarion Development Team"
LABEL description="Clarion TrustSec Policy Copilot - Main API Service"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create data directory for database
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app/src
ENV CLARION_DB_PATH=/app/data/clarion.db
ENV PORT=8000

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')" || exit 1

# Run the API server
CMD ["python", "-m", "uvicorn", "clarion.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

