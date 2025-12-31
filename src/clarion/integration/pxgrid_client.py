"""
Cisco ISE pxGrid Client

Provides pxGrid subscription capabilities for real-time ISE session and endpoint events.
pxGrid is a pub/sub messaging system that enables ISE to push events to external systems.

Key Topics:
- com.cisco.ise.session - Authentication session events
- com.cisco.ise.endpoint - Endpoint/device events
- com.cisco.ise.anc - Adaptive Network Control events
"""

from __future__ import annotations

import json
import logging
import ssl
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
import requests
from requests.auth import HTTPBasicAuth

# WebSocket support (optional - for future STOMP implementation)
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    websocket = None  # type: ignore

logger = logging.getLogger(__name__)


class PxGridError(Exception):
    """Base exception for pxGrid errors."""
    pass


class PxGridAuthenticationError(PxGridError):
    """Raised when pxGrid authentication fails."""
    pass


class PxGridSubscriptionError(PxGridError):
    """Raised when pxGrid subscription fails."""
    pass


@dataclass
class PxGridConfig:
    """Configuration for pxGrid connection."""
    ise_hostname: str  # ISE hostname or IP (e.g., "192.168.10.31" or "ise.example.com")
    username: str  # pxGrid client username
    password: str  # pxGrid client password (can use certificate-based auth instead)
    client_name: str  # Unique client name (e.g., "clarion-pxgrid-client")
    use_ssl: bool = True
    verify_ssl: bool = False  # Set to False for self-signed certificates
    port: int = 8910  # pxGrid REST API port (default 8910)
    ws_port: int = 8910  # pxGrid WebSocket port (same as REST)
    timeout: int = 30


@dataclass
class ISESessionEvent:
    """ISE session event from pxGrid."""
    session_id: str
    state: str  # 'authenticated', 'updated', 'terminated'
    username: Optional[str]
    mac_address: Optional[str]
    ip_address: Optional[str]
    nas_ip_address: Optional[str]  # Network Access Server IP (switch/router)
    user_sgt: Optional[int]  # User SGT assigned
    device_sgt: Optional[int]  # Device SGT assigned
    sgt_value: Optional[int]  # Current SGT (user takes precedence over device)
    ad_groups: List[str]  # AD groups from session
    ise_profile: Optional[str]  # ISE endpoint profile
    authentication_method: Optional[str]  # e.g., "dot1x", "mab"
    policy_set: Optional[str]  # Policy set that matched
    authz_profile: Optional[str]  # Authorization profile applied
    posture_status: Optional[str]  # Compliance status
    vlan: Optional[int]
    switch_id: Optional[str]
    switch_port: Optional[str]
    timestamp: datetime
    raw_data: Dict[str, Any]  # Full event payload


@dataclass
class ISEEndpointEvent:
    """ISE endpoint event from pxGrid."""
    mac_address: str
    ip_address: Optional[str]
    endpoint_profile: Optional[str]
    device_type: Optional[str]
    posture_status: Optional[str]
    sgt_value: Optional[int]
    ise_profile: Optional[str]
    timestamp: datetime
    raw_data: Dict[str, Any]  # Full event payload


