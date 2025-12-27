"""
Sketch Builder - Convert flow data to EndpointSketches.

This module processes flow records and builds behavioral sketches
for each endpoint. It's designed to simulate streaming ingestion
from the synthetic dataset.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterator, List, Optional, Tuple
import logging

import pandas as pd

from clarion.sketches import EndpointSketch
from clarion.ingest.loader import ClarionDataset

logger = logging.getLogger(__name__)


@dataclass
class SketchStore:
    """
    In-memory store for EndpointSketches.
    
    Maps endpoint_id (MAC address) to its sketch.
    """
    _sketches: Dict[str, EndpointSketch] = field(default_factory=dict)
    
    def get_or_create(
        self, 
        endpoint_id: str,
        switch_id: Optional[str] = None,
    ) -> EndpointSketch:
        """
        Get existing sketch or create new one.
        
        Args:
            endpoint_id: MAC address
            switch_id: Switch ID where this endpoint was seen
            
        Returns:
            EndpointSketch for this endpoint
        """
        if endpoint_id not in self._sketches:
            self._sketches[endpoint_id] = EndpointSketch(
                endpoint_id=endpoint_id,
                switch_id=switch_id,
            )
        return self._sketches[endpoint_id]
    
    def get(self, endpoint_id: str) -> Optional[EndpointSketch]:
        """Get sketch by endpoint ID, or None if not found."""
        return self._sketches.get(endpoint_id)
    
    def all(self) -> List[EndpointSketch]:
        """Get all sketches."""
        return list(self._sketches.values())
    
    def __len__(self) -> int:
        return len(self._sketches)
    
    def __iter__(self) -> Iterator[EndpointSketch]:
        return iter(self._sketches.values())
    
    def memory_bytes(self) -> int:
        """Total memory usage across all sketches."""
        return sum(s.memory_bytes() for s in self._sketches.values())
    
    def summary(self) -> Dict:
        """Summary statistics."""
        if not self._sketches:
            return {"count": 0}
        
        sketches = list(self._sketches.values())
        return {
            "count": len(sketches),
            "total_flows": sum(s.flow_count for s in sketches),
            "total_bytes": sum(s.bytes_in + s.bytes_out for s in sketches),
            "avg_peer_diversity": sum(s.peer_diversity for s in sketches) / len(sketches),
            "avg_port_diversity": sum(s.port_diversity for s in sketches) / len(sketches),
            "memory_bytes": self.memory_bytes(),
            "memory_mb": self.memory_bytes() / (1024 * 1024),
        }


class SketchBuilder:
    """
    Build EndpointSketches from flow data.
    
    Processes flows and updates sketches for source endpoints.
    Can optionally resolve services by destination IP/port.
    
    Example:
        >>> builder = SketchBuilder()
        >>> store = builder.build_from_dataset(dataset)
        >>> print(f"Built {len(store)} sketches")
    """
    
    def __init__(
        self,
        service_lookup: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the sketch builder.
        
        Args:
            service_lookup: Optional IP→service_name lookup table
        """
        self.service_lookup = service_lookup or {}
        self._flows_processed = 0
    
    def build_from_dataset(
        self,
        dataset: ClarionDataset,
        batch_size: int = 10000,
        progress_callback: Optional[callable] = None,
    ) -> SketchStore:
        """
        Build sketches from a ClarionDataset.
        
        Processes all flows in the dataset, updating sketches
        for each source endpoint.
        
        Args:
            dataset: The loaded dataset
            batch_size: Number of flows to process per batch
            progress_callback: Optional callback(processed, total) for progress
            
        Returns:
            SketchStore with all endpoint sketches
        """
        # Build service lookup from services table
        self._build_service_lookup(dataset.services)
        
        # Build MAC → device_id lookup for enrichment
        mac_to_device = self._build_mac_lookup(dataset.endpoints)
        
        store = SketchStore()
        flows = dataset.flows
        total_flows = len(flows)
        
        logger.info(f"Building sketches from {total_flows:,} flows")
        
        # Process in batches
        for batch_start in range(0, total_flows, batch_size):
            batch_end = min(batch_start + batch_size, total_flows)
            batch = flows.iloc[batch_start:batch_end]
            
            for _, flow in batch.iterrows():
                self._process_flow(flow, store, mac_to_device)
            
            self._flows_processed = batch_end
            
            if progress_callback:
                progress_callback(batch_end, total_flows)
            
            if batch_end % 50000 == 0:
                logger.info(
                    f"Processed {batch_end:,}/{total_flows:,} flows, "
                    f"{len(store)} endpoints"
                )
        
        logger.info(
            f"Built {len(store)} sketches from {total_flows:,} flows "
            f"(memory: {store.memory_bytes() / 1024 / 1024:.1f}MB)"
        )
        
        return store
    
    def _process_flow(
        self,
        flow: pd.Series,
        store: SketchStore,
        mac_to_device: Dict[str, str],
    ) -> None:
        """
        Process a single flow record.
        
        Updates the sketch for the source endpoint.
        
        Args:
            flow: Flow record (pandas Series)
            store: SketchStore to update
            mac_to_device: MAC → device_id lookup
        """
        src_mac = flow["src_mac"]
        if pd.isna(src_mac):
            return
        
        # Get or create sketch for source endpoint
        sketch = store.get_or_create(
            endpoint_id=src_mac,
            switch_id=flow["exporter_switch_id"],
        )
        
        # Set device_id if known
        if sketch.device_id is None and src_mac in mac_to_device:
            sketch.device_id = mac_to_device[src_mac]
        
        # Resolve service name if possible
        dst_ip = flow["dst_ip"]
        dst_port = flow["dst_port"]
        proto = flow["proto"]
        service_name = self._lookup_service(dst_ip, dst_port, proto)
        
        # Parse timestamp
        timestamp = flow["start_time"]
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)
        
        # Record the flow
        sketch.record_flow(
            dst_ip=dst_ip,
            dst_port=dst_port,
            proto=proto,
            bytes_out=flow["bytes"],
            bytes_in=0,  # We only have outbound bytes in this dataset
            packets_out=flow["packets"],
            packets_in=0,
            service_name=service_name,
            timestamp=timestamp.to_pydatetime() if hasattr(timestamp, 'to_pydatetime') else timestamp,
        )
    
    def _build_service_lookup(self, services: pd.DataFrame) -> None:
        """Build IP→service_name lookup from services table."""
        for _, service in services.iterrows():
            ip = service["ip"]
            name = service["service_name"]
            self.service_lookup[ip] = name
        
        logger.debug(f"Built service lookup with {len(self.service_lookup)} entries")
    
    def _build_mac_lookup(self, endpoints: pd.DataFrame) -> Dict[str, str]:
        """Build MAC→device_id lookup from endpoints table."""
        return dict(zip(endpoints["mac"], endpoints["device_id"]))
    
    def _lookup_service(
        self, 
        dst_ip: str, 
        dst_port: int, 
        proto: str,
    ) -> Optional[str]:
        """
        Look up service name for destination.
        
        First checks IP-based lookup, then falls back to well-known ports.
        """
        # Check IP-based lookup
        if dst_ip in self.service_lookup:
            return self.service_lookup[dst_ip]
        
        # Fall back to well-known ports
        return self._port_to_service(dst_port, proto)
    
    def _port_to_service(self, port: int, proto: str) -> Optional[str]:
        """Map well-known ports to service names."""
        well_known = {
            (53, "udp"): "DNS",
            (53, "tcp"): "DNS",
            (80, "tcp"): "HTTP",
            (443, "tcp"): "HTTPS",
            (22, "tcp"): "SSH",
            (445, "tcp"): "SMB",
            (389, "tcp"): "LDAP",
            (636, "tcp"): "LDAPS",
            (88, "tcp"): "Kerberos",
            (464, "tcp"): "Kerberos-Change",
            (135, "tcp"): "RPC",
            (3389, "tcp"): "RDP",
            (8080, "tcp"): "HTTP-Proxy",
            (3128, "tcp"): "Proxy",
            (25, "tcp"): "SMTP",
            (587, "tcp"): "SMTP-Submission",
            (993, "tcp"): "IMAPS",
            (995, "tcp"): "POP3S",
            (123, "udp"): "NTP",
            (161, "udp"): "SNMP",
            (162, "udp"): "SNMP-Trap",
            (514, "udp"): "Syslog",
            (1433, "tcp"): "MSSQL",
            (3306, "tcp"): "MySQL",
            (5432, "tcp"): "PostgreSQL",
            (1521, "tcp"): "Oracle",
            (27017, "tcp"): "MongoDB",
            (6379, "tcp"): "Redis",
            (5672, "tcp"): "AMQP",
            (9092, "tcp"): "Kafka",
            (8443, "tcp"): "HTTPS-Alt",
        }
        return well_known.get((port, proto))


def build_sketches(dataset: ClarionDataset) -> SketchStore:
    """
    Convenience function to build sketches from a dataset.
    
    Args:
        dataset: Loaded ClarionDataset
        
    Returns:
        SketchStore with all endpoint sketches
        
    Example:
        >>> dataset = load_dataset("data/raw/trustsec_copilot_synth_campus")
        >>> store = build_sketches(dataset)
    """
    builder = SketchBuilder()
    return builder.build_from_dataset(dataset)


