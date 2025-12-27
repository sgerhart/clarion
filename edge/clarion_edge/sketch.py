"""
Edge Sketches - Lightweight behavioral fingerprints.

Memory-optimized sketches for edge deployment.
Uses pure Python implementations to minimize dependencies.
"""

from __future__ import annotations

import hashlib
import math
import struct
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import json


class EdgeHyperLogLog:
    """
    Lightweight HyperLogLog for cardinality estimation.
    
    Uses 4KB of memory (2^10 registers) for ~2% error rate.
    Pure Python implementation - no external dependencies.
    """
    
    def __init__(self, precision: int = 10):
        """
        Initialize HyperLogLog.
        
        Args:
            precision: Number of bits for register indexing (default 10 = 1024 registers)
        """
        self.precision = precision
        self.num_registers = 1 << precision
        self.registers = bytearray(self.num_registers)
        self._alpha = self._get_alpha()
    
    def _get_alpha(self) -> float:
        """Get alpha correction factor."""
        m = self.num_registers
        if m == 16:
            return 0.673
        elif m == 32:
            return 0.697
        elif m == 64:
            return 0.709
        else:
            return 0.7213 / (1 + 1.079 / m)
    
    def _hash(self, item: Any) -> int:
        """Hash an item to 64-bit integer."""
        h = hashlib.md5(str(item).encode()).digest()
        return struct.unpack('<Q', h[:8])[0]
    
    def add(self, item: Any) -> None:
        """Add an item to the sketch."""
        h = self._hash(item)
        idx = h & (self.num_registers - 1)
        remaining = h >> self.precision
        
        # Count leading zeros + 1
        rho = 1
        while remaining & 1 == 0 and rho <= 64 - self.precision:
            rho += 1
            remaining >>= 1
        
        self.registers[idx] = max(self.registers[idx], rho)
    
    def count(self) -> int:
        """Estimate cardinality."""
        # Harmonic mean
        indicator = sum(2.0 ** (-r) for r in self.registers)
        raw_estimate = self._alpha * self.num_registers ** 2 / indicator
        
        # Small range correction
        if raw_estimate <= 2.5 * self.num_registers:
            zeros = self.registers.count(0)
            if zeros > 0:
                return int(self.num_registers * math.log(self.num_registers / zeros))
        
        return int(raw_estimate)
    
    def merge(self, other: "EdgeHyperLogLog") -> None:
        """Merge another HLL into this one."""
        if self.num_registers != other.num_registers:
            raise ValueError("Cannot merge HLLs with different precision")
        
        for i in range(self.num_registers):
            self.registers[i] = max(self.registers[i], other.registers[i])
    
    def memory_bytes(self) -> int:
        """Return memory usage in bytes."""
        return self.num_registers
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        return bytes([self.precision]) + bytes(self.registers)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "EdgeHyperLogLog":
        """Deserialize from bytes."""
        precision = data[0]
        hll = cls(precision=precision)
        hll.registers = bytearray(data[1:])
        return hll


class EdgeCountMinSketch:
    """
    Lightweight Count-Min Sketch for frequency estimation.
    
    Uses ~16KB of memory (4 hash functions, 1024 counters each).
    Pure Python implementation - no external dependencies.
    """
    
    def __init__(self, width: int = 1024, depth: int = 4):
        """
        Initialize Count-Min Sketch.
        
        Args:
            width: Number of counters per hash function
            depth: Number of hash functions
        """
        self.width = width
        self.depth = depth
        self.counters = [[0] * width for _ in range(depth)]
        self._total = 0
    
    def _hash(self, item: Any, seed: int) -> int:
        """Hash an item with a seed."""
        h = hashlib.md5(f"{seed}:{item}".encode()).digest()
        return struct.unpack('<I', h[:4])[0] % self.width
    
    def add(self, item: Any, count: int = 1) -> None:
        """Add an item with optional count."""
        for i in range(self.depth):
            idx = self._hash(item, i)
            self.counters[i][idx] += count
        self._total += count
    
    def count(self, item: Any) -> int:
        """Estimate count of an item."""
        return min(
            self.counters[i][self._hash(item, i)]
            for i in range(self.depth)
        )
    
    def total(self) -> int:
        """Return total count."""
        return self._total
    
    def merge(self, other: "EdgeCountMinSketch") -> None:
        """Merge another CMS into this one."""
        if self.width != other.width or self.depth != other.depth:
            raise ValueError("Cannot merge CMS with different dimensions")
        
        for i in range(self.depth):
            for j in range(self.width):
                self.counters[i][j] += other.counters[i][j]
        self._total += other._total
    
    def memory_bytes(self) -> int:
        """Return memory usage in bytes."""
        # Each counter is 4 bytes (int32)
        return self.width * self.depth * 4
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        header = struct.pack('<HH', self.width, self.depth)
        data = b''.join(
            struct.pack(f'<{self.width}I', *row)
            for row in self.counters
        )
        return header + data
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "EdgeCountMinSketch":
        """Deserialize from bytes."""
        width, depth = struct.unpack('<HH', data[:4])
        cms = cls(width=width, depth=depth)
        
        offset = 4
        for i in range(depth):
            row = struct.unpack(f'<{width}I', data[offset:offset + width * 4])
            cms.counters[i] = list(row)
            offset += width * 4
        
        # Recalculate total
        cms._total = sum(cms.counters[0])
        
        return cms


