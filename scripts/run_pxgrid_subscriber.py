#!/usr/bin/env python3
"""
pxGrid Subscriber Service

Standalone script to run the pxGrid subscriber service as a background process.
This subscribes to ISE pxGrid events and updates the Clarion database.

Usage:
    python scripts/run_pxgrid_subscriber.py \
        --ise-hostname 192.168.10.31 \
        --username clarion-client \
        --password secret \
        --client-name clarion-pxgrid-client

Or use environment variables:
    export PXGRID_ISE_HOSTNAME=192.168.10.31
    export PXGRID_USERNAME=clarion-client
    export PXGRID_PASSWORD=secret
    export PXGRID_CLIENT_NAME=clarion-pxgrid-client
    python scripts/run_pxgrid_subscriber.py
"""

import sys
import os
import argparse
import logging
import signal
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clarion.integration.pxgrid_client import PxGridConfig
from clarion.integration.pxgrid_subscriber import PxGridSubscriber
from clarion.storage import init_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global subscriber instance for signal handling
subscriber: PxGridSubscriber = None


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info("\n🛑 Received shutdown signal, stopping pxGrid subscriber...")
    if subscriber:
        subscriber.stop()
    sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="pxGrid Subscriber Service for Clarion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--ise-hostname',
        type=str,
        default=None,
        help='ISE hostname or IP address (e.g., 192.168.10.31)'
    )
    parser.add_argument(
        '--username',
        type=str,
        default=None,
        help='pxGrid client username'
    )
    parser.add_argument(
        '--password',
        type=str,
        default=None,
        help='pxGrid client password'
    )
    parser.add_argument(
        '--client-name',
        type=str,
        default='clarion-pxgrid-client',
        help='Unique pxGrid client name (default: clarion-pxgrid-client)'
    )
    parser.add_argument(
        '--use-ssl',
        action='store_true',
        default=True,
        help='Use SSL/TLS for connection (default: True)'
    )
    parser.add_argument(
        '--no-ssl',
        dest='use_ssl',
        action='store_false',
        help='Disable SSL/TLS'
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
        '--db-path',
        type=str,
        default='clarion.db',
        help='Path to Clarion database file (default: clarion.db)'
    )
    
    args = parser.parse_args()
    
    # Get configuration from args or environment variables
    ise_hostname = args.ise_hostname or sys.argv[1] if len(sys.argv) > 1 else None
    if not ise_hostname:
        ise_hostname = os.environ.get('PXGRID_ISE_HOSTNAME')
    
    username = args.username or os.environ.get('PXGRID_USERNAME')
    password = args.password or os.environ.get('PXGRID_PASSWORD')
    client_name = args.client_name or os.environ.get('PXGRID_CLIENT_NAME', 'clarion-pxgrid-client')
    
    if not ise_hostname or not username or not password:
        logger.error("❌ Missing required configuration:")
        logger.error("   --ise-hostname, --username, and --password are required")
        logger.error("   Or set PXGRID_ISE_HOSTNAME, PXGRID_USERNAME, PXGRID_PASSWORD environment variables")
        sys.exit(1)
    
    # Initialize database
    logger.info(f"📊 Initializing database: {args.db_path}")
    init_database(args.db_path)
    
    # Create pxGrid configuration
    config = PxGridConfig(
        ise_hostname=ise_hostname,
        username=username,
        password=password,
        client_name=client_name,
        use_ssl=args.use_ssl,
        verify_ssl=args.verify_ssl,
        port=args.port,
    )
    
    # Create subscriber
    global subscriber
    subscriber = PxGridSubscriber(config)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start subscriber
    logger.info(f"🚀 Starting pxGrid subscriber for ISE: {ise_hostname}")
    logger.info(f"   Client name: {client_name}")
    logger.info(f"   Port: {args.port}")
    logger.info(f"   SSL: {args.use_ssl} (verify: {args.verify_ssl})")
    
    try:
        success = subscriber.start()
        if not success:
            logger.error("❌ Failed to start pxGrid subscriber")
            sys.exit(1)
        
        logger.info("✅ pxGrid subscriber started successfully")
        logger.info("📡 Subscribed to ISE session and endpoint events")
        logger.info("   Press Ctrl+C to stop")
        
        # Keep running
        while subscriber.is_running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if subscriber:
            subscriber.stop()
        logger.info("👋 pxGrid subscriber stopped")


if __name__ == "__main__":
    main()

