"""
Policy Matrix - SGT to SGT Communication Matrix.

Builds a matrix showing traffic patterns between Security Group Tags,
forming the basis for SGACL policy generation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
import logging

import pandas as pd

from clarion.sketches import EndpointSketch
from clarion.ingest.loader import ClarionDataset
from clarion.ingest.sketch_builder import SketchStore
from clarion.clustering.clusterer import ClusterResult
from clarion.clustering.sgt_mapper import SGTTaxonomy, SGTRecommendation

logger = logging.getLogger(__name__)


@dataclass
class MatrixCell:
    """
    One cell in the SGT × SGT policy matrix.
    
    Represents observed traffic from src_sgt to dst_sgt.
    """
    src_sgt: int
    src_sgt_name: str
    dst_sgt: int
    dst_sgt_name: str
    
    # Observed traffic patterns
    observed_ports: Dict[str, int] = field(default_factory=dict)  # "tcp/443" → flow_count
    total_bytes: int = 0
    total_flows: int = 0
    unique_src_endpoints: int = 0
    unique_dst_endpoints: int = 0
    
    # Temporal
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    
    # Service names if resolved
    services: Set[str] = field(default_factory=set)
    
    def add_flow(
        self,
        port: int,
        proto: str,
        bytes_count: int,
        service_name: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Add a flow to this cell."""
        port_key = f"{proto}/{port}"
        self.observed_ports[port_key] = self.observed_ports.get(port_key, 0) + 1
        self.total_bytes += bytes_count
        self.total_flows += 1
        
        if service_name:
            self.services.add(service_name)
        
        if timestamp:
            if self.first_seen is None or timestamp < self.first_seen:
                self.first_seen = timestamp
            if self.last_seen is None or timestamp > self.last_seen:
                self.last_seen = timestamp
    
    def top_ports(self, k: int = 10) -> List[Tuple[str, int]]:
        """Get top-k most used ports."""
        sorted_ports = sorted(
            self.observed_ports.items(),
            key=lambda x: -x[1]
        )
        return sorted_ports[:k]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "src_sgt": self.src_sgt,
            "src_sgt_name": self.src_sgt_name,
            "dst_sgt": self.dst_sgt,
            "dst_sgt_name": self.dst_sgt_name,
            "observed_ports": dict(self.observed_ports),
            "total_bytes": self.total_bytes,
            "total_flows": self.total_flows,
            "unique_src_endpoints": self.unique_src_endpoints,
            "unique_dst_endpoints": self.unique_dst_endpoints,
            "services": list(self.services),
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }


