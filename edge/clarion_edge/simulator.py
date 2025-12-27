"""
Flow Simulator - Simulate switch flow data for testing.

Provides two modes:
1. Replay: Play back flows from a CSV file
2. Synthetic: Generate realistic flow patterns

This allows testing the edge agent without a physical switch.
"""

from __future__ import annotations

import csv
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)


@dataclass
class SimulatedFlow:
    """A single simulated NetFlow record."""
    src_mac: str
    src_ip: str
    dst_ip: str
    dst_port: int
    src_port: int
    proto: str
    bytes: int
    packets: int
    timestamp: int  # Unix timestamp
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "src_mac": self.src_mac,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "dst_port": self.dst_port,
            "src_port": self.src_port,
            "proto": self.proto,
            "bytes": self.bytes,
            "packets": self.packets,
            "timestamp": self.timestamp,
        }


@dataclass
class SimulatorConfig:
    """Configuration for the flow simulator."""
    mode: str = "synthetic"  # "synthetic" or "replay"
    
    # Replay mode settings
    csv_path: Optional[str] = None
    replay_speed: float = 1.0  # 1.0 = real-time, 10.0 = 10x speed
    
    # Synthetic mode settings
    num_endpoints: int = 50
    flows_per_second: float = 100.0
    
    # Network patterns
    server_ips: List[str] = field(default_factory=lambda: [
        "10.0.1.10", "10.0.1.11", "10.0.1.12",  # Web servers
        "10.0.1.20",  # DNS
        "10.0.1.30",  # LDAP/AD
        "10.0.1.40",  # File server
    ])
    
    common_ports: List[int] = field(default_factory=lambda: [
        80, 443, 53, 389, 445, 22, 3389, 8080, 8443,
    ])
    
    # Endpoint types (for realistic patterns)
    endpoint_types: Dict[str, float] = field(default_factory=lambda: {
        "workstation": 0.6,
        "server": 0.15,
        "printer": 0.1,
        "iot": 0.15,
    })


