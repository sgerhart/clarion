"""
EndpointSketch - Lightweight behavioral fingerprint per endpoint.

This is the core data structure for Clarion's edge processing.
Each endpoint (identified by MAC address) gets a sketch that captures
its behavioral patterns using bounded memory (~10KB).

The sketch is designed to run on Catalyst 9K switches with limited
resources (256-512MB RAM for the container).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

from clarion.sketches.hyperloglog import HyperLogLogSketch
from clarion.sketches.countmin import CountMinSketch


@dataclass
class EndpointSketch:
    """
    Behavioral fingerprint for a single endpoint.
    
    Captures:
    - Cardinality: How many unique peers/services does it talk to?
    - Frequency: What ports/services does it use most?
    - Volume: How much traffic in/out?
    - Temporal: When is it active?
    
    Memory budget: ~10KB per endpoint
    - unique_peers HLL: ~1.5KB
    - unique_services HLL: ~1.5KB
    - port_frequency CMS: ~5KB (reduced width)
    - service_frequency CMS: ~2KB (reduced width)
    - Aggregates + metadata: ~1KB
    
    Example:
        >>> sketch = EndpointSketch(endpoint_id="aa:bb:cc:dd:ee:ff")
        >>> sketch.record_flow(
        ...     dst_ip="10.0.0.1",
        ...     dst_port=443,
        ...     proto="tcp",
        ...     bytes_out=1000,
        ...     bytes_in=5000,
        ...     timestamp=datetime.now()
        ... )
        >>> sketch.peer_diversity  # Returns ~1
    """
    
    # Identity
    endpoint_id: str  # MAC address (primary key)
    switch_id: Optional[str] = None  # Source switch
    device_id: Optional[str] = None  # Device ID if known
    
    # Cardinality sketches (HyperLogLog)
    unique_peers: HyperLogLogSketch = field(default=None)
    unique_services: HyperLogLogSketch = field(default=None)
    unique_ports: HyperLogLogSketch = field(default=None)
    
    # Frequency sketches (Count-Min)
    # Reduced width for memory efficiency on edge
    port_frequency: CountMinSketch = field(default=None)
    service_frequency: CountMinSketch = field(default=None)
    
    # Volume aggregates
    bytes_in: int = 0
    bytes_out: int = 0
    packets_in: int = 0
    packets_out: int = 0
    flow_count: int = 0
    
    # Temporal metadata
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    active_hours: int = 0  # 24-bit bitmap (bit i = active in hour i)
    
    # Local clustering (computed on edge)
    local_cluster_id: int = -1  # -1 = not assigned
    
    # Sync metadata
    last_sync: Optional[datetime] = None
    version: int = 0
    
    # Identity context (enriched from backend)
    user_id: Optional[str] = None
    username: Optional[str] = None
    ad_groups: List[str] = field(default_factory=list)
    ise_profile: Optional[str] = None
    device_type: Optional[str] = None
    
    def __post_init__(self):
        """Initialize sketch structures if not provided."""
        if self.unique_peers is None:
            self.unique_peers = HyperLogLogSketch(
                name=f"{self.endpoint_id}_peers",
                precision=12  # ~1KB, ~4% error
            )
        if self.unique_services is None:
            self.unique_services = HyperLogLogSketch(
                name=f"{self.endpoint_id}_services",
                precision=12
            )
        if self.unique_ports is None:
            self.unique_ports = HyperLogLogSketch(
                name=f"{self.endpoint_id}_ports",
                precision=10  # ~0.5KB
            )
        if self.port_frequency is None:
            self.port_frequency = CountMinSketch(
                name=f"{self.endpoint_id}_port_freq",
                width=500,  # Reduced for edge
                depth=4
            )
        if self.service_frequency is None:
            self.service_frequency = CountMinSketch(
                name=f"{self.endpoint_id}_service_freq",
                width=200,  # Smaller - fewer services
                depth=4
            )
    
    def record_flow(
        self,
        dst_ip: str,
        dst_port: int,
        proto: str,
        bytes_out: int = 0,
        bytes_in: int = 0,
        packets_out: int = 0,
        packets_in: int = 0,
        service_name: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record an outbound flow from this endpoint.
        
        Args:
            dst_ip: Destination IP address
            dst_port: Destination port
            proto: Protocol (tcp, udp, icmp)
            bytes_out: Bytes sent
            bytes_in: Bytes received
            packets_out: Packets sent
            packets_in: Packets received
            service_name: Optional service name if resolved
            timestamp: Flow timestamp
        """
        # Update cardinality sketches
        self.unique_peers.add(dst_ip)
        port_key = f"{proto}/{dst_port}"
        self.unique_ports.add(port_key)
        
        if service_name:
            self.unique_services.add(service_name)
            self.service_frequency.add(service_name)
        
        # Update frequency sketches
        self.port_frequency.add(port_key)
        
        # Update aggregates
        self.bytes_out += bytes_out
        self.bytes_in += bytes_in
        self.packets_out += packets_out
        self.packets_in += packets_in
        self.flow_count += 1
        
        # Update temporal
        if timestamp:
            if self.first_seen is None or timestamp < self.first_seen:
                self.first_seen = timestamp
            if self.last_seen is None or timestamp > self.last_seen:
                self.last_seen = timestamp
            
            # Set active hour bit
            hour = timestamp.hour
            self.active_hours |= (1 << hour)
        
        # Increment version for sync tracking
        self.version += 1
    
    def record_inbound_flow(
        self,
        src_ip: str,
        src_port: int,
        dst_port: int,
        proto: str,
        bytes_in: int = 0,
        packets_in: int = 0,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record an inbound flow to this endpoint.
        
        Used to track if this endpoint is acting as a server.
        
        Args:
            src_ip: Source IP address
            src_port: Source port
            dst_port: Destination port (this endpoint's listening port)
            proto: Protocol
            bytes_in: Bytes received
            packets_in: Packets received
            timestamp: Flow timestamp
        """
        # Track that we received traffic on this port (server behavior)
        port_key = f"{proto}/{dst_port}"
        self.port_frequency.add(f"listen:{port_key}")
        
        # Update inbound aggregates
        self.bytes_in += bytes_in
        self.packets_in += packets_in
        self.flow_count += 1
        
        # Update temporal
        if timestamp:
            if self.first_seen is None or timestamp < self.first_seen:
                self.first_seen = timestamp
            if self.last_seen is None or timestamp > self.last_seen:
                self.last_seen = timestamp
            hour = timestamp.hour
            self.active_hours |= (1 << hour)
        
        self.version += 1
    
    # ─────────────────────────────────────────────────────────────────
    # Derived metrics (for clustering features)
    # ─────────────────────────────────────────────────────────────────
    
    @property
    def peer_diversity(self) -> int:
        """Number of unique peers communicated with."""
        return self.unique_peers.count()
    
    @property
    def service_diversity(self) -> int:
        """Number of unique services accessed."""
        return self.unique_services.count()
    
    @property
    def port_diversity(self) -> int:
        """Number of unique port/proto combinations used."""
        return self.unique_ports.count()
    
    @property
    def in_out_ratio(self) -> float:
        """
        Ratio of bytes in to total bytes.
        
        Returns:
            0.0 = pure sender (client)
            0.5 = balanced
            1.0 = pure receiver (server)
        """
        total = self.bytes_in + self.bytes_out
        if total == 0:
            return 0.5
        return self.bytes_in / total
    
    @property
    def is_likely_server(self) -> bool:
        """
        Heuristic: does this endpoint behave like a server?
        
        Servers typically:
        - Receive more than they send (in_out_ratio > 0.6)
        - Have low peer diversity (many clients connect to them)
        - Listen on specific ports
        """
        return self.in_out_ratio > 0.6 and self.peer_diversity < 100
    
    @property
    def active_hour_count(self) -> int:
        """Number of hours this endpoint was active (0-24)."""
        return bin(self.active_hours).count('1')
    
    @property
    def is_business_hours_only(self) -> bool:
        """
        Is this endpoint primarily active during business hours (8-18)?
        """
        business_mask = 0b000000111111111100000000  # Hours 8-17
        business_activity = bin(self.active_hours & business_mask).count('1')
        total_activity = self.active_hour_count
        if total_activity == 0:
            return False
        return (business_activity / total_activity) > 0.8
    
    def get_top_ports(self, k: int = 5) -> List[Tuple[str, int]]:
        """
        Get the top-k most used ports.
        
        Note: Requires providing candidate ports since CMS doesn't
        track keys. Uses common enterprise ports as candidates.
        
        Args:
            k: Number of top ports to return
            
        Returns:
            List of (port_key, count) tuples
        """
        # Common enterprise ports to check
        candidates = [
            "tcp/443", "tcp/80", "tcp/22", "tcp/445", "tcp/389",
            "tcp/636", "tcp/88", "tcp/464", "tcp/135", "tcp/3389",
            "tcp/8080", "tcp/8443", "tcp/3128", "tcp/53",
            "udp/53", "udp/123", "udp/161", "udp/500", "udp/4500",
            "tcp/25", "tcp/587", "tcp/993", "tcp/995", "tcp/143",
            "tcp/1433", "tcp/3306", "tcp/5432", "tcp/1521",
            "tcp/27017", "tcp/6379", "tcp/5672", "tcp/9092",
        ]
        return self.port_frequency.top_k(candidates, k)
    
    # ─────────────────────────────────────────────────────────────────
    # Merge and sync
    # ─────────────────────────────────────────────────────────────────
    
    def merge(self, other: EndpointSketch) -> EndpointSketch:
        """
        Merge another sketch for the same endpoint.
        
        Used when aggregating sketches from multiple switches
        (endpoint roamed or is seen from different vantage points).
        
        Args:
            other: Another EndpointSketch for the same endpoint
            
        Returns:
            Self (for chaining)
        """
        if self.endpoint_id != other.endpoint_id:
            raise ValueError(
                f"Cannot merge sketches for different endpoints: "
                f"{self.endpoint_id} vs {other.endpoint_id}"
            )
        
        # Merge HyperLogLogs
        self.unique_peers.merge(other.unique_peers)
        self.unique_services.merge(other.unique_services)
        self.unique_ports.merge(other.unique_ports)
        
        # Merge Count-Min Sketches
        self.port_frequency.merge(other.port_frequency)
        self.service_frequency.merge(other.service_frequency)
        
        # Sum aggregates
        self.bytes_in += other.bytes_in
        self.bytes_out += other.bytes_out
        self.packets_in += other.packets_in
        self.packets_out += other.packets_out
        self.flow_count += other.flow_count
        
        # Merge temporal
        if other.first_seen:
            if self.first_seen is None or other.first_seen < self.first_seen:
                self.first_seen = other.first_seen
        if other.last_seen:
            if self.last_seen is None or other.last_seen > self.last_seen:
                self.last_seen = other.last_seen
        self.active_hours |= other.active_hours
        
        # Take enrichment from other if we don't have it
        if not self.user_id and other.user_id:
            self.user_id = other.user_id
            self.username = other.username
        if not self.ad_groups and other.ad_groups:
            self.ad_groups = other.ad_groups
        if not self.ise_profile and other.ise_profile:
            self.ise_profile = other.ise_profile
        if not self.device_type and other.device_type:
            self.device_type = other.device_type
        
        self.version += 1
        return self
    
    def memory_bytes(self) -> int:
        """
        Estimate total memory usage in bytes.
        
        Returns:
            Estimated memory usage
        """
        total = 0
        total += self.unique_peers.memory_bytes()
        total += self.unique_services.memory_bytes()
        total += self.unique_ports.memory_bytes()
        total += self.port_frequency.memory_bytes()
        total += self.service_frequency.memory_bytes()
        total += 500  # Overhead for other fields
        return total
    
    def to_dict(self) -> Dict:
        """
        Convert to dictionary for JSON serialization.
        
        Note: Sketches are converted to their counts/totals,
        not the full sketch data. Use to_bytes() for full serialization.
        """
        return {
            "endpoint_id": self.endpoint_id,
            "switch_id": self.switch_id,
            "device_id": self.device_id,
            "peer_diversity": self.peer_diversity,
            "service_diversity": self.service_diversity,
            "port_diversity": self.port_diversity,
            "bytes_in": self.bytes_in,
            "bytes_out": self.bytes_out,
            "packets_in": self.packets_in,
            "packets_out": self.packets_out,
            "flow_count": self.flow_count,
            "in_out_ratio": self.in_out_ratio,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "active_hours": self.active_hours,
            "active_hour_count": self.active_hour_count,
            "local_cluster_id": self.local_cluster_id,
            "user_id": self.user_id,
            "username": self.username,
            "ad_groups": self.ad_groups,
            "ise_profile": self.ise_profile,
            "device_type": self.device_type,
            "memory_bytes": self.memory_bytes(),
            "version": self.version,
        }
    
    def __repr__(self) -> str:
        return (
            f"EndpointSketch("
            f"endpoint_id='{self.endpoint_id}', "
            f"flows={self.flow_count}, "
            f"peers={self.peer_diversity}, "
            f"ports={self.port_diversity}, "
            f"ratio={self.in_out_ratio:.2f})"
        )

