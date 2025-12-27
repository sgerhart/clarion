"""
Edge Agent - Main controller for edge processing.

Coordinates:
1. Flow ingestion (from simulator or NetFlow)
2. Sketch building
3. Lightweight clustering
4. Backend streaming
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path

from clarion_edge.sketch import EdgeSketch, EdgeSketchStore
from clarion_edge.simulator import FlowSimulator, SimulatorConfig, SimulatedFlow

logger = logging.getLogger(__name__)


@dataclass
class EdgeConfig:
    """Configuration for the edge agent."""
    switch_id: str = "edge-001"
    
    # Memory limits
    max_endpoints: int = 500  # ~2.5 MB for sketches
    
    # Clustering
    enable_clustering: bool = True
    n_clusters: int = 8
    cluster_interval_seconds: int = 300  # Re-cluster every 5 minutes
    
    # Backend sync
    backend_url: Optional[str] = None
    sync_interval_seconds: int = 60
    
    # Persistence
    data_dir: str = "/data"
    
    # Metrics
    metrics_interval_seconds: int = 30


class LightweightKMeans:
    """
    Memory-efficient Mini-Batch K-Means for edge deployment.
    
    Pure Python implementation - no numpy/sklearn dependency.
    """
    
    def __init__(self, n_clusters: int = 8, max_iter: int = 10):
        """
        Initialize K-Means.
        
        Args:
            n_clusters: Number of clusters
            max_iter: Maximum iterations
        """
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.centroids: List[List[float]] = []
    
    def fit(self, X: List[List[float]]) -> List[int]:
        """
        Fit the model and return cluster labels.
        
        Args:
            X: Feature matrix (list of feature vectors)
            
        Returns:
            List of cluster labels
        """
        if len(X) < self.n_clusters:
            # Not enough points - each point is its own cluster
            return list(range(len(X)))
        
        # Initialize centroids (k-means++)
        self.centroids = self._init_centroids(X)
        
        labels = [0] * len(X)
        
        for _ in range(self.max_iter):
            # Assign points to nearest centroid
            new_labels = [self._nearest_centroid(x) for x in X]
            
            # Check for convergence
            if new_labels == labels:
                break
            
            labels = new_labels
            
            # Update centroids
            self._update_centroids(X, labels)
        
        return labels
    
    def predict(self, X: List[List[float]]) -> List[int]:
        """Predict cluster labels for new data."""
        if not self.centroids:
            raise ValueError("Model not fitted")
        
        return [self._nearest_centroid(x) for x in X]
    
    def _init_centroids(self, X: List[List[float]]) -> List[List[float]]:
        """Initialize centroids using k-means++."""
        import random
        
        n_features = len(X[0])
        centroids = []
        
        # First centroid is random
        centroids.append(X[random.randint(0, len(X) - 1)][:])
        
        for _ in range(1, self.n_clusters):
            # Calculate distance to nearest centroid for each point
            distances = []
            for x in X:
                min_dist = min(self._distance(x, c) for c in centroids)
                distances.append(min_dist ** 2)
            
            # Weighted random selection
            total = sum(distances)
            if total == 0:
                # All points are at centroids
                idx = random.randint(0, len(X) - 1)
            else:
                threshold = random.random() * total
                cumulative = 0
                idx = 0
                for i, d in enumerate(distances):
                    cumulative += d
                    if cumulative >= threshold:
                        idx = i
                        break
            
            centroids.append(X[idx][:])
        
        return centroids
    
    def _nearest_centroid(self, x: List[float]) -> int:
        """Find the nearest centroid for a point."""
        min_dist = float('inf')
        nearest = 0
        
        for i, c in enumerate(self.centroids):
            dist = self._distance(x, c)
            if dist < min_dist:
                min_dist = dist
                nearest = i
        
        return nearest
    
    def _distance(self, a: List[float], b: List[float]) -> float:
        """Euclidean distance between two vectors."""
        return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))
    
    def _update_centroids(self, X: List[List[float]], labels: List[int]) -> None:
        """Update centroids based on assigned points."""
        n_features = len(X[0])
        
        for k in range(self.n_clusters):
            # Find all points in this cluster
            cluster_points = [X[i] for i, l in enumerate(labels) if l == k]
            
            if cluster_points:
                # New centroid is the mean
                self.centroids[k] = [
                    sum(p[j] for p in cluster_points) / len(cluster_points)
                    for j in range(n_features)
                ]


class EdgeAgent:
    """
    Main edge processing agent.
    
    Runs on the switch to:
    1. Ingest flows (from NetFlow or simulator)
    2. Build behavioral sketches
    3. Periodically cluster endpoints
    4. Stream results to backend
    
    Example:
        >>> config = EdgeConfig(switch_id="switch-1")
        >>> agent = EdgeAgent(config)
        >>> 
        >>> # Use with simulator for testing
        >>> sim_config = SimulatorConfig(num_endpoints=50)
        >>> agent.run_with_simulator(sim_config, duration_seconds=60)
    """
    
    def __init__(self, config: EdgeConfig):
        """Initialize the agent."""
        self.config = config
        self.store = EdgeSketchStore(
            max_endpoints=config.max_endpoints,
            switch_id=config.switch_id,
        )
        self.clusterer = LightweightKMeans(n_clusters=config.n_clusters)
        
        # Metrics
        self._flow_count = 0
        self._last_cluster_time = 0
        self._last_sync_time = 0
        self._start_time = time.time()
        
        # Callbacks
        self._on_cluster_complete: Optional[Callable] = None
        self._on_sync_complete: Optional[Callable] = None
    
    def process_flow(self, flow: SimulatedFlow) -> None:
        """
        Process a single flow.
        
        Args:
            flow: The flow to process
        """
        # Get or create sketch for this endpoint
        sketch = self.store.get_or_create(flow.src_mac)
        
        # Record the flow
        sketch.record_flow(
            dst_ip=flow.dst_ip,
            dst_port=flow.dst_port,
            proto=flow.proto,
            bytes_count=flow.bytes,
            is_outbound=True,
            timestamp=flow.timestamp,
        )
        
        self._flow_count += 1
        
        # Check if we need to re-cluster
        if self._should_cluster():
            self._run_clustering()
    
    def _should_cluster(self) -> bool:
        """Check if we should run clustering."""
        if not self.config.enable_clustering:
            return False
        
        elapsed = time.time() - self._last_cluster_time
        return elapsed >= self.config.cluster_interval_seconds
    
    def _run_clustering(self) -> None:
        """Run lightweight clustering on current sketches."""
        if len(self.store) < self.config.n_clusters:
            logger.debug(f"Not enough endpoints for clustering ({len(self.store)})")
            return
        
        logger.info(f"Running clustering on {len(self.store)} endpoints")
        
        # Extract features
        features, endpoint_ids = self.store.get_feature_matrix()
        
        # Run K-means
        start = time.time()
        labels = self.clusterer.fit(features)
        elapsed = time.time() - start
        
        # Assign labels back to sketches
        for endpoint_id, label in zip(endpoint_ids, labels):
            sketch = self.store._sketches.get(endpoint_id)
            if sketch:
                sketch.local_cluster_id = label
        
        # Count cluster sizes
        cluster_sizes = {}
        for label in labels:
            cluster_sizes[label] = cluster_sizes.get(label, 0) + 1
        
        logger.info(
            f"Clustering complete in {elapsed:.2f}s: "
            f"{len(cluster_sizes)} clusters, sizes: {cluster_sizes}"
        )
        
        self._last_cluster_time = time.time()
        
        if self._on_cluster_complete:
            self._on_cluster_complete(labels, cluster_sizes)
    
    def get_sketches_for_sync(self) -> List[Dict]:
        """Get sketches ready for syncing to backend."""
        return [s.to_dict() for s in self.store]
    
    def get_serialized_sketches(self) -> bytes:
        """Get serialized sketches for efficient network transfer."""
        sketches = self.store.get_all_sketches()
        
        # Simple framing: count + concatenated sketch bytes
        parts = [len(sketches).to_bytes(4, 'little')]
        for s in sketches:
            sketch_bytes = s.to_bytes()
            parts.append(len(sketch_bytes).to_bytes(4, 'little'))
            parts.append(sketch_bytes)
        
        return b''.join(parts)
    
    async def sync_to_backend(self) -> bool:
        """
        Sync sketches to backend.
        
        Returns:
            True if sync was successful
        """
        if not self.config.backend_url:
            logger.debug("No backend URL configured, skipping sync")
            return False
        
        try:
            import httpx
            
            sketches = self.get_sketches_for_sync()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.backend_url}/api/edge/sketches",
                    json={
                        "switch_id": self.config.switch_id,
                        "sketches": sketches,
                        "timestamp": int(time.time()),
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
            
            logger.info(f"Synced {len(sketches)} sketches to backend")
            self._last_sync_time = time.time()
            
            if self._on_sync_complete:
                self._on_sync_complete(len(sketches))
            
            return True
            
        except ImportError:
            logger.warning("httpx not installed, cannot sync to backend")
            return False
        except Exception as e:
            logger.error(f"Failed to sync to backend: {e}")
            return False
    
    def get_metrics(self) -> Dict:
        """Get current metrics."""
        uptime = time.time() - self._start_time
        
        return {
            "switch_id": self.config.switch_id,
            "uptime_seconds": int(uptime),
            "flows_processed": self._flow_count,
            "flows_per_second": self._flow_count / max(uptime, 1),
            "endpoints_tracked": len(self.store),
            "memory_kb": self.store.memory_bytes() / 1024,
            "last_cluster_seconds_ago": time.time() - self._last_cluster_time if self._last_cluster_time else None,
            "last_sync_seconds_ago": time.time() - self._last_sync_time if self._last_sync_time else None,
        }
    
    def run_with_simulator(
        self,
        simulator_config: SimulatorConfig,
        duration_seconds: int = 60,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Dict:
        """
        Run the agent with a flow simulator.
        
        This is the main entry point for testing without a physical switch.
        
        Args:
            simulator_config: Configuration for the simulator
            duration_seconds: How long to run
            progress_callback: Called with flow count periodically
            
        Returns:
            Final metrics
        """
        logger.info(
            f"Starting edge agent with simulator "
            f"({simulator_config.num_endpoints} endpoints, {duration_seconds}s)"
        )
        
        simulator = FlowSimulator(simulator_config)
        
        last_progress = 0
        for flow in simulator.generate(duration_seconds=duration_seconds):
            self.process_flow(flow)
            
            if progress_callback and self._flow_count - last_progress >= 1000:
                progress_callback(self._flow_count)
                last_progress = self._flow_count
        
        # Final clustering
        if self.config.enable_clustering:
            self._run_clustering()
        
        metrics = self.get_metrics()
        logger.info(
            f"Agent finished: {metrics['flows_processed']} flows, "
            f"{metrics['endpoints_tracked']} endpoints, "
            f"{metrics['memory_kb']:.1f} KB memory"
        )
        
        return metrics
    
    def save_state(self, path: Optional[str] = None) -> str:
        """
        Save current state to disk.
        
        Args:
            path: Path to save to (defaults to data_dir/state.json)
            
        Returns:
            Path where state was saved
        """
        if path is None:
            path = f"{self.config.data_dir}/state.json"
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            "config": {
                "switch_id": self.config.switch_id,
                "max_endpoints": self.config.max_endpoints,
            },
            "metrics": self.get_metrics(),
            "sketches": self.get_sketches_for_sync(),
        }
        
        with open(path, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Saved state to {path}")
        return path
    
    def print_summary(self) -> None:
        """Print a summary of current state."""
        metrics = self.get_metrics()
        store_summary = self.store.summary()
        
        print("\n" + "=" * 60)
        print("EDGE AGENT SUMMARY")
        print("=" * 60)
        print(f"Switch ID:         {self.config.switch_id}")
        print(f"Uptime:            {metrics['uptime_seconds']}s")
        print(f"Flows processed:   {metrics['flows_processed']:,}")
        print(f"Flows/second:      {metrics['flows_per_second']:.1f}")
        print(f"Endpoints:         {metrics['endpoints_tracked']}/{self.config.max_endpoints}")
        print(f"Memory:            {metrics['memory_kb']:.1f} KB")
        print(f"Total flows:       {store_summary['total_flows']:,}")
        print("=" * 60)
        
        # Cluster distribution
        if self.config.enable_clustering:
            cluster_counts: Dict[int, int] = {}
            for sketch in self.store:
                cid = sketch.local_cluster_id
                cluster_counts[cid] = cluster_counts.get(cid, 0) + 1
            
            print("\nCluster Distribution:")
            for cid in sorted(cluster_counts.keys()):
                count = cluster_counts[cid]
                bar = "█" * (count // 2)
                print(f"  Cluster {cid:2d}: {count:4d} {bar}")
        
        print()


