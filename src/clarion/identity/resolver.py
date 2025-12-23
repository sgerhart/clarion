"""
Identity Resolver - Map endpoints to users and enrich sketches.

This module resolves the identity chain:
  IP → MAC → Endpoint → User → AD Groups

It enriches EndpointSketches with identity context from ISE sessions
and Active Directory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
import logging

import pandas as pd

from clarion.sketches import EndpointSketch
from clarion.ingest.loader import ClarionDataset
from clarion.ingest.sketch_builder import SketchStore

logger = logging.getLogger(__name__)


@dataclass
class IdentityContext:
    """
    Complete identity context for an endpoint.
    
    Aggregates information from multiple sources:
    - Endpoint inventory (device_type, OS)
    - ISE sessions (username, auth_method, profile)
    - Active Directory (user details, group memberships)
    """
    endpoint_id: str  # MAC address
    device_id: Optional[str] = None
    
    # Device info (from endpoints table)
    device_type: Optional[str] = None
    os: Optional[str] = None
    hostname: Optional[str] = None
    
    # User info (from ISE + AD)
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    
    # ISE context
    ise_profile: Optional[str] = None
    auth_method: Optional[str] = None
    
    # AD groups
    ad_groups: List[str] = field(default_factory=list)
    ad_group_names: List[str] = field(default_factory=list)
    
    # Resolution metadata
    confidence: float = 0.0
    resolution_source: str = "unknown"
    
    def has_user(self) -> bool:
        """Check if we have user identity."""
        return self.username is not None
    
    def has_groups(self) -> bool:
        """Check if we have AD group memberships."""
        return len(self.ad_groups) > 0
    
    def is_privileged(self) -> bool:
        """Check if user is in privileged groups."""
        privileged_groups = {"Privileged-IT", "Network-Admins", "DevOps"}
        return bool(set(self.ad_group_names) & privileged_groups)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "endpoint_id": self.endpoint_id,
            "device_id": self.device_id,
            "device_type": self.device_type,
            "os": self.os,
            "hostname": self.hostname,
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "department": self.department,
            "title": self.title,
            "ise_profile": self.ise_profile,
            "auth_method": self.auth_method,
            "ad_groups": self.ad_groups,
            "ad_group_names": self.ad_group_names,
            "confidence": self.confidence,
            "resolution_source": self.resolution_source,
        }


class IdentityResolver:
    """
    Resolve endpoint identities from multiple data sources.
    
    Resolution chain:
    1. MAC → Endpoint (from endpoints table)
    2. MAC → ISE Session → Username (from ise_sessions table)
    3. Username → User details (from ad_users table)
    4. User → AD Groups (from ad_group_membership table)
    
    Example:
        >>> resolver = IdentityResolver(dataset)
        >>> context = resolver.resolve("aa:bb:cc:dd:ee:ff")
        >>> print(context.username, context.ad_group_names)
    """
    
    def __init__(self, dataset: ClarionDataset):
        """
        Initialize the resolver with dataset tables.
        
        Args:
            dataset: Loaded ClarionDataset with identity tables
        """
        self.dataset = dataset
        
        # Build lookup tables for fast resolution
        self._mac_to_endpoint: Dict[str, pd.Series] = {}
        self._mac_to_session: Dict[str, pd.Series] = {}
        self._username_to_user: Dict[str, pd.Series] = {}
        self._userid_to_user: Dict[str, pd.Series] = {}
        self._user_to_groups: Dict[str, List[str]] = {}
        self._group_id_to_name: Dict[str, str] = {}
        
        self._build_lookups()
    
    def _build_lookups(self) -> None:
        """Build lookup tables from dataset."""
        logger.info("Building identity lookup tables...")
        
        # MAC → Endpoint
        for _, row in self.dataset.endpoints.iterrows():
            self._mac_to_endpoint[row["mac"]] = row
        logger.debug(f"  {len(self._mac_to_endpoint)} MAC→endpoint mappings")
        
        # MAC → ISE Session (most recent session per MAC)
        sessions_sorted = self.dataset.ise_sessions.sort_values(
            "session_start", ascending=False
        )
        for _, row in sessions_sorted.iterrows():
            mac = row["mac"]
            if mac not in self._mac_to_session:
                self._mac_to_session[mac] = row
        logger.debug(f"  {len(self._mac_to_session)} MAC→session mappings")
        
        # Username → User (lowercase for case-insensitive lookup)
        for _, row in self.dataset.ad_users.iterrows():
            username = row["samaccountname"].lower()
            self._username_to_user[username] = row
            self._userid_to_user[row["user_id"]] = row
        logger.debug(f"  {len(self._username_to_user)} username→user mappings")
        
        # Group ID → Name
        for _, row in self.dataset.ad_groups.iterrows():
            self._group_id_to_name[row["group_id"]] = row["group_name"]
        
        # User → Groups
        for _, row in self.dataset.ad_group_membership.iterrows():
            user_id = row["user_id"]
            group_id = row["group_id"]
            if user_id not in self._user_to_groups:
                self._user_to_groups[user_id] = []
            self._user_to_groups[user_id].append(group_id)
        logger.debug(f"  {len(self._user_to_groups)} user→groups mappings")
        
        logger.info("Identity lookup tables built successfully")
    
    def resolve(self, endpoint_id: str) -> IdentityContext:
        """
        Resolve identity for a single endpoint.
        
        Args:
            endpoint_id: MAC address
            
        Returns:
            IdentityContext with all resolved information
        """
        context = IdentityContext(endpoint_id=endpoint_id)
        
        # Step 1: Resolve endpoint info
        if endpoint_id in self._mac_to_endpoint:
            endpoint = self._mac_to_endpoint[endpoint_id]
            context.device_id = endpoint["device_id"]
            context.device_type = endpoint["device_type"]
            context.os = endpoint["os"]
            context.hostname = endpoint["hostname"]
            context.confidence = 0.3
            context.resolution_source = "endpoint_inventory"
        
        # Step 2: Resolve ISE session
        if endpoint_id in self._mac_to_session:
            session = self._mac_to_session[endpoint_id]
            context.ise_profile = session["endpoint_profile"]
            context.auth_method = session["auth_method"]
            
            username = session["username"]
            if pd.notna(username) and username:
                context.username = username
                context.confidence = 0.8
                context.resolution_source = "ise_session"
                
                # Step 3: Resolve user details from AD
                username_lower = username.lower()
                if username_lower in self._username_to_user:
                    user = self._username_to_user[username_lower]
                    context.user_id = user["user_id"]
                    context.email = user["email"]
                    context.department = user["department"]
                    context.title = user["title"]
                    context.confidence = 1.0
                    context.resolution_source = "active_directory"
                    
                    # Step 4: Resolve AD groups
                    if context.user_id in self._user_to_groups:
                        context.ad_groups = self._user_to_groups[context.user_id]
                        context.ad_group_names = [
                            self._group_id_to_name.get(gid, gid)
                            for gid in context.ad_groups
                        ]
        
        return context
    
    def enrich_sketch(self, sketch: EndpointSketch) -> IdentityContext:
        """
        Resolve identity and enrich a sketch with the context.
        
        Args:
            sketch: EndpointSketch to enrich
            
        Returns:
            IdentityContext used for enrichment
        """
        context = self.resolve(sketch.endpoint_id)
        
        # Apply identity to sketch
        sketch.device_id = context.device_id
        sketch.device_type = context.device_type
        sketch.user_id = context.user_id
        sketch.username = context.username
        sketch.ad_groups = context.ad_group_names
        sketch.ise_profile = context.ise_profile
        
        return context
    
    def enrich_store(self, store: SketchStore) -> Dict[str, IdentityContext]:
        """
        Enrich all sketches in a store with identity context.
        
        Args:
            store: SketchStore with sketches to enrich
            
        Returns:
            Dictionary mapping endpoint_id to IdentityContext
        """
        logger.info(f"Enriching {len(store)} sketches with identity context")
        
        contexts = {}
        resolved_users = 0
        resolved_groups = 0
        
        for sketch in store:
            context = self.enrich_sketch(sketch)
            contexts[sketch.endpoint_id] = context
            
            if context.has_user():
                resolved_users += 1
            if context.has_groups():
                resolved_groups += 1
        
        logger.info(
            f"Enriched {len(store)} sketches: "
            f"{resolved_users} with users ({resolved_users/len(store)*100:.1f}%), "
            f"{resolved_groups} with groups ({resolved_groups/len(store)*100:.1f}%)"
        )
        
        return contexts
    
    def get_group_members(self, group_name: str) -> List[str]:
        """
        Get all endpoint IDs (MACs) for members of an AD group.
        
        Args:
            group_name: AD group name
            
        Returns:
            List of endpoint IDs (MACs) for group members
        """
        # Find group ID
        group_id = None
        for gid, name in self._group_id_to_name.items():
            if name == group_name:
                group_id = gid
                break
        
        if not group_id:
            return []
        
        # Find users in this group
        user_ids = set()
        for user_id, groups in self._user_to_groups.items():
            if group_id in groups:
                user_ids.add(user_id)
        
        # Find endpoints owned by these users
        endpoints = []
        for mac, endpoint in self._mac_to_endpoint.items():
            if endpoint["owner_user_id"] in user_ids:
                endpoints.append(mac)
        
        return endpoints
    
    def resolution_stats(self) -> Dict:
        """Get statistics about resolution coverage."""
        return {
            "endpoints": len(self._mac_to_endpoint),
            "sessions": len(self._mac_to_session),
            "users": len(self._username_to_user),
            "groups": len(self._group_id_to_name),
            "user_group_mappings": sum(len(g) for g in self._user_to_groups.values()),
        }


def enrich_sketches(store: SketchStore, dataset: ClarionDataset) -> Dict[str, IdentityContext]:
    """
    Convenience function to enrich all sketches with identity.
    
    Args:
        store: SketchStore with sketches
        dataset: ClarionDataset with identity tables
        
    Returns:
        Dictionary mapping endpoint_id to IdentityContext
    """
    resolver = IdentityResolver(dataset)
    return resolver.enrich_store(store)

