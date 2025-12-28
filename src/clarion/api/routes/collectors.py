"""
Collector Management API Routes

Manages NetFlow/IPFIX collectors including:
- Collector registry and status
- Configuration management
- Metrics and health monitoring
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
import logging
import httpx
from datetime import datetime

from clarion.storage import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Request/Response Models ==========

class CollectorConfig(BaseModel):
    """Collector configuration."""
    collector_id: str
    name: str
    type: str = Field(..., description="native or agent")
    host: str = Field(..., description="Collector host/IP")
    http_port: int = Field(default=8081, description="HTTP port for health/metrics")
    backend_url: str = Field(default="http://localhost:8000", description="Backend API URL")
    netflow_port: Optional[int] = Field(None, description="NetFlow UDP port")
    ipfix_port: Optional[int] = Field(None, description="IPFIX UDP port")
    batch_size: Optional[int] = Field(None, description="Batch size")
    batch_interval_seconds: Optional[float] = Field(None, description="Batch interval")
    enabled: bool = Field(default=True, description="Whether collector is enabled")
    description: Optional[str] = None


class CollectorResponse(BaseModel):
    """Collector response with status."""
    collector_id: str
    name: str
    type: str
    host: str
    http_port: int
    backend_url: str
    netflow_port: Optional[int] = None
    ipfix_port: Optional[int] = None
    batch_size: Optional[int] = None
    batch_interval_seconds: Optional[float] = None
    enabled: bool
    description: Optional[str] = None
    status: str = Field(..., description="online, offline, unknown")
    last_seen: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class CollectorCreate(BaseModel):
    """Request to create a collector."""
    collector_id: str
    name: str
    type: str
    host: str
    http_port: int = 8081
    backend_url: str = "http://localhost:8000"
    netflow_port: Optional[int] = None
    ipfix_port: Optional[int] = None
    batch_size: Optional[int] = None
    batch_interval_seconds: Optional[float] = None
    description: Optional[str] = None


class CollectorUpdate(BaseModel):
    """Request to update a collector."""
    name: Optional[str] = None
    host: Optional[str] = None
    http_port: Optional[int] = None
    backend_url: Optional[str] = None
    netflow_port: Optional[int] = None
    ipfix_port: Optional[int] = None
    batch_size: Optional[int] = None
    batch_interval_seconds: Optional[float] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None


async def _check_collector_health(host: str, http_port: int) -> tuple[str, Optional[Dict]]:
    """Check collector health and return status and metrics."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check health
            health_url = f"http://{host}:{http_port}/health"
            health_response = await client.get(health_url)
            health_response.raise_for_status()
            
            # Get metrics
            metrics_url = f"http://{host}:{http_port}/metrics"
            metrics_response = await client.get(metrics_url)
            if metrics_response.status_code == 200:
                metrics = metrics_response.json()
            else:
                metrics = None
            
            return "online", metrics
    except Exception as e:
        logger.debug(f"Collector {host}:{http_port} health check failed: {e}")
        return "offline", None


