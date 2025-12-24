"""
NetFlow Ingestion Endpoints

Receives NetFlow/IPFIX data from collectors and stores it.
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from clarion.storage import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


class NetFlowRecord(BaseModel):
    """Single NetFlow record."""
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: int
    bytes: int
    packets: int
    flow_start: int  # Unix timestamp
    flow_end: int
    switch_id: Optional[str] = None


class NetFlowBatch(BaseModel):
    """Batch of NetFlow records."""
    records: List[NetFlowRecord]
    switch_id: Optional[str] = None


@router.post("/netflow")
async def receive_netflow(batch: NetFlowBatch):
    """
    Receive NetFlow records from a collector.
    
    This endpoint accepts NetFlow/IPFIX data from network collectors.
    """
    logger.info(f"Received {len(batch.records)} NetFlow records")
    
    db = get_database()
    stored_count = 0
    
    for record in batch.records:
        db.store_netflow(
            src_ip=record.src_ip,
            dst_ip=record.dst_ip,
            src_port=record.src_port,
            dst_port=record.dst_port,
            protocol=record.protocol,
            bytes=record.bytes,
            packets=record.packets,
            flow_start=record.flow_start,
            flow_end=record.flow_end,
            switch_id=record.switch_id or batch.switch_id,
        )
        stored_count += 1
    
    return {
        "status": "received",
        "records_received": len(batch.records),
        "records_stored": stored_count,
    }


@router.get("/netflow")
async def list_netflow(limit: int = 1000, since: Optional[int] = None):
    """List recent NetFlow records."""
    db = get_database()
    records = db.get_recent_netflow(limit=limit, since=since)
    
    return {
        "count": len(records),
        "records": [
            {
                "src_ip": r['src_ip'],
                "dst_ip": r['dst_ip'],
                "src_port": r['src_port'],
                "dst_port": r['dst_port'],
                "protocol": r['protocol'],
                "bytes": r['bytes'],
                "packets": r['packets'],
                "flow_start": r['flow_start'],
                "switch_id": r['switch_id'],
            }
            for r in records
        ],
    }

