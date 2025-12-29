"""
User Management Endpoints

Endpoints for listing and viewing users.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from clarion.storage import get_database
from clarion.clustering.user_clusterer import cluster_users
from clarion.clustering.user_traffic_clusterer import cluster_users_with_traffic

logger = logging.getLogger(__name__)

router = APIRouter()


class UserResponse(BaseModel):
    """User response model."""
    user_id: str
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    is_active: bool = True
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    source: Optional[str] = None


class UserDetailResponse(BaseModel):
    """User detail response with devices and groups."""
    user_id: str
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    is_active: bool = True
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    source: Optional[str] = None
    devices: List[Dict[str, Any]] = []
    ad_groups: List[Dict[str, Any]] = []


@router.get("/users", response_model=Dict[str, Any])
async def list_users(
    search: Optional[str] = Query(None, description="Search by username, email, or display name"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of users to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all users.
    
    Returns a paginated list of users with optional search filtering.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Build query
        query = "SELECT * FROM users WHERE 1=1"
        params = []
        
        if search:
            query += " AND (username LIKE ? OR email LIKE ? OR display_name LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Get paginated results
        query += " ORDER BY username LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = conn.execute(query, params)
        users = [dict(row) for row in cursor.fetchall()]
        
        return {
            "users": users,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/clusters")
async def get_user_clusters():
    """
    Get all user clusters (users grouped by AD groups/departments).
    
    Returns user clusters with user counts and metadata.
    """
    db = get_database()
    conn = db._get_connection()
    
    # Check if user_clusters table exists
    try:
        clusters = conn.execute("""
            SELECT 
                cluster_id,
                name,
                user_count,
                primary_department,
                primary_ad_group,
                departments,
                ad_groups,
                confidence,
                created_at,
                updated_at
            FROM user_clusters
            ORDER BY user_count DESC
        """).fetchall()
        
        import json
        result = []
        for row in clusters:
            cluster_dict = dict(row)
            # Parse JSON fields
            if cluster_dict.get('departments'):
                cluster_dict['departments'] = json.loads(cluster_dict['departments'])
            else:
                cluster_dict['departments'] = []
            if cluster_dict.get('ad_groups'):
                cluster_dict['ad_groups'] = json.loads(cluster_dict['ad_groups'])
            else:
                cluster_dict['ad_groups'] = []
            result.append(cluster_dict)
        
        return {
            "clusters": result,
            "count": len(result),
        }
    except Exception as e:
        # Table doesn't exist yet - return empty
        logger.warning(f"User clusters table not found: {e}")
        return {
            "clusters": [],
            "count": 0,
            "message": "User clusters not generated yet. Run clustering to create them.",
        }


@router.get("/users/clusters/{cluster_id}/users")
async def get_cluster_users(cluster_id: int):
    """
    Get all users in a specific user cluster.
    
    Returns user details for all users in the cluster.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Get users in this cluster
        users = conn.execute("""
            SELECT 
                u.user_id,
                u.username,
                u.email,
                u.display_name,
                u.department,
                u.title,
                u.is_active,
                u.last_seen,
                GROUP_CONCAT(DISTINCT agm.group_name) as ad_groups
            FROM user_cluster_assignments uca
            JOIN users u ON uca.user_id = u.user_id
            LEFT JOIN ad_group_memberships agm ON u.user_id = agm.user_id
            WHERE uca.cluster_id = ?
            GROUP BY u.user_id, u.username, u.email, u.display_name, u.department, u.title, u.is_active, u.last_seen
            ORDER BY u.username
        """, (cluster_id,)).fetchall()
        
        result = []
        for row in users:
            user_dict = dict(row)
            # Parse AD groups
            if user_dict.get('ad_groups'):
                user_dict['ad_groups'] = [g.strip() for g in user_dict['ad_groups'].split(',') if g.strip()]
            else:
                user_dict['ad_groups'] = []
            result.append(user_dict)
        
        return {
            "cluster_id": cluster_id,
            "users": result,
            "count": len(result),
        }
    except Exception as e:
        logger.error(f"Error getting cluster users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/clusters/generate")
async def generate_user_clusters(use_traffic: bool = True):
    """
    Generate user clusters based on AD groups and optionally traffic patterns.
    
    Args:
        use_traffic: If True, use traffic-enhanced clustering (AD groups + traffic patterns).
                    If False, use AD groups only.
    """
    try:
        if use_traffic:
            clusters = cluster_users_with_traffic()
            method = "traffic_enhanced"
        else:
            clusters = cluster_users()
            method = "ad_groups_only"
        
        return {
            "status": "success",
            "method": method,
            "clusters_created": len(clusters),
            "message": f"Created {len(clusters)} user clusters using {method}",
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "name": c.name,
                    "user_count": c.user_count,
                    "primary_department": c.primary_department,
                    "primary_ad_group": c.primary_ad_group,
                }
                for c in clusters
            ],
        }
    except Exception as e:
        logger.error(f"Error generating user clusters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(user_id: str):
    """
    Get detailed information for a specific user.
    
    Returns user details including associated devices and AD groups.
    """
    db = get_database()
    
    try:
        # Get user
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        # Get devices for user
        devices = db.get_devices_for_user(user_id)
        
        # Get AD groups for user
        ad_groups = db.get_user_groups(user_id)
        
        # Convert to response format
        user_dict = dict(user)
        
        return UserDetailResponse(
            user_id=user_dict['user_id'],
            username=user_dict['username'],
            email=user_dict.get('email'),
            display_name=user_dict.get('display_name'),
            department=user_dict.get('department'),
            title=user_dict.get('title'),
            is_active=bool(user_dict.get('is_active', True)),
            first_seen=user_dict.get('first_seen'),
            last_seen=user_dict.get('last_seen'),
            source=user_dict.get('source'),
            devices=[dict(device) for device in devices],
            ad_groups=[dict(group) for group in ad_groups],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

