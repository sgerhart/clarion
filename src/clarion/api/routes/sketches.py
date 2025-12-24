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


from clarion.storage import get_database


@router.post("/sketches")
async def receive_sketches(batch: SketchBatch):
    """
    Receive sketches from an edge device.
    
    This endpoint accepts sketches from edge containers running on switches.
    """
    logger.info(
        f"Received {batch.sketch_count} sketches from switch {batch.switch_id}"
    )
    
    db = get_database()
    stored_count = 0
    
    # Store each sketch in database
    for sketch in batch.sketches:
        db.store_sketch(
            endpoint_id=sketch.endpoint_id,
            switch_id=sketch.switch_id,
            unique_peers=sketch.unique_peers,
            unique_ports=sketch.unique_ports,
            bytes_in=sketch.bytes_in,
            bytes_out=sketch.bytes_out,
            flow_count=sketch.flow_count,
            first_seen=sketch.first_seen,
            last_seen=sketch.last_seen,
            active_hours=sketch.active_hours,
            local_cluster_id=sketch.local_cluster_id,
        )
        stored_count += 1
    
    # Get total sketches for this switch
    all_sketches = db.list_sketches(switch_id=batch.switch_id)
    
    return {
        "status": "received",
        "switch_id": batch.switch_id,
        "sketches_received": batch.sketch_count,
        "sketches_stored": stored_count,
        "total_sketches": len(all_sketches),
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
async def list_sketches(switch_id: Optional[str] = None, limit: int = 100):
    """List all stored sketches."""
    db = get_database()
    sketches = db.list_sketches(switch_id=switch_id, limit=limit)
    
    # Get unique switches
    all_sketches = db.list_sketches(limit=10000)  # Get enough to find switches
    switches = list(set(s['switch_id'] for s in all_sketches))
    
    return {
        "count": len(sketches),
        "switches": switches,
        "sketches": [
            {
                "endpoint_id": s['endpoint_id'],
                "switch_id": s['switch_id'],
                "flow_count": s['flow_count'],
                "unique_peers": s['unique_peers'],
                "last_seen": s['last_seen'],
            }
            for s in sketches
        ],
    }


@router.get("/sketches/stats")
async def sketch_stats():
    """Get statistics about stored sketches."""
    db = get_database()
    stats = db.get_sketch_stats()
    
    # Get per-switch counts
    all_sketches = db.list_sketches(limit=100000)
    switches_detail = {}
    for s in all_sketches:
        switch_id = s['switch_id']
        switches_detail[switch_id] = switches_detail.get(switch_id, 0) + 1
    
    return {
        "total_sketches": stats.get('total_sketches', 0),
        "total_flows": stats.get('total_flows', 0),
        "switches": stats.get('total_switches', 0),
        "unique_endpoints": stats.get('unique_endpoints', 0),
        "switches_detail": switches_detail,
    }