@dataclass
class EdgeSketch:
    """
    Lightweight behavioral sketch for an endpoint.
    
    Designed for edge deployment with minimal memory:
    - ~5KB per endpoint (vs 50KB+ for full sketches)
    - No numpy dependency
    - Serializable for network transfer
    """
    endpoint_id: str  # MAC address
    switch_id: str
    
    # Cardinality sketches
    unique_peers: EdgeHyperLogLog = field(default_factory=EdgeHyperLogLog)
    unique_ports: EdgeHyperLogLog = field(default_factory=EdgeHyperLogLog)
    
    # Frequency sketches
    port_frequency: EdgeCountMinSketch = field(default_factory=EdgeCountMinSketch)
    
    # Simple aggregates (no sketch needed)
    bytes_in: int = 0
    bytes_out: int = 0
    flow_count: int = 0
    
    # Timestamps
    first_seen: int = 0  # Unix timestamp
    last_seen: int = 0
    
    # Temporal pattern (24-bit bitmap for hours)
    active_hours: int = 0
    
    # Local cluster assignment (from edge K-means)
    local_cluster_id: int = -1
    
    def record_flow(
        self,
        dst_ip: str,
        dst_port: int,
        proto: str,
        bytes_count: int,
        is_outbound: bool,
        timestamp: Optional[int] = None,
    ) -> None:
        """Record a flow in this sketch."""
        if timestamp is None:
            timestamp = int(time.time())
        
        # Update timestamps
        if self.first_seen == 0:
            self.first_seen = timestamp
        self.last_seen = timestamp
        
        # Update cardinality
        self.unique_peers.add(dst_ip)
        self.unique_ports.add(f"{proto}/{dst_port}")
        
        # Update frequency
        self.port_frequency.add(f"{proto}/{dst_port}")
        
        # Update byte counts
        if is_outbound:
            self.bytes_out += bytes_count
        else:
            self.bytes_in += bytes_count
        
        self.flow_count += 1
        
        # Update hourly bitmap
        from datetime import datetime
        hour = datetime.fromtimestamp(timestamp).hour
        self.active_hours |= (1 << hour)
    
    def get_feature_vector(self) -> List[float]:
        """
        Extract features for clustering.
        
        Returns a normalized feature vector suitable for Mini-Batch K-Means.
        """
        # Avoid division by zero
        total_bytes = max(self.bytes_in + self.bytes_out, 1)
        
        features = [
            # Diversity (log-scaled)
            math.log1p(self.unique_peers.count()),
            math.log1p(self.unique_ports.count()),
            
            # Traffic volume (log-scaled)
            math.log1p(self.bytes_out),
            math.log1p(self.bytes_in),
            math.log1p(self.flow_count),
            
            # Ratio features
            self.bytes_out / total_bytes,  # In/out ratio
            
            # Temporal (normalized)
            bin(self.active_hours).count('1') / 24.0,  # Active hours ratio
        ]
        
        return features
    
    def memory_bytes(self) -> int:
        """Estimate memory usage in bytes."""
        return (
            self.unique_peers.memory_bytes() +
            self.unique_ports.memory_bytes() +
            self.port_frequency.memory_bytes() +
            64  # Other fields
        )
    
    def merge(self, other: "EdgeSketch") -> None:
        """Merge another sketch into this one."""
        if self.endpoint_id != other.endpoint_id:
            raise ValueError("Cannot merge sketches for different endpoints")
        
        self.unique_peers.merge(other.unique_peers)
        self.unique_ports.merge(other.unique_ports)
        self.port_frequency.merge(other.port_frequency)
        
        self.bytes_in += other.bytes_in
        self.bytes_out += other.bytes_out
        self.flow_count += other.flow_count
        
        self.first_seen = min(self.first_seen, other.first_seen) or max(self.first_seen, other.first_seen)
        self.last_seen = max(self.last_seen, other.last_seen)
        self.active_hours |= other.active_hours
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "endpoint_id": self.endpoint_id,
            "switch_id": self.switch_id,
            "unique_peers": self.unique_peers.count(),
            "unique_ports": self.unique_ports.count(),
            "bytes_in": self.bytes_in,
            "bytes_out": self.bytes_out,
            "flow_count": self.flow_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "active_hours": self.active_hours,
            "local_cluster_id": self.local_cluster_id,
            "memory_bytes": self.memory_bytes(),
        }
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes for network transfer."""
        # Header
        header = json.dumps({
            "endpoint_id": self.endpoint_id,
            "switch_id": self.switch_id,
            "bytes_in": self.bytes_in,
            "bytes_out": self.bytes_out,
            "flow_count": self.flow_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "active_hours": self.active_hours,
            "local_cluster_id": self.local_cluster_id,
        }).encode()
        
        # Sketches
        peers_bytes = self.unique_peers.to_bytes()
        ports_bytes = self.unique_ports.to_bytes()
        freq_bytes = self.port_frequency.to_bytes()
        
        # Pack everything
        return struct.pack(
            '<III',
            len(header),
            len(peers_bytes),
            len(ports_bytes),
        ) + header + peers_bytes + ports_bytes + freq_bytes
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "EdgeSketch":
        """Deserialize from bytes."""
        header_len, peers_len, ports_len = struct.unpack('<III', data[:12])
        
        offset = 12
        header = json.loads(data[offset:offset + header_len].decode())
        offset += header_len
        
        peers = EdgeHyperLogLog.from_bytes(data[offset:offset + peers_len])
        offset += peers_len
        
        ports = EdgeHyperLogLog.from_bytes(data[offset:offset + ports_len])
        offset += ports_len
        
        freq = EdgeCountMinSketch.from_bytes(data[offset:])
        
        sketch = cls(
            endpoint_id=header["endpoint_id"],
            switch_id=header["switch_id"],
            unique_peers=peers,
            unique_ports=ports,
            port_frequency=freq,
            bytes_in=header["bytes_in"],
            bytes_out=header["bytes_out"],
            flow_count=header["flow_count"],
            first_seen=header["first_seen"],
            last_seen=header["last_seen"],
            active_hours=header["active_hours"],
            local_cluster_id=header["local_cluster_id"],
        )
        
        return sketch


class EdgeSketchStore:
    """
    In-memory store for edge sketches.
    
    Memory-constrained: evicts least-recently-seen sketches when full.
    """
    
    def __init__(self, max_endpoints: int = 500, switch_id: str = "unknown"):
        """
        Initialize the store.
        
        Args:
            max_endpoints: Maximum number of endpoints to track
            switch_id: Identifier for this switch
        """
        self.max_endpoints = max_endpoints
        self.switch_id = switch_id
        self._sketches: Dict[str, EdgeSketch] = {}
    
    def get_or_create(self, endpoint_id: str) -> EdgeSketch:
        """Get or create a sketch for an endpoint."""
        if endpoint_id not in self._sketches:
            # Check capacity
            if len(self._sketches) >= self.max_endpoints:
                self._evict_oldest()
            
            self._sketches[endpoint_id] = EdgeSketch(
                endpoint_id=endpoint_id,
                switch_id=self.switch_id,
            )
        
        return self._sketches[endpoint_id]
    
    def _evict_oldest(self) -> None:
        """Evict the least-recently-seen sketch."""
        if not self._sketches:
            return
        
        oldest_id = min(
            self._sketches.keys(),
            key=lambda k: self._sketches[k].last_seen
        )
        del self._sketches[oldest_id]
    
    def __len__(self) -> int:
        return len(self._sketches)
    
    def __iter__(self):
        return iter(self._sketches.values())
    
    def get_all_sketches(self) -> List[EdgeSketch]:
        """Get all sketches."""
        return list(self._sketches.values())
    
    def get_feature_matrix(self) -> Tuple[List[List[float]], List[str]]:
        """
        Get feature matrix for clustering.
        
        Returns:
            Tuple of (feature_matrix, endpoint_ids)
        """
        sketches = self.get_all_sketches()
        features = [s.get_feature_vector() for s in sketches]
        ids = [s.endpoint_id for s in sketches]
        return features, ids
    
    def memory_bytes(self) -> int:
        """Estimate total memory usage."""
        return sum(s.memory_bytes() for s in self._sketches.values())
    
    def summary(self) -> Dict:
        """Get store summary."""
        return {
            "switch_id": self.switch_id,
            "endpoint_count": len(self._sketches),
            "max_endpoints": self.max_endpoints,
            "memory_kb": self.memory_bytes() / 1024,
            "total_flows": sum(s.flow_count for s in self._sketches.values()),
        }


