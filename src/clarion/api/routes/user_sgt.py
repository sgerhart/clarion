"""
User SGT Management Endpoints

Endpoints for managing user SGT assignments, traffic patterns, and recommendations.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from clarion.storage import get_database
from clarion.policy.user_sgt_recommendation import (
    UserSGTRecommendationEngine,
    generate_user_sgt_recommendation,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class UserSGTResponse(BaseModel):
    """User SGT assignment response model."""
    user_id: str
    sgt_value: int
    sgt_name: Optional[str] = None
    category: Optional[str] = None
    assigned_at: Optional[str] = None
    assigned_by: Optional[str] = None
    confidence: Optional[float] = None
    user_cluster_id: Optional[int] = None


class UserTrafficPatternResponse(BaseModel):
    """User traffic pattern response model."""
    user_id: str
    total_bytes_in: int = 0
    total_bytes_out: int = 0
    total_flows: int = 0
    unique_peers: int = 0
    unique_services: int = 0
    top_ports: List[Dict] = []
    top_protocols: List[Dict] = []
    last_updated: Optional[str] = None


class UserSGTRecommendationResponse(BaseModel):
    """User SGT recommendation response model."""
    id: Optional[int] = None
    user_id: Optional[str] = None
    user_cluster_id: Optional[int] = None
    recommended_sgt: int
    recommended_sgt_name: Optional[str] = None
    ad_group_based_sgt: Optional[int] = None
    ad_group_based_sgt_name: Optional[str] = None
    primary_ad_groups: List[str] = []
    traffic_suggested_sgt: Optional[int] = None
    traffic_suggested_sgt_name: Optional[str] = None
    traffic_pattern_summary: Optional[Dict] = None
    recommendation_type: str
    confidence: float
    justification: str
    users_affected: int = 1
    security_concerns: List[str] = []
    status: str = "pending"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("/users/{user_id}/sgt", response_model=UserSGTResponse)
async def get_user_sgt(user_id: str):
    """
    Get the current SGT assignment for a user.
    
    Returns the SGT currently assigned to the user, if any.
    """
    db = get_database()
    try:
        sgt_assignment = db.get_user_sgt(user_id)
        if not sgt_assignment:
            raise HTTPException(status_code=404, detail=f"No SGT assignment found for user {user_id}")
        
        return UserSGTResponse(
            user_id=sgt_assignment['user_id'],
            sgt_value=sgt_assignment['sgt_value'],
            sgt_name=sgt_assignment.get('sgt_name'),
            category=sgt_assignment.get('category'),
            assigned_at=str(sgt_assignment.get('assigned_at', '')),
            assigned_by=sgt_assignment.get('assigned_by'),
            confidence=sgt_assignment.get('confidence'),
            user_cluster_id=sgt_assignment.get('user_cluster_id'),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user SGT for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}/sgt")
async def assign_user_sgt(
    user_id: str,
    sgt_value: int,
    assigned_by: str = "manual",
    confidence: Optional[float] = None,
    user_cluster_id: Optional[int] = None,
):
    """
    Assign an SGT to a user.
    
    Args:
        user_id: User ID
        sgt_value: SGT value to assign
        assigned_by: Source of assignment ('manual', 'clustering', 'traffic_analysis', etc.)
        confidence: Confidence score (0.0-1.0)
        user_cluster_id: Optional user cluster ID if assignment is based on clustering
    """
    db = get_database()
    try:
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        # Verify SGT exists
        sgt = db.get_sgt(sgt_value)
        if not sgt:
            raise HTTPException(status_code=404, detail=f"SGT {sgt_value} not found")
        
        # Assign SGT
        db.assign_sgt_to_user(
            user_id=user_id,
            sgt_value=sgt_value,
            assigned_by=assigned_by,
            confidence=confidence,
            user_cluster_id=user_cluster_id,
        )
        
        return {
            "success": True,
            "message": f"Assigned SGT {sgt_value} to user {user_id}",
            "user_id": user_id,
            "sgt_value": sgt_value,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning SGT to user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}/sgt")
async def unassign_user_sgt(user_id: str):
    """
    Unassign SGT from a user.
    
    Removes the current SGT assignment and records it in history.
    """
    db = get_database()
    try:
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        # Check if user has an SGT assignment
        sgt_assignment = db.get_user_sgt(user_id)
        if not sgt_assignment:
            raise HTTPException(status_code=404, detail=f"No SGT assignment found for user {user_id}")
        
        # Unassign
        db.unassign_sgt_from_user(user_id)
        
        return {
            "success": True,
            "message": f"Unassigned SGT from user {user_id}",
            "user_id": user_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unassigning SGT from user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/traffic", response_model=UserTrafficPatternResponse)
async def get_user_traffic_pattern(user_id: str):
    """
    Get traffic pattern for a user.
    
    Returns aggregated traffic statistics and patterns.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        # Get traffic pattern
        cursor = conn.execute("""
            SELECT * FROM user_traffic_patterns WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        
        if not row:
            # Return empty pattern if no traffic data
            return UserTrafficPatternResponse(
                user_id=user_id,
                total_bytes_in=0,
                total_bytes_out=0,
                total_flows=0,
                unique_peers=0,
                unique_services=0,
                top_ports=[],
                top_protocols=[],
            )
        
        import json
        result = dict(row)
        
        # Parse JSON fields
        top_ports = []
        if result.get('top_ports'):
            try:
                top_ports = json.loads(result['top_ports'])
            except (json.JSONDecodeError, TypeError):
                top_ports = []
        
        top_protocols = []
        if result.get('top_protocols'):
            try:
                top_protocols = json.loads(result['top_protocols'])
            except (json.JSONDecodeError, TypeError):
                top_protocols = []
        
        return UserTrafficPatternResponse(
            user_id=result['user_id'],
            total_bytes_in=result.get('total_bytes_in', 0) or 0,
            total_bytes_out=result.get('total_bytes_out', 0) or 0,
            total_flows=result.get('total_flows', 0) or 0,
            unique_peers=result.get('unique_peers', 0) or 0,
            unique_services=result.get('unique_services', 0) or 0,
            top_ports=top_ports,
            top_protocols=top_protocols,
            last_updated=str(result.get('last_updated', '')),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting traffic pattern for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/recommendation", response_model=UserSGTRecommendationResponse)
async def get_user_sgt_recommendation(user_id: str):
    """
    Get SGT recommendation for a user.
    
    Generates a recommendation by comparing AD groups with traffic patterns.
    """
    db = get_database()
    try:
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        # Get user's cluster if any
        conn = db._get_connection()
        cluster_cursor = conn.execute("""
            SELECT user_cluster_id FROM user_cluster_assignments WHERE user_id = ? LIMIT 1
        """, (user_id,))
        cluster_row = cluster_cursor.fetchone()
        user_cluster_id = cluster_row['user_cluster_id'] if cluster_row else None
        
        # Generate recommendation
        engine = UserSGTRecommendationEngine(db)
        recommendation = engine.generate_user_recommendation(user_id, user_cluster_id)
        
        if not recommendation:
            raise HTTPException(
                status_code=404,
                detail=f"Could not generate recommendation for user {user_id} (insufficient data)"
            )
        
        return UserSGTRecommendationResponse(**recommendation.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendation for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/clusters/{cluster_id}/recommendation", response_model=UserSGTRecommendationResponse)
async def get_cluster_sgt_recommendation(cluster_id: int):
    """
    Get SGT recommendation for a user cluster.
    
    Generates a cluster-level recommendation based on aggregated analysis.
    """
    db = get_database()
    try:
        # Generate cluster recommendation
        engine = UserSGTRecommendationEngine(db)
        recommendation = engine.generate_cluster_recommendation(cluster_id)
        
        if not recommendation:
            raise HTTPException(
                status_code=404,
                detail=f"Could not generate recommendation for cluster {cluster_id}"
            )
        
        return UserSGTRecommendationResponse(**recommendation.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendation for cluster {cluster_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sgts/{sgt_value}/users")
async def get_users_by_sgt(sgt_value: int):
    """
    Get all users assigned to a specific SGT.
    
    Returns a list of users with the given SGT assignment.
    """
    db = get_database()
    try:
        users = db.list_users_by_sgt(sgt_value)
        
        return {
            "sgt_value": sgt_value,
            "users": users,
            "count": len(users),
        }
    except Exception as e:
        logger.error(f"Error listing users for SGT {sgt_value}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/sgt/history")
async def get_user_sgt_history(user_id: str):
    """
    Get SGT assignment history for a user.
    
    Returns all past and current SGT assignments.
    """
    db = get_database()
    try:
        # Verify user exists
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        history = db.get_user_sgt_assignment_history(user_id)
        
        return {
            "user_id": user_id,
            "history": history,
            "count": len(history),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting SGT history for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

