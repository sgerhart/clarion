"""
Data Loader for Clarion synthetic and production datasets.

This module loads CSV/Parquet data into pandas DataFrames with proper
typing and validation. It's used for both development (synthetic data)
and production (live data from connectors).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
import logging

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ClarionDataset:
    """
    Container for all loaded Clarion data tables.
    
    Attributes:
        flows: Network flow records
        endpoints: Device/endpoint inventory
        ise_sessions: ISE session directory
        ip_assignments: IP/MAC bindings (DHCP/static)
        ad_users: Active Directory users
        ad_groups: Active Directory groups
        ad_group_membership: User→Group mappings
        services: Service catalog
        switches: Switch inventory
        interfaces: Switch interface inventory
        trustsec_sgts: SGT catalog
        flow_truth: Ground truth for validation
    """
    flows: pd.DataFrame
    endpoints: pd.DataFrame
    ise_sessions: pd.DataFrame
    ip_assignments: pd.DataFrame
    ad_users: pd.DataFrame
    ad_groups: pd.DataFrame
    ad_group_membership: pd.DataFrame
    services: pd.DataFrame
    switches: pd.DataFrame
    interfaces: pd.DataFrame
    trustsec_sgts: pd.DataFrame
    flow_truth: Optional[pd.DataFrame] = None
    
    def summary(self) -> Dict[str, int]:
        """Return record counts for each table."""
        return {
            "flows": len(self.flows),
            "endpoints": len(self.endpoints),
            "ise_sessions": len(self.ise_sessions),
            "ip_assignments": len(self.ip_assignments),
            "ad_users": len(self.ad_users),
            "ad_groups": len(self.ad_groups),
            "ad_group_membership": len(self.ad_group_membership),
            "services": len(self.services),
            "switches": len(self.switches),
            "interfaces": len(self.interfaces),
            "trustsec_sgts": len(self.trustsec_sgts),
            "flow_truth": len(self.flow_truth) if self.flow_truth is not None else 0,
        }
    
    def __repr__(self) -> str:
        summary = self.summary()
        total = sum(summary.values())
        return f"ClarionDataset({total:,} total records across {len(summary)} tables)"


class DataLoader:
    """
    Loader for Clarion datasets.
    
    Handles loading CSV files with proper types and parsing.
    
    Example:
        >>> loader = DataLoader()
        >>> dataset = loader.load_synthetic("data/raw/trustsec_copilot_synth_campus")
        >>> print(dataset.summary())
    """
    
    # Column type specifications for each table
    FLOW_DTYPES = {
        "flow_id": str,
        "src_ip": str,
        "dst_ip": str,
        "src_port": int,
        "dst_port": int,
        "proto": str,
        "bytes": int,
        "packets": int,
        "vlan": int,
        "exporter_switch_id": str,
        "ingress_interface": str,
        "src_mac": str,
        "dst_sgt": int,
        "src_sgt": int,
    }
    
    ENDPOINT_DTYPES = {
        "device_id": str,
        "device_type": str,
        "os": str,
        "mac": str,
        "hostname": str,
        "owner_user_id": str,
        "attached_switch_id": str,
        "attached_interface": str,
        "vlan": int,
    }
    
    ISE_SESSION_DTYPES = {
        "session_id": str,
        "mac": str,
        "ip": str,
        "device_id": str,
        "username": str,
        "auth_method": str,
        "endpoint_profile": str,
        "location": str,
        "vlan": int,
        "sgt": int,
    }
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize the data loader.
        
        Args:
            base_path: Optional base path for data files.
                      If not provided, uses current working directory.
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
    
    def load_synthetic(
        self, 
        data_dir: str | Path,
        load_flow_truth: bool = True,
    ) -> ClarionDataset:
        """
        Load the synthetic campus dataset.
        
        Args:
            data_dir: Path to the synthetic data directory
                     (e.g., "data/raw/trustsec_copilot_synth_campus")
            load_flow_truth: Whether to load the ground truth file
            
        Returns:
            ClarionDataset with all tables loaded
        """
        data_path = Path(data_dir)
        if not data_path.is_absolute():
            data_path = self.base_path / data_path
        
        logger.info(f"Loading synthetic dataset from {data_path}")
        
        # Load all tables
        flows = self._load_flows(data_path / "flows.csv")
        endpoints = self._load_endpoints(data_path / "endpoints.csv")
        ise_sessions = self._load_ise_sessions(data_path / "ise_sessions.csv")
        ip_assignments = self._load_ip_assignments(data_path / "ip_assignments.csv")
        ad_users = self._load_ad_users(data_path / "ad_users.csv")
        ad_groups = self._load_ad_groups(data_path / "ad_groups.csv")
        ad_group_membership = self._load_ad_group_membership(
            data_path / "ad_group_membership.csv"
        )
        services = self._load_services(data_path / "services.csv")
        switches = self._load_csv(data_path / "switches.csv")
        interfaces = self._load_csv(data_path / "interfaces.csv")
        trustsec_sgts = self._load_csv(data_path / "trustsec_sgts.csv")
        
        flow_truth = None
        if load_flow_truth:
            truth_path = data_path / "flow_truth.csv"
            if truth_path.exists():
                flow_truth = self._load_csv(truth_path)
        
        dataset = ClarionDataset(
            flows=flows,
            endpoints=endpoints,
            ise_sessions=ise_sessions,
            ip_assignments=ip_assignments,
            ad_users=ad_users,
            ad_groups=ad_groups,
            ad_group_membership=ad_group_membership,
            services=services,
            switches=switches,
            interfaces=interfaces,
            trustsec_sgts=trustsec_sgts,
            flow_truth=flow_truth,
        )
        
        logger.info(f"Loaded {dataset}")
        return dataset
    
    def _load_csv(self, path: Path) -> pd.DataFrame:
        """Load a CSV file with basic settings."""
        logger.debug(f"Loading {path}")
        return pd.read_csv(path)
    
    def _load_flows(self, path: Path) -> pd.DataFrame:
        """Load flow records with proper types and datetime parsing."""
        df = pd.read_csv(path)
        
        # Parse datetime columns (mixed formats in data)
        df["start_time"] = pd.to_datetime(df["start_time"], format="mixed", utc=True)
        df["end_time"] = pd.to_datetime(df["end_time"], format="mixed", utc=True)
        
        # Sort by start time for streaming simulation
        df = df.sort_values("start_time").reset_index(drop=True)
        
        logger.info(f"Loaded {len(df):,} flows from {path}")
        return df
    
    def _load_endpoints(self, path: Path) -> pd.DataFrame:
        """Load endpoint inventory."""
        df = pd.read_csv(path, dtype=self.ENDPOINT_DTYPES)
        logger.info(f"Loaded {len(df):,} endpoints from {path}")
        return df
    
    def _load_ise_sessions(self, path: Path) -> pd.DataFrame:
        """Load ISE session data with datetime parsing."""
        df = pd.read_csv(path)
        
        # Parse datetime columns (mixed formats in data)
        df["session_start"] = pd.to_datetime(df["session_start"], format="mixed", utc=True)
        df["session_end"] = pd.to_datetime(df["session_end"], format="mixed", utc=True)
        
        logger.info(f"Loaded {len(df):,} ISE sessions from {path}")
        return df
    
    def _load_ip_assignments(self, path: Path) -> pd.DataFrame:
        """Load IP assignment data with datetime parsing."""
        df = pd.read_csv(path)
        
        # Parse datetime columns (mixed formats in data)
        df["lease_start"] = pd.to_datetime(df["lease_start"], format="mixed", utc=True)
        df["lease_end"] = pd.to_datetime(df["lease_end"], format="mixed", utc=True)
        
        logger.info(f"Loaded {len(df):,} IP assignments from {path}")
        return df
    
    def _load_ad_users(self, path: Path) -> pd.DataFrame:
        """Load AD user data."""
        df = pd.read_csv(path)
        logger.info(f"Loaded {len(df):,} AD users from {path}")
        return df
    
    def _load_ad_groups(self, path: Path) -> pd.DataFrame:
        """Load AD group data."""
        df = pd.read_csv(path)
        logger.info(f"Loaded {len(df):,} AD groups from {path}")
        return df
    
    def _load_ad_group_membership(self, path: Path) -> pd.DataFrame:
        """Load AD group membership data."""
        df = pd.read_csv(path)
        logger.info(f"Loaded {len(df):,} AD group memberships from {path}")
        return df
    
    def _load_services(self, path: Path) -> pd.DataFrame:
        """Load service catalog."""
        df = pd.read_csv(path)
        
        # Parse the ports column (comma-separated string to list)
        df["ports_list"] = df["ports"].apply(
            lambda x: [int(p.strip()) for p in str(x).split(",")]
        )
        
        logger.info(f"Loaded {len(df):,} services from {path}")
        return df


def load_dataset(data_dir: str | Path) -> ClarionDataset:
    """
    Convenience function to load a dataset.
    
    Args:
        data_dir: Path to the data directory
        
    Returns:
        Loaded ClarionDataset
        
    Example:
        >>> dataset = load_dataset("data/raw/trustsec_copilot_synth_campus")
    """
    loader = DataLoader()
    return loader.load_synthetic(data_dir)
