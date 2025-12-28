"""
Collector configuration management.
"""

from pydantic import BaseModel, Field
from typing import Optional
import os


class CollectorConfig(BaseModel):
    """Configuration for the Clarion collector."""
    
    # Backend API
    backend_url: str = Field(
        default_factory=lambda: os.getenv("CLARION_COLLECTOR_BACKEND_URL", "http://localhost:8000")
    )
    
    # NetFlow ports
    netflow_port: int = Field(
        default_factory=lambda: int(os.getenv("CLARION_COLLECTOR_NETFLOW_PORT", "2055"))
    )
    ipfix_port: int = Field(
        default_factory=lambda: int(os.getenv("CLARION_COLLECTOR_IPFIX_PORT", "4739"))
    )
    sflow_port: int = Field(
        default_factory=lambda: int(os.getenv("CLARION_COLLECTOR_SFLOW_PORT", "6343"))
    )
    
    # Binding
    bind_host: str = Field(
        default_factory=lambda: os.getenv("CLARION_COLLECTOR_BIND_HOST", "0.0.0.0")
    )
    
    # Batch settings
    batch_size: int = Field(
        default_factory=lambda: int(os.getenv("CLARION_COLLECTOR_BATCH_SIZE", "1000"))
    )
    batch_interval_seconds: float = Field(
        default_factory=lambda: float(os.getenv("CLARION_COLLECTOR_BATCH_INTERVAL", "5.0"))
    )
    
    # Switch ID mapping (optional - can be derived from source IP)
    switch_id_from_source_ip: bool = Field(
        default_factory=lambda: os.getenv("CLARION_COLLECTOR_SWITCH_ID_FROM_IP", "true").lower() == "true"
    )
    
    # Logging
    log_level: str = Field(
        default_factory=lambda: os.getenv("CLARION_COLLECTOR_LOG_LEVEL", "INFO")
    )
    
    # Socket buffer sizes (requires privileges)
    udp_rcvbuf_size: Optional[int] = Field(
        default_factory=lambda: int(os.getenv("CLARION_COLLECTOR_UDP_RCVBUF", "0")) or None
    )
    
    # Retry settings
    retry_max_attempts: int = Field(
        default_factory=lambda: int(os.getenv("CLARION_COLLECTOR_RETRY_ATTEMPTS", "3"))
    )
    retry_backoff_factor: float = Field(
        default_factory=lambda: float(os.getenv("CLARION_COLLECTOR_RETRY_BACKOFF", "1.5"))
    )

