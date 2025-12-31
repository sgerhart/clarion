"""
Cisco ISE ERS API Client

Client library for interacting with Cisco ISE via the ERS (External RESTful Services) API.
Provides functionality to create SGTs, authorization policies, and manage ISE configuration.
"""

from __future__ import annotations

import requests
from typing import Dict, List, Optional, Any
import logging
from urllib.parse import urljoin
import base64

logger = logging.getLogger(__name__)


class ISEAuthenticationError(Exception):
    """Raised when ISE authentication fails."""
    pass


class ISEAPIError(Exception):
    """Raised when ISE API request fails."""
    pass


class ISEClient:
    """
    Cisco ISE ERS API client.
    
    Provides methods to interact with ISE for policy deployment.
    
    Example:
        >>> client = ISEClient("https://192.168.10.31", "admin", "C!sco#123")
        >>> client.create_sgt("Engineering-Users", 10, "Engineering department users")
        >>> client.create_authorization_policy(...)
    """
    
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
        timeout: int = 30,
    ):
        """
        Initialize ISE ERS API client.
        
        Args:
            base_url: ISE server base URL (e.g., "https://192.168.10.31" or "https://ise.example.com")
                      Port is optional (defaults to 443 for HTTPS). ERS API operates on port 443.
            username: ISE admin username
            password: ISE admin password
            verify_ssl: Whether to verify SSL certificates (default: False for self-signed certs)
            timeout: Request timeout in seconds
        """
        # Ensure base_url doesn't end with /
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        
        # ERS API base path
        self.ers_base = "/ers/config"
        
        # Session for connection pooling and cookie handling
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        
        # Authenticate on initialization
        self._authenticate()
    
    def _authenticate(self) -> None:
        """
        Authenticate with ISE and get session cookie.
        
        ERS API uses basic authentication with each request,
        but we'll use session-based auth for efficiency.
        """
        # Prepare basic auth header
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.session.headers['Authorization'] = f'Basic {encoded_credentials}'
        
        # Test authentication by making a simple request
        try:
            url = urljoin(self.base_url, f"{self.ers_base}/sgt")
            logger.info(f"Testing ISE authentication: GET {url} with username {self.username}")
            response = self.session.get(
                url,
                timeout=self.timeout,
                params={'size': 1}  # Just get first page to test auth
            )
            
            logger.info(f"ISE authentication response: status_code={response.status_code}, headers={dict(response.headers)}")
            
            if response.status_code == 401:
                error_detail = response.text if response.text else "No error message provided by ISE"
                logger.error(f"ISE authentication failed (401): {error_detail}. URL: {url}, Username: {self.username}")
                raise ISEAuthenticationError(f"ISE authentication failed (401): {error_detail}")
            elif response.status_code not in (200, 404):  # 404 is OK if no SGTs exist
                error_detail = response.text if response.text else f"Status code {response.status_code}"
                logger.warning(f"ISE API returned status {response.status_code}: {error_detail}")
                # For non-401 errors, still raise authentication error if it's a client error
                if 400 <= response.status_code < 500:
                    raise ISEAuthenticationError(f"ISE API error ({response.status_code}): {error_detail}")
                
        except requests.exceptions.RequestException as e:
            raise ISEAuthenticationError(f"Failed to connect to ISE: {e}")
        
        logger.info(f"Successfully authenticated to ISE at {self.base_url}")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict:
        """
        Make a request to the ISE ERS API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/sgt", "/authorizationprofile")
            data: Request body data (will be JSON encoded)
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            ISEAPIError: If request fails
        """
        url = urljoin(self.base_url, f"{self.ers_base}{endpoint}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.timeout,
            )
            
            # Handle different response codes
            if response.status_code == 401:
                # Re-authenticate and retry once
                self._authenticate()
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=self.timeout,
                )
            
            if response.status_code == 204:  # No content (successful DELETE)
                return {}
            
            if response.status_code == 201:  # Created (successful POST) - may have empty body
                # Try to parse JSON if present, otherwise return empty dict (success)
                if response.text:
                    try:
                        return response.json()
                    except:
                        return {}  # Empty response body on 201 is acceptable
                return {}
            
            if response.status_code >= 400:
                # Include the URL in the error message for debugging
                error_detail = response.text.strip() if response.text else "No error details provided"
                
                # Provide helpful hints for common errors
                if response.status_code == 404:
                    hint = " (Hint: Check that the ISE URL and endpoint path are correct. ERS API path is /ers/config/...)"
                    error_msg = f"ISE API error (404): {error_detail}. URL: {url}{hint}"
                else:
                    error_msg = f"ISE API error ({response.status_code}): {error_detail}. URL: {url}"
                logger.error(error_msg)
                raise ISEAPIError(error_msg)
            
            # Parse JSON response
            if response.text:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request to ISE failed: {e}"
            logger.error(error_msg)
            raise ISEAPIError(error_msg)
    
    def create_sgt(
        self,
        name: str,
        value: int,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a Security Group Tag (SGT) in ISE.
        
        Args:
            name: SGT name (e.g., "Engineering-Users")
            value: SGT value (0-65519)
            description: Optional description
            
        Returns:
            Created SGT data from ISE
            
        Raises:
            ISEAPIError: If SGT creation fails (e.g., duplicate name/value)
        """
        payload = {
            "Sgt": {
                "name": name,
                "value": str(value),  # ISE API expects string
                "description": description or f"SGT {value}: {name}",
                "generationId": "0",
            }
        }
        
        logger.info(f"Creating SGT in ISE: {name} (value: {value})")
        response = self._make_request("POST", "/sgt", data=payload)
        
        # ISE returns the created resource in response
        if 'Sgt' in response:
            logger.info(f"✅ Successfully created SGT {name} (value: {value})")
            return response['Sgt']
        
        raise ISEAPIError(f"Unexpected response from ISE when creating SGT: {response}")
    
    def get_sgt(self, name: Optional[str] = None, value: Optional[int] = None) -> Optional[Dict]:
        """
        Get an SGT from ISE by name or value.
        
        Args:
            name: SGT name to search for
            value: SGT value to search for
            
        Returns:
            SGT data if found, None otherwise
        """
        if name:
            # Search by name
            response = self._make_request("GET", "/sgt", params={"filter": f"name.EQ.{name}"})
        elif value is not None:
            # Search by value
            response = self._make_request("GET", "/sgt", params={"filter": f"value.EQ.{value}"})
        else:
            raise ValueError("Must provide either name or value")
        
        if 'SearchResult' in response and response['SearchResult']['total'] > 0:
            sgt_id = response['SearchResult']['resources'][0]['id']
            # Get full SGT details
            sgt_response = self._make_request("GET", f"/sgt/{sgt_id}")
            return sgt_response.get('Sgt')
        
        return None
    
    def list_sgts(self, page: int = 1, size: int = 100) -> Dict[str, Any]:
        """
        List all SGTs from ISE.
        
        Args:
            page: Page number (1-indexed)
            size: Number of results per page (max 100)
            
        Returns:
            Dictionary with 'total', 'resources' list containing SGT data
        """
        response = self._make_request("GET", "/sgt", params={"page": page, "size": size})
        
        if 'SearchResult' in response:
            return response['SearchResult']
        return {"total": 0, "resources": []}
    
    def get_all_sgts(self) -> List[Dict[str, Any]]:
        """
        Get all SGTs from ISE (handles pagination automatically).
        
        Returns:
            List of all SGT dictionaries with full details
        """
        all_sgts = []
        page = 1
        size = 100
        
        while True:
            result = self.list_sgts(page=page, size=size)
            resources = result.get('resources', [])
            total = result.get('total', 0)
            
            # Fetch full details for each SGT
            for resource in resources:
                sgt_id = resource.get('id')
                if sgt_id:
                    try:
                        sgt_detail = self._make_request("GET", f"/sgt/{sgt_id}")
                        if 'Sgt' in sgt_detail:
                            all_sgts.append(sgt_detail['Sgt'])
                    except Exception as e:
                        logger.warning(f"Failed to get details for SGT {sgt_id}: {e}")
            
            # Check if there are more pages
            if len(all_sgts) >= total or len(resources) < size:
                break
            page += 1
        
        logger.info(f"Retrieved {len(all_sgts)} SGTs from ISE")
        return all_sgts
    
    def list_authorization_profiles(self, page: int = 1, size: int = 100) -> Dict[str, Any]:
        """
        List all authorization profiles from ISE.
        
        Args:
            page: Page number (1-indexed)
            size: Number of results per page (max 100)
            
        Returns:
            Dictionary with 'total', 'resources' list
        """
        response = self._make_request("GET", "/authorizationprofile", params={"page": page, "size": size})
        
        if 'SearchResult' in response:
            return response['SearchResult']
        return {"total": 0, "resources": []}
    
    def get_all_authorization_profiles(self) -> List[Dict[str, Any]]:
        """
        Get all authorization profiles from ISE (handles pagination).
        
        Returns:
            List of all authorization profile dictionaries with full details
        """
        all_profiles = []
        page = 1
        size = 100
        
        while True:
            result = self.list_authorization_profiles(page=page, size=size)
            resources = result.get('resources', [])
            total = result.get('total', 0)
            
            # Fetch full details for each profile
            for resource in resources:
                profile_id = resource.get('id')
                if profile_id:
                    try:
                        profile_detail = self._make_request("GET", f"/authorizationprofile/{profile_id}")
                        if 'AuthorizationProfile' in profile_detail:
                            all_profiles.append(profile_detail['AuthorizationProfile'])
                    except Exception as e:
                        logger.warning(f"Failed to get details for authorization profile {profile_id}: {e}")
            
            if len(all_profiles) >= total or len(resources) < size:
                break
            page += 1
        
        logger.info(f"Retrieved {len(all_profiles)} authorization profiles from ISE")
        return all_profiles
    
    def list_authorization_policies(self, page: int = 1, size: int = 100) -> Dict[str, Any]:
        """
        List all authorization policies from ISE.
        
        Args:
            page: Page number (1-indexed)
            size: Number of results per page (max 100)
            
        Returns:
            Dictionary with 'total', 'resources' list
        """
        try:
            response = self._make_request("GET", "/authorizationpolicy", params={"page": page, "size": size})
            
            if 'SearchResult' in response:
                return response['SearchResult']
            return {"total": 0, "resources": []}
        except ISEAPIError as e:
            # Some ISE versions or configurations may not support this endpoint or return 404 if empty
            # Return empty result instead of raising exception
            if "404" in str(e):
                logger.warning(f"Authorization policies endpoint returned 404 (may not be available or empty): {e}")
                return {"total": 0, "resources": []}
            raise
    
    def get_all_authorization_policies(self) -> List[Dict[str, Any]]:
        """
        Get all authorization policies from ISE (handles pagination).
        
        Returns:
            List of all authorization policy dictionaries with full details
        """
        all_policies = []
        page = 1
        size = 100
        
        while True:
            result = self.list_authorization_policies(page=page, size=size)
            resources = result.get('resources', [])
            total = result.get('total', 0)
            
            # Fetch full details for each policy
            for resource in resources:
                policy_id = resource.get('id')
                if policy_id:
                    try:
                        policy_detail = self._make_request("GET", f"/authorizationpolicy/{policy_id}")
                        if 'AuthorizationPolicy' in policy_detail:
                            all_policies.append(policy_detail['AuthorizationPolicy'])
                    except Exception as e:
                        logger.warning(f"Failed to get details for authorization policy {policy_id}: {e}")
            
            if len(all_policies) >= total or len(resources) < size:
                break
            page += 1
        
        logger.info(f"Retrieved {len(all_policies)} authorization policies from ISE")
        return all_policies
    
    def extract_sgt_from_profile(self, profile: Dict[str, Any]) -> Optional[int]:
        """
        Extract SGT value from an authorization profile.
        
        Profiles can assign SGTs via:
        - Direct 'sgt' field (string)
        - advancedAttributes with cisco-av-pair containing security-group-tag=X
        
        Args:
            profile: Authorization profile dictionary from ISE
            
        Returns:
            SGT value (int) if found, None otherwise
        """
        # Check direct sgt field
        if 'sgt' in profile and profile['sgt']:
            try:
                return int(profile['sgt'])
            except (ValueError, TypeError):
                pass
        
        # Check advancedAttributes for cisco-av-pair
        if 'advancedAttributes' in profile and isinstance(profile['advancedAttributes'], list):
            for attr in profile['advancedAttributes']:
                right_hand = attr.get('rightHandSideAttribueValue', {})
                value = right_hand.get('value', '') if isinstance(right_hand, dict) else str(right_hand)
                
                # Look for security-group-tag=X pattern
                if isinstance(value, str) and 'security-group-tag=' in value:
                    try:
                        sgt_str = value.split('security-group-tag=')[1].split()[0]  # Get value after =, before space
                        return int(sgt_str)
                    except (ValueError, IndexError):
                        pass
        
        return None
    
    def create_authorization_profile(
        self,
        name: str,
        sgt_value: int,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an authorization profile that assigns an SGT.
        
        Args:
            name: Profile name (e.g., "Assign-SGT-10")
            sgt_value: SGT value to assign
            description: Optional description
            
        Returns:
            Created authorization profile data from ISE
        """
        # ISE ERS API requires accessType and authzProfileType
        # SGT is assigned via advancedAttributes using cisco-av-pair
        payload = {
            "AuthorizationProfile": {
                "name": name,
                "description": description or f"Assign SGT {sgt_value}",
                "accessType": "ACCESS_ACCEPT",
                "authzProfileType": "SWITCH",
                "advancedAttributes": [
                    {
                        "leftHandSideDictionaryAttribue": {
                            "AdvancedAttributeValueType": "AdvancedDictionaryAttribute",
                            "dictionaryName": "Cisco",
                            "attributeName": "cisco-av-pair"
                        },
                        "rightHandSideAttribueValue": {
                            "AdvancedAttributeValueType": "AttributeValue",
                            "value": f"security-group-tag={sgt_value}"
                        }
                    }
                ]
            }
        }
        
        logger.info(f"Creating authorization profile in ISE: {name} (SGT: {sgt_value})")
        response = self._make_request("POST", "/authorizationprofile", data=payload)
        
        # ISE returns 201 Created, often with empty body
        # If we got here, the request succeeded (201), even if response is empty
        if 'AuthorizationProfile' in response:
            logger.info(f"✅ Successfully created authorization profile {name}")
            return response['AuthorizationProfile']
        
        # If response is empty but we got here (no exception), it was successful
        # Try to GET the profile we just created to return its details
        logger.info(f"Profile creation succeeded, fetching details for {name}")
        try:
            # Search for the profile we just created
            search_response = self._make_request("GET", "/authorizationprofile", params={'filter': f'name.EQ.{name}'})
            if 'SearchResult' in search_response and search_response['SearchResult'].get('total', 0) > 0:
                profile_id = search_response['SearchResult']['resources'][0]['id']
                profile_detail = self._make_request("GET", f"/authorizationprofile/{profile_id}")
                if 'AuthorizationProfile' in profile_detail:
                    logger.info(f"✅ Successfully created and retrieved authorization profile {name}")
                    return profile_detail['AuthorizationProfile']
        except Exception as e:
            logger.warning(f"Could not retrieve created profile details: {e}")
        
        # Return a minimal success response
        logger.info(f"✅ Successfully created authorization profile {name} (details unavailable)")
        return {"name": name, "id": "created"}
    
    def create_authorization_policy(
        self,
        name: str,
        condition: str,
        profile_name: str,
        rank: int = 0,
        state: str = "enabled",
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an authorization policy in ISE.
        
        Args:
            name: Policy name
            condition: Policy condition (e.g., "AD1:ExternalGroups EQUALS Engineering-Users")
            profile_name: Authorization profile name (must exist)
            rank: Policy rank (order of evaluation, 0 = highest priority)
            state: Policy state ("enabled" or "disabled")
            description: Optional description
            
        Returns:
            Created authorization policy data from ISE
        """
        payload = {
            "AuthorizationPolicy": {
                "name": name,
                "description": description or f"Authorization policy: {name}",
                "rank": rank,
                "state": state,
                "condition": {
                    "conditionType": "ConditionAndBlock",
                    "isNegate": False,
                    "name": name,
                    "attributeName": "",
                    "attributeValue": "",
                    "dictionaryName": "",
                    "operator": "",
                    "children": [
                        {
                            "conditionType": "ConditionAttributes",
                            "isNegate": False,
                            "attributeName": "",
                            "attributeValue": "",
                            "dictionaryName": "",
                            "operator": "",
                            "children": None,
                            "description": None,
                            "id": None,
                            "name": None,
                            "link": None,
                        }
                    ],
                    "description": None,
                    "id": None,
                    "link": None,
                },
                "commands": [
                    {
                        "grant": "ACCESS_ACCEPT",
                        "dacl": None,
                        "aces": None,
                    }
                ],
                "profile": profile_name,
            }
        }
        
        # Set the condition attribute from the condition string
        # Simple parsing for common patterns like "AD1:ExternalGroups EQUALS Engineering-Users"
        if "EQUALS" in condition:
            parts = condition.split("EQUALS")
            attribute = parts[0].strip()
            value = parts[1].strip().strip("'\"")
            
            # Parse attribute (e.g., "AD1:ExternalGroups" -> dictionary="AD1", attribute="ExternalGroups")
            if ":" in attribute:
                dict_name, attr_name = attribute.split(":", 1)
                payload["AuthorizationPolicy"]["condition"]["children"][0]["dictionaryName"] = dict_name
                payload["AuthorizationPolicy"]["condition"]["children"][0]["attributeName"] = attr_name
                payload["AuthorizationPolicy"]["condition"]["children"][0]["attributeValue"] = value
                payload["AuthorizationPolicy"]["condition"]["children"][0]["operator"] = "EQUALS"
        
        logger.info(f"Creating authorization policy in ISE: {name}")
        response = self._make_request("POST", "/authorizationpolicy", data=payload)
        
        if 'AuthorizationPolicy' in response:
            logger.info(f"✅ Successfully created authorization policy {name}")
            return response['AuthorizationPolicy']
        
        raise ISEAPIError(f"Unexpected response from ISE when creating authorization policy: {response}")
    
    def test_connection(self) -> bool:
        """
        Test connection to ISE server.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            self._make_request("GET", "/sgt", params={"size": 1})
            return True
        except Exception as e:
            logger.error(f"ISE connection test failed: {e}")
            return False