@router.get("/collectors", response_model=List[CollectorResponse])
async def list_collectors(
    type: Optional[str] = Query(None, description="Filter by type: native or agent"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
):
    """List all registered collectors."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        query = "SELECT * FROM collectors WHERE 1=1"
        params = []
        
        if type:
            query += " AND type = ?"
            params.append(type)
        
        if enabled is not None:
            query += " AND enabled = ?"
            params.append(1 if enabled else 0)
        
        query += " ORDER BY name"
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        collectors = []
        for row in rows:
            collector = dict(row)
            
            # Check health status
            status, metrics = await _check_collector_health(
                collector["host"],
                collector["http_port"]
            )
            
            collector_response = CollectorResponse(
                collector_id=collector["collector_id"],
                name=collector["name"],
                type=collector["type"],
                host=collector["host"],
                http_port=collector["http_port"],
                backend_url=collector.get("backend_url", "http://localhost:8000"),
                netflow_port=collector.get("netflow_port"),
                ipfix_port=collector.get("ipfix_port"),
                batch_size=collector.get("batch_size"),
                batch_interval_seconds=collector.get("batch_interval_seconds"),
                enabled=bool(collector["enabled"]),
                description=collector.get("description"),
                status=status,
                last_seen=collector.get("last_seen"),
                metrics=metrics,
            )
            collectors.append(collector_response)
        
        return collectors
    except Exception as e:
        logger.error(f"Error listing collectors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collectors/{collector_id}", response_model=CollectorResponse)
async def get_collector(collector_id: str):
    """Get collector details."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute(
            "SELECT * FROM collectors WHERE collector_id = ?",
            (collector_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Collector {collector_id} not found")
        
        collector = dict(row)
        
        # Check health status
        status, metrics = await _check_collector_health(
            collector["host"],
            collector["http_port"]
        )
        
        return CollectorResponse(
            collector_id=collector["collector_id"],
            name=collector["name"],
            type=collector["type"],
            host=collector["host"],
            http_port=collector["http_port"],
            backend_url=collector.get("backend_url", "http://localhost:8000"),
            netflow_port=collector.get("netflow_port"),
            ipfix_port=collector.get("ipfix_port"),
            batch_size=collector.get("batch_size"),
            batch_interval_seconds=collector.get("batch_interval_seconds"),
            enabled=bool(collector["enabled"]),
            description=collector.get("description"),
            status=status,
            last_seen=collector.get("last_seen"),
            metrics=metrics,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collector {collector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collectors", response_model=CollectorResponse)
async def create_collector(collector: CollectorCreate):
    """Register a new collector."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Check if collector already exists
        cursor = conn.execute(
            "SELECT collector_id FROM collectors WHERE collector_id = ?",
            (collector.collector_id,)
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail=f"Collector {collector.collector_id} already exists"
            )
        
        # Insert collector
        conn.execute("""
            INSERT INTO collectors (
                collector_id, name, type, host, http_port, backend_url,
                netflow_port, ipfix_port, batch_size, batch_interval_seconds,
                enabled, description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            collector.collector_id,
            collector.name,
            collector.type,
            collector.host,
            collector.http_port,
            collector.backend_url,
            collector.netflow_port,
            collector.ipfix_port,
            collector.batch_size,
            collector.batch_interval_seconds,
            1,  # enabled
            collector.description,
        ))
        conn.commit()
        
        # Return created collector
        return await get_collector(collector.collector_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating collector: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/collectors/{collector_id}", response_model=CollectorResponse)
async def update_collector(collector_id: str, update: CollectorUpdate):
    """Update collector configuration."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Verify collector exists
        cursor = conn.execute(
            "SELECT collector_id FROM collectors WHERE collector_id = ?",
            (collector_id,)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Collector {collector_id} not found")
        
        # Build update query
        updates = []
        params = []
        
        if update.name is not None:
            updates.append("name = ?")
            params.append(update.name)
        if update.host is not None:
            updates.append("host = ?")
            params.append(update.host)
        if update.http_port is not None:
            updates.append("http_port = ?")
            params.append(update.http_port)
        if update.backend_url is not None:
            updates.append("backend_url = ?")
            params.append(update.backend_url)
        if update.netflow_port is not None:
            updates.append("netflow_port = ?")
            params.append(update.netflow_port)
        if update.ipfix_port is not None:
            updates.append("ipfix_port = ?")
            params.append(update.ipfix_port)
        if update.batch_size is not None:
            updates.append("batch_size = ?")
            params.append(update.batch_size)
        if update.batch_interval_seconds is not None:
            updates.append("batch_interval_seconds = ?")
            params.append(update.batch_interval_seconds)
        if update.enabled is not None:
            updates.append("enabled = ?")
            params.append(update.enabled)
        if update.description is not None:
            updates.append("description = ?")
            params.append(update.description)
        
        if not updates:
            # No updates provided
            return await get_collector(collector_id)
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(collector_id)
        
        query = f"UPDATE collectors SET {', '.join(updates)} WHERE collector_id = ?"
        conn.execute(query, params)
        conn.commit()
        
        return await get_collector(collector_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating collector {collector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collectors/{collector_id}")
async def delete_collector(collector_id: str):
    """Delete a collector registration."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute(
            "SELECT collector_id FROM collectors WHERE collector_id = ?",
            (collector_id,)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Collector {collector_id} not found")
        
        conn.execute("DELETE FROM collectors WHERE collector_id = ?", (collector_id,))
        conn.commit()
        
        return {"status": "deleted", "collector_id": collector_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting collector {collector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collectors/{collector_id}/metrics")
async def get_collector_metrics(collector_id: str):
    """Get collector metrics (proxied from collector)."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute(
            "SELECT host, http_port FROM collectors WHERE collector_id = ?",
            (collector_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Collector {collector_id} not found")
        
        collector = dict(row)
        metrics_url = f"http://{collector['host']}:{collector['http_port']}/metrics"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(metrics_url)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Collector unreachable: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics for collector {collector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collectors/{collector_id}/health")
async def get_collector_health(collector_id: str):
    """Get collector health status (proxied from collector)."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute(
            "SELECT host, http_port FROM collectors WHERE collector_id = ?",
            (collector_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Collector {collector_id} not found")
        
        collector = dict(row)
        health_url = f"http://{collector['host']}:{collector['http_port']}/health"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(health_url)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Collector unreachable: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting health for collector {collector_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

