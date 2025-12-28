"""
SGT Lifecycle Management

Manages Security Group Tags (SGTs) with stable registry and dynamic membership.

Key concepts:
- SGT Registry: Stable SGT definitions (don't change frequently)
- SGT Membership: Dynamic endpoint→SGT assignments (change as endpoints move/change)
- Assignment History: Audit trail of all SGT assignments
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from clarion.storage import get_database
from clarion.clustering.confidence import ConfidenceScorer

logger = logging.getLogger(__name__)


class SGTLifecycleManager:
    """
    Manages SGT lifecycle: registry, membership, and history.
    
    Key principles:
    1. SGTs are stable - once created, they rarely change
    2. Endpoint assignments are dynamic - endpoints move between SGTs
    3. History is preserved - all assignment changes are tracked
    4. Confidence scores track assignment certainty
    
    Example:
        >>> manager = SGTLifecycleManager()
        >>> 
        >>> # Create an SGT
        >>> manager.create_sgt(100, "Users", category="users", description="User devices")
        >>> 
        >>> # Assign endpoint to SGT
        >>> manager.assign_endpoint(endpoint_id="aa:bb:cc:dd:ee:ff", sgt_value=100, 
        ...                        assigned_by="clustering", confidence=0.95, cluster_id=1)
        >>> 
        >>> # Get current SGT for endpoint
        >>> assignment = manager.get_endpoint_sgt("aa:bb:cc:dd:ee:ff")
        >>> print(f"Endpoint is in SGT {assignment['sgt_value']}")
    """
    
    def __init__(self, db=None):
        """
        Initialize SGT lifecycle manager.
        
        Args:
            db: Optional database instance. If None, uses get_database().
        """
        self.db = db or get_database()
    
    # ========== SGT Registry Operations ==========
    
    def create_sgt(
        self,
        sgt_value: int,
        sgt_name: str,
        category: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new SGT in the registry.
        
        Args:
            sgt_value: SGT numeric value (e.g., 100)
            sgt_name: Human-readable name (e.g., "Users")
            category: Optional category (e.g., "users", "servers", "devices", "special")
            description: Optional description
            
        Returns:
            Dict with SGT details
            
        Raises:
            ValueError: If SGT already exists
        """
        # Check if SGT already exists
        existing = self.db.get_sgt(sgt_value)
        if existing and existing.get('is_active', 1):
            raise ValueError(f"SGT {sgt_value} ({existing['sgt_name']}) already exists")
        
        # Create the SGT
        self.db.create_sgt(sgt_value, sgt_name, category, description)
        
        logger.info(f"Created SGT {sgt_value}: {sgt_name}")
        return self.db.get_sgt(sgt_value)
    
    def get_sgt(self, sgt_value: int) -> Optional[Dict[str, Any]]:
        """
        Get an SGT from the registry.
        
        Args:
            sgt_value: SGT numeric value
            
        Returns:
            Dict with SGT details, or None if not found
        """
        return self.db.get_sgt(sgt_value)
    
    def list_sgts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        List all SGTs in the registry.
        
        Args:
            active_only: If True, only return active SGTs
            
        Returns:
            List of SGT dicts
        """
        return self.db.list_sgts(active_only=active_only)
    
    def update_sgt(
        self,
        sgt_value: int,
        sgt_name: Optional[str] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Update an SGT in the registry.
        
        Args:
            sgt_value: SGT numeric value
            sgt_name: New name (optional)
            category: New category (optional)
            description: New description (optional)
            is_active: Active status (optional)
            
        Returns:
            Updated SGT dict
            
        Raises:
            ValueError: If SGT not found
        """
        existing = self.db.get_sgt(sgt_value)
        if not existing:
            raise ValueError(f"SGT {sgt_value} not found")
        
        self.db.update_sgt(sgt_value, sgt_name, category, description, is_active)
        
        logger.info(f"Updated SGT {sgt_value}")
        return self.db.get_sgt(sgt_value)
    
    def deactivate_sgt(self, sgt_value: int) -> None:
        """
        Deactivate an SGT (soft delete).
        
        This marks the SGT as inactive but doesn't delete assignments.
        
        Args:
            sgt_value: SGT numeric value
        """
        self.update_sgt(sgt_value, is_active=False)
        logger.info(f"Deactivated SGT {sgt_value}")
    
    # ========== SGT Membership Operations ==========
    
    def assign_endpoint(
        self,
        endpoint_id: str,
        sgt_value: int,
        assigned_by: str = "clustering",
        confidence: Optional[float] = None,
        cluster_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Assign an endpoint to an SGT.
        
        This creates/updates the membership and records history.
        
        Args:
            endpoint_id: Endpoint identifier (MAC address)
            sgt_value: SGT to assign
            assigned_by: Who/what assigned it ("clustering", "manual", "ise", "incremental")
            confidence: Confidence score (0.0-1.0)
            cluster_id: Optional cluster ID this came from
            
        Returns:
            Membership dict with assignment details
            
        Raises:
            ValueError: If SGT doesn't exist or is inactive
        """
        # Verify SGT exists and is active
        sgt = self.db.get_sgt(sgt_value)
        if not sgt:
            raise ValueError(f"SGT {sgt_value} not found")
        if not sgt.get('is_active', 1):
            raise ValueError(f"SGT {sgt_value} is not active")
        
        # Calculate confidence if not provided
        if confidence is None:
            # Get cluster assignment confidence if available
            cluster_confidence = None
            if cluster_id is not None:
                conn = self.db._get_connection()
                cursor = conn.execute("""
                    SELECT confidence FROM cluster_assignments 
                    WHERE endpoint_id = ? AND cluster_id = ?
                """, (endpoint_id, cluster_id))
                row = cursor.fetchone()
                if row:
                    cluster_confidence = row[0]
            
            # Get assignment history count for stability
            history = self.get_assignment_history(endpoint_id)
            assignment_count = len(history) if history else 0
            
            # Calculate SGT confidence
            confidence = ConfidenceScorer.for_sgt_assignment(
                cluster_confidence=cluster_confidence or 0.7,
                assignment_history_count=assignment_count,
            )
            
            # Override with perfect confidence for manual assignments
            if assigned_by == "manual":
                confidence = 1.0
        
        # Assign the endpoint
        self.db.assign_sgt_to_endpoint(
            endpoint_id=endpoint_id,
            sgt_value=sgt_value,
            assigned_by=assigned_by,
            confidence=confidence,
            cluster_id=cluster_id,
        )
        
        logger.info(f"Assigned endpoint {endpoint_id} to SGT {sgt_value} (confidence={confidence})")
        return self.db.get_endpoint_sgt(endpoint_id)
    
    def get_endpoint_sgt(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current SGT assignment for an endpoint.
        
        Args:
            endpoint_id: Endpoint identifier
            
        Returns:
            Membership dict, or None if endpoint has no SGT assignment
        """
        return self.db.get_endpoint_sgt(endpoint_id)
    
    def unassign_endpoint(self, endpoint_id: str) -> None:
        """
        Unassign SGT from an endpoint.
        
        This removes the membership and records the unassignment in history.
        
        Args:
            endpoint_id: Endpoint identifier
        """
        assignment = self.db.get_endpoint_sgt(endpoint_id)
        if assignment:
            self.db.unassign_sgt_from_endpoint(endpoint_id)
            logger.info(f"Unassigned SGT {assignment['sgt_value']} from endpoint {endpoint_id}")
    
    def list_endpoints_by_sgt(self, sgt_value: int) -> List[Dict[str, Any]]:
        """
        List all endpoints assigned to a specific SGT.
        
        Args:
            sgt_value: SGT numeric value
            
        Returns:
            List of membership dicts
        """
        return self.db.list_endpoints_by_sgt(sgt_value)
    
    def get_sgt_member_count(self, sgt_value: int) -> int:
        """
        Get the number of endpoints assigned to an SGT.
        
        Args:
            sgt_value: SGT numeric value
            
        Returns:
            Number of endpoints in this SGT
        """
        members = self.db.list_endpoints_by_sgt(sgt_value)
        return len(members)
    
    def get_assignment_history(self, endpoint_id: str) -> List[Dict[str, Any]]:
        """
        Get assignment history for an endpoint.
        
        Args:
            endpoint_id: Endpoint identifier
            
        Returns:
            List of historical assignments (ordered by assigned_at DESC)
        """
        return self.db.get_sgt_assignment_history(endpoint_id)
    
    # ========== Bulk Operations ==========
    
    def assign_endpoints_bulk(
        self,
        assignments: List[Dict[str, Any]],
        assigned_by: str = "clustering",
    ) -> Dict[str, Any]:
        """
        Assign multiple endpoints to SGTs in bulk.
        
        Args:
            assignments: List of dicts with keys: endpoint_id, sgt_value, confidence (optional), cluster_id (optional)
            assigned_by: Who/what assigned them
            
        Returns:
            Dict with summary: assigned_count, errors (list)
        """
        assigned_count = 0
        errors = []
        
        for assignment in assignments:
            try:
                self.assign_endpoint(
                    endpoint_id=assignment['endpoint_id'],
                    sgt_value=assignment['sgt_value'],
                    assigned_by=assigned_by,
                    confidence=assignment.get('confidence'),
                    cluster_id=assignment.get('cluster_id'),
                )
                assigned_count += 1
            except Exception as e:
                errors.append({
                    'endpoint_id': assignment.get('endpoint_id'),
                    'error': str(e),
                })
        
        result = {
            'assigned_count': assigned_count,
            'total_count': len(assignments),
            'errors': errors,
        }
        
        logger.info(f"Bulk assigned {assigned_count}/{len(assignments)} endpoints")
        return result
    
    def get_sgt_summary(self, sgt_value: int) -> Dict[str, Any]:
        """
        Get comprehensive summary for an SGT.
        
        Args:
            sgt_value: SGT numeric value
            
        Returns:
            Dict with SGT details, member count, and statistics
        """
        sgt = self.db.get_sgt(sgt_value)
        if not sgt:
            return {}
        
        members = self.db.list_endpoints_by_sgt(sgt_value)
        
        # Calculate statistics
        confidences = [m.get('confidence') for m in members if m.get('confidence') is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None
        
        # Count by assignment source
        by_source = {}
        for member in members:
            source = member.get('assigned_by', 'unknown')
            by_source[source] = by_source.get(source, 0) + 1
        
        return {
            'sgt': sgt,
            'member_count': len(members),
            'average_confidence': avg_confidence,
            'assignments_by_source': by_source,
        }
    
    def list_all_assignments(
        self,
        sgt_value: Optional[int] = None,
        assigned_by: Optional[str] = None,
        min_confidence: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all SGT assignments with optional filters.
        
        Args:
            sgt_value: Filter by SGT value
            assigned_by: Filter by assignment source
            min_confidence: Minimum confidence score
            
        Returns:
            List of membership dicts
        """
        conn = self.db._get_connection()
        
        query = "SELECT * FROM sgt_membership WHERE 1=1"
        params = []
        
        if sgt_value is not None:
            query += " AND sgt_value = ?"
            params.append(sgt_value)
        
        if assigned_by:
            query += " AND assigned_by = ?"
            params.append(assigned_by)
        
        if min_confidence is not None:
            query += " AND confidence >= ?"
            params.append(min_confidence)
        
        query += " ORDER BY assigned_at DESC"
        
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

