"""
Main entry point for Clarion Edge.

Can run in multiple modes:
1. Simulator mode - For testing without a physical switch
2. NetFlow mode - Listen for actual NetFlow data
3. API mode - Expose REST API for control

Usage:
    python -m clarion_edge.main --mode simulator --duration 60
    python -m clarion_edge.main --mode netflow --port 2055
    python -m clarion_edge.main --mode api --api-port 8080
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path

from clarion_edge.agent import EdgeAgent, EdgeConfig
from clarion_edge.simulator import FlowSimulator, SimulatorConfig
from clarion_edge.streaming import StreamConfig, SketchStreamer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Clarion Edge - Lightweight flow collector"
    )
    
    parser.add_argument(
        "--mode",
        choices=["simulator", "netflow", "api"],
        default="simulator",
        help="Operating mode",
    )
    
    parser.add_argument(
        "--switch-id",
        default=os.environ.get("CLARION_EDGE_SWITCH_ID", "edge-001"),
        help="Switch identifier",
    )
    
    # Simulator mode options
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Simulator duration in seconds",
    )
    
    parser.add_argument(
        "--endpoints",
        type=int,
        default=50,
        help="Number of simulated endpoints",
    )
    
    parser.add_argument(
        "--flows-per-second",
        type=float,
        default=100.0,
        help="Simulated flows per second",
    )
    
    parser.add_argument(
        "--replay-csv",
        type=str,
        help="CSV file to replay (overrides synthetic generation)",
    )
    
    # Backend options
    parser.add_argument(
        "--backend-url",
        default=os.environ.get("CLARION_EDGE_BACKEND_URL", ""),
        help="Backend URL for syncing",
    )
    
    parser.add_argument(
        "--sync-interval",
        type=int,
        default=60,
        help="Sync interval in seconds",
    )
    
    # Storage options
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("CLARION_EDGE_DATA_DIR", "./data"),
        help="Data directory for state persistence",
    )
    
    # Clustering options
    parser.add_argument(
        "--clusters",
        type=int,
        default=8,
        help="Number of clusters for K-means",
    )
    
    parser.add_argument(
        "--cluster-interval",
        type=int,
        default=300,
        help="Clustering interval in seconds",
    )
    
    # API mode options
    parser.add_argument(
        "--api-port",
        type=int,
        default=int(os.environ.get("CLARION_EDGE_API_PORT", "8080")),
        help="API server port",
    )
    
    return parser.parse_args()


def run_simulator_mode(args) -> None:
    """Run in simulator mode."""
    logger.info("Starting in simulator mode")
    
    # Configure edge agent
    edge_config = EdgeConfig(
        switch_id=args.switch_id,
        max_endpoints=500,
        enable_clustering=True,
        n_clusters=args.clusters,
        cluster_interval_seconds=args.cluster_interval,
        backend_url=args.backend_url if args.backend_url else None,
        sync_interval_seconds=args.sync_interval,
        data_dir=args.data_dir,
    )
    
    agent = EdgeAgent(edge_config)
    
    # Configure simulator
    if args.replay_csv:
        sim_config = SimulatorConfig(
            mode="replay",
            csv_path=args.replay_csv,
            replay_speed=1.0,
        )
    else:
        sim_config = SimulatorConfig(
            mode="synthetic",
            num_endpoints=args.endpoints,
            flows_per_second=args.flows_per_second,
        )
    
    # Progress callback
    def on_progress(count):
        logger.info(f"Processed {count:,} flows...")
    
    # Run
    metrics = agent.run_with_simulator(
        sim_config,
        duration_seconds=args.duration,
        progress_callback=on_progress,
    )
    
    # Print summary
    agent.print_summary()
    
    # Save state
    state_path = agent.save_state()
    logger.info(f"State saved to {state_path}")
    
    # Sync to backend if configured
    if args.backend_url:
        logger.info(f"Syncing to backend: {args.backend_url}")
        asyncio.run(_sync_to_backend(agent, args))


async def _sync_to_backend(agent: EdgeAgent, args) -> None:
    """Sync agent state to backend."""
    config = StreamConfig(
        backend_url=args.backend_url,
        switch_id=args.switch_id,
    )
    
    streamer = SketchStreamer(config)
    
    try:
        if await streamer.start():
            sketches = agent.store.get_all_sketches()
            success = await streamer.send(sketches)
            
            if success:
                logger.info(f"Successfully synced {len(sketches)} sketches")
            else:
                logger.error("Failed to sync sketches")
        else:
            logger.error("Failed to connect to backend")
    finally:
        await streamer.stop()


def run_api_mode(args) -> None:
    """Run in API mode with FastAPI server."""
    logger.info(f"Starting API server on port {args.api_port}")
    
    try:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        import uvicorn
    except ImportError:
        logger.error("FastAPI/uvicorn not installed. Install with: pip install fastapi uvicorn")
        sys.exit(1)
    
    # Create agent
    edge_config = EdgeConfig(
        switch_id=args.switch_id,
        max_endpoints=500,
        enable_clustering=True,
        n_clusters=args.clusters,
        cluster_interval_seconds=args.cluster_interval,
        backend_url=args.backend_url if args.backend_url else None,
        data_dir=args.data_dir,
    )
    
    agent = EdgeAgent(edge_config)
    
    # Create FastAPI app
    app = FastAPI(
        title="Clarion Edge API",
        description="Edge agent REST API",
        version="0.2.0",
    )
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "switch_id": args.switch_id}
    
    @app.get("/metrics")
    async def metrics():
        """Get agent metrics."""
        return agent.get_metrics()
    
    @app.get("/sketches")
    async def get_sketches():
        """Get all sketches."""
        return {
            "switch_id": args.switch_id,
            "count": len(agent.store),
            "sketches": agent.get_sketches_for_sync(),
        }
    
    @app.get("/summary")
    async def summary():
        """Get store summary."""
        return agent.store.summary()
    
    @app.post("/simulate")
    async def simulate(
        duration: int = 10,
        endpoints: int = 20,
        flows_per_second: float = 50.0,
    ):
        """Run a quick simulation."""
        sim_config = SimulatorConfig(
            mode="synthetic",
            num_endpoints=endpoints,
            flows_per_second=flows_per_second,
        )
        
        metrics = agent.run_with_simulator(
            sim_config,
            duration_seconds=duration,
        )
        
        return {
            "status": "completed",
            "metrics": metrics,
        }
    
    @app.post("/sync")
    async def sync():
        """Sync to backend."""
        if not args.backend_url:
            return JSONResponse(
                status_code=400,
                content={"error": "No backend URL configured"},
            )
        
        await _sync_to_backend(agent, args)
        return {"status": "synced"}
    
    # Run server
    uvicorn.run(app, host="0.0.0.0", port=args.api_port)


def main():
    """Main entry point."""
    args = parse_args()
    
    logger.info(f"Clarion Edge starting (switch_id={args.switch_id})")
    
    # Ensure data directory exists
    Path(args.data_dir).mkdir(parents=True, exist_ok=True)
    
    if args.mode == "simulator":
        run_simulator_mode(args)
    elif args.mode == "api":
        run_api_mode(args)
    elif args.mode == "netflow":
        logger.error("NetFlow mode not yet implemented")
        logger.info("Use simulator mode for testing")
        sys.exit(1)
    else:
        logger.error(f"Unknown mode: {args.mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()


