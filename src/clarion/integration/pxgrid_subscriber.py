"""
pxGrid Subscriber Service

Service that subscribes to pxGrid events and processes them to update the Clarion database.
This handles real-time ISE session and endpoint events, populating the user database
and tracking current SGT assignments.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Optional
import hashlib

from clarion.integration.pxgrid_client import (
    PxGridClient,
    PxGridConfig,
    ISESessionEvent,
    ISEEndpointEvent,
)
from clarion.storage import get_database

logger = logging.getLogger(__name__)


class PxGridSubscriber:
    """
    pxGrid subscriber service that processes ISE events and updates the database.
    
    This service:
    1. Connects to pxGrid
    2. Subscribes to session and endpoint events
    3. Processes events to update user database
    4. Stores current SGT assignments from ISE
    5. Tracks user-device associations
    """
    
    def __init__(self, config: PxGridConfig):
        """Initialize pxGrid subscriber."""
        self.config = config
        self.client = PxGridClient(config)
        self.db = get_database()
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def start(self) -> bool:
        """
        Start the pxGrid subscriber service.
        
        Returns:
            True if started successfully
        """
        if self.is_running:
            logger.warning("pxGrid subscriber is already running")
            return True
        
        try:
            # Connect to pxGrid
            if not self.client.connect():
                logger.error("Failed to connect to pxGrid")
                return False
            
            # Subscribe to session events
            self.client.subscribe_to_session_events(self._handle_session_event)
            
            # Subscribe to endpoint events
            self.client.subscribe_to_endpoint_events(self._handle_endpoint_event)
            
            # Start processing thread (for future WebSocket implementation)
            self.is_running = True
            self._stop_event.clear()
            
            logger.info("✅ pxGrid subscriber started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start pxGrid subscriber: {e}", exc_info=True)
            self.is_running = False
            return False
    
    def stop(self) -> None:
        """Stop the pxGrid subscriber service."""
        if not self.is_running:
            return
        
        logger.info("Stopping pxGrid subscriber...")
        self.is_running = False
        self._stop_event.set()
        
        if self.client:
            self.client.disconnect()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        
        logger.info("pxGrid subscriber stopped")
    
    def _handle_session_event(self, event: ISESessionEvent) -> None:
        """
        Handle an ISE session event from pxGrid.
        
        This processes session events to:
        1. Create/update user records
        2. Create user-device associations
        3. Store current SGT assignments
        4. Update user last_seen timestamps
        """
        try:
            logger.debug(f"Processing session event: {event.session_id} ({event.state})")
            
            # Only process authenticated and updated sessions
            if event.state not in ['authenticated', 'updated']:
                if event.state == 'terminated':
                    # Clear assignment when session terminates
                    self.db.clear_ise_session_assignment(event.session_id)
                return
            
            if not event.mac_address:
                logger.warning(f"Session event {event.session_id} missing MAC address")
                return
            
            # Process user information if username is present
            user_id = None
            if event.username:
                user_id = self._ensure_user_exists(
                    username=event.username,
                    source="ise"
                )
                
                # Update user last_seen timestamp
                if user_id:
                    self.db.update_user_last_seen(user_id)
            
            # Create/update user-device association
            if user_id and event.mac_address:
                self.db.create_user_device_association(
                    user_id=user_id,
                    endpoint_id=event.mac_address,
                    ip_address=event.ip_address,
                    association_type="ise_session",
                    session_id=event.session_id
                )
            
            # Store AD groups from session (if available)
            if user_id and event.ad_groups:
                for group_name in event.ad_groups:
                    # Generate a simple group_id from group_name
                    group_id = hashlib.md5(group_name.encode()).hexdigest()
                    try:
                        self.db.create_ad_group_membership(
                            user_id=user_id,
                            group_id=group_id,
                            group_name=group_name
                        )
                    except Exception as e:
                        # Group membership might already exist
                        logger.debug(f"Could not add group membership {group_name}: {e}")
            
            # Store current SGT assignment from ISE
            self.db.store_ise_session_sgt_assignment(
                endpoint_id=event.mac_address,
                user_id=user_id,
                session_id=event.session_id,
                user_sgt=event.user_sgt,
                device_sgt=event.device_sgt,
                current_sgt=event.sgt_value,
                ise_profile=event.ise_profile,
                policy_set=event.policy_set,
                authz_profile=event.authz_profile,
                ip_address=event.ip_address,
                switch_id=event.switch_id
            )
            
            logger.debug(
                f"✅ Processed session event {event.session_id}: "
                f"user={event.username}, mac={event.mac_address}, sgt={event.sgt_value}"
            )
            
        except Exception as e:
            logger.error(f"Error processing session event: {e}", exc_info=True)
    
    def _handle_endpoint_event(self, event: ISEEndpointEvent) -> None:
        """
        Handle an ISE endpoint event from pxGrid.
        
        This processes endpoint events to update device profiles and SGT assignments.
        """
        try:
            logger.debug(f"Processing endpoint event: {event.mac_address}")
            
            if not event.mac_address:
                logger.warning("Endpoint event missing MAC address")
                return
            
            # Update identity table with endpoint information
            # Note: This could also update the endpoints table if it exists
            # For now, we'll just log it
            
            # If endpoint has SGT assignment, store it
            if event.sgt_value:
                # Endpoint events don't have user_id or session_id
                self.db.store_ise_session_sgt_assignment(
                    endpoint_id=event.mac_address,
                    user_id=None,
                    session_id=f"endpoint-{event.mac_address}",  # Placeholder
                    user_sgt=None,
                    device_sgt=event.sgt_value,
                    current_sgt=event.sgt_value,
                    ise_profile=event.ise_profile,
                    policy_set=None,
                    authz_profile=None,
                    ip_address=event.ip_address,
                    switch_id=None
                )
            
            logger.debug(f"✅ Processed endpoint event: mac={event.mac_address}, sgt={event.sgt_value}")
            
        except Exception as e:
            logger.error(f"Error processing endpoint event: {e}", exc_info=True)
    
    def _ensure_user_exists(self, username: str, source: str = "ise") -> Optional[str]:
        """
        Ensure a user exists in the database, creating if needed.
        
        Args:
            username: Username
            source: Data source ("ise", "ad", "manual")
            
        Returns:
            user_id if user exists or was created, None otherwise
        """
        # Generate user_id from username (for ISE, we use username as user_id)
        # In production, you might want to use AD SID or ISE internal ID
        user_id = username.lower().strip()
        
        # Check if user exists
        existing_user = self.db.get_user(user_id)
        if existing_user:
            return user_id
        
        # Create new user
        try:
            self.db.create_user(
                user_id=user_id,
                username=username,
                source=source
            )
            logger.debug(f"Created new user: {username}")
            return user_id
        except Exception as e:
            logger.warning(f"Could not create user {username}: {e}")
            return None

