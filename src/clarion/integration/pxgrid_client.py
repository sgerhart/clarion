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
import os
import ssl
import tempfile
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


class PxGridPendingApprovalError(PxGridError):
    """Raised when pxGrid account is pending approval in ISE."""
    pass


@dataclass
class PxGridConfig:
    """Configuration for pxGrid connection."""
    ise_hostname: str  # ISE hostname or IP (e.g., "192.168.10.31" or "ise.example.com")
    client_name: str  # Unique client name (e.g., "clarion-pxgrid-client")
    username: str = ""  # pxGrid client username (optional if using certificates)
    password: str = ""  # pxGrid client password (optional if using certificates)
    use_ssl: bool = True
    verify_ssl: bool = False  # Set to False for self-signed certificates
    port: int = 8910  # pxGrid REST API port (default 8910)
    ws_port: int = 8910  # pxGrid WebSocket port (same as REST)
    timeout: int = 30
    # Certificate-based authentication (mutual TLS)
    client_cert_data: Optional[bytes] = None  # Client certificate data (PEM format)
    client_key_data: Optional[bytes] = None  # Client private key data (PEM format)
    ca_cert_data: Optional[bytes] = None  # CA certificate data for trust (PEM format)


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
        
        # Initialize temporary file handles (for cleanup)
        self._temp_cert_file = None
        self._temp_key_file = None
        self._temp_ca_file = None
        
        # Setup certificate-based authentication (mutual TLS) if certificates are provided
        if config.client_cert_data and config.client_key_data:
            # Create temporary files for certificates (requests requires file paths)
            self._temp_cert_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.crt')
            self._temp_key_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.key')
            
            self._temp_cert_file.write(config.client_cert_data)
            self._temp_cert_file.flush()
            
            self._temp_key_file.write(config.client_key_data)
            self._temp_key_file.flush()
            
            # Use client certificate and key for mutual TLS
            self.session.cert = (self._temp_cert_file.name, self._temp_key_file.name)
            logger.info("Using certificate-based authentication (mutual TLS)")
            
            # If CA cert is provided, use it for verification
            if config.ca_cert_data:
                self._temp_ca_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.crt')
                self._temp_ca_file.write(config.ca_cert_data)
                self._temp_ca_file.flush()
                logger.info("CA certificate provided (using for trust verification)")
        else:
            logger.info("Using password-based authentication")
        
        if not config.verify_ssl:
            # Suppress SSL warnings for self-signed certs
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.access_token: Optional[str] = None
        self.node_name: Optional[str] = None
        self.ws_connection: Optional[websocket.WebSocketApp] = None
        self.subscribed_topics: List[str] = []
        self.is_connected = False
        self.bootstrap_password: Optional[str] = None  # Password returned from AccountCreate
        
        # Event handlers
        self.session_event_handler: Optional[Callable[[ISESessionEvent], None]] = None
        self.endpoint_event_handler: Optional[Callable[[ISEEndpointEvent], None]] = None
    
    def connect(self) -> bool:
        """
        Connect to pxGrid and authenticate.
        
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            PxGridPendingApprovalError: If account is pending approval in ISE
            PxGridAuthenticationError: If authentication fails
        """
        try:
            # Step 1: Account activation (if first time)
            self._activate_account()
            
            # Step 2: Authenticate and get access token
            # Note: For ISE 2.0, Auth endpoint may return 404, but ServiceLookup works with Basic Auth
            try:
                self._authenticate()
            except PxGridAuthenticationError as e:
                if "404" in str(e):
                    logger.warning(f"⚠️  Auth endpoint returned 404 (ISE 2.0 may not require Auth endpoint)")
                    logger.warning(f"⚠️  Continuing with Basic Auth for ServiceLookup...")
                    # For ISE 2.0, we can use Basic Auth directly for ServiceLookup
                    self.access_token = None
                else:
                    raise
            
            # Step 3: Get pxGrid node name (works with Basic Auth even without access token)
            self._get_node_name()
            
            self.is_connected = True
            logger.info(f"✅ Successfully connected to pxGrid at {self.config.ise_hostname}")
            return True
            
        except PxGridPendingApprovalError:
            # Re-raise pending approval errors as-is (don't wrap in AuthenticationError)
            self.is_connected = False
            raise
        except PxGridAuthenticationError:
            # Re-raise authentication errors as-is (don't double-wrap)
            self.is_connected = False
            raise
        except Exception as e:
            logger.error(f"❌ Failed to connect to pxGrid: {e}", exc_info=True)
            self.is_connected = False
            # Only wrap if it's not already a PxGrid error
            if isinstance(e, (PxGridError, PxGridAuthenticationError, PxGridPendingApprovalError)):
                raise
            raise PxGridAuthenticationError(f"pxGrid connection failed: {e}") from e
    
    def test_account_activate(self) -> dict:
        """
        Test AccountActivate only (for test connection button).
        Returns account state information without attempting full authentication.
        """
        use_cert_auth = self.config.client_cert_data and self.config.client_key_data
        url = f"{self.base_url}/pxgrid/control/AccountActivate"
        payload = {"nodeName": self.config.client_name}
        
        try:
            if not use_cert_auth:
                if '@' in self.config.client_name:
                    activate_username = self.config.client_name.split('@')[0]
                elif self.config.username and '@' not in self.config.username:
                    activate_username = self.config.username
                else:
                    activate_username = self.config.client_name
                auth_header = HTTPBasicAuth(activate_username, self.config.password)
            else:
                auth_header = None
            
            response = self.session.post(
                url,
                json=payload,
                auth=auth_header,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                account_state = result.get("accountState", "UNKNOWN")
                version = result.get("version", "unknown")
                return {
                    "success": True,
                    "account_state": account_state,
                    "version": version,
                    "message": f"Account state: {account_state} (pxGrid version {version})"
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "account_state": None,
                    "message": "Authentication failed. Please check your credentials."
                }
            else:
                return {
                    "success": False,
                    "account_state": None,
                    "message": f"AccountActivate failed with status {response.status_code}"
                }
        except requests.RequestException as e:
            return {
                "success": False,
                "account_state": None,
                "message": f"Connection failed: {e}"
            }
    
    def _activate_account(self) -> None:
        """
        Activate pxGrid client account (first-time setup).
        
        Supports both authentication methods:
        - Certificate-based: Uses mutual TLS (certificates set in session.cert)
        - Password-based: Uses HTTP Basic Auth with username/password
        
        For password-based authentication:
        - If client doesn't exist: Use ISE admin credentials to create account via AccountCreate
        - If client exists: Use client credentials to activate via AccountActivate
        
        Note: The username/password in config should be:
        - For new clients: ISE admin username/password
        - For existing clients: Client name (as username) and client password
        """
        use_cert_auth = self.config.client_cert_data and self.config.client_key_data
        
        # First, try AccountActivate (for existing clients)
        url = f"{self.base_url}/pxgrid/control/AccountActivate"
        
        payload = {
            "nodeName": self.config.client_name
        }
        
        try:
            auth_method = "certificate" if use_cert_auth else "password"
            logger.info(f"🔍 Attempting to activate pxGrid account '{self.config.client_name}' (auth: {auth_method})...")
            logger.info(f"🔍 AccountActivate URL: {url}")
            
            # For certificate-based auth, no HTTP Basic Auth needed (mutual TLS handles it)
            # For password-based auth, use HTTP Basic Auth
            # AccountActivate uses the base client name (without @xgrid.cisco.com) for username
            if not use_cert_auth:
                # Extract base name for AccountActivate (ISE uses base name for auth, not full domain)
                if '@' in self.config.client_name:
                    activate_username = self.config.client_name.split('@')[0]
                elif self.config.username and '@' not in self.config.username:
                    activate_username = self.config.username
                else:
                    activate_username = self.config.client_name
                
                logger.info(f"🔍 AccountActivate - Using credentials: username={activate_username}, client_name={self.config.client_name}, password_length={len(self.config.password) if self.config.password else 0}")
                logger.info(f"   - Username is base name (without domain): {activate_username}")
            else:
                activate_username = None
            
            auth_header = None if use_cert_auth else HTTPBasicAuth(activate_username, self.config.password)
            
            logger.warning(f"🔍 AccountActivate request details:")
            logger.warning(f"   - URL: {url}")
            logger.warning(f"   - Payload: {payload}")
            logger.warning(f"   - Auth username: {activate_username if activate_username else 'None (cert auth)'}")
            logger.warning(f"   - Auth password length: {len(self.config.password) if self.config.password else 0}")
            logger.warning(f"   - SSL verify: {self.session.verify}")
            
            logger.warning(f"🔍 SENDING AccountActivate POST REQUEST to ISE...")
            response = self.session.post(
                url,
                json=payload,
                auth=auth_header,
                timeout=self.config.timeout
            )
            
            logger.warning(f"🔍 AccountActivate HTTP response received: status={response.status_code}")
            
            logger.info(f"🔍 AccountActivate response: status={response.status_code}, text_length={len(response.text) if response.text else 0}")
            if response.status_code != 200:
                logger.warning(f"⚠️  AccountActivate response text (first 500 chars): {response.text[:500] if response.text else 'No response text'}")
            
            if response.status_code == 200:
                result = response.json()
                account_state = result.get("accountState")
                logger.warning(f"🔍 AccountActivate response JSON: {result}")
                logger.warning(f"🔍 Account state from AccountActivate: {account_state}")
                # Check if ISE returned a different nodeName (e.g., with @xgrid.cisco.com domain)
                returned_node_name = result.get("nodeName")
                if returned_node_name:
                    logger.warning(f"🔍 ISE returned nodeName: '{returned_node_name}' (we sent: '{self.config.client_name}')")
                    # Use the nodeName that ISE returns for Auth endpoint
                    # Store it temporarily for use in _authenticate
                    self._ise_node_name = returned_node_name
                else:
                    # No nodeName in response, use what we sent
                    self._ise_node_name = self.config.client_name
                if account_state == "PENDING":
                    logger.warning(
                        f"⚠️  pxGrid account '{self.config.client_name}' is pending approval in ISE. "
                        f"Please approve it in ISE GUI: Administration > pxGrid Services > Client Management > Clients"
                    )
                    # Raise special exception for pending approval - don't try to authenticate
                    raise PxGridPendingApprovalError(
                        f"pxGrid account '{self.config.client_name}' was created successfully but is PENDING approval. "
                        f"Please approve it in ISE GUI: Administration > pxGrid Services > Client Management > Clients. "
                        f"After approval, try connecting again."
                    )
                elif account_state == "ENABLED":
                    logger.info(f"✅ pxGrid account '{self.config.client_name}' is enabled")
                    # Account is enabled - if we're using client credentials and this succeeds, the password is correct
                    # If we're using ISE admin credentials, we should note that client exists and needs client password
                    if self.config.username and self.config.username != self.config.client_name:
                        logger.info(f"ℹ️  Account is ENABLED but we're using ISE admin credentials. Client '{self.config.client_name}' exists and is enabled - you may need to use client credentials for authentication.")
                else:
                    logger.info(f"ℹ️  pxGrid account state: {account_state}")
            elif response.status_code == 404:
                # Account doesn't exist, try AccountCreate (requires ISE admin credentials)
                logger.info(f"ℹ️  Account '{self.config.client_name}' doesn't exist, attempting to create...")
                try:
                    self._create_account()
                except PxGridPendingApprovalError:
                    # Re-raise pending approval errors from account creation
                    raise
            elif response.status_code == 401:
                # Authentication failed - client might not exist, or we're using wrong credentials
                # If we're using client credentials (username == client_name), the client should exist
                # If we're using ISE admin credentials (username != client_name), try to create account
                if self.config.username and self.config.username != self.config.client_name:
                    # Using ISE admin credentials - try to create account
                    logger.warning(
                        f"⚠️  Account activation failed with 401 using ISE admin credentials. "
                        f"Username ({self.config.username}) != client_name ({self.config.client_name}). "
                        f"This might mean the client doesn't exist yet. "
                        f"Trying AccountCreate with ISE admin credentials..."
                    )
                    try:
                        bootstrap_password = self._create_account()
                        # _create_account() will raise an exception if it fails
                        # If it returns None, it means account already exists (409) - handled below
                        if bootstrap_password:
                            # Store bootstrap password in config for persistence
                            self.config.password = bootstrap_password
                            self.config.username = self.config.client_name
                            logger.info(f"✅ Account created successfully, bootstrap password stored. Config updated: username={self.config.username}, password_length={len(bootstrap_password)}")
                        else:
                            # Account already exists (409) - _create_account() returned None
                            logger.info(f"ℹ️  Account '{self.config.client_name}' already exists (409). Need client credentials.")
                            raise PxGridAuthenticationError(
                                f"pxGrid client '{self.config.client_name}' already exists in ISE.\n\n"
                                f"To create a fresh client:\n"
                                f"1. Click 'Disable' on the pxGrid connector - this will delete the client from ISE and clear the database\n"
                                f"2. Then click 'Enable' again with ISE admin credentials to create a fresh client\n\n"
                                f"Or manually delete the client from ISE:\n"
                                f"- Go to: Administration > pxGrid Services > Client Management > Clients\n"
                                f"- Find and delete the client named '{self.config.client_name}'\n"
                                f"- Then click 'Enable' again here\n\n"
                                f"Or use certificate-based authentication instead."
                            )
                    except PxGridPendingApprovalError:
                        # Re-raise pending approval errors from account creation
                        raise
                    except PxGridAuthenticationError as e:
                        # If account already exists (409), we should use client credentials
                        if "already exists" in str(e) or "409" in str(e):
                            logger.info(f"ℹ️  Account '{self.config.client_name}' already exists. Need to use client credentials or delete and recreate.")
                            raise PxGridAuthenticationError(
                                f"pxGrid client '{self.config.client_name}' already exists in ISE.\n\n"
                                f"To start fresh:\n"
                                f"1. Click 'Disable' on the pxGrid connector - this will delete the client from ISE and clear the database\n"
                                f"2. Then click 'Enable' again with ISE admin credentials to create a fresh client\n\n"
                                f"OR if you want to use the existing client:\n"
                                f"1. You need the CLIENT password for '{self.config.client_name}'\n"
                                f"2. Update the password in the connector configuration\n"
                                f"3. The username should be '{self.config.client_name}' (the client name)\n\n"
                                f"To find/reset the client password:\n"
                                f"- Go to ISE: Administration > pxGrid Services > Client Management > Clients > {self.config.client_name}\n"
                                f"- You can view or reset the password there\n\n"
                                f"Or use certificate-based authentication instead."
                            )
                        raise
                else:
                    # Using client credentials (username == client_name) - authentication failed
                    # This means either: client doesn't exist, password is wrong, or account is not approved
                    logger.error(
                        f"Account activation failed with 401 using client credentials. "
                        f"Username ({self.config.username}) == client_name ({self.config.client_name}). "
                        f"This could mean:\n"
                        f"1. The client password is incorrect\n"
                        f"2. The client doesn't exist in ISE\n"
                        f"3. The client account is not approved in ISE"
                    )
                    raise PxGridAuthenticationError(
                        f"Authentication failed with client credentials. "
                        f"The client '{self.config.client_name}' may not exist, the password is incorrect, or the account is not approved in ISE. "
                        f"Please verify the client exists and is approved in ISE: Administration > pxGrid Services > Client Management > Clients"
                    )
            else:
                logger.warning(f"⚠️  Account activation check returned status {response.status_code}: {response.text[:200]}")
                
        except requests.RequestException as e:
            logger.warning(f"⚠️  Could not check account activation status: {e}")
    
    def _create_account(self) -> Optional[str]:
        """
        Create a new pxGrid client account.
        
        For certificate-based auth: Certificates are used for mutual TLS
        For password-based auth: Requires ISE admin credentials
        
        Returns:
            Bootstrap password if account was created successfully, None otherwise
        """
        use_cert_auth = self.config.client_cert_data and self.config.client_key_data
        
        url = f"{self.base_url}/pxgrid/control/AccountCreate"
        
        # AccountCreate only takes nodeName - ISE generates and returns the password
        payload = {
            "nodeName": self.config.client_name
        }
        
        try:
            # AccountCreate: According to pxGrid documentation and sample code,
            # AccountCreate does NOT require authentication - ISE generates the client password
            # However, some ISE configurations may require admin credentials via BasicAuth
            # Try without auth first, then with auth if needed
            logger.info(f"Creating pxGrid account '{self.config.client_name}'...")
            
            # Try without authentication first (as per sample code)
            response = self.session.post(
                url,
                json=payload,
                auth=None,  # No authentication required for AccountCreate
                timeout=self.config.timeout
            )
            
            logger.info(f"AccountCreate response (no auth): status={response.status_code}")
            
            # If 401 or 503, try with ISE admin credentials (some ISE configs require auth)
            if response.status_code in (401, 503) and not use_cert_auth and self.config.username and self.config.password:
                logger.info(f"AccountCreate returned {response.status_code}, retrying with ISE admin credentials...")
                auth_header = HTTPBasicAuth(self.config.username, self.config.password)
                response = self.session.post(
                    url,
                    json=payload,
                    auth=auth_header,
                    timeout=self.config.timeout
                )
                logger.info(f"AccountCreate response (with auth): status={response.status_code}, text={response.text[:200]}")
            
            if response.status_code == 200:
                result = response.json()
                bootstrap_password = result.get("password")
                logger.info(f"🔍 AccountCreate response: status=200, has_password={bool(bootstrap_password)}, password_length={len(bootstrap_password) if bootstrap_password else 0}")
                if bootstrap_password:
                    # CRITICAL: Store the bootstrap password - this becomes the client password for subsequent operations
                    # This MUST be saved to database when exception is raised
                    self.bootstrap_password = bootstrap_password
                    # Update config password so it can be used for AccountActivate and Auth
                    self.config.password = bootstrap_password
                    # Update username to client_name for subsequent operations (AccountActivate and Auth use client credentials)
                    self.config.username = self.config.client_name
                    logger.info(f"✅ pxGrid account '{self.config.client_name}' created successfully")
                    logger.info(f"✅ Bootstrap password received from ISE and stored in client object (length: {len(bootstrap_password)})")
                    logger.info(f"   This password MUST be saved to database when PxGridPendingApprovalError is raised")
                    
                    # Check account state by calling AccountActivate with the bootstrap password
                    activate_url = f"{self.base_url}/pxgrid/control/AccountActivate"
                    activate_auth = HTTPBasicAuth(self.config.client_name, bootstrap_password)
                    activate_response = self.session.post(
                        activate_url,
                        json={"nodeName": self.config.client_name},
                        auth=activate_auth,
                        timeout=self.config.timeout
                    )
                    
                    if activate_response.status_code == 200:
                        activate_result = activate_response.json()
                        account_state = activate_result.get("accountState")
                        if account_state == "ENABLED":
                            logger.info(f"✅ pxGrid account '{self.config.client_name}' is ENABLED - ready to use")
                            # Account is enabled, continue with connection
                            return
                        elif account_state == "PENDING":
                            logger.info(
                                f"ℹ️  Account is PENDING approval in ISE. "
                                f"Please approve it in ISE GUI: Administration > pxGrid Services > Client Management > Clients"
                            )
                            # IMPORTANT: Return bootstrap_password even when PENDING so it can be saved to database
                            # Raise special exception for pending approval - don't try to authenticate
                            # But ensure bootstrap_password is available for database storage
                            raise PxGridPendingApprovalError(
                                f"pxGrid account '{self.config.client_name}' was created successfully but is PENDING approval. "
                                f"Please approve it in ISE GUI: Administration > pxGrid Services > Client Management > Clients. "
                                f"After approval, try connecting again."
                            )
                        else:
                            logger.info(f"ℹ️  Account state: {account_state}")
                            # Continue anyway - let authentication try
                            return bootstrap_password
                    else:
                        logger.warning(f"AccountActivate returned {activate_response.status_code}: {activate_response.text[:200]}")
                        # Continue anyway - account was created successfully, might be auto-approved
                        return bootstrap_password
                else:
                    logger.warning(f"⚠️  AccountCreate succeeded but no password in response: {result}")
                    logger.warning(
                        f"⚠️  Account is now PENDING approval. "
                        f"Please approve it in ISE GUI: Administration > pxGrid Services > Client Management > Clients"
                    )
                    return None
            elif response.status_code == 409:
                # Client already exists - we should use client credentials for AccountActivate
                logger.info(f"ℹ️  Client '{self.config.client_name}' already exists in ISE (409 Conflict)")
                # If we're using ISE admin credentials, we need to tell user to delete the client first
                if self.config.username and self.config.username != self.config.client_name:
                    raise PxGridAuthenticationError(
                        f"pxGrid client '{self.config.client_name}' already exists in ISE.\n\n"
                        f"To create a fresh client:\n"
                        f"1. Click 'Disable' on the pxGrid connector - this will delete the client from ISE and clear the database\n"
                        f"2. Then click 'Enable' again with ISE admin credentials to create a fresh client\n\n"
                        f"Or manually delete the client from ISE:\n"
                        f"- Go to: Administration > pxGrid Services > Client Management > Clients\n"
                        f"- Find and delete the client named '{self.config.client_name}'\n"
                        f"- Then click 'Enable' again here\n\n"
                        f"Or use certificate-based authentication instead."
                    )
                # Don't raise error - return None to indicate account exists, let authentication proceed
                # The account should be enabled, so authentication should work with client credentials
                return None
            elif response.status_code == 401:
                # 401 on AccountCreate means ISE admin credentials are invalid or request format is wrong
                error_detail = response.text[:500] if response.text else "No error details provided"
                logger.error(f"AccountCreate 401 response: {error_detail}")
                
                # Check if we're actually using ISE admin credentials (username != client_name)
                if self.config.username and self.config.username == self.config.client_name:
                    # User is using client credentials, but AccountCreate requires ISE admin credentials
                    raise PxGridAuthenticationError(
                        f"Account creation failed with 401. "
                        f"AccountCreate requires ISE admin credentials (username should be your ISE admin username, not '{self.config.client_name}'). "
                        f"If the client '{self.config.client_name}' already exists in ISE, you should use client credentials instead "
                        f"(username='{self.config.client_name}', password=client_password). "
                        f"Response: {error_detail}"
                    )
                else:
                    # Using ISE admin credentials, but they're invalid or format is wrong
                    # Check if password is empty
                    if not self.config.password:
                        raise PxGridAuthenticationError(
                            f"Account creation failed with 401. Password is empty. "
                            f"Please ensure the password is saved in the configuration. "
                            f"Response: {error_detail}"
                        )
                    
                    raise PxGridAuthenticationError(
                        f"Account creation failed with 401. "
                        f"This could mean:\n"
                        f"1. ISE admin credentials are incorrect\n"
                        f"2. ISE admin account doesn't have pxGrid Admin role\n"
                        f"3. pxGrid service is not enabled on ISE\n"
                        f"4. SSL/TLS connection issue (try disabling SSL verification if using self-signed certs)\n\n"
                        f"Username: {self.config.username}\n"
                        f"Password length: {len(self.config.password) if self.config.password else 0}\n"
                        f"URL: {url}\n"
                        f"Response: {error_detail}"
                    )
            else:
                # AccountCreate returned an unexpected status code
                error_detail = response.text[:500] if response.text else "No error details provided"
                logger.error(f"❌ AccountCreate returned unexpected status {response.status_code}: {error_detail}")
                raise PxGridAuthenticationError(
                    f"Account creation failed with status {response.status_code}. "
                    f"This could indicate an ISE configuration issue or network problem. "
                    f"Response: {error_detail}"
                )
                
        except PxGridAuthenticationError:
            raise
        except requests.RequestException as e:
            logger.error(f"❌ AccountCreate request failed: {e}")
            raise PxGridAuthenticationError(
                f"Failed to create pxGrid account '{self.config.client_name}': {e}. "
                f"Please check ISE connectivity and credentials."
            ) from e
    
    def _authenticate(self) -> None:
        """
        Authenticate with pxGrid and get access token.
        
        For certificate-based authentication (mutual TLS):
        - Client certificate and key are used for TLS handshake (set via session.cert)
        - No username/password needed for HTTP Basic Auth
        - JSON payload uses: nodeName (client_name), password can be empty or omitted
        
        For password-based authentication:
        - username should be the client name (nodeName)
        - password should be the client password
        - HTTP Basic Auth uses: client_name as username, client_password as password
        - JSON payload uses: nodeName (client_name) and password (client_password)
        """
        url = f"{self.base_url}/pxgrid/control/Auth"
        
        # Determine authentication method
        use_cert_auth = self.config.client_cert_data and self.config.client_key_data
        
        if use_cert_auth:
            # Certificate-based authentication (mutual TLS)
            # Certificates are already set in session.cert during __init__
            payload = {
                "nodeName": self.config.client_name,
                # Password not needed for cert-based auth, but some ISE versions may require it
                "password": self.config.password if self.config.password else ""
            }
            auth_header = None  # No HTTP Basic Auth for cert-based auth
            logger.info(f"Authenticating to pxGrid using certificate (client: '{self.config.client_name}')...")
        else:
            # Password-based authentication
            # For Auth endpoint: username should be the base client name (without @xgrid.cisco.com domain)
            # The nodeName in payload should be the full client name (with domain if ISE added it)
            # But the HTTP Basic Auth username should be just the base name
            # If username is set and matches the base part of client_name, use it; otherwise extract base name
            if self.config.username and '@' not in self.config.username:
                # Username is already the base name (e.g., "clarion")
                auth_username = self.config.username
            elif '@' in self.config.client_name:
                # Extract base name from client_name (e.g., "clarion" from "clarion@xgrid.cisco.com")
                auth_username = self.config.client_name.split('@')[0]
            else:
                # Use client_name as-is if no domain
                auth_username = self.config.client_name
            
            # For Auth endpoint, try both the base name and the full name with domain
            # ISE may have registered the client with @xgrid.cisco.com domain
            # Try the full name first if client_name doesn't have domain
            auth_node_name = self.config.client_name
            if '@' not in self.config.client_name:
                # Try adding @xgrid.cisco.com domain - ISE may have registered it this way
                auth_node_name = f"{self.config.client_name}@xgrid.cisco.com"
                logger.warning(f"🔍 Client name '{self.config.client_name}' has no domain, trying '{auth_node_name}' for Auth nodeName")
            else:
                logger.warning(f"🔍 Using client_name as-is for Auth nodeName: '{auth_node_name}'")
            
            payload = {
                "nodeName": auth_node_name,  # Try full name with domain if base name doesn't have it
                "password": self.config.password
            }
            auth_header = HTTPBasicAuth(auth_username, self.config.password)
            logger.warning(f"🔍 AUTHENTICATING: to pxGrid as '{auth_username}' (client nodeName: '{self.config.client_name}')...")
            logger.warning(f"🔍 Auth endpoint URL: {url}")
            logger.warning(f"🔍 Auth payload: nodeName={self.config.client_name}, password_length={len(self.config.password)}")
            logger.warning(f"🔍 Auth request details:")
            logger.warning(f"   - URL: {url}")
            logger.warning(f"   - Payload: {payload}")
            logger.warning(f"   - Auth username: {auth_username}")
            logger.warning(f"   - Auth password length: {len(self.config.password) if self.config.password else 0}")
            logger.warning(f"   - SSL verify: {self.session.verify}")
            logger.warning(f"   - Base URL: {self.base_url}")
        
        try:
            logger.warning(f"🔍 SENDING AUTH POST REQUEST to ISE at {url}...")
            response = self.session.post(
                url,
                json=payload,
                auth=auth_header,  # None for cert-based, HTTPBasicAuth for password-based
                timeout=self.config.timeout
            )
            
            logger.info(f"🔍 Auth HTTP response received: status={response.status_code}, text_length={len(response.text) if response.text else 0}")
            logger.info(f"🔍 Auth response URL: {response.url}")
            if response.status_code != 200:
                logger.warning(f"⚠️  Auth response headers: {dict(response.headers)}")
                logger.warning(f"⚠️  Auth response text (first 500 chars): {response.text[:500] if response.text else 'No response text'}")
            
            if response.status_code == 401:
                error_msg = (
                    f"Authentication failed with 401 Unauthorized. "
                    f"This usually means:\n"
                    f"1. The client '{self.config.client_name}' doesn't exist in ISE (use ISE admin credentials to create it first)\n"
                    f"2. The client password is incorrect\n"
                    f"3. The client account is not approved in ISE (check Administration > pxGrid Services > Client Management)\n"
                    f"4. You're using ISE admin credentials instead of client credentials for Auth endpoint\n\n"
                    f"Response: {response.text[:500]}"
                )
                raise PxGridAuthenticationError(error_msg)
            elif response.status_code != 200:
                raise PxGridAuthenticationError(
                    f"Authentication failed with status {response.status_code}: {response.text[:500]}"
                )
            
            # Check if response is JSON (might be HTML error page)
            try:
                result = response.json()
            except ValueError:
                raise PxGridAuthenticationError(
                    f"Received non-JSON response (likely HTML error page): {response.text[:500]}"
                )
            
            self.access_token = result.get("access_token")
            
            if not self.access_token:
                raise PxGridAuthenticationError("No access token received from pxGrid")
            
            logger.info("✅ Successfully authenticated to pxGrid")
            
        except PxGridAuthenticationError:
            raise
        except requests.RequestException as e:
            raise PxGridAuthenticationError(f"Authentication request failed: {e}") from e
    
    def _get_node_name(self) -> None:
        """Get the pxGrid node name (ISE server name)."""
        url = f"{self.base_url}/pxgrid/control/ServiceLookup"
        
        payload = {
            "name": "com.cisco.ise.session"
        }
        
        # For ISE 2.0, ServiceLookup works with Basic Auth (nodeName:password)
        # If we have an access token, use it; otherwise use Basic Auth
        headers = {"Content-Type": "application/json"}
        auth_header = None
        
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        else:
            # Use Basic Auth with client credentials
            from requests.auth import HTTPBasicAuth
            auth_username = self.config.username if self.config.username else self.config.client_name
            if '@' in auth_username:
                auth_username = auth_username.split('@')[0]
            auth_header = HTTPBasicAuth(auth_username, self.config.password)
            logger.warning(f"🔍 Using Basic Auth for ServiceLookup (username: {auth_username})")
        
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                auth=auth_header,
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
    
    def delete_account(self, admin_username: Optional[str] = None, admin_password: Optional[str] = None) -> bool:
        """
        Delete the pxGrid client account from ISE.
        
        Tries to delete using client credentials first, then falls back to ISE admin credentials if provided.
        
        Args:
            admin_username: Optional ISE admin username to use if client credentials fail
            admin_password: Optional ISE admin password to use if client credentials fail
        
        Returns:
            True if deletion was successful or attempted, False otherwise
        """
        try:
            # Try AccountDelete endpoint (may not exist in all ISE versions)
            url = f"{self.base_url}/pxgrid/control/AccountDelete"
            
            payload = {
                "nodeName": self.config.client_name
            }
            
            # Try with client credentials first
            use_cert_auth = self.config.client_cert_data and self.config.client_key_data
            auth_header = None if use_cert_auth else HTTPBasicAuth(self.config.username, self.config.password)
            
            logger.info(f"Attempting to delete pxGrid account '{self.config.client_name}' from ISE using client credentials...")
            response = self.session.post(
                url,
                json=payload,
                auth=auth_header,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                logger.info(f"✅ pxGrid account '{self.config.client_name}' deleted successfully from ISE")
                return True
            elif response.status_code == 404:
                logger.info(f"ℹ️  pxGrid account '{self.config.client_name}' not found in ISE (may already be deleted)")
                return True  # Consider this success - account doesn't exist
            elif response.status_code == 401 and admin_username and admin_password:
                # Client credentials failed, try with ISE admin credentials
                logger.info(f"Client credentials failed (401), trying with ISE admin credentials...")
                admin_auth = HTTPBasicAuth(admin_username, admin_password)
                response = self.session.post(
                    url,
                    json=payload,
                    auth=admin_auth,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ pxGrid account '{self.config.client_name}' deleted successfully from ISE using admin credentials")
                    return True
                elif response.status_code == 404:
                    logger.info(f"ℹ️  pxGrid account '{self.config.client_name}' not found in ISE (may already be deleted)")
                    return True
                else:
                    logger.warning(f"⚠️  AccountDelete with admin credentials returned status {response.status_code}: {response.text[:200]}")
                    logger.warning(f"⚠️  Account may need to be deleted manually in ISE GUI: Administration > pxGrid Services > Client Management > Clients")
                    return False
            elif response.status_code == 401:
                logger.warning(f"⚠️  Authentication failed when trying to delete account. Client may need to be deleted manually in ISE GUI.")
                return False
            else:
                logger.warning(f"⚠️  AccountDelete returned status {response.status_code}: {response.text[:200]}")
                logger.warning(f"⚠️  Account may need to be deleted manually in ISE GUI: Administration > pxGrid Services > Client Management > Clients")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️  Error calling AccountDelete API: {e}")
            logger.warning(f"⚠️  Account may need to be deleted manually in ISE GUI: Administration > pxGrid Services > Client Management > Clients")
            return False
        except Exception as e:
            logger.warning(f"⚠️  Unexpected error deleting account: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from pxGrid."""
        if self.ws_connection:
            self.ws_connection.close()
            self.ws_connection = None
        
        # Clean up temporary certificate files
        if self._temp_cert_file:
            try:
                os.unlink(self._temp_cert_file.name)
            except Exception:
                pass
        if self._temp_key_file:
            try:
                os.unlink(self._temp_key_file.name)
            except Exception:
                pass
        if self._temp_ca_file:
            try:
                os.unlink(self._temp_ca_file.name)
            except Exception:
                pass
        
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

