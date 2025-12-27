"""
Device Management Endpoints

Endpoints for listing, viewing, and managing devices (endpoints).
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from clarion.storage import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


class DeviceResponse(BaseModel):
    """Device/endpoint response model."""
    endpoint_id: str  # MAC address
    switch_id: Optional[str] = None
    
    # Behavioral data (from sketches)
    flow_count: int = 0
    unique_peers: int = 0
    unique_ports: int = 0
    bytes_in: int = 0
    bytes_out: int = 0
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
    active_hours: int = 0
    
    # Identity data
    ip_address: Optional[str] = None
    user_name: Optional[str] = None
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    ad_groups: List[str] = []
    ise_profile: Optional[str] = None
    
    # Cluster assignment
    cluster_id: Optional[int] = None
    cluster_label: Optional[str] = None
    sgt_value: Optional[int] = None
    sgt_name: Optional[str] = None


class DeviceUpdateRequest(BaseModel):
    """Request model for updating device assignments."""
    cluster_id: Optional[int] = None
    sgt_value: Optional[int] = None


@router.get("/devices", response_model=Dict[str, Any])
async def list_devices(
    switch_id: Optional[str] = Query(None, description="Filter by switch ID"),
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    search: Optional[str] = Query(None, description="Search by MAC, IP, or name"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of devices to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all devices with their behavioral and identity data.
    
    Returns devices with:
    - Behavioral metrics (flows, peers, traffic)
    - Identity information (user, device type, AD groups)
    - Cluster assignment and SGT
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Build query with JOINs
        query = """
            SELECT 
                s.endpoint_id,
                s.switch_id,
                s.flow_count,
                s.unique_peers,
                s.unique_ports,
                s.bytes_in,
                s.bytes_out,
                s.first_seen,
                s.last_seen,
                s.active_hours,
                i.ip_address,
                i.user_name,
                i.device_name,
                i.ise_profile,
                i.ad_groups,
                ca.cluster_id,
                c.cluster_label,
                c.sgt_value,
                c.sgt_name
            FROM sketches s
            LEFT JOIN identity i ON s.endpoint_id = i.mac_address
            LEFT JOIN cluster_assignments ca ON s.endpoint_id = ca.endpoint_id
            LEFT JOIN clusters c ON ca.cluster_id = c.cluster_id
            WHERE 1=1
        """
        params = []
        
        # Apply filters
        if switch_id:
            query += " AND s.switch_id = ?"
            params.append(switch_id)
        
        if cluster_id is not None:
            query += " AND ca.cluster_id = ?"
            params.append(cluster_id)
        
        if device_type:
            # Filter by device_name or ise_profile containing the device type
            query += " AND (i.device_name LIKE ? OR i.ise_profile LIKE ?)"
            params.extend([f"%{device_type}%", f"%{device_type}%"])
        
        if search:
            query += " AND (s.endpoint_id LIKE ? OR i.ip_address LIKE ? OR i.user_name LIKE ? OR i.device_name LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param, search_param])
        
        # Order by last_seen descending (most recent first)
        query += " ORDER BY s.last_seen DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        # Get total count for pagination
        count_query = """
            SELECT COUNT(DISTINCT s.endpoint_id)
            FROM sketches s
            LEFT JOIN identity i ON s.endpoint_id = i.mac_address
            LEFT JOIN cluster_assignments ca ON s.endpoint_id = ca.endpoint_id
            WHERE 1=1
        """
        count_params = []
        if switch_id:
            count_query += " AND s.switch_id = ?"
            count_params.append(switch_id)
        if cluster_id is not None:
            count_query += " AND ca.cluster_id = ?"
            count_params.append(cluster_id)
        if device_type:
            count_query += " AND (i.device_name LIKE ? OR i.ise_profile LIKE ?)"
            count_params.extend([f"%{device_type}%", f"%{device_type}%"])
        if search:
            count_query += " AND (s.endpoint_id LIKE ? OR i.ip_address LIKE ? OR i.user_name LIKE ? OR i.device_name LIKE ?)"
            search_param = f"%{search}%"
            count_params.extend([search_param, search_param, search_param, search_param])
        
        count_cursor = conn.execute(count_query, count_params)
        total_count = count_cursor.fetchone()[0]
        
        # Convert rows to device objects
        devices = []
        for row in rows:
            device_dict = dict(row)
            
            # Parse AD groups JSON
            if device_dict.get('ad_groups'):
                import json
                try:
                    device_dict['ad_groups'] = json.loads(device_dict['ad_groups']) if isinstance(device_dict['ad_groups'], str) else device_dict['ad_groups']
                except:
                    device_dict['ad_groups'] = []
            else:
                device_dict['ad_groups'] = []
            
            # Extract device_type from device_name or ise_profile if not explicitly set
            if not device_dict.get('device_type'):
                device_name_lower = (device_dict.get('device_name') or '').lower()
                ise_profile_lower = (device_dict.get('ise_profile') or '').lower()
                combined = f"{device_name_lower} {ise_profile_lower}"
                
                if 'server' in combined or 'svr' in combined:
                    device_dict['device_type'] = 'server'
                elif 'laptop' in combined:
                    device_dict['device_type'] = 'laptop'
                elif 'printer' in combined:
                    device_dict['device_type'] = 'printer'
                elif 'iot' in combined or 'camera' in combined:
                    device_dict['device_type'] = 'iot'
                elif 'phone' in combined or 'mobile' in combined:
                    device_dict['device_type'] = 'mobile'
            
            devices.append(DeviceResponse(**device_dict))
        
        return {
            "devices": [d.dict() for d in devices],
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }
        
    except Exception as e:
        logger.error(f"Error listing devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{endpoint_id}", response_model=DeviceResponse)
async def get_device(endpoint_id: str):
    """
    Get detailed information for a specific device.
    
    Returns full device details including behavioral data, identity, and cluster assignment.
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        query = """
            SELECT 
                s.endpoint_id,
                s.switch_id,
                s.flow_count,
                s.unique_peers,
                s.unique_ports,
                s.bytes_in,
                s.bytes_out,
                s.first_seen,
                s.last_seen,
                s.active_hours,
                i.ip_address,
                i.user_name,
                i.device_name,
                i.ise_profile,
                i.ad_groups,
                ca.cluster_id,
                c.cluster_label,
                c.sgt_value,
                c.sgt_name
            FROM sketches s
            LEFT JOIN identity i ON s.endpoint_id = i.mac_address
            LEFT JOIN cluster_assignments ca ON s.endpoint_id = ca.endpoint_id
            LEFT JOIN clusters c ON ca.cluster_id = c.cluster_id
            WHERE s.endpoint_id = ?
            LIMIT 1
        """
        cursor = conn.execute(query, (endpoint_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Device {endpoint_id} not found")
        
        device_dict = dict(row)
        
        # Parse AD groups JSON
        if device_dict.get('ad_groups'):
            import json
            try:
                device_dict['ad_groups'] = json.loads(device_dict['ad_groups']) if isinstance(device_dict['ad_groups'], str) else device_dict['ad_groups']
            except:
                device_dict['ad_groups'] = []
        else:
            device_dict['ad_groups'] = []
        
        return DeviceResponse(**device_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device {endpoint_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{endpoint_id}/flows")
async def get_device_flows(
    endpoint_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of flows to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get flows for a specific device (by MAC address or IP)."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Get IP address for this device
        identity = db.get_identity(endpoint_id) if len(endpoint_id) > 17 else None  # MAC addresses are 17 chars
        if not identity:
            # Try to find identity by MAC address
            cursor = conn.execute("""
                SELECT ip_address FROM identity WHERE mac_address = ?
            """, (endpoint_id,))
            row = cursor.fetchone()
            ip_address = row[0] if row else endpoint_id
        else:
            ip_address = identity.get('ip_address', endpoint_id)
        
        # Get flows where this device is source or destination (by MAC address or IP)
        if ip_address:
            query = """
                SELECT 
                    id, src_ip, dst_ip, src_port, dst_port, protocol,
                    bytes, packets, flow_start, flow_end, switch_id,
                    src_sgt, dst_sgt, src_mac, dst_mac, vlan_id
                FROM netflow
                WHERE (src_ip = ? OR dst_ip = ? OR src_mac = ? OR dst_mac = ?)
                ORDER BY flow_start DESC
                LIMIT ? OFFSET ?
            """
            params = (ip_address, ip_address, endpoint_id, endpoint_id, limit, offset)
            count_query = """
                SELECT COUNT(*)
                FROM netflow
                WHERE (src_ip = ? OR dst_ip = ? OR src_mac = ? OR dst_mac = ?)
            """
            count_params = (ip_address, ip_address, endpoint_id, endpoint_id)
        else:
            # If no IP found, search by MAC only
            query = """
                SELECT 
                    id, src_ip, dst_ip, src_port, dst_port, protocol,
                    bytes, packets, flow_start, flow_end, switch_id,
                    src_sgt, dst_sgt, src_mac, dst_mac, vlan_id
                FROM netflow
                WHERE (src_mac = ? OR dst_mac = ?)
                ORDER BY flow_start DESC
                LIMIT ? OFFSET ?
            """
            params = (endpoint_id, endpoint_id, limit, offset)
            count_query = """
                SELECT COUNT(*)
                FROM netflow
                WHERE (src_mac = ? OR dst_mac = ?)
            """
            count_params = (endpoint_id, endpoint_id)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        # Get total count
        count_cursor = conn.execute(count_query, count_params)
        total_count = count_cursor.fetchone()[0]
        
        flows = [dict(row) for row in rows]
        
        return {
            "flows": flows,
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }
        
    except Exception as e:
        logger.error(f"Error getting flows for device {endpoint_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/devices/{endpoint_id}")
async def update_device(
    endpoint_id: str,
    update: DeviceUpdateRequest,
):
    """Update device cluster assignment or SGT."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Verify device exists
        device = await get_device(endpoint_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {endpoint_id} not found")
        
        # Update cluster assignment if provided
        if update.cluster_id is not None:
            # Remove existing assignment
            conn.execute("""
                DELETE FROM cluster_assignments WHERE endpoint_id = ?
            """, (endpoint_id,))
            
            # Add new assignment
            if update.cluster_id >= 0:  # -1 means unassign
                db.assign_endpoint_to_cluster(endpoint_id, update.cluster_id)
                conn.commit()
        
        # Update SGT if provided (this would require updating the cluster's SGT)
        # For now, we'll need to update the cluster's SGT value
        if update.sgt_value is not None:
            # Get current cluster
            cursor = conn.execute("""
                SELECT cluster_id FROM cluster_assignments WHERE endpoint_id = ?
            """, (endpoint_id,))
            row = cursor.fetchone()
            
            if row:
                cluster_id = row[0]
                # Update cluster's SGT value
                conn.execute("""
                    UPDATE clusters SET sgt_value = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE cluster_id = ?
                """, (update.sgt_value, cluster_id))
                conn.commit()
        
        # Return updated device
        return await get_device(endpoint_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating device {endpoint_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/stats")
async def device_stats():
    """Get device statistics."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Total devices
        total_cursor = conn.execute("SELECT COUNT(DISTINCT endpoint_id) FROM sketches")
        total_devices = total_cursor.fetchone()[0]
        
        # Devices by switch
        switch_cursor = conn.execute("""
            SELECT switch_id, COUNT(DISTINCT endpoint_id) as count
            FROM sketches
            GROUP BY switch_id
        """)
        by_switch = {row[0]: row[1] for row in switch_cursor.fetchall()}
        
        # Devices with identity
        identity_cursor = conn.execute("""
            SELECT COUNT(DISTINCT s.endpoint_id)
            FROM sketches s
            JOIN identity i ON s.endpoint_id = i.mac_address
        """)
        with_identity = identity_cursor.fetchone()[0]
        
        # Devices by cluster
        cluster_cursor = conn.execute("""
            SELECT ca.cluster_id, COUNT(*) as count
            FROM cluster_assignments ca
            GROUP BY ca.cluster_id
        """)
        by_cluster = {row[0]: row[1] for row in cluster_cursor.fetchall()}
        
        # Devices by device type
        type_cursor = conn.execute("""
            SELECT 
                CASE 
                    WHEN i.device_name LIKE '%server%' OR i.device_name LIKE '%svr%' THEN 'server'
                    WHEN i.device_name LIKE '%laptop%' THEN 'laptop'
                    WHEN i.device_name LIKE '%printer%' THEN 'printer'
                    WHEN i.device_name LIKE '%iot%' OR i.device_name LIKE '%camera%' THEN 'iot'
                    ELSE 'unknown'
                END as device_type,
                COUNT(DISTINCT s.endpoint_id) as count
            FROM sketches s
            LEFT JOIN identity i ON s.endpoint_id = i.mac_address
            GROUP BY device_type
        """)
        by_type = {row[0]: row[1] for row in type_cursor.fetchall()}
        
        return {
            "total_devices": total_devices,
            "with_identity": with_identity,
            "by_switch": by_switch,
            "by_cluster": by_cluster,
            "by_device_type": by_type,
        }
        
    except Exception as e:
        logger.error(f"Error getting device stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
