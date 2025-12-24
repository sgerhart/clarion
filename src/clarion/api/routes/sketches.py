"""
Edge Sketch Ingestion Endpoints

Receives sketches from edge devices and stores them for processing.
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class EdgeSketchData(BaseModel):
    """Edge sketch data model."""
    endpoint_id: str
    switch_id: str
    unique_peers: int
    unique_ports: int
    bytes_in: int
    bytes_out: int
    flow_count: int
    first_seen: int
    last_seen: int
    active_hours: int
    local_cluster_id: int = -1


class SketchBatch(BaseModel):
    """Batch of sketches from an edge device."""
    switch_id: str
    timestamp: int
    sketch_count: int
    sketches: List[EdgeSketchData]


# In-memory storage (replace with database in production)
_sketch_storage: Dict[str, List[EdgeSketchData]] = {}


@router.post("/sketches")
async def receive_sketches(batch: SketchBatch):
    """
    Receive sketches from an edge device.
    
    This endpoint accepts sketches from edge containers running on switches.
    """
    logger.info(
        f"Received {batch.sketch_count} sketches from switch {batch.switch_id}"
    )
    
    # Store sketches (grouped by switch)
    if batch.switch_id not in _sketch_storage:
        _sketch_storage[batch.switch_id] = []
    
    _sketch_storage[batch.switch_id].extend(batch.sketches)
    
    # Keep only recent sketches (last 24 hours)
    cutoff_time = batch.timestamp - (24 * 3600)
    _sketch_storage[batch.switch_id] = [
        s for s in _sketch_storage[batch.switch_id]
        if s.last_seen >= cutoff_time
    ]
    
    return {
        "status": "received",
        "switch_id": batch.switch_id,
        "sketches_received": batch.sketch_count,
        "total_sketches": len(_sketch_storage[batch.switch_id]),
    }


@router.post("/sketches/binary")
async def receive_sketches_binary(
    content: bytes = Body(...),
    x_switch_id: Optional[str] = None,
    x_sketch_count: Optional[str] = None,
):
    """
    Receive binary-encoded sketches.
    
    More efficient than JSON for large batches.
    """
    # TODO: Implement binary deserialization
    # For now, return success
    return {
        "status": "received",
        "format": "binary",
        "size_bytes": len(content),
    }


@router.get("/sketches")
async def list_sketches(switch_id: Optional[str] = None):
    """List all stored sketches."""
    if switch_id:
        sketches = _sketch_storage.get(switch_id, [])
    else:
        # All sketches from all switches
        sketches = []
        for switch_sketches in _sketch_storage.values():
            sketches.extend(switch_sketches)
    
    return {
        "count": len(sketches),
        "switches": list(_sketch_storage.keys()),
        "sketches": [
            {
                "endpoint_id": s.endpoint_id,
                "switch_id": s.switch_id,
                "flow_count": s.flow_count,
                "unique_peers": s.unique_peers,
            }
            for s in sketches[:100]  # Limit response size
        ],
    }


@router.get("/sketches/stats")
async def sketch_stats():
    """Get statistics about stored sketches."""
    total_sketches = sum(len(s) for s in _sketch_storage.values())
    total_flows = sum(
        s.flow_count
        for sketches in _sketch_storage.values()
        for s in sketches
    )
    
    return {
        "total_sketches": total_sketches,
        "total_flows": total_flows,
        "switches": len(_sketch_storage),
        "switches_detail": {
            switch_id: len(sketches)
            for switch_id, sketches in _sketch_storage.items()
        },
    }

