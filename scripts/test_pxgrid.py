#!/usr/bin/env python3
"""
Test pxGrid Integration

Simple test script to verify pxGrid connection and basic functionality.

Usage:
    python scripts/test_pxgrid.py \
        --ise-hostname 192.168.10.31 \
        --username admin \
        --password C!sco#123 \
        --client-name clarion-test-client
"""

import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clarion.integration.pxgrid_client import (
    PxGridClient,
    PxGridConfig,
    PxGridAuthenticationError,
    PxGridError,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_connection(config: PxGridConfig) -> bool:
    """Test pxGrid connection."""
    logger.info("=" * 60)
    logger.info("TEST 1: pxGrid Connection Test")
    logger.info("=" * 60)
    
    try:
        client = PxGridClient(config)
        success = client.connect()
        
        if success:
            logger.info("✅ Connection successful!")
            logger.info(f"   ISE Hostname: {config.ise_hostname}")
            logger.info(f"   Client Name: {config.client_name}")
            logger.info(f"   Access Token: {'*' * 20}...{str(client.access_token)[-10:] if client.access_token else 'None'}")
            logger.info(f"   Node Name: {client.node_name or 'Not retrieved'}")
            
            # Disconnect
            client.disconnect()
            return True
        else:
            logger.error("❌ Connection failed")
            return False
            
    except PxGridAuthenticationError as e:
        logger.error(f"❌ Authentication failed: {e}")
        logger.error("")
        logger.error("Common issues:")
        logger.error("  1. pxGrid service not enabled on ISE")
        logger.error("  2. Wrong username/password")
        logger.error("  3. Client not approved in ISE GUI")
        logger.error("     → Go to: Administration > pxGrid Services > Client Management > Clients")
        logger.error("     → Approve the client: {}".format(config.client_name))
        return False
    except PxGridError as e:
        logger.error(f"❌ pxGrid error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return False


def test_event_parsing():
    """Test event parsing functions."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 2: Event Parsing Test")
    logger.info("=" * 60)
    
    try:
        from clarion.integration.pxgrid_client import ISESessionEvent, ISEEndpointEvent
        
        # Create a dummy config (not used for parsing)
        config = PxGridConfig(
            ise_hostname="test.example.com",
            username="test",
            password="test",
            client_name="test-client"
        )
        client = PxGridClient(config)
        
        # Test session event parsing
        sample_session_event = {
            "sessionId": "test-session-123",
            "state": "authenticated",
            "userName": "jdoe",
            "macAddress": "00:11:22:33:44:55",
            "ipAddress": "192.168.1.100",
            "sgt": 10,
            "userSgt": 10,
            "deviceSgt": 5,
            "adGroups": ["Engineering-Users", "Domain Users"],
            "endpointProfile": "Corporate-Laptop",
            "authenticationMethod": "dot1x",
            "policySet": "Default",
            "authorizationProfile": "PermitAccess",
            "timestamp": "2025-01-15T10:30:00Z"
        }
        
        parsed_event = client.parse_session_event(sample_session_event)
        logger.info("✅ Session event parsing successful!")
        logger.info(f"   Session ID: {parsed_event.session_id}")
        logger.info(f"   Username: {parsed_event.username}")
        logger.info(f"   MAC: {parsed_event.mac_address}")
        logger.info(f"   SGT: {parsed_event.sgt_value}")
        logger.info(f"   AD Groups: {', '.join(parsed_event.ad_groups)}")
        
        # Test endpoint event parsing
        sample_endpoint_event = {
            "macAddress": "00:11:22:33:44:55",
            "ipAddress": "192.168.1.100",
            "endpointProfile": "Corporate-Laptop",
            "deviceType": "Laptop",
            "sgt": 5,
            "timestamp": "2025-01-15T10:30:00Z"
        }
        
        parsed_endpoint = client.parse_endpoint_event(sample_endpoint_event)
        logger.info("✅ Endpoint event parsing successful!")
        logger.info(f"   MAC: {parsed_endpoint.mac_address}")
        logger.info(f"   Profile: {parsed_endpoint.ise_profile}")
        logger.info(f"   SGT: {parsed_endpoint.sgt_value}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Event parsing test failed: {e}", exc_info=True)
        return False


def test_subscriber_initialization(config: PxGridConfig) -> bool:
    """Test subscriber initialization (without starting)."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 3: Subscriber Initialization Test")
    logger.info("=" * 60)
    
    try:
        from clarion.integration.pxgrid_subscriber import PxGridSubscriber
        from clarion.storage import init_database
        
        # Initialize database
        init_database()
        logger.info("✅ Database initialized")
        
        # Create subscriber
        subscriber = PxGridSubscriber(config)
        logger.info("✅ Subscriber created")
        logger.info(f"   ISE Hostname: {subscriber.config.ise_hostname}")
        logger.info(f"   Client Name: {subscriber.config.client_name}")
        logger.info(f"   Is Running: {subscriber.is_running}")
        
        # Note: We don't actually start it here to avoid long-running connection
        logger.info("ℹ️  Subscriber ready (not started - use scripts/run_pxgrid_subscriber.py to run)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Subscriber initialization failed: {e}", exc_info=True)
        return False


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test pxGrid Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        help='pxGrid client username (usually same as ISE admin username)'
    )
    parser.add_argument(
        '--password',
        type=str,
        required=True,
        help='pxGrid client password (usually same as ISE admin password)'
    )
    parser.add_argument(
        '--client-name',
        type=str,
        default='clarion-test-client',
        help='Unique pxGrid client name (default: clarion-test-client)'
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
    parser.add_argument(
        '--skip-connection',
        action='store_true',
        help='Skip connection test (useful if ISE is not available)'
    )
    
    args = parser.parse_args()
    
    # Create configuration
    config = PxGridConfig(
        ise_hostname=args.ise_hostname,
        username=args.username,
        password=args.password,
        client_name=args.client_name,
        use_ssl=not args.no_ssl,
        verify_ssl=args.verify_ssl,
        port=args.port,
    )
    
    logger.info("🧪 pxGrid Integration Test Suite")
    logger.info("")
    
    results = []
    
    # Test 1: Connection
    if not args.skip_connection:
        results.append(("Connection", test_connection(config)))
    else:
        logger.info("⏭️  Skipping connection test (--skip-connection)")
        results.append(("Connection", None))
    
    # Test 2: Event Parsing
    results.append(("Event Parsing", test_event_parsing()))
    
    # Test 3: Subscriber Initialization
    if not args.skip_connection:
        results.append(("Subscriber Init", test_subscriber_initialization(config)))
    else:
        logger.info("⏭️  Skipping subscriber initialization test (--skip-connection)")
        results.append(("Subscriber Init", None))
    
    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    for test_name, result in results:
        if result is None:
            status = "⏭️  SKIPPED"
        elif result:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        logger.info(f"{test_name:.<40} {status}")
    
    # Overall result
    passed = sum(1 for _, r in results if r is True)
    total = sum(1 for _, r in results if r is not None)
    
    if total > 0:
        logger.info("")
        if passed == total:
            logger.info("✅ All tests passed!")
            return 0
        else:
            logger.warning(f"⚠️  {passed}/{total} tests passed")
            return 1
    else:
        logger.info("ℹ️  All tests were skipped")
        return 0


if __name__ == "__main__":
    sys.exit(main())

