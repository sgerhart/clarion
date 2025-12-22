"""
Clarion Configuration Management

Centralized configuration for paths, defaults, and settings.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import os


# Project root (where this file lives: src/clarion/config.py -> project root is 3 levels up)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SYNTH_CAMPUS_DIR = RAW_DATA_DIR / "trustsec_copilot_synth_campus"


@dataclass
class DataFiles:
    """Paths to synthetic campus data files."""
    
    switches: Path = field(default_factory=lambda: SYNTH_CAMPUS_DIR / "switches.csv")
    interfaces: Path = field(default_factory=lambda: SYNTH_CAMPUS_DIR / "interfaces.csv")
    ad_users: Path = field(default_factory=lambda: SYNTH_CAMPUS_DIR / "ad_users.csv")
    ad_groups: Path = field(default_factory=lambda: SYNTH_CAMPUS_DIR / "ad_groups.csv")
    ad_group_membership: Path = field(default_factory=lambda: SYNTH_CAMPUS_DIR / "ad_group_membership.csv")
    endpoints: Path = field(default_factory=lambda: SYNTH_CAMPUS_DIR / "endpoints.csv")
    ip_assignments: Path = field(default_factory=lambda: SYNTH_CAMPUS_DIR / "ip_assignments.csv")
    ise_sessions: Path = field(default_factory=lambda: SYNTH_CAMPUS_DIR / "ise_sessions.csv")
    services: Path = field(default_factory=lambda: SYNTH_CAMPUS_DIR / "services.csv")
    sgts: Path = field(default_factory=lambda: SYNTH_CAMPUS_DIR / "trustsec_sgts.csv")
    flows: Path = field(default_factory=lambda: SYNTH_CAMPUS_DIR / "flows.csv")
    flow_truth: Path = field(default_factory=lambda: SYNTH_CAMPUS_DIR / "flow_truth.csv")
    
    def validate(self) -> list[str]:
        """Check that all data files exist. Returns list of missing files."""
        missing = []
        for field_name in self.__dataclass_fields__:
            path = getattr(self, field_name)
            if not path.exists():
                missing.append(str(path))
        return missing


@dataclass
class ClarionConfig:
    """Main configuration for Clarion."""
    
    # Data settings
    data_files: DataFiles = field(default_factory=DataFiles)
    
    # Analysis settings
    flow_time_bucket_seconds: int = 300  # 5-minute buckets
    min_flow_count_for_edge: int = 1     # Minimum flows to create an edge
    identity_ttl_hours: int = 24         # How long identity bindings are valid
    
    # SGT recommendation settings
    min_sgt_count: int = 6               # Minimum SGTs to recommend
    max_sgt_count: int = 15              # Maximum SGTs to recommend
    
    # Server detection ports
    server_ports: set[int] = field(default_factory=lambda: {
        22, 53, 80, 88, 389, 443, 445, 464, 636,
        1433, 1521, 2049, 3128, 3306, 3389, 5432,
        8080, 8443, 9100
    })
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    @classmethod
    def from_env(cls) -> "ClarionConfig":
        """Create config from environment variables."""
        config = cls()
        
        # Override with env vars if present
        if data_dir := os.environ.get("CLARION_DATA_DIR"):
            synth_dir = Path(data_dir) / "trustsec_copilot_synth_campus"
            config.data_files = DataFiles(
                switches=synth_dir / "switches.csv",
                interfaces=synth_dir / "interfaces.csv",
                ad_users=synth_dir / "ad_users.csv",
                ad_groups=synth_dir / "ad_groups.csv",
                ad_group_membership=synth_dir / "ad_group_membership.csv",
                endpoints=synth_dir / "endpoints.csv",
                ip_assignments=synth_dir / "ip_assignments.csv",
                ise_sessions=synth_dir / "ise_sessions.csv",
                services=synth_dir / "services.csv",
                sgts=synth_dir / "trustsec_sgts.csv",
                flows=synth_dir / "flows.csv",
                flow_truth=synth_dir / "flow_truth.csv",
            )
        
        if api_port := os.environ.get("CLARION_API_PORT"):
            config.api_port = int(api_port)
            
        return config


# Default config instance
config = ClarionConfig()

