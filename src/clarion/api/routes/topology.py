"""
Topology Management API Routes

Manages network topology including:
- Locations (hierarchy: Campus -> Building -> IDF)
- Address Spaces (internal IP ranges)
- Subnets (network segments)
- Switches (network devices)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import logging

from clarion.storage import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Request/Response Models ==========

class LocationCreate(BaseModel):
    """Request model for creating a location."""
    location_id: str
    name: str
    type: str = Field(..., description="CAMPUS, BRANCH, REMOTE_SITE, BUILDING, IDF, ROOM")
    parent_id: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    site_type: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    timezone: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LocationUpdate(BaseModel):
    """Request model for updating a location."""
    name: Optional[str] = None
    type: Optional[str] = None
    parent_id: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    site_type: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    timezone: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AddressSpaceCreate(BaseModel):
    """Request model for creating an address space."""
    space_id: str
    name: str
    cidr: str  # e.g., "10.0.0.0/8"
    description: Optional[str] = None


class AddressSpaceUpdate(BaseModel):
    """Request model for updating an address space."""
    name: Optional[str] = None
    cidr: Optional[str] = None
    description: Optional[str] = None


class SubnetCreate(BaseModel):
    """Request model for creating a subnet."""
    subnet_id: str
    name: str
    cidr: str  # e.g., "10.1.0.0/24"
    address_space_id: str
    location_id: Optional[str] = None
    vlan_id: Optional[int] = None
    description: Optional[str] = None


class SubnetUpdate(BaseModel):
    """Request model for updating a subnet."""
    name: Optional[str] = None
    cidr: Optional[str] = None
    address_space_id: Optional[str] = None
    location_id: Optional[str] = None
    vlan_id: Optional[int] = None
    description: Optional[str] = None


class SwitchCreate(BaseModel):
    """Request model for creating a switch."""
    switch_id: str
    name: str
    location_id: str
    model: Optional[str] = None
    management_ip: Optional[str] = None
    serial_number: Optional[str] = None
    description: Optional[str] = None


class SwitchUpdate(BaseModel):
    """Request model for updating a switch."""
    name: Optional[str] = None
    location_id: Optional[str] = None
    model: Optional[str] = None
    management_ip: Optional[str] = None
    serial_number: Optional[str] = None
    description: Optional[str] = None


# ========== Location Endpoints ==========

@router.get("/topology/locations")
async def list_locations(
    parent_id: Optional[str] = Query(None, description="Filter by parent location"),
    type: Optional[str] = Query(None, description="Filter by location type"),
    search: Optional[str] = Query(None, description="Search by name"),
):
    """List all locations with optional filters."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        query = "SELECT * FROM locations WHERE 1=1"
        params = []
        
        if parent_id:
            query += " AND parent_id = ?"
            params.append(parent_id)
        
        if type:
            query += " AND type = ?"
            params.append(type)
        
        if search:
            query += " AND name LIKE ?"
            params.append(f"%{search}%")
        
        query += " ORDER BY type, name"
        
        cursor = conn.execute(query, params)
        locations = [dict(row) for row in cursor.fetchall()]
        
        # Parse metadata JSON if present
        for loc in locations:
            if loc.get('metadata'):
                import json
                try:
                    loc['metadata'] = json.loads(loc['metadata']) if isinstance(loc['metadata'], str) else loc['metadata']
                except:
                    loc['metadata'] = {}
        
        return {"locations": locations}
    except Exception as e:
        logger.error(f"Error listing locations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topology/locations/{location_id}")
