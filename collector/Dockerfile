# Clarion Collector
# Central flow collector for switches that cannot host containers
#
# Build: docker build -t clarion-collector:latest .

FROM python:3.11-slim

LABEL maintainer="Clarion Development Team"
LABEL description="Clarion Collector - Central NetFlow/IPFIX/sFlow collector"
LABEL version="0.1.0"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcap-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 clarion

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY clarion_collector/ ./clarion_collector/

# Create data directory
RUN mkdir -p /data && chown clarion:clarion /data

# Switch to non-root
USER clarion

# Environment
ENV CLARION_COLLECTOR_DATA_DIR=/data
ENV CLARION_COLLECTOR_NETFLOW_PORT=2055
ENV CLARION_COLLECTOR_IPFIX_PORT=4739
ENV CLARION_COLLECTOR_SFLOW_PORT=6343

# Expose collector ports
EXPOSE 2055/udp
EXPOSE 4739/udp
EXPOSE 6343/udp
EXPOSE 8080/tcp  # Agent collector HTTP
EXPOSE 8081/tcp  # Native collector HTTP (health/metrics)

# Health check (check native collector on 8081, or agent collector on 8080)
# Note: When running in "both" mode, both ports are available
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8081/health || curl -f http://localhost:8080/health || exit 1

# Entrypoint
ENTRYPOINT ["python", "-m", "clarion_collector.main"]

