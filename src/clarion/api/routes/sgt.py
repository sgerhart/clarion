"""
SGT Lifecycle Management API Routes

Manages Security Group Tags (SGTs) including:
- SGT registry (create, read, update, list)
- SGT membership (assign, unassign, list)
- Assignment history
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from clarion.clustering import SGTLifecycleManager
from clarion.storage import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Request/Response Models ==========

class SGTCreate(BaseModel):
    """Request model for creating an SGT."""
    sgt_value: int = Field(..., ge=0, le=65535, description="SGT numeric value")
    sgt_name: str = Field(..., min_length=1, description="Human-readable SGT name")
    category: Optional[str] = Field(None, description="Category: users, servers, devices, special")
    description: Optional[str] = None


class SGTUpdate(BaseModel):
    """Request model for updating an SGT."""
    sgt_name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SGTResponse(BaseModel):
    """SGT registry response."""
    sgt_value: int
    sgt_name: str
    category: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_active: Optional[int] = None


class SGTAssignmentRequest(BaseModel):
    """Request model for assigning an endpoint to an SGT."""
    endpoint_id: str
    sgt_value: int
    assigned_by: str = "manual"
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    cluster_id: Optional[int] = None


class SGTAssignmentResponse(BaseModel):
    """SGT assignment response."""
    endpoint_id: str
    sgt_value: int
    assigned_at: Optional[str] = None
    assigned_by: Optional[str] = None
    confidence: Optional[float] = None
    cluster_id: Optional[int] = None


class SGTBulkAssignmentRequest(BaseModel):
    """Request model for bulk SGT assignments."""
    assignments: List[Dict[str, Any]]
    assigned_by: str = "clustering"


# ========== SGT Registry Endpoints ==========

@router.get("/sgts", response_model=List[SGTResponse])
async def list_sgts(
    active_only: bool = Query(True, description="Only return active SGTs"),
):
    """List all SGTs in the registry."""
    try:
        manager = SGTLifecycleManager()
        sgts = manager.list_sgts(active_only=active_only)
        return sgts
    except Exception as e:
        logger.error(f"Error listing SGTs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sgts/{sgt_value}", response_model=SGTResponse)
async def get_sgt(sgt_value: int):
    """Get details for a specific SGT."""
    try:
        manager = SGTLifecycleManager()
        sgt = manager.get_sgt(sgt_value)
        
        if not sgt:
            raise HTTPException(status_code=404, detail=f"SGT {sgt_value} not found")
        
        return sgt
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting SGT {sgt_value}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sgts", response_model=SGTResponse)
async def create_sgt(sgt: SGTCreate):
    """Create a new SGT in the registry."""
    try:
        manager = SGTLifecycleManager()
        created = manager.create_sgt(
            sgt_value=sgt.sgt_value,
            sgt_name=sgt.sgt_name,
            category=sgt.category,
            description=sgt.description,
        )
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating SGT: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sgts/{sgt_value}", response_model=SGTResponse)
async def update_sgt(sgt_value: int, update: SGTUpdate):
    """Update an SGT in the registry."""
    try:
        manager = SGTLifecycleManager()
        updated = manager.update_sgt(
            sgt_value=sgt_value,
            sgt_name=update.sgt_name,
            category=update.category,
            description=update.description,
            is_active=update.is_active,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating SGT {sgt_value}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sgts/{sgt_value}")
async def deactivate_sgt(sgt_value: int):
    """Deactivate an SGT (soft delete)."""
    try:
        manager = SGTLifecycleManager()
        manager.deactivate_sgt(sgt_value)
        return {"status": "deactivated", "sgt_value": sgt_value}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deactivating SGT {sgt_value}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========== SGT Membership Endpoints ==========

@router.post("/sgts/{sgt_value}/members", response_model=SGTAssignmentResponse)
async def assign_endpoint_to_sgt(
    sgt_value: int,
    assignment: SGTAssignmentRequest,
):
    """Assign an endpoint to an SGT."""
    try:
        manager = SGTLifecycleManager()
        result = manager.assign_endpoint(
            endpoint_id=assignment.endpoint_id,
            sgt_value=sgt_value,
            assigned_by=assignment.assigned_by,
            confidence=assignment.confidence,
            cluster_id=assignment.cluster_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error assigning endpoint to SGT: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sgts/{sgt_value}/members", response_model=List[SGTAssignmentResponse])
async def list_sgt_members(sgt_value: int):
    """List all endpoints assigned to an SGT."""
    try:
        manager = SGTLifecycleManager()
        members = manager.list_endpoints_by_sgt(sgt_value)
        return members
    except Exception as e:
        logger.error(f"Error listing SGT members: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sgts/{sgt_value}/members/{endpoint_id}")
async def unassign_endpoint_from_sgt(sgt_value: int, endpoint_id: str):
    """Unassign an endpoint from an SGT."""
    try:
        manager = SGTLifecycleManager()
        # Verify the endpoint is actually assigned to this SGT
        current = manager.get_endpoint_sgt(endpoint_id)
        if not current:
            raise HTTPException(status_code=404, detail=f"Endpoint {endpoint_id} has no SGT assignment")
        if current['sgt_value'] != sgt_value:
            raise HTTPException(
                status_code=400,
                detail=f"Endpoint {endpoint_id} is assigned to SGT {current['sgt_value']}, not {sgt_value}"
            )
        
        manager.unassign_endpoint(endpoint_id)
        return {"status": "unassigned", "endpoint_id": endpoint_id, "sgt_value": sgt_value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unassigning endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sgts/membership/{endpoint_id}", response_model=SGTAssignmentResponse)
async def get_endpoint_sgt(endpoint_id: str):
    """Get the current SGT assignment for an endpoint."""
    try:
        manager = SGTLifecycleManager()
        assignment = manager.get_endpoint_sgt(endpoint_id)
        
        if not assignment:
            raise HTTPException(status_code=404, detail=f"Endpoint {endpoint_id} has no SGT assignment")
        
        return assignment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting endpoint SGT: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sgts/{sgt_value}/history/{endpoint_id}", response_model=List[Dict[str, Any]])
async def get_endpoint_assignment_history(sgt_value: int, endpoint_id: str):
    """Get assignment history for an endpoint and SGT."""
    try:
        manager = SGTLifecycleManager()
        history = manager.get_assignment_history(endpoint_id)
        
        # Filter to this SGT
        sgt_history = [h for h in history if h['sgt_value'] == sgt_value]
        return sgt_history
    except Exception as e:
        logger.error(f"Error getting assignment history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sgts/bulk-assign")
async def bulk_assign_endpoints(request: SGTBulkAssignmentRequest):
    """Assign multiple endpoints to SGTs in bulk."""
    try:
        manager = SGTLifecycleManager()
        result = manager.assign_endpoints_bulk(
            assignments=request.assignments,
            assigned_by=request.assigned_by,
        )
        return result
    except Exception as e:
        logger.error(f"Error in bulk assignment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sgts/{sgt_value}/summary", response_model=Dict[str, Any])
async def get_sgt_summary(sgt_value: int):
    """Get comprehensive summary for an SGT."""
    try:
        manager = SGTLifecycleManager()
        summary = manager.get_sgt_summary(sgt_value)
        
        if not summary:
            raise HTTPException(status_code=404, detail=f"SGT {sgt_value} not found")
        
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting SGT summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

