"""
Clarion Collector - Main Entry Point

Supports two modes:
1. Native NetFlow Collector - Receives NetFlow/IPFIX from switches
2. Agent Collector - Receives sketches from edge agents
"""

import asyncio
import logging
import sys
from typing import Optional

from .config import CollectorConfig
from .native_collector import NativeNetFlowCollector
from .agent_collector import AgentCollector


def setup_logging(level: str = "INFO"):
    """Set up logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def run_native_collector(config: CollectorConfig, http_port: int = 8081):
    """Run the native NetFlow collector."""
    collector = NativeNetFlowCollector(config)
    await collector.start(http_port=http_port)


async def run_agent_collector(config: CollectorConfig, port: int = 8080):
    """Run the agent collector."""
    collector = AgentCollector(config)
    await collector.start(host=config.bind_host, port=port)


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Clarion Collector - NetFlow and Agent Collector"
    )
    parser.add_argument(
        "--mode",
        choices=["native", "agent", "both"],
        default="both",
        help="Collector mode: native (NetFlow), agent (edge agents), or both"
    )
    parser.add_argument(
        "--backend-url",
        type=str,
        help="Backend API URL (default: from CLARION_COLLECTOR_BACKEND_URL env var)"
    )
    parser.add_argument(
        "--netflow-port",
        type=int,
        help="NetFlow UDP port (default: 2055)"
    )
    parser.add_argument(
        "--ipfix-port",
        type=int,
        help="IPFIX UDP port (default: 4739)"
    )
    parser.add_argument(
        "--agent-port",
        type=int,
        default=8080,
        help="Agent collector HTTP port (default: 8080)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Batch size for NetFlow records (default: 1000)"
    )
    parser.add_argument(
        "--batch-interval",
        type=float,
        help="Batch interval in seconds (default: 5.0)"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    # Create config
    config = CollectorConfig()
    
    # Override with CLI args
    if args.backend_url:
        config.backend_url = args.backend_url
    if args.netflow_port:
        config.netflow_port = args.netflow_port
    if args.ipfix_port:
        config.ipfix_port = args.ipfix_port
    if args.batch_size:
        config.batch_size = args.batch_size
    if args.batch_interval:
        config.batch_interval_seconds = args.batch_interval
    if args.log_level:
        config.log_level = args.log_level
    if args.udp_rcvbuf:
        config.udp_rcvbuf_size = args.udp_rcvbuf
    if args.retry_attempts:
        config.retry_max_attempts = args.retry_attempts
    if args.retry_backoff:
        config.retry_backoff_factor = args.retry_backoff
    if args.udp_rcvbuf:
        config.udp_rcvbuf_size = args.udp_rcvbuf
    if args.retry_attempts:
        config.retry_max_attempts = args.retry_attempts
    if args.retry_backoff:
        config.retry_backoff_factor = args.retry_backoff
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Clarion Collector")
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Backend URL: {config.backend_url}")
    
    # Run collectors based on mode
    try:
        if args.mode == "native":
            await run_native_collector(config, http_port=args.native_http_port)
        elif args.mode == "agent":
            await run_agent_collector(config, port=args.agent_port)
        elif args.mode == "both":
            # Run both collectors concurrently
            await asyncio.gather(
                run_native_collector(config, http_port=args.native_http_port),
                run_agent_collector(config, port=args.agent_port),
            )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

