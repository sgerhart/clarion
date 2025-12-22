"""
Data Loader Module

Load synthetic campus data from CSV files into pandas DataFrames.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from clarion.config import config, DataFiles


@dataclass
class CampusData:
    """Container for all loaded campus data."""
    
    switches: pd.DataFrame
    interfaces: pd.DataFrame
    ad_users: pd.DataFrame
    ad_groups: pd.DataFrame
    ad_group_membership: pd.DataFrame
    endpoints: pd.DataFrame
    ip_assignments: pd.DataFrame
    ise_sessions: pd.DataFrame
    services: pd.DataFrame
    sgts: pd.DataFrame
    flows: pd.DataFrame
    flow_truth: Optional[pd.DataFrame] = None
    
    def summary(self) -> dict:
        """Return summary statistics for all loaded data."""
        return {
            "switches": len(self.switches),
            "interfaces": len(self.interfaces),
            "ad_users": len(self.ad_users),
            "ad_groups": len(self.ad_groups),
            "ad_group_membership": len(self.ad_group_membership),
            "endpoints": len(self.endpoints),
            "ip_assignments": len(self.ip_assignments),
            "ise_sessions": len(self.ise_sessions),
            "services": len(self.services),
            "sgts": len(self.sgts),
            "flows": len(self.flows),
            "flow_truth": len(self.flow_truth) if self.flow_truth is not None else 0,
        }


def load_csv(path: Path, parse_dates: Optional[list[str]] = None) -> pd.DataFrame:
    """Load a CSV file with optional date parsing."""
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    
    return pd.read_csv(path, parse_dates=parse_dates)


def load_switches(data_files: Optional[DataFiles] = None) -> pd.DataFrame:
    """Load switch inventory."""
    files = data_files or config.data_files
    return load_csv(files.switches)


def load_interfaces(data_files: Optional[DataFiles] = None) -> pd.DataFrame:
    """Load interface inventory."""
    files = data_files or config.data_files
    return load_csv(files.interfaces)


def load_ad_users(data_files: Optional[DataFiles] = None) -> pd.DataFrame:
    """Load Active Directory users."""
    files = data_files or config.data_files
    return load_csv(files.ad_users)


def load_ad_groups(data_files: Optional[DataFiles] = None) -> pd.DataFrame:
    """Load Active Directory groups."""
    files = data_files or config.data_files
    return load_csv(files.ad_groups)


def load_ad_group_membership(data_files: Optional[DataFiles] = None) -> pd.DataFrame:
    """Load AD group membership mappings."""
    files = data_files or config.data_files
    return load_csv(files.ad_group_membership)


def load_endpoints(data_files: Optional[DataFiles] = None) -> pd.DataFrame:
    """Load endpoint inventory."""
    files = data_files or config.data_files
    return load_csv(files.endpoints)


def load_ip_assignments(data_files: Optional[DataFiles] = None) -> pd.DataFrame:
    """Load IP/MAC assignments with lease times."""
    files = data_files or config.data_files
    return load_csv(files.ip_assignments, parse_dates=["lease_start", "lease_end"])


def load_ise_sessions(data_files: Optional[DataFiles] = None) -> pd.DataFrame:
    """Load ISE session directory data."""
    files = data_files or config.data_files
    return load_csv(files.ise_sessions, parse_dates=["session_start", "session_end"])


def load_services(data_files: Optional[DataFiles] = None) -> pd.DataFrame:
    """Load service catalog."""
    files = data_files or config.data_files
    return load_csv(files.services)


def load_sgts(data_files: Optional[DataFiles] = None) -> pd.DataFrame:
    """Load SGT taxonomy."""
    files = data_files or config.data_files
    return load_csv(files.sgts)


def load_flows(data_files: Optional[DataFiles] = None) -> pd.DataFrame:
    """Load flow records."""
    files = data_files or config.data_files
    return load_csv(files.flows, parse_dates=["start_time", "end_time"])


def load_flow_truth(data_files: Optional[DataFiles] = None) -> pd.DataFrame:
    """Load flow ground truth (for validation)."""
    files = data_files or config.data_files
    return load_csv(files.flow_truth)


def load_all(data_files: Optional[DataFiles] = None, 
             include_flow_truth: bool = False) -> CampusData:
    """
    Load all campus data files.
    
    Args:
        data_files: Optional custom data file paths
        include_flow_truth: Whether to load flow_truth (validation data)
    
    Returns:
        CampusData container with all loaded DataFrames
    """
    files = data_files or config.data_files
    
    # Validate that files exist
    missing = files.validate()
    if missing:
        raise FileNotFoundError(f"Missing data files: {missing}")
    
    return CampusData(
        switches=load_switches(files),
        interfaces=load_interfaces(files),
        ad_users=load_ad_users(files),
        ad_groups=load_ad_groups(files),
        ad_group_membership=load_ad_group_membership(files),
        endpoints=load_endpoints(files),
        ip_assignments=load_ip_assignments(files),
        ise_sessions=load_ise_sessions(files),
        services=load_services(files),
        sgts=load_sgts(files),
        flows=load_flows(files),
        flow_truth=load_flow_truth(files) if include_flow_truth else None,
    )

