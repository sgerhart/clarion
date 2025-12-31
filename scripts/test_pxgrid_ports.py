#!/usr/bin/env python3
"""
pxGrid Port and Connection Diagnostic

Tests different ports and URL formats to find the correct pxGrid endpoint.

Usage:
    python scripts/test_pxgrid_ports.py \
        --ise-hostname 192.168.10.31 \
        --username admin \
        --password 'C!sco#123'
"""

import sys
import argparse
import logging
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_endpoint(url: str, username: str, password: str, verify_ssl: bool = False) -> dict:
    """Test an endpoint."""
    session = requests.Session()
    session.verify = verify_ssl
    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        # Try AccountActivate endpoint
        response = session.post(
            f"{url}/pxgrid/control/AccountActivate",
            json={"nodeName": "test-client"},
            auth=HTTPBasicAuth(username, password),
            timeout=5
        )
        
        return {
            "url": url,
            "status_code": response.status_code,
            "success": response.status_code in [200, 404],
            "response_preview": response.text[:200] if response.text else ""
        }
    except requests.exceptions.ConnectionError:
        return {
            "url": url,
            "status_code": None,
            "success": False,
            "response_preview": "Connection refused"
        }
    except Exception as e:
        return {
            "url": url,
            "status_code": None,
            "success": False,
            "response_preview": str(e)[:200]
        }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test pxGrid Connection on Different Ports"
    )
    
    parser.add_argument('--ise-hostname', required=True)
    parser.add_argument('--username', required=True)
    parser.add_argument('--password', required=True)
    parser.add_argument('--verify-ssl', action='store_true', default=False)
    
    args = parser.parse_args()
    
    # Common ISE ports
    ports_to_test = [
        (8910, "pxGrid REST API (standard)"),
        (443, "ISE ERS API (HTTPS default)"),
        (443, "HTTPS (standard)"),
        (8443, "HTTPS (alternative)"),
    ]
    
    logger.info("=" * 70)
    logger.info("pxGrid Port Diagnostic")
    logger.info("=" * 70)
    logger.info(f"Testing ISE: {args.ise_hostname}")
    logger.info("")
    
    results = []
    
    for port, description in ports_to_test:
        for protocol in ["https", "http"]:
            url = f"{protocol}://{args.ise_hostname}:{port}"
            logger.info(f"Testing: {url} ({description})")
            result = test_endpoint(url, args.username, args.password, args.verify_ssl)
            results.append((url, description, result))
            
            if result["success"]:
                logger.info(f"  ✅ Status: {result['status_code']} - Connection successful!")
            else:
                logger.info(f"  ❌ Status: {result.get('status_code', 'N/A')} - Failed")
            logger.info("")
    
    # Summary
    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    
    successful = [r for r in results if r[2]["success"]]
    
    if successful:
        logger.info("✅ Working endpoints:")
        for url, desc, result in successful:
            logger.info(f"   {url} - {desc} (Status: {result['status_code']})")
    else:
        logger.info("❌ No working endpoints found")
        logger.info("")
        logger.info("Possible issues:")
        logger.info("  1. pxGrid service may not be enabled on ISE")
        logger.info("  2. Network connectivity issues")
        logger.info("  3. Firewall blocking ports")
        logger.info("  4. ISE may require certificate-based authentication for pxGrid")
    
    logger.info("")


if __name__ == "__main__":
    main()