async def get_location(location_id: str):
    """Get a specific location with its hierarchy."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Get location
        cursor = conn.execute("SELECT * FROM locations WHERE location_id = ?", (location_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Location {location_id} not found")
        
        location = dict(row)
        
        # Parse metadata
        if location.get('metadata'):
            import json
            try:
                location['metadata'] = json.loads(location['metadata']) if isinstance(location['metadata'], str) else location['metadata']
            except:
                location['metadata'] = {}
        
        # Get parent hierarchy
        hierarchy = []
        current_id = location.get('parent_id')
        while current_id:
            parent_cursor = conn.execute("SELECT location_id, name, type, parent_id FROM locations WHERE location_id = ?", (current_id,))
            parent_row = parent_cursor.fetchone()
            if parent_row:
                parent_dict = dict(parent_row)
                hierarchy.insert(0, {
                    'location_id': parent_dict['location_id'],
                    'name': parent_dict['name'],
                    'type': parent_dict['type']
                })
                current_id = parent_dict.get('parent_id')
            else:
                break
        
        # Get children
        children_cursor = conn.execute("SELECT location_id, name, type FROM locations WHERE parent_id = ?", (location_id,))
        children = [dict(row) for row in children_cursor.fetchall()]
        
        # Get subnets at this location
        subnets_cursor = conn.execute("SELECT subnet_id, name, cidr FROM subnets WHERE location_id = ?", (location_id,))
        subnets = [dict(row) for row in subnets_cursor.fetchall()]
        
        # Get switches at this location
        switches_cursor = conn.execute("SELECT switch_id, name, model FROM switches WHERE location_id = ?", (location_id,))
        switches = [dict(row) for row in switches_cursor.fetchall()]
        
        return {
            "location": location,
            "hierarchy": hierarchy,
            "children": children,
            "subnets": subnets,
            "switches": switches,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting location {location_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topology/locations")
async def create_location(location: LocationCreate):
    """Create a new location."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        import json
        
        # Validate parent exists if provided
        if location.parent_id:
            parent_cursor = conn.execute("SELECT location_id FROM locations WHERE location_id = ?", (location.parent_id,))
            if not parent_cursor.fetchone():
                raise HTTPException(status_code=400, detail=f"Parent location {location.parent_id} not found")
        
        metadata_json = json.dumps(location.metadata) if location.metadata else None
        
        conn.execute("""
            INSERT INTO locations (
                location_id, name, type, parent_id, address,
                latitude, longitude, site_type, contact_name,
                contact_phone, contact_email, timezone, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            location.location_id,
            location.name,
            location.type,
            location.parent_id,
            location.address,
            location.latitude,
            location.longitude,
            location.site_type,
            location.contact_name,
            location.contact_phone,
            location.contact_email,
            location.timezone,
            metadata_json,
        ))
        conn.commit()
        
        return {"status": "created", "location_id": location.location_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating location: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/topology/locations/{location_id}")
async def update_location(location_id: str, update: LocationUpdate):
    """Update a location."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Verify location exists
        cursor = conn.execute("SELECT location_id FROM locations WHERE location_id = ?", (location_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Location {location_id} not found")
        
        # Build update query
        updates = []
        params = []
        
        if update.name is not None:
            updates.append("name = ?")
            params.append(update.name)
        if update.type is not None:
            updates.append("type = ?")
            params.append(update.type)
        if update.parent_id is not None:
            # Validate parent exists
            if update.parent_id:
                parent_cursor = conn.execute("SELECT location_id FROM locations WHERE location_id = ?", (update.parent_id,))
                if not parent_cursor.fetchone():
                    raise HTTPException(status_code=400, detail=f"Parent location {update.parent_id} not found")
            updates.append("parent_id = ?")
            params.append(update.parent_id)
        if update.address is not None:
            updates.append("address = ?")
            params.append(update.address)
        if update.latitude is not None:
            updates.append("latitude = ?")
            params.append(update.latitude)
        if update.longitude is not None:
            updates.append("longitude = ?")
            params.append(update.longitude)
        if update.site_type is not None:
            updates.append("site_type = ?")
            params.append(update.site_type)
        if update.contact_name is not None:
            updates.append("contact_name = ?")
            params.append(update.contact_name)
        if update.contact_phone is not None:
            updates.append("contact_phone = ?")
            params.append(update.contact_phone)
        if update.contact_email is not None:
            updates.append("contact_email = ?")
            params.append(update.contact_email)
        if update.timezone is not None:
            updates.append("timezone = ?")
            params.append(update.timezone)
        if update.metadata is not None:
            import json
            updates.append("metadata = ?")
            params.append(json.dumps(update.metadata))
        
        if not updates:
            return await get_location(location_id)
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(location_id)
        
        query = f"UPDATE locations SET {', '.join(updates)} WHERE location_id = ?"
        conn.execute(query, params)
        conn.commit()
        
        return await get_location(location_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating location {location_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/topology/locations/{location_id}")
async def delete_location(location_id: str):
    """Delete a location (only if it has no children or subnets)."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Check for children
        children_cursor = conn.execute("SELECT COUNT(*) FROM locations WHERE parent_id = ?", (location_id,))
        child_count = children_cursor.fetchone()[0]
        if child_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete location {location_id}: it has {child_count} child locations"
            )
        
        # Check for subnets
        subnets_cursor = conn.execute("SELECT COUNT(*) FROM subnets WHERE location_id = ?", (location_id,))
        subnet_count = subnets_cursor.fetchone()[0]
        if subnet_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete location {location_id}: it has {subnet_count} subnets"
            )
        
        # Check for switches
        switches_cursor = conn.execute("SELECT COUNT(*) FROM switches WHERE location_id = ?", (location_id,))
        switch_count = switches_cursor.fetchone()[0]
        if switch_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete location {location_id}: it has {switch_count} switches"
            )
        
        conn.execute("DELETE FROM locations WHERE location_id = ?", (location_id,))
        conn.commit()
        
        return {"status": "deleted", "location_id": location_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting location {location_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========== Address Space Endpoints ==========

@router.get("/topology/address-spaces")
async def list_address_spaces():
    """List all address spaces."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        cursor = conn.execute("SELECT * FROM address_spaces ORDER BY name")
        spaces = [dict(row) for row in cursor.fetchall()]
        return {"address_spaces": spaces}
    except Exception as e:
        logger.error(f"Error listing address spaces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topology/address-spaces")
async def create_address_space(space: AddressSpaceCreate):
    """Create a new address space."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Check if address space already exists
        existing = conn.execute("SELECT space_id FROM address_spaces WHERE space_id = ?", (space.space_id,))
        if existing.fetchone():
            raise HTTPException(status_code=400, detail=f"Address space {space.space_id} already exists")
        
        conn.execute("""
            INSERT INTO address_spaces (space_id, name, cidr, type, description, is_internal)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            space.space_id,
            space.name,
            space.cidr,
            "GLOBAL",  # Default type
            space.description,
            1  # Default to internal
        ))
        conn.commit()
        
        # Return the created address space
        cursor = conn.execute("SELECT * FROM address_spaces WHERE space_id = ?", (space.space_id,))
        created = dict(cursor.fetchone())
        
        return {"status": "created", "space_id": space.space_id, "address_space": created}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating address space: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/topology/address-spaces/{space_id}")
async def update_address_space(space_id: str, update: AddressSpaceUpdate):
    """Update an address space."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Check if address space exists
        existing = conn.execute("SELECT * FROM address_spaces WHERE space_id = ?", (space_id,))
        existing_row = existing.fetchone()
        if not existing_row:
            raise HTTPException(status_code=404, detail=f"Address space {space_id} not found")
        
        # Check if CIDR already exists (if changing CIDR)
        if update.cidr:
            cidr_existing = conn.execute("SELECT space_id FROM address_spaces WHERE cidr = ? AND space_id != ?", (update.cidr, space_id))
            if cidr_existing.fetchone():
                raise HTTPException(status_code=400, detail=f"Address space with CIDR {update.cidr} already exists")
        
        # Build update query dynamically
        updates = []
        params = []
        
        if update.name is not None:
            updates.append("name = ?")
            params.append(update.name)
        if update.cidr is not None:
            updates.append("cidr = ?")
            params.append(update.cidr)
        if update.description is not None:
            updates.append("description = ?")
            params.append(update.description)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(space_id)
        
        query = f"UPDATE address_spaces SET {', '.join(updates)} WHERE space_id = ?"
        conn.execute(query, params)
        conn.commit()
        
        # Return updated address space
        cursor = conn.execute("SELECT * FROM address_spaces WHERE space_id = ?", (space_id,))
        updated = dict(cursor.fetchone())
        
        return {"status": "updated", "space_id": space_id, "address_space": updated}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating address space {space_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/topology/address-spaces/{space_id}")
async def delete_address_space(space_id: str):
    """Delete an address space (only if no subnets reference it)."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Check if address space exists
        cursor = conn.execute("SELECT space_id FROM address_spaces WHERE space_id = ?", (space_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Address space {space_id} not found")
        
        # Check for subnets referencing this address space
        subnets_cursor = conn.execute("SELECT COUNT(*) FROM subnets WHERE address_space_id = ?", (space_id,))
        subnet_count = subnets_cursor.fetchone()[0]
        if subnet_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete address space {space_id}: it has {subnet_count} subnets"
            )
        
        conn.execute("DELETE FROM address_spaces WHERE space_id = ?", (space_id,))
        conn.commit()
        
        return {"status": "deleted", "space_id": space_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting address space {space_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========== Subnet Endpoints ==========

@router.get("/topology/subnets")
async def list_subnets(
    location_id: Optional[str] = Query(None, description="Filter by location"),
    address_space_id: Optional[str] = Query(None, description="Filter by address space"),
):
    """List all subnets with optional filters."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        query = "SELECT * FROM subnets WHERE 1=1"
        params = []
        
        if location_id:
            query += " AND location_id = ?"
            params.append(location_id)
        
        if address_space_id:
            query += " AND address_space_id = ?"
            params.append(address_space_id)
        
        query += " ORDER BY cidr"
        
        cursor = conn.execute(query, params)
        subnets = [dict(row) for row in cursor.fetchall()]
        return {"subnets": subnets}
    except Exception as e:
        logger.error(f"Error listing subnets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topology/subnets")
async def create_subnet(subnet: SubnetCreate):
    """Create a new subnet."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Check if subnet already exists
        existing = conn.execute("SELECT subnet_id FROM subnets WHERE subnet_id = ?", (subnet.subnet_id,))
        if existing.fetchone():
            raise HTTPException(status_code=400, detail=f"Subnet {subnet.subnet_id} already exists")
        
        # Check if CIDR already exists
        cidr_existing = conn.execute("SELECT subnet_id FROM subnets WHERE cidr = ?", (subnet.cidr,))
        if cidr_existing.fetchone():
            raise HTTPException(status_code=400, detail=f"Subnet with CIDR {subnet.cidr} already exists")
        
        # Validate address space exists
        space_cursor = conn.execute("SELECT space_id FROM address_spaces WHERE space_id = ?", (subnet.address_space_id,))
        if not space_cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Address space {subnet.address_space_id} not found")
        
        # Validate location exists (required by schema)
        if not subnet.location_id:
            raise HTTPException(status_code=400, detail="location_id is required")
        
        loc_cursor = conn.execute("SELECT location_id FROM locations WHERE location_id = ?", (subnet.location_id,))
        if not loc_cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Location {subnet.location_id} not found")
        
        # Set default purpose if not provided
        purpose = "USER"  # Default purpose
        
        conn.execute("""
            INSERT INTO subnets (subnet_id, name, cidr, address_space_id, location_id, vlan_id, purpose, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            subnet.subnet_id,
            subnet.name,
            subnet.cidr,
            subnet.address_space_id,
            subnet.location_id,
            subnet.vlan_id,
            purpose,
            subnet.description,
        ))
        conn.commit()
        
        # Return the created subnet
        cursor = conn.execute("SELECT * FROM subnets WHERE subnet_id = ?", (subnet.subnet_id,))
        created = dict(cursor.fetchone())
        
        return {"status": "created", "subnet_id": subnet.subnet_id, "subnet": created}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subnet: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/topology/subnets/{subnet_id}")
async def update_subnet(subnet_id: str, update: SubnetUpdate):
    """Update a subnet."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Check if subnet exists
        existing = conn.execute("SELECT * FROM subnets WHERE subnet_id = ?", (subnet_id,))
        existing_row = existing.fetchone()
        if not existing_row:
            raise HTTPException(status_code=404, detail=f"Subnet {subnet_id} not found")
        
        # Validate address space if provided
        if update.address_space_id:
            space_cursor = conn.execute("SELECT space_id FROM address_spaces WHERE space_id = ?", (update.address_space_id,))
            if not space_cursor.fetchone():
                raise HTTPException(status_code=400, detail=f"Address space {update.address_space_id} not found")
        
        # Validate location if provided
        if update.location_id:
            loc_cursor = conn.execute("SELECT location_id FROM locations WHERE location_id = ?", (update.location_id,))
            if not loc_cursor.fetchone():
                raise HTTPException(status_code=400, detail=f"Location {update.location_id} not found")
        
        # Check if CIDR already exists (if changing CIDR)
        if update.cidr:
            cidr_existing = conn.execute("SELECT subnet_id FROM subnets WHERE cidr = ? AND subnet_id != ?", (update.cidr, subnet_id))
            if cidr_existing.fetchone():
                raise HTTPException(status_code=400, detail=f"Subnet with CIDR {update.cidr} already exists")
        
        # Build update query dynamically
        updates = []
        params = []
        
        if update.name is not None:
            updates.append("name = ?")
            params.append(update.name)
        if update.cidr is not None:
            updates.append("cidr = ?")
            params.append(update.cidr)
        if update.address_space_id is not None:
            updates.append("address_space_id = ?")
            params.append(update.address_space_id)
        if update.location_id is not None:
            updates.append("location_id = ?")
            params.append(update.location_id)
        if update.vlan_id is not None:
            updates.append("vlan_id = ?")
            params.append(update.vlan_id)
        if update.description is not None:
            updates.append("description = ?")
            params.append(update.description)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        params.append(subnet_id)
        query = f"UPDATE subnets SET {', '.join(updates)} WHERE subnet_id = ?"
        conn.execute(query, params)
        conn.commit()
        
        # Return updated subnet
        cursor = conn.execute("SELECT * FROM subnets WHERE subnet_id = ?", (subnet_id,))
        updated = dict(cursor.fetchone())
        
        return {"status": "updated", "subnet_id": subnet_id, "subnet": updated}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subnet: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/topology/subnets/{subnet_id}")
async def delete_subnet(subnet_id: str):
    """Delete a subnet."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Check if subnet exists
        cursor = conn.execute("SELECT subnet_id FROM subnets WHERE subnet_id = ?", (subnet_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Subnet {subnet_id} not found")
        
        conn.execute("DELETE FROM subnets WHERE subnet_id = ?", (subnet_id,))
        conn.commit()
        
        return {"status": "deleted", "subnet_id": subnet_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting subnet {subnet_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========== Switch Endpoints ==========

@router.get("/topology/switches")
async def list_switches(
    location_id: Optional[str] = Query(None, description="Filter by location"),
    search: Optional[str] = Query(None, description="Search by name or switch_id"),
):
    """List all switches with optional filters."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        query = "SELECT * FROM switches WHERE 1=1"
        params = []
        
        if location_id:
            query += " AND location_id = ?"
            params.append(location_id)
        
        if search:
            query += " AND (COALESCE(name, hostname) LIKE ? OR switch_id LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
        
        query += " ORDER BY COALESCE(name, hostname)"
        
        cursor = conn.execute(query, params)
        switches = [dict(row) for row in cursor.fetchall()]
        return {"switches": switches}
    except Exception as e:
        logger.error(f"Error listing switches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topology/switches")
async def create_switch(switch: SwitchCreate):
    """Create a new switch."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Check if switch already exists
        existing = conn.execute("SELECT switch_id FROM switches WHERE switch_id = ?", (switch.switch_id,))
        if existing.fetchone():
            raise HTTPException(status_code=400, detail=f"Switch {switch.switch_id} already exists")
        
        # Validate location exists
        loc_cursor = conn.execute("SELECT location_id FROM locations WHERE location_id = ?", (switch.location_id,))
        if not loc_cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Location {switch.location_id} not found")
        
        # Use switch_id as hostname if name not provided
        hostname = switch.name or switch.switch_id
        # Provide default for management_ip if not provided (schema requires it)
        management_ip = switch.management_ip or ''
        
        conn.execute("""
            INSERT INTO switches (switch_id, hostname, name, location_id, model, management_ip, serial_number, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            switch.switch_id,
            hostname,
            switch.name,
            switch.location_id,
            switch.model,
            management_ip,
            switch.serial_number,
            switch.description,
        ))
        conn.commit()
        
        # Return the created switch
        cursor = conn.execute("SELECT * FROM switches WHERE switch_id = ?", (switch.switch_id,))
        created = dict(cursor.fetchone())
        
        return {"status": "created", "switch_id": switch.switch_id, "switch": created}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating switch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/topology/switches/{switch_id}")
async def update_switch(switch_id: str, update: SwitchUpdate):
    """Update a switch."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Check if switch exists
        existing = conn.execute("SELECT * FROM switches WHERE switch_id = ?", (switch_id,))
        existing_row = existing.fetchone()
        if not existing_row:
            raise HTTPException(status_code=404, detail=f"Switch {switch_id} not found")
        
        # Validate location if provided
        if update.location_id:
            loc_cursor = conn.execute("SELECT location_id FROM locations WHERE location_id = ?", (update.location_id,))
            if not loc_cursor.fetchone():
                raise HTTPException(status_code=400, detail=f"Location {update.location_id} not found")
        
        # Build update query dynamically
        updates = []
        params = []
        
        if update.name is not None:
            updates.append("name = ?")
            params.append(update.name)
            updates.append("hostname = ?")
            params.append(update.name)  # Update hostname too
        if update.location_id is not None:
            updates.append("location_id = ?")
            params.append(update.location_id)
        if update.model is not None:
            updates.append("model = ?")
            params.append(update.model)
        if update.management_ip is not None:
            updates.append("management_ip = ?")
            params.append(update.management_ip)
        if update.serial_number is not None:
            updates.append("serial_number = ?")
            params.append(update.serial_number)
        if update.description is not None:
            updates.append("description = ?")
            params.append(update.description)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        params.append(switch_id)
        query = f"UPDATE switches SET {', '.join(updates)} WHERE switch_id = ?"
        conn.execute(query, params)
        conn.commit()
        
        # Return updated switch
        cursor = conn.execute("SELECT * FROM switches WHERE switch_id = ?", (switch_id,))
        updated = dict(cursor.fetchone())
        
        return {"status": "updated", "switch_id": switch_id, "switch": updated}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating switch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/topology/switches/{switch_id}")
async def delete_switch(switch_id: str):
    """Delete a switch."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Check if switch exists
        cursor = conn.execute("SELECT switch_id FROM switches WHERE switch_id = ?", (switch_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Switch {switch_id} not found")
        
        # Note: We could check for references in other tables if needed
        # (e.g., sketches table might reference switch_id, but it's not a foreign key constraint)
        
        conn.execute("DELETE FROM switches WHERE switch_id = ?", (switch_id,))
        conn.commit()
        
        return {"status": "deleted", "switch_id": switch_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting switch {switch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topology/hierarchy")
async def get_topology_hierarchy():
    """Get the complete topology hierarchy tree."""
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Get all locations
        cursor = conn.execute("SELECT * FROM locations ORDER BY type, name")
        all_locations = [dict(row) for row in cursor.fetchall()]
        
        # Build tree structure
        location_map = {loc['location_id']: loc for loc in all_locations}
        root_locations = [loc for loc in all_locations if not loc.get('parent_id')]
        
        def build_tree(location):
            """Recursively build location tree."""
            children = [
                build_tree(location_map[child_id])
                for child_id, loc in location_map.items()
                if loc.get('parent_id') == location['location_id']
            ]
            
            # Get subnets and switches for this location
            subnets_cursor = conn.execute("SELECT subnet_id, name, cidr FROM subnets WHERE location_id = ?", (location['location_id'],))
            subnets = [dict(row) for row in subnets_cursor.fetchall()]
            
            switches_cursor = conn.execute("SELECT switch_id, name, model FROM switches WHERE location_id = ?", (location['location_id'],))
            switches = [dict(row) for row in switches_cursor.fetchall()]
            
            return {
                **location,
                "children": children,
                "subnets": subnets,
                "switches": switches,
            }
        
        tree = [build_tree(loc) for loc in root_locations]
        
        return {"hierarchy": tree}
    except Exception as e:
        logger.error(f"Error building topology hierarchy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topology/resolve-ip")
async def resolve_ip_to_subnet(ip: str = Query(..., description="IP address to resolve")):
    """
    Resolve an IP address to its subnet and location.
    
    Returns the subnet, location hierarchy, and related information.
    """
    import ipaddress
    
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Parse IP
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid IP address: {ip}")
        
        # Get all subnets
        cursor = conn.execute("SELECT * FROM subnets")
        subnets = [dict(row) for row in cursor.fetchall()]
        
        # Find matching subnet (longest prefix match)
        best_match = None
        best_prefix_len = -1
        
        for subnet in subnets:
            try:
                subnet_net = ipaddress.ip_network(subnet['cidr'], strict=False)
                if ip_obj in subnet_net:
                    prefix_len = subnet_net.prefixlen
                    if prefix_len > best_prefix_len:
                        best_prefix_len = prefix_len
                        best_match = subnet
            except ValueError:
                # Invalid CIDR, skip
                continue
        
        if not best_match:
            return {
                "ip": ip,
                "subnet": None,
                "location": None,
                "location_path": None,
            }
        
        # Get location for this subnet
        location = None
        location_path = None
        
        if best_match.get('location_id'):
            loc_cursor = conn.execute("SELECT * FROM locations WHERE location_id = ?", (best_match['location_id'],))
            loc_row = loc_cursor.fetchone()
            if loc_row:
                location = dict(loc_row)
                
                # Build location path
                path_parts = []
                current_id = location.get('parent_id')
                path_parts.insert(0, f"{location['type']}: {location['name']}")
                
                while current_id:
                    parent_cursor = conn.execute("SELECT location_id, name, type, parent_id FROM locations WHERE location_id = ?", (current_id,))
                    parent_row = parent_cursor.fetchone()
                    if parent_row:
                        parent = dict(parent_row)
                        path_parts.insert(0, f"{parent['type']}: {parent['name']}")
                        current_id = parent.get('parent_id')
                    else:
                        break
                
                location_path = " > ".join(path_parts)
        
        return {
            "ip": ip,
            "subnet": {
                "subnet_id": best_match['subnet_id'],
                "name": best_match['name'],
                "cidr": best_match['cidr'],
                "vlan_id": best_match.get('vlan_id'),
            },
            "location": location,
            "location_path": location_path,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving IP {ip}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

