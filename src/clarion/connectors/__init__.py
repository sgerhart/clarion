"""
Clarion Connectors - External system integrations.

Connectors for pulling identity and context data from:
- Cisco ISE (pxGrid)
- Active Directory (LDAP)
- CMDB (ServiceNow, etc.)
- DHCP/DNS (Infoblox, etc.)
"""

from typing import Protocol, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SyncResult:
    """Result of a connector sync operation."""
    connector_name: str
    records_synced: int
    sync_time: datetime
    duration_seconds: float
    success: bool
    error_message: str | None = None


class Connector(Protocol):
    """Protocol for all Clarion connectors."""
    
    @property
    def name(self) -> str:
        """Connector name for logging/metrics."""
        ...
    
    async def connect(self) -> bool:
        """Establish connection to the external system."""
        ...
    
    async def disconnect(self) -> None:
        """Close connection gracefully."""
        ...
    
    async def sync(self) -> SyncResult:
        """Perform a sync operation."""
        ...
    
    async def health_check(self) -> bool:
        """Check if the connection is healthy."""
        ...