class PxGridClient:
    """
    Cisco ISE pxGrid client for subscribing to real-time events.
    
    pxGrid uses a two-phase authentication:
    1. REST API authentication (get access token)
    2. WebSocket connection for pub/sub messages
    
    Example:
        >>> config = PxGridConfig(
        ...     ise_hostname="192.168.10.31",
        ...     username="clarion-client",
        ...     password="secret",
        ...     client_name="clarion-pxgrid-client"
        ... )
        >>> client = PxGridClient(config)
        >>> await client.connect()
        >>> client.subscribe_to_session_events(callback_function)
    """
    
    def __init__(self, config: PxGridConfig):
        """Initialize pxGrid client."""
        self.config = config
        self.base_url = f"{'https' if config.use_ssl else 'http'}://{config.ise_hostname}:{config.port}"
        self.ws_url = f"{'wss' if config.use_ssl else 'ws'}://{config.ise_hostname}:{config.ws_port}"
        
        self.session = requests.Session()
        self.session.verify = config.verify_ssl
        if not config.verify_ssl:
            # Suppress SSL warnings for self-signed certs
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.access_token: Optional[str] = None
        self.node_name: Optional[str] = None
        self.ws_connection: Optional[websocket.WebSocketApp] = None
        self.subscribed_topics: List[str] = []
        self.is_connected = False
        
        # Event handlers
        self.session_event_handler: Optional[Callable[[ISESessionEvent], None]] = None
        self.endpoint_event_handler: Optional[Callable[[ISEEndpointEvent], None]] = None
    
    def connect(self) -> bool:
        """
        Connect to pxGrid and authenticate.
        
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            PxGridAuthenticationError: If authentication fails
        """
        try:
            # Step 1: Account activation (if first time)
            self._activate_account()
            
            # Step 2: Authenticate and get access token
            self._authenticate()
            
            # Step 3: Get pxGrid node name
            self._get_node_name()
            
            self.is_connected = True
            logger.info(f"✅ Successfully connected to pxGrid at {self.config.ise_hostname}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to pxGrid: {e}", exc_info=True)
            self.is_connected = False
            raise PxGridAuthenticationError(f"pxGrid connection failed: {e}") from e
    
    def _activate_account(self) -> None:
        """Activate pxGrid client account (first-time setup)."""
        url = f"{self.base_url}/pxgrid/control/AccountActivate"
        
        payload = {
            "nodeName": self.config.client_name
        }
        
        try:
            response = self.session.post(
                url,
                json=payload,
                auth=HTTPBasicAuth(self.config.username, self.config.password),
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("accountState") == "PENDING":
                    logger.warning(
                        f"⚠️  pxGrid account '{self.config.client_name}' is pending approval in ISE. "
                        f"Please approve it in ISE GUI: Administration > pxGrid Services > Client Management > Clients"
                    )
                elif result.get("accountState") == "ENABLED":
                    logger.info(f"✅ pxGrid account '{self.config.client_name}' is enabled")
            elif response.status_code == 404:
                # Account doesn't exist yet, will be created on first connection
                logger.info(f"ℹ️  pxGrid account '{self.config.client_name}' will be created on first connection")
            else:
                logger.warning(f"⚠️  Account activation check returned status {response.status_code}")
                
        except requests.RequestException as e:
            logger.warning(f"⚠️  Could not check account activation status: {e}")
    
    def _authenticate(self) -> None:
        """Authenticate with pxGrid and get access token."""
        url = f"{self.base_url}/pxgrid/control/Auth"
        
        # pxGrid authentication uses POST with JSON payload
        payload = {
            "nodeName": self.config.client_name,
            "password": self.config.password
        }
        
        try:
            response = self.session.post(
                url,
                json=payload,
                auth=HTTPBasicAuth(self.config.username, self.config.password),
                timeout=self.config.timeout
            )
            
            if response.status_code != 200:
                raise PxGridAuthenticationError(
                    f"Authentication failed with status {response.status_code}: {response.text}"
                )
            
            result = response.json()
            self.access_token = result.get("access_token")
            
            if not self.access_token:
                raise PxGridAuthenticationError("No access token received from pxGrid")
            
            logger.info("✅ Successfully authenticated to pxGrid")
            
        except requests.RequestException as e:
            raise PxGridAuthenticationError(f"Authentication request failed: {e}") from e
    
    def _get_node_name(self) -> None:
        """Get the pxGrid node name (ISE server name)."""
        url = f"{self.base_url}/pxgrid/control/ServiceLookup"
        
        payload = {
            "name": "com.cisco.ise.session"
        }
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                services = result.get("services", [])
                if services:
                    self.node_name = services[0].get("nodeName")
                    logger.info(f"✅ Found pxGrid node: {self.node_name}")
            else:
                logger.warning(f"⚠️  Service lookup returned status {response.status_code}")
                
        except requests.RequestException as e:
            logger.warning(f"⚠️  Could not get node name: {e}")
    
    def subscribe_to_session_events(
        self,
        callback: Callable[[ISESessionEvent], None]
    ) -> bool:
        """
        Subscribe to ISE session events (com.cisco.ise.session topic).
        
        Args:
            callback: Function to call when session events are received
            
        Returns:
            True if subscription successful
        """
        self.session_event_handler = callback
        return self._subscribe_to_topic("com.cisco.ise.session")
    
    def subscribe_to_endpoint_events(
        self,
        callback: Callable[[ISEEndpointEvent], None]
    ) -> bool:
        """
        Subscribe to ISE endpoint events (com.cisco.ise.endpoint topic).
        
        Args:
            callback: Function to call when endpoint events are received
            
        Returns:
            True if subscription successful
        """
        self.endpoint_event_handler = callback
        return self._subscribe_to_topic("com.cisco.ise.endpoint")
    
    def _subscribe_to_topic(self, topic: str) -> bool:
        """
        Subscribe to a pxGrid topic via WebSocket.
        
        Args:
            topic: pxGrid topic name (e.g., "com.cisco.ise.session")
            
        Returns:
            True if subscription successful
        """
        if not self.is_connected:
            raise PxGridSubscriptionError("Not connected to pxGrid. Call connect() first.")
        
        if topic in self.subscribed_topics:
            logger.info(f"Already subscribed to topic: {topic}")
            return True
        
        # Note: Full WebSocket implementation would go here
        # For now, we'll create a placeholder that can be extended
        logger.info(f"📡 Subscribing to pxGrid topic: {topic}")
        self.subscribed_topics.append(topic)
        
        # TODO: Implement WebSocket connection and subscription
        # This requires:
        # 1. WebSocket connection with authentication
        # 2. Topic subscription message
        # 3. Message handling loop
        # 4. Event parsing and callback invocation
        
        return True
    
    def disconnect(self) -> None:
        """Disconnect from pxGrid."""
        if self.ws_connection:
            self.ws_connection.close()
            self.ws_connection = None
        
        self.is_connected = False
        self.subscribed_topics.clear()
        logger.info("Disconnected from pxGrid")
    
    def parse_session_event(self, event_data: Dict[str, Any]) -> ISESessionEvent:
        """
        Parse a pxGrid session event into ISESessionEvent.
        
        Args:
            event_data: Raw event data from pxGrid
            
        Returns:
            Parsed ISESessionEvent
        """
        # Extract common fields
        session_id = event_data.get("sessionId") or event_data.get("session_id", "")
        state = event_data.get("state", "unknown")
        
        # Extract user/device identity
        username = event_data.get("userName") or event_data.get("username")
        mac_address = event_data.get("macAddress") or event_data.get("mac_address")
        ip_address = event_data.get("ipAddress") or event_data.get("ip_address")
        
        # Extract SGT information
        # SGT can be in multiple locations depending on ISE version
        user_sgt = None
        device_sgt = None
        sgt_value = None
        
        if "userSgt" in event_data:
            user_sgt = event_data["userSgt"]
        elif "user_sgt" in event_data:
            user_sgt = event_data["user_sgt"]
        
        if "deviceSgt" in event_data:
            device_sgt = event_data["deviceSgt"]
        elif "device_sgt" in event_data:
            device_sgt = event_data["device_sgt"]
        
        # Current SGT (user takes precedence)
        if "sgt" in event_data:
            sgt_value = event_data["sgt"]
        elif "sgtValue" in event_data:
            sgt_value = event_data["sgtValue"]
        elif user_sgt is not None:
            sgt_value = user_sgt
        elif device_sgt is not None:
            sgt_value = device_sgt
        
        # Extract AD groups
        ad_groups = []
        if "adGroups" in event_data:
            ad_groups = event_data["adGroups"]
        elif "ad_groups" in event_data:
            ad_groups = event_data["ad_groups"]
        elif "identityGroups" in event_data:
            # Some ISE versions use identityGroups
            ad_groups = event_data["identityGroups"]
        
        if not isinstance(ad_groups, list):
            ad_groups = []
        
        # Extract other fields
        ise_profile = event_data.get("endpointProfile") or event_data.get("endpoint_profile") or event_data.get("ise_profile")
        auth_method = event_data.get("authenticationMethod") or event_data.get("authentication_method")
        policy_set = event_data.get("policySet") or event_data.get("policy_set")
        authz_profile = event_data.get("authorizationProfile") or event_data.get("authorization_profile")
        posture_status = event_data.get("postureStatus") or event_data.get("posture_status")
        
        # Extract network context
        nas_ip = event_data.get("nasIpAddress") or event_data.get("nas_ip_address")
        vlan = event_data.get("vlan")
        switch_id = event_data.get("networkDeviceId") or event_data.get("network_device_id") or nas_ip
        switch_port = event_data.get("networkDevicePort") or event_data.get("network_device_port")
        
        # Timestamp
        timestamp_str = event_data.get("timestamp") or event_data.get("timeStamp")
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()
        
        return ISESessionEvent(
            session_id=session_id,
            state=state,
            username=username,
            mac_address=mac_address,
            ip_address=ip_address,
            nas_ip_address=nas_ip,
            user_sgt=user_sgt,
            device_sgt=device_sgt,
            sgt_value=sgt_value,
            ad_groups=ad_groups,
            ise_profile=ise_profile,
            authentication_method=auth_method,
            policy_set=policy_set,
            authz_profile=authz_profile,
            posture_status=posture_status,
            vlan=vlan,
            switch_id=switch_id,
            switch_port=switch_port,
            timestamp=timestamp,
            raw_data=event_data
        )
    
    def parse_endpoint_event(self, event_data: Dict[str, Any]) -> ISEEndpointEvent:
        """
        Parse a pxGrid endpoint event into ISEEndpointEvent.
        
        Args:
            event_data: Raw event data from pxGrid
            
        Returns:
            Parsed ISEEndpointEvent
        """
        mac_address = event_data.get("macAddress") or event_data.get("mac_address", "")
        ip_address = event_data.get("ipAddress") or event_data.get("ip_address")
        endpoint_profile = event_data.get("endpointProfile") or event_data.get("endpoint_profile")
        device_type = event_data.get("deviceType") or event_data.get("device_type")
        posture_status = event_data.get("postureStatus") or event_data.get("posture_status")
        sgt_value = event_data.get("sgt") or event_data.get("sgtValue") or event_data.get("sgt_value")
        ise_profile = event_data.get("iseProfile") or event_data.get("ise_profile") or endpoint_profile
        
        timestamp_str = event_data.get("timestamp") or event_data.get("timeStamp")
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()
        
        return ISEEndpointEvent(
            mac_address=mac_address,
            ip_address=ip_address,
            endpoint_profile=endpoint_profile,
            device_type=device_type,
            posture_status=posture_status,
            sgt_value=sgt_value,
            ise_profile=ise_profile,
            timestamp=timestamp,
            raw_data=event_data
        )

