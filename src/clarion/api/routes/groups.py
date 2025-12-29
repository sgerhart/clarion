"""
Groups/Clusters Management Endpoints

Endpoints for managing device groups (clusters) including assignments, SGTs, and labels.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from clarion.storage import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


class GroupResponse(BaseModel):
    """Group/Cluster response model."""
    cluster_id: int
    cluster_label: Optional[str] = None
    sgt_value: Optional[int] = None
    sgt_name: Optional[str] = None
    endpoint_count: int = 0
    explanation: Optional[str] = None
    primary_reason: Optional[str] = None
    confidence: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class GroupUpdateRequest(BaseModel):
    """
    Request model for updating group metadata.
    
    Note: sgt_value and sgt_name are deprecated. SGTs are assigned by Cisco ISE 
    authorization policies, not directly. To change SGT assignments, use the policy 
    recommendation feature to generate ISE authorization policies.
    """
    cluster_label: Optional[str] = None
    sgt_value: Optional[int] = Field(
        None,
        description="⚠️ DEPRECATED: SGTs are managed by ISE authorization policies. "
                   "This parameter is ignored. Use policy recommendations to change SGT assignments."
    )
    sgt_name: Optional[str] = Field(
        None,
        description="⚠️ DEPRECATED: SGTs are managed by ISE authorization policies. "
                   "This parameter is ignored. Use policy recommendations to change SGT assignments."
    )


class GroupMember(BaseModel):
    """Group member (device) model."""
    endpoint_id: str
    switch_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_name: Optional[str] = None
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    flow_count: int = 0
    bytes_in: int = 0
    bytes_out: int = 0


@router.get("/groups", response_model=Dict[str, Any])
async def list_groups(
    search: Optional[str] = Query(None, description="Search by label or SGT name"),
    has_sgt: Optional[bool] = Query(None, description="Filter by whether SGT is assigned"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of groups to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all groups (clusters) with their metadata.
    
    Returns groups with:
    - Cluster ID and label
    - SGT assignment (value and name)
    - Endpoint count (calculated from cluster_assignments)
    - Timestamps
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Use a subquery to calculate actual endpoint_count and determine SGT from member assignments
        # Get the most common SGT for each cluster using correlated subqueries
        query = """
            SELECT 
                c.cluster_id,
                c.cluster_label,
                COALESCE(c.sgt_value, (
                    SELECT sm.sgt_value
                    FROM cluster_assignments ca2
                    JOIN sgt_membership sm ON ca2.endpoint_id = sm.endpoint_id
                    WHERE ca2.cluster_id = c.cluster_id
                    GROUP BY sm.sgt_value
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                )) as sgt_value,
                COALESCE(c.sgt_name, (
                    SELECT sr.sgt_name
                    FROM cluster_assignments ca2
                    JOIN sgt_membership sm ON ca2.endpoint_id = sm.endpoint_id
                    LEFT JOIN sgt_registry sr ON sm.sgt_value = sr.sgt_value
                    WHERE ca2.cluster_id = c.cluster_id
                    GROUP BY sm.sgt_value, sr.sgt_name
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                )) as sgt_name,
                COALESCE(COUNT(DISTINCT ca.endpoint_id), 0) as endpoint_count,
                c.explanation,
                c.primary_reason,
                c.confidence,
                c.created_at,
                c.updated_at
            FROM clusters c
            LEFT JOIN cluster_assignments ca ON c.cluster_id = ca.cluster_id
            WHERE 1=1
        """
        params = []
        
        # Apply filters
        if search:
            query += " AND (c.cluster_label LIKE ? OR c.sgt_name LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
        
        if has_sgt is not None:
            # Note: This filter checks the cluster table's sgt_value directly
            # For a more accurate filter that checks member SGTs, we'd need a HAVING clause
            # For now, this filters based on what's in the clusters table
            if has_sgt:
                query += " AND (c.sgt_value IS NOT NULL OR EXISTS (SELECT 1 FROM cluster_assignments ca2 JOIN sgt_membership sm ON ca2.endpoint_id = sm.endpoint_id WHERE ca2.cluster_id = c.cluster_id))"
            else:
                query += " AND c.sgt_value IS NULL AND NOT EXISTS (SELECT 1 FROM cluster_assignments ca2 JOIN sgt_membership sm ON ca2.endpoint_id = sm.endpoint_id WHERE ca2.cluster_id = c.cluster_id)"
        
        # Group by cluster_id and order
        query += " GROUP BY c.cluster_id ORDER BY c.cluster_id LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        # Get total count for pagination (use same query structure but COUNT DISTINCT)
        count_query = """
            SELECT COUNT(DISTINCT c.cluster_id)
            FROM clusters c
            WHERE 1=1
        """
        count_params = []
        if search:
            count_query += " AND (c.cluster_label LIKE ? OR c.sgt_name LIKE ?)"
            count_params.extend([f"%{search}%", f"%{search}%"])
        if has_sgt is not None:
            if has_sgt:
                count_query += " AND c.sgt_value IS NOT NULL"
            else:
                count_query += " AND c.sgt_value IS NULL"
        
        count_cursor = conn.execute(count_query, count_params)
        total_count = count_cursor.fetchone()[0]
        
        groups = [GroupResponse(**dict(row)) for row in rows]
        
        return {
            "groups": [g.dict() for g in groups],
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }
        
    except Exception as e:
        logger.error(f"Error listing groups: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/groups/{cluster_id}", response_model=Dict[str, Any])
async def get_group(cluster_id: int):
    """
    Get detailed information for a specific group.
    
    Returns group metadata and member list.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Get group metadata with actual endpoint count and SGT from member assignments
        cursor = conn.execute("""
            SELECT 
                c.cluster_id,
                c.cluster_label,
                COALESCE(c.sgt_value, (
                    SELECT sm.sgt_value
                    FROM cluster_assignments ca2
                    JOIN sgt_membership sm ON ca2.endpoint_id = sm.endpoint_id
                    WHERE ca2.cluster_id = c.cluster_id
                    GROUP BY sm.sgt_value
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                )) as sgt_value,
                COALESCE(c.sgt_name, (
                    SELECT sr.sgt_name
                    FROM cluster_assignments ca2
                    JOIN sgt_membership sm ON ca2.endpoint_id = sm.endpoint_id
                    LEFT JOIN sgt_registry sr ON sm.sgt_value = sr.sgt_value
                    WHERE ca2.cluster_id = c.cluster_id
                    GROUP BY sm.sgt_value, sr.sgt_name
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                )) as sgt_name,
                COALESCE(COUNT(DISTINCT ca.endpoint_id), 0) as endpoint_count,
                c.explanation,
                c.primary_reason,
                c.confidence,
                c.created_at,
                c.updated_at
            FROM clusters c
            LEFT JOIN cluster_assignments ca ON c.cluster_id = ca.cluster_id
            WHERE c.cluster_id = ?
            GROUP BY c.cluster_id
        """, (cluster_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Group {cluster_id} not found")
        
        group_dict = dict(row)
        
        # Get group members
        members_cursor = conn.execute("""
            SELECT 
                s.endpoint_id,
                s.switch_id,
                s.flow_count,
                s.bytes_in,
                s.bytes_out,
                i.ip_address,
                i.user_name,
                i.device_name
            FROM cluster_assignments ca
            JOIN sketches s ON ca.endpoint_id = s.endpoint_id
            LEFT JOIN identity i ON s.endpoint_id = i.mac_address
            WHERE ca.cluster_id = ?
            ORDER BY s.flow_count DESC
        """, (cluster_id,))
        
        members_rows = members_cursor.fetchall()
        members = []
        
        for member_row in members_rows:
            member_dict = dict(member_row)
            
            # Extract device_type from device_name if available
            device_name_lower = (member_dict.get('device_name') or '').lower()
            if 'server' in device_name_lower or 'svr' in device_name_lower:
                member_dict['device_type'] = 'server'
            elif 'laptop' in device_name_lower:
                member_dict['device_type'] = 'laptop'
            elif 'printer' in device_name_lower:
                member_dict['device_type'] = 'printer'
            elif 'iot' in device_name_lower or 'camera' in device_name_lower:
                member_dict['device_type'] = 'iot'
            elif 'phone' in device_name_lower or 'mobile' in device_name_lower:
                member_dict['device_type'] = 'mobile'
            
            members.append(GroupMember(**member_dict))
        
        return {
            "group": GroupResponse(**group_dict).dict(),
            "members": [m.dict() for m in members],
            "member_count": len(members),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting group {cluster_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/groups/{cluster_id}")
async def update_group(
    cluster_id: int,
    update: GroupUpdateRequest,
):
    """
    Update group metadata (cluster label).
    
    Note: sgt_value and sgt_name parameters are deprecated. SGTs are assigned by 
    Cisco ISE authorization policies, not directly. To change SGT assignments, use 
    the policy recommendation feature to generate ISE authorization policies.
    
    See: docs/CLUSTER_ASSIGNMENT_WORKFLOW.md for details.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Verify group exists
        cursor = conn.execute("SELECT cluster_id FROM clusters WHERE cluster_id = ?", (cluster_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Group {cluster_id} not found")
        
        # Deprecation warnings for SGT parameters
        if update.sgt_value is not None:
            logger.warning(
                f"⚠️ DEPRECATED: sgt_value parameter in PUT /api/groups/{cluster_id} is deprecated. "
                f"SGTs are managed by ISE authorization policies. The sgt_value parameter is being ignored. "
                f"Use policy recommendations to change SGT assignments. See docs/CLUSTER_ASSIGNMENT_WORKFLOW.md"
            )
        
        if update.sgt_name is not None:
            logger.warning(
                f"⚠️ DEPRECATED: sgt_name parameter in PUT /api/groups/{cluster_id} is deprecated. "
                f"SGTs are managed by ISE authorization policies. The sgt_name parameter is being ignored. "
                f"Use policy recommendations to change SGT assignments. See docs/CLUSTER_ASSIGNMENT_WORKFLOW.md"
            )
        
        # Build update query dynamically based on provided fields
        updates = []
        params = []
        
        if update.cluster_label is not None:
            updates.append("cluster_label = ?")
            params.append(update.cluster_label)
        
        # Do not process sgt_value or sgt_name - they're deprecated
        
        if not updates:
            # No changes to make
            return await get_group(cluster_id)
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(cluster_id)
        
        query = f"UPDATE clusters SET {', '.join(updates)} WHERE cluster_id = ?"
        conn.execute(query, params)
        conn.commit()
        
        if update.cluster_label is not None:
            logger.info(f"Group {cluster_id} label updated to '{update.cluster_label}'")
        
        # Return updated group
        return await get_group(cluster_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating group {cluster_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/groups/stats")
async def group_stats():
    """Get group statistics."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Total groups
        total_cursor = conn.execute("SELECT COUNT(*) FROM clusters")
        total_groups = total_cursor.fetchone()[0]
        
        # Groups with SGT
        sgt_cursor = conn.execute("SELECT COUNT(*) FROM clusters WHERE sgt_value IS NOT NULL")
        groups_with_sgt = sgt_cursor.fetchone()[0]
        
        # Total endpoints in groups (count from cluster_assignments, excluding noise cluster -1)
        endpoints_cursor = conn.execute("""
            SELECT COUNT(*) FROM cluster_assignments WHERE cluster_id >= 0
        """)
        total_endpoints = endpoints_cursor.fetchone()[0] or 0
        
        # Average group size (calculate from assignments, excluding noise cluster -1)
        avg_size_cursor = conn.execute("""
            SELECT AVG(count) FROM (
                SELECT COUNT(*) as count
                FROM cluster_assignments
                WHERE cluster_id >= 0
                GROUP BY cluster_id
            )
        """)
        avg_size_row = avg_size_cursor.fetchone()
        avg_size = avg_size_row[0] if avg_size_row and avg_size_row[0] else 0
        
        return {
            "total_groups": total_groups,
            "groups_with_sgt": groups_with_sgt,
            "total_endpoints": total_endpoints,
            "average_group_size": round(avg_size, 2) if avg_size else 0,
        }
        
    except Exception as e:
        logger.error(f"Error getting group stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
