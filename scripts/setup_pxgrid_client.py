#!/usr/bin/env python3
"""
pxGrid Client Registration Helper

This script helps register a pxGrid client with ISE and provides clear
instructions for approving it in the ISE GUI.

Usage:
    python scripts/setup_pxgrid_client.py \
        --ise-hostname 192.168.10.31 \
        --username admin \
        --password 'C!sco#123' \
        --client-name clarion-pxgrid-client
"""

import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def register_pxgrid_client(
    ise_hostname: str,
    username: str,
    password: str,
    client_name: str,
    use_ssl: bool = True,
    verify_ssl: bool = False,
    port: int = 8910
) -> dict:
    """
    Register a pxGrid client with ISE.
    
    Returns:
        Dictionary with registration status information
    """
    protocol = "https" if use_ssl else "http"
    base_url = f"{protocol}://{ise_hostname}:{port}"
    
    url = f"{base_url}/pxgrid/control/AccountActivate"
    
    payload = {
        "nodeName": client_name
    }
    
    session = requests.Session()
    session.verify = verify_ssl
    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    logger.info(f"🔐 Attempting to register pxGrid client: {client_name}")
    logger.info(f"   ISE Server: {ise_hostname}:{port}")
    
    try:
        response = session.post(
            url,
            json=payload,
            auth=HTTPBasicAuth(username, password),
            timeout=30
        )
        
        logger.info(f"   Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            account_state = result.get("accountState", "UNKNOWN")
            
            if account_state == "PENDING":
                logger.info("")
                logger.info("=" * 70)
                logger.info("⚠️  CLIENT REGISTRATION SUCCESSFUL - APPROVAL REQUIRED")
                logger.info("=" * 70)
                logger.info("")
                logger.info(f"Client '{client_name}' has been registered with ISE.")
                logger.info("The client is currently in PENDING state and needs approval.")
                logger.info("")
                logger.info("📋 NEXT STEPS:")
                logger.info("")
                logger.info("1. Log in to ISE GUI:")
                logger.info(f"   https://{ise_hostname}/admin")
                logger.info("")
                logger.info("2. Navigate to:")
                logger.info("   Administration > pxGrid Services > Client Management > Clients")
                logger.info("")
                logger.info("3. Find the client:")
                logger.info(f"   Name: {client_name}")
                logger.info("")
                logger.info("4. Click 'Approve' to approve the client")
                logger.info("")
                logger.info("5. After approval, run the connection test again:")
                logger.info(f"   python scripts/test_pxgrid.py --ise-hostname {ise_hostname} \\")
                logger.info(f"       --username {username} --password '<password>' \\")
                logger.info(f"       --client-name {client_name}")
                logger.info("")
                
                return {
                    "success": True,
                    "status": "PENDING",
                    "message": "Client registered, approval required",
                    "client_name": client_name
                }
                
            elif account_state == "ENABLED":
                logger.info("")
                logger.info("=" * 70)
                logger.info("✅ CLIENT ALREADY REGISTERED AND APPROVED")
                logger.info("=" * 70)
                logger.info("")
                logger.info(f"Client '{client_name}' is already registered and enabled in ISE.")
                logger.info("You can proceed with authentication!")
                logger.info("")
                
                return {
                    "success": True,
                    "status": "ENABLED",
                    "message": "Client already enabled",
                    "client_name": client_name
                }
            else:
                logger.warning(f"⚠️  Unexpected account state: {account_state}")
                return {
                    "success": False,
                    "status": account_state,
                    "message": f"Unexpected state: {account_state}",
                    "client_name": client_name
                }
        elif response.status_code == 401:
            logger.error("")
            logger.error("=" * 70)
            logger.error("❌ AUTHENTICATION FAILED")
            logger.error("=" * 70)
            logger.error("")
            logger.error("Unable to authenticate with ISE.")
            logger.error("")
            logger.error("Please check:")
            logger.error("  1. Username and password are correct")
            logger.error("  2. pxGrid service is enabled on ISE")
            logger.error("  3. User has pxGrid admin permissions")
            logger.error("")
            
            return {
                "success": False,
                "status": "AUTH_FAILED",
                "message": "Authentication failed",
                "client_name": client_name
            }
        elif response.status_code == 404:
            logger.info("")
            logger.info("=" * 70)
            logger.info("ℹ️  CLIENT NOT FOUND")
            logger.info("=" * 70)
            logger.info("")
            logger.info(f"Client '{client_name}' is not registered yet.")
            logger.info("Attempting to register...")
            logger.info("")
            
            # The 404 might mean we need to use a different endpoint or method
            # Some ISE versions might require different registration flow
            return {
                "success": False,
                "status": "NOT_FOUND",
                "message": "Client not found - registration may require manual setup",
                "client_name": client_name
            }
        else:
            logger.error(f"❌ Unexpected response status: {response.status_code}")
            logger.error(f"Response: {response.text[:500]}")
            
            return {
                "success": False,
                "status": f"HTTP_{response.status_code}",
                "message": f"Unexpected status code: {response.status_code}",
                "client_name": client_name
            }
            
    except requests.exceptions.ConnectionError as e:
        logger.error("")
        logger.error("=" * 70)
        logger.error("❌ CONNECTION ERROR")
        logger.error("=" * 70)
        logger.error("")
        logger.error(f"Could not connect to ISE at {ise_hostname}:{port}")
        logger.error("")
        logger.error("Please check:")
        logger.error("  1. ISE hostname/IP is correct")
        logger.error("  2. ISE is reachable from this machine")
        logger.error("  3. Port {} is open".format(port))
        logger.error(f"  4. pxGrid service is enabled on ISE")
        logger.error("")
        logger.error(f"Error: {e}")
        logger.error("")
        
        return {
            "success": False,
            "status": "CONNECTION_ERROR",
            "message": f"Connection failed: {e}",
            "client_name": client_name
        }
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return {
            "success": False,
            "status": "ERROR",
            "message": f"Unexpected error: {e}",
            "client_name": client_name
        }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Register pxGrid Client with ISE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--ise-hostname',
        type=str,
        required=True,
        help='ISE hostname or IP address (e.g., 192.168.10.31)'
    )
    parser.add_argument(
        '--username',
        type=str,
        required=True,
        help='ISE admin username'
    )
    parser.add_argument(
        '--password',
        type=str,
        required=True,
        help='ISE admin password'
    )
    parser.add_argument(
        '--client-name',
        type=str,
        default='clarion-pxgrid-client',
        help='Unique pxGrid client name (default: clarion-pxgrid-client)'
    )
    parser.add_argument(
        '--no-ssl',
        action='store_true',
        help='Disable SSL/TLS (not recommended)'
    )
    parser.add_argument(
        '--verify-ssl',
        action='store_true',
        default=False,
        help='Verify SSL certificates (default: False for self-signed certs)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8910,
        help='pxGrid REST API port (default: 8910)'
    )
    
    args = parser.parse_args()
    
    result = register_pxgrid_client(
        ise_hostname=args.ise_hostname,
        username=args.username,
        password=args.password,
        client_name=args.client_name,
        use_ssl=not args.no_ssl,
        verify_ssl=args.verify_ssl,
        port=args.port
    )
    
    if result["success"] and result["status"] == "ENABLED":
        return 0
    elif result["success"] and result["status"] == "PENDING":
        return 0  # Successfully registered, just needs approval
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())