class FlowSimulator:
    """
    Simulate NetFlow data for testing.
    
    Example (synthetic mode):
        >>> config = SimulatorConfig(mode="synthetic", num_endpoints=50)
        >>> simulator = FlowSimulator(config)
        >>> for flow in simulator.generate():
        ...     agent.process_flow(flow)
    
    Example (replay mode):
        >>> config = SimulatorConfig(mode="replay", csv_path="flows.csv")
        >>> simulator = FlowSimulator(config)
        >>> for flow in simulator.generate():
        ...     agent.process_flow(flow)
    """
    
    def __init__(self, config: SimulatorConfig):
        """Initialize the simulator."""
        self.config = config
        self._endpoints: List[Dict] = []
        self._running = False
        
        if config.mode == "synthetic":
            self._init_synthetic_endpoints()
    
    def _init_synthetic_endpoints(self) -> None:
        """Initialize synthetic endpoints with realistic patterns."""
        for i in range(self.config.num_endpoints):
            # Random MAC address
            mac = ":".join(f"{random.randint(0, 255):02x}" for _ in range(6))
            
            # Assign an IP
            ip = f"10.0.{random.randint(10, 250)}.{random.randint(1, 254)}"
            
            # Assign endpoint type
            type_roll = random.random()
            cumulative = 0.0
            endpoint_type = "workstation"
            for etype, prob in self.config.endpoint_types.items():
                cumulative += prob
                if type_roll < cumulative:
                    endpoint_type = etype
                    break
            
            # Generate behavior pattern
            pattern = self._generate_pattern(endpoint_type)
            
            self._endpoints.append({
                "mac": mac,
                "ip": ip,
                "type": endpoint_type,
                "pattern": pattern,
            })
        
        logger.info(f"Initialized {len(self._endpoints)} synthetic endpoints")
    
    def _generate_pattern(self, endpoint_type: str) -> Dict:
        """Generate realistic traffic pattern for endpoint type."""
        if endpoint_type == "workstation":
            return {
                "target_servers": random.sample(
                    self.config.server_ips,
                    k=min(4, len(self.config.server_ips))
                ),
                "common_ports": [80, 443, 53, 389, 445],
                "flows_per_hour": random.randint(50, 200),
                "bytes_per_flow": (500, 50000),
                "active_hours": list(range(8, 18)),  # Business hours
            }
        elif endpoint_type == "server":
            return {
                "target_servers": [],  # Servers receive traffic
                "common_ports": [22, 443, 80, 8080],
                "flows_per_hour": random.randint(500, 2000),
                "bytes_per_flow": (1000, 500000),
                "active_hours": list(range(24)),  # Always on
            }
        elif endpoint_type == "printer":
            return {
                "target_servers": self.config.server_ips[:1],
                "common_ports": [9100, 631, 515],
                "flows_per_hour": random.randint(5, 20),
                "bytes_per_flow": (1000, 100000),
                "active_hours": list(range(8, 18)),
            }
        else:  # iot
            return {
                "target_servers": self.config.server_ips[:2],
                "common_ports": [443, 80, 8883, 1883],  # MQTT
                "flows_per_hour": random.randint(10, 50),
                "bytes_per_flow": (100, 5000),
                "active_hours": list(range(24)),
            }
    
    def generate(
        self,
        duration_seconds: Optional[int] = None,
        max_flows: Optional[int] = None,
    ) -> Iterator[SimulatedFlow]:
        """
        Generate flows.
        
        Args:
            duration_seconds: Stop after this many seconds (None = infinite)
            max_flows: Stop after this many flows (None = infinite)
            
        Yields:
            SimulatedFlow objects
        """
        if self.config.mode == "replay":
            yield from self._replay_flows(max_flows)
        else:
            yield from self._generate_synthetic(duration_seconds, max_flows)
    
    def _replay_flows(
        self,
        max_flows: Optional[int] = None,
    ) -> Iterator[SimulatedFlow]:
        """Replay flows from a CSV file."""
        if not self.config.csv_path:
            raise ValueError("csv_path required for replay mode")
        
        path = Path(self.config.csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")
        
        count = 0
        first_timestamp = None
        start_time = time.time()
        
        with open(path, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Parse timestamp
                try:
                    ts = datetime.fromisoformat(row.get("start_time", ""))
                    timestamp = int(ts.timestamp())
                except (ValueError, TypeError):
                    timestamp = int(time.time())
                
                if first_timestamp is None:
                    first_timestamp = timestamp
                
                # Wait for real-time replay
                if self.config.replay_speed > 0:
                    elapsed = time.time() - start_time
                    flow_time = (timestamp - first_timestamp) / self.config.replay_speed
                    if flow_time > elapsed:
                        time.sleep(flow_time - elapsed)
                
                flow = SimulatedFlow(
                    src_mac=row.get("src_mac", "00:00:00:00:00:00"),
                    src_ip=row.get("src_ip", "0.0.0.0"),
                    dst_ip=row.get("dst_ip", "0.0.0.0"),
                    dst_port=int(row.get("dst_port", 0)),
                    src_port=int(row.get("src_port", 0)),
                    proto=row.get("proto", "tcp"),
                    bytes=int(row.get("bytes", 0)),
                    packets=int(row.get("packets", 1)),
                    timestamp=timestamp,
                )
                
                yield flow
                count += 1
                
                if max_flows and count >= max_flows:
                    break
        
        logger.info(f"Replayed {count} flows from {path}")
    
    def _generate_synthetic(
        self,
        duration_seconds: Optional[int] = None,
        max_flows: Optional[int] = None,
    ) -> Iterator[SimulatedFlow]:
        """Generate synthetic flows."""
        self._running = True
        start_time = time.time()
        count = 0
        
        # Calculate inter-flow delay
        delay = 1.0 / self.config.flows_per_second
        
        while self._running:
            # Check termination conditions
            if duration_seconds and (time.time() - start_time) >= duration_seconds:
                break
            if max_flows and count >= max_flows:
                break
            
            # Select a random endpoint
            endpoint = random.choice(self._endpoints)
            pattern = endpoint["pattern"]
            
            # Check if endpoint is active this hour
            current_hour = datetime.now().hour
            if current_hour not in pattern.get("active_hours", range(24)):
                # Low probability of activity outside hours
                if random.random() > 0.1:
                    time.sleep(delay)
                    continue
            
            # Generate flow
            flow = self._generate_flow(endpoint)
            yield flow
            count += 1
            
            if count % 1000 == 0:
                logger.debug(f"Generated {count} flows")
            
            # Small delay to simulate real-time
            if delay > 0:
                time.sleep(delay * random.uniform(0.5, 1.5))
        
        logger.info(f"Generated {count} synthetic flows")
    
    def _generate_flow(self, endpoint: Dict) -> SimulatedFlow:
        """Generate a single flow for an endpoint."""
        pattern = endpoint["pattern"]
        
        # Choose destination
        if pattern["target_servers"]:
            dst_ip = random.choice(pattern["target_servers"])
        else:
            # Random destination
            dst_ip = f"10.0.{random.randint(1, 250)}.{random.randint(1, 254)}"
        
        # Choose port
        if pattern["common_ports"]:
            dst_port = random.choice(pattern["common_ports"])
        else:
            dst_port = random.choice(self.config.common_ports)
        
        # Random source port
        src_port = random.randint(49152, 65535)
        
        # Protocol
        proto = "tcp" if dst_port not in [53, 123, 161] else "udp"
        
        # Bytes
        min_bytes, max_bytes = pattern["bytes_per_flow"]
        bytes_count = random.randint(min_bytes, max_bytes)
        
        return SimulatedFlow(
            src_mac=endpoint["mac"],
            src_ip=endpoint["ip"],
            dst_ip=dst_ip,
            dst_port=dst_port,
            src_port=src_port,
            proto=proto,
            bytes=bytes_count,
            packets=max(1, bytes_count // 1500),
            timestamp=int(time.time()),
        )
    
    def stop(self) -> None:
        """Stop the simulator."""
        self._running = False


def create_test_csv(
    output_path: str,
    num_flows: int = 1000,
    num_endpoints: int = 20,
) -> None:
    """
    Create a test CSV file for replay mode.
    
    Args:
        output_path: Path to output CSV
        num_flows: Number of flows to generate
        num_endpoints: Number of unique endpoints
    """
    config = SimulatorConfig(
        mode="synthetic",
        num_endpoints=num_endpoints,
        flows_per_second=float('inf'),  # No delay
    )
    
    simulator = FlowSimulator(config)
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "src_mac", "src_ip", "dst_ip", "dst_port", "src_port",
            "proto", "bytes", "packets", "start_time",
        ])
        writer.writeheader()
        
        base_time = datetime.now()
        for i, flow in enumerate(simulator.generate(max_flows=num_flows)):
            # Add realistic timestamps
            ts = base_time + timedelta(seconds=i * 0.1)
            
            row = flow.to_dict()
            row["start_time"] = ts.isoformat()
            del row["timestamp"]
            
            writer.writerow(row)
    
    logger.info(f"Created test CSV with {num_flows} flows: {output_path}")


