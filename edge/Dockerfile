# Clarion Edge Container
# Optimized for Cisco IOx App Hosting on Catalyst 9K switches
#
# Build: docker build -t clarion-edge:latest .
# Size target: < 100MB

FROM python:3.11-alpine3.18

LABEL maintainer="Clarion Development Team"
LABEL description="Clarion Edge - NetFlow collector for Cisco App Hosting"
LABEL version="0.1.0"

# Install minimal dependencies
RUN apk add --no-cache \
    sqlite \
    && rm -rf /var/cache/apk/*

# Create app user (non-root)
RUN adduser -D -u 1000 clarion

# Set working directory
WORKDIR /app

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY clarion_edge/ ./clarion_edge/
COPY scripts/ ./scripts/

# Create data directories
RUN mkdir -p /data/flows /data/graphs && \
    chown -R clarion:clarion /data

# Switch to non-root user
USER clarion

# Environment variables
ENV CLARION_EDGE_DATA_DIR=/data
ENV CLARION_EDGE_FLOW_PORT=2055
ENV CLARION_EDGE_API_PORT=8080

# Expose ports
EXPOSE 2055/udp
EXPOSE 8080/tcp

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:8080/health || exit 1

# Entrypoint
ENTRYPOINT ["python", "-m", "clarion_edge.main"]

