"""
API Routes

All route modules for the FastAPI application.
"""

from clarion.api.routes import (
    health,
    sketches,
    netflow,
    clustering,
    policy,
    visualization,
    export,
    devices,
    groups,
    topology,
    collectors,
    sgt,
    policy_recommendations,
    users,
    user_sgt,
    ise_config,
    pxgrid,
    connectors,
    certificates,
)

__all__ = [
    "health",
    "sketches",
    "netflow",
    "clustering",
    "policy",
    "visualization",
    "export",
    "devices",
    "groups",
    "topology",
    "collectors",
    "sgt",
    "policy_recommendations",
    "users",
    "user_sgt",
    "ise_config",
    "pxgrid",
    "connectors",
    "certificates",
]