@dataclass
class PolicyMatrix:
    """
    SGT × SGT policy matrix.
    
    Contains all observed traffic patterns between SGT pairs,
    forming the basis for SGACL policy generation.
    """
    cells: Dict[Tuple[int, int], MatrixCell] = field(default_factory=dict)
    sgt_names: Dict[int, str] = field(default_factory=dict)
    
    # Statistics
    total_flows: int = 0
    total_bytes: int = 0
    
    def get_cell(self, src_sgt: int, dst_sgt: int) -> Optional[MatrixCell]:
        """Get a specific cell, or None if no traffic observed."""
        return self.cells.get((src_sgt, dst_sgt))
    
    def get_or_create_cell(self, src_sgt: int, dst_sgt: int) -> MatrixCell:
        """Get or create a cell for the SGT pair."""
        key = (src_sgt, dst_sgt)
        if key not in self.cells:
            self.cells[key] = MatrixCell(
                src_sgt=src_sgt,
                src_sgt_name=self.sgt_names.get(src_sgt, f"SGT-{src_sgt}"),
                dst_sgt=dst_sgt,
                dst_sgt_name=self.sgt_names.get(dst_sgt, f"SGT-{dst_sgt}"),
            )
        return self.cells[key]
    
    def add_sgt_name(self, sgt: int, name: str) -> None:
        """Register an SGT name."""
        self.sgt_names[sgt] = name
    
    @property
    def sgt_values(self) -> List[int]:
        """Get all SGT values in the matrix."""
        sgts = set()
        for src, dst in self.cells.keys():
            sgts.add(src)
            sgts.add(dst)
        return sorted(sgts)
    
    @property
    def n_cells(self) -> int:
        """Number of non-empty cells."""
        return len(self.cells)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame for analysis."""
        rows = []
        for (src, dst), cell in self.cells.items():
            row = {
                "src_sgt": src,
                "src_sgt_name": cell.src_sgt_name,
                "dst_sgt": dst,
                "dst_sgt_name": cell.dst_sgt_name,
                "total_flows": cell.total_flows,
                "total_bytes": cell.total_bytes,
                "unique_ports": len(cell.observed_ports),
                "top_port": cell.top_ports(1)[0][0] if cell.observed_ports else None,
            }
            rows.append(row)
        return pd.DataFrame(rows)
    
    def to_heatmap_data(self) -> Tuple[List[int], List[int], List[List[int]]]:
        """
        Convert to heatmap format.
        
        Returns:
            Tuple of (src_sgts, dst_sgts, flow_counts_matrix)
        """
        sgts = self.sgt_values
        n = len(sgts)
        sgt_to_idx = {sgt: i for i, sgt in enumerate(sgts)}
        
        matrix = [[0] * n for _ in range(n)]
        
        for (src, dst), cell in self.cells.items():
            if src in sgt_to_idx and dst in sgt_to_idx:
                matrix[sgt_to_idx[src]][sgt_to_idx[dst]] = cell.total_flows
        
        return sgts, sgts, matrix
    
    def summary(self) -> Dict:
        """Get matrix summary statistics."""
        return {
            "n_sgts": len(self.sgt_values),
            "n_cells": self.n_cells,
            "total_flows": self.total_flows,
            "total_bytes": self.total_bytes,
            "density": self.n_cells / max(len(self.sgt_values) ** 2, 1),
        }


class PolicyMatrixBuilder:
    """
    Build a policy matrix from flow data and SGT assignments.
    
    Maps observed flows to SGT pairs based on cluster assignments
    and the SGT taxonomy.
    
    Example:
        >>> builder = PolicyMatrixBuilder(taxonomy)
        >>> matrix = builder.build(dataset, store, cluster_result)
    """
    
    def __init__(self, taxonomy: SGTTaxonomy):
        """
        Initialize the builder.
        
        Args:
            taxonomy: SGT taxonomy with cluster → SGT mappings
        """
        self.taxonomy = taxonomy
        
        # Build cluster → SGT lookup
        self._cluster_to_sgt: Dict[int, int] = {}
        self._cluster_to_name: Dict[int, str] = {}
        
        for rec in taxonomy.recommendations:
            self._cluster_to_sgt[rec.cluster_id] = rec.sgt_value
            self._cluster_to_name[rec.cluster_id] = rec.sgt_name
    
    def build(
        self,
        dataset: ClarionDataset,
        store: SketchStore,
        cluster_result: ClusterResult,
        sample_flows: Optional[int] = None,
    ) -> PolicyMatrix:
        """
        Build the policy matrix from flow data.
        
        Args:
            dataset: Dataset with flows
            store: SketchStore with sketches
            cluster_result: Cluster assignments
            sample_flows: Optional limit on flows to process
            
        Returns:
            PolicyMatrix with observed traffic
        """
        logger.info("Building policy matrix from flows")
        
        # Initialize matrix with SGT names
        matrix = PolicyMatrix()
        for rec in self.taxonomy.recommendations:
            matrix.add_sgt_name(rec.sgt_value, rec.sgt_name)
        
        # Build endpoint → cluster lookup
        endpoint_to_cluster = dict(zip(
            cluster_result.endpoint_ids,
            cluster_result.labels
        ))
        
        # Build MAC → endpoint lookup for flows
        mac_to_endpoint = {s.endpoint_id: s for s in store}
        
        # Build IP → MAC lookup from ip_assignments (for faster destination resolution)
        ip_to_mac: Dict[str, str] = {}
        if not dataset.ip_assignments.empty:
            for _, row in dataset.ip_assignments.iterrows():
                ip = str(row.get("ip", ""))
                mac = str(row.get("mac", ""))
                if ip and mac:
                    ip_to_mac[ip] = mac
        
        # Build service IP → service name lookup
        service_lookup = self._build_service_lookup(dataset)
        
        # Process flows
        flows = dataset.flows
        if sample_flows:
            flows = flows.head(sample_flows)
        
        total_flows = len(flows)
        processed = 0
        skipped = 0
        
        # Track unique endpoints per cell
        cell_src_endpoints: Dict[Tuple[int, int], Set[str]] = defaultdict(set)
        cell_dst_endpoints: Dict[Tuple[int, int], Set[str]] = defaultdict(set)
        
        for _, flow in flows.iterrows():
            src_mac = flow["src_mac"]
            dst_ip = flow["dst_ip"]
            
            if pd.isna(src_mac):
                skipped += 1
                continue
            
            # PRIORITY 1: Use SGTs directly from flow data if available AND non-zero
            src_sgt = None
            dst_sgt = None
            
            if "src_sgt" in flow and pd.notna(flow["src_sgt"]):
                src_sgt_val = int(flow["src_sgt"])
                if src_sgt_val != 0:  # Only use if not zero (zero means unknown/unset)
                    src_sgt = src_sgt_val
            
            if "dst_sgt" in flow and pd.notna(flow["dst_sgt"]):
                dst_sgt_val = int(flow["dst_sgt"])
                if dst_sgt_val != 0:  # Only use if not zero
                    dst_sgt = dst_sgt_val
            
            # PRIORITY 2: If flow doesn't have valid SGTs, resolve from clusters
            if src_sgt is None:
                src_cluster = endpoint_to_cluster.get(src_mac, -1)
                src_sgt = self._cluster_to_sgt.get(src_cluster)
            
            if src_sgt is None:
                skipped += 1
                continue
            
            if dst_sgt is None:
                # Try quick IP→MAC lookup first
                dst_mac = ip_to_mac.get(dst_ip)
                
                if dst_mac and dst_mac in endpoint_to_cluster:
                    cluster = endpoint_to_cluster[dst_mac]
                    dst_sgt = self._cluster_to_sgt.get(cluster)
                
                # If still not found, use the full resolution method
                if dst_sgt is None:
                    dst_sgt = self._resolve_dst_sgt(
                        dst_ip, flow, dataset, endpoint_to_cluster, mac_to_endpoint
                    )
                
                # Last resort: Use SGT 0 (Unknown) - but only if we really can't resolve
                if dst_sgt is None:
                    dst_sgt = 0
                    matrix.add_sgt_name(0, "Unknown")
            
            # Add to matrix cell
            cell = matrix.get_or_create_cell(src_sgt, dst_sgt)
            
            # Parse timestamp
            timestamp = flow["start_time"]
            if hasattr(timestamp, 'to_pydatetime'):
                timestamp = timestamp.to_pydatetime()
            
            # Get service name
            service_name = service_lookup.get(dst_ip)
            
            cell.add_flow(
                port=flow["dst_port"],
                proto=flow["proto"],
                bytes_count=flow["bytes"],
                service_name=service_name,
                timestamp=timestamp,
            )
            
            # Track unique endpoints
            key = (src_sgt, dst_sgt)
            cell_src_endpoints[key].add(src_mac)
            cell_dst_endpoints[key].add(dst_ip)
            
            processed += 1
            matrix.total_flows += 1
            matrix.total_bytes += flow["bytes"]
        
        # Update unique endpoint counts
        for key, endpoints in cell_src_endpoints.items():
            if key in matrix.cells:
                matrix.cells[key].unique_src_endpoints = len(endpoints)
        for key, endpoints in cell_dst_endpoints.items():
            if key in matrix.cells:
                matrix.cells[key].unique_dst_endpoints = len(endpoints)
        
        logger.info(
            f"Built policy matrix: {matrix.n_cells} cells, "
            f"{processed} flows processed, {skipped} skipped"
        )
        
        return matrix
    
    def _resolve_dst_sgt(
        self,
        dst_ip: str,
        flow: pd.Series,
        dataset: ClarionDataset,
        endpoint_to_cluster: Dict[str, int],
        mac_to_endpoint: Dict[str, EndpointSketch],
    ) -> Optional[int]:
        """Resolve destination IP to SGT with improved logic."""
        # Method 1: Check if flow has dst_mac (if available)
        if "dst_mac" in flow and pd.notna(flow.get("dst_mac")):
            dst_mac = flow["dst_mac"]
            if dst_mac in endpoint_to_cluster:
                cluster = endpoint_to_cluster[dst_mac]
                return self._cluster_to_sgt.get(cluster)
        
        # Method 2: Look up by IP in ip_assignments
        ip_match = dataset.ip_assignments[
            dataset.ip_assignments["ip"] == dst_ip
        ]
        
        if not ip_match.empty:
            mac = ip_match.iloc[0]["mac"]
            if mac in endpoint_to_cluster:
                cluster = endpoint_to_cluster[mac]
                sgt = self._cluster_to_sgt.get(cluster)
                if sgt is not None:
                    return sgt
        
        # Method 3: Check if destination IP matches any sketch's known IPs
        # (This requires checking sketches, which we can do via reverse lookup)
        # For now, we'll use a simpler approach: check if it's in our endpoint IPs
        
        # Method 4: Check if it's a known service
        if hasattr(dataset, 'services') and not dataset.services.empty:
            service_match = dataset.services[
                dataset.services["ip"] == dst_ip
            ]
            
            if not service_match.empty:
                # Services get SGT 10 (Servers) by default, but check if we have a better match
                # First check if this service IP is assigned to an endpoint
                service_ip_match = dataset.ip_assignments[
                    dataset.ip_assignments["ip"] == dst_ip
                ]
                if not service_ip_match.empty:
                    mac = service_ip_match.iloc[0]["mac"]
                    if mac in endpoint_to_cluster:
                        cluster = endpoint_to_cluster[mac]
                        sgt = self._cluster_to_sgt.get(cluster)
                        if sgt is not None:
                            return sgt
                # Default to SGT 10 for services
                return 10
        
        # Method 5: Try to find destination by checking all sketches
        # Look for sketches that might have communicated with this IP
        # This is expensive, so we'll do a limited check
        for mac, sketch in list(mac_to_endpoint.items())[:1000]:  # Limit search
            # Check if this endpoint's sketch has this IP as a peer
            # (This would require checking the sketch's peer data, which we don't have direct access to)
            pass
        
        return None
    
    def _build_service_lookup(self, dataset: ClarionDataset) -> Dict[str, str]:
        """Build IP → service name lookup."""
        lookup = {}
        for _, row in dataset.services.iterrows():
            lookup[row["ip"]] = row["service_name"]
        return lookup


def build_policy_matrix(
    dataset: ClarionDataset,
    store: SketchStore,
    cluster_result: ClusterResult,
    taxonomy: SGTTaxonomy,
) -> PolicyMatrix:
    """
    Convenience function to build a policy matrix.
    
    Args:
        dataset: Loaded dataset with flows
        store: SketchStore with enriched sketches
        cluster_result: Cluster assignments
        taxonomy: SGT taxonomy
        
    Returns:
        PolicyMatrix with observed traffic
    """
    builder = PolicyMatrixBuilder(taxonomy)
    return builder.build(dataset, store, cluster_result)

