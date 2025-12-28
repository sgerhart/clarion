"""
Clustering Endpoints

Endpoints for running clustering analysis and retrieving results.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from clarion.ingest.loader import load_dataset
from clarion.ingest.sketch_builder import build_sketches
from clarion.identity import enrich_sketches
from clarion.clustering.clusterer import EndpointClusterer
from clarion.clustering.labeling import SemanticLabeler
from clarion.clustering.sgt_mapper import generate_sgt_taxonomy
from clarion.clustering.incremental import IncrementalClusterer
from clarion.clustering.features import FeatureExtractor
from clarion.storage import get_database
from clarion.policy.matrix import build_policy_matrix
from clarion.sketches import EndpointSketch

logger = logging.getLogger(__name__)

router = APIRouter()


class ClusteringRequest(BaseModel):
    """Request to run clustering."""
    data_path: Optional[str] = None
    min_cluster_size: int = 50
    min_samples: int = 10


class ClusteringResponse(BaseModel):
    """Clustering results."""
    n_clusters: int
    n_noise: int
    silhouette_score: Optional[float]
    cluster_sizes: Dict[int, int]
    endpoint_count: int


@router.post("/run", response_model=ClusteringResponse)
async def run_clustering(request: ClusteringRequest):
    """
    Run clustering analysis on loaded data.
    
    If data_path is provided, loads that dataset.
    Otherwise uses default synthetic data.
    """
    try:
        # Load data
        if request.data_path:
            dataset = load_dataset(request.data_path)
        else:
            # Use default synthetic data
            import os
            default_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "..", "data", "raw", "trustsec_copilot_synth_campus"
            )
            if not os.path.exists(default_path):
                raise HTTPException(
                    status_code=404,
                    detail=f"Default data path not found: {default_path}"
                )
            dataset = load_dataset(default_path)
        
        # Build sketches
        logger.info("Building sketches...")
        store = build_sketches(dataset)
        
        # Enrich with identity
        logger.info("Enriching with identity...")
        enrich_sketches(store, dataset)
        
        # Cluster
        logger.info("Running clustering...")
        clusterer = EndpointClusterer(
            min_cluster_size=request.min_cluster_size,
            min_samples=request.min_samples,
        )
        result = clusterer.cluster(store)
        
        # Label clusters
        logger.info("Labeling clusters...")
        labeler = SemanticLabeler(dataset)
        labels = labeler.label_clusters(store, result)
        
        # Generate SGT taxonomy
        logger.info("Generating SGT taxonomy...")
        mapper = generate_sgt_taxonomy(store, result)
        
        return ClusteringResponse(
            n_clusters=result.n_clusters,
            n_noise=result.n_noise,
            silhouette_score=result.silhouette,
            cluster_sizes=result.cluster_sizes,
            endpoint_count=len(result.endpoint_ids),
        )
        
    except Exception as e:
        logger.error(f"Clustering failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results")
async def get_clustering_results():
    """Get latest clustering results (if available)."""
    # TODO: Store results in database/cache
    return {
        "message": "No clustering results available. Run /api/clustering/run first.",
    }


@router.get("/clusters")
async def get_clusters():
    """Get all clusters from database."""
    db = get_database()
    clusters = db.get_clusters()
    return clusters


@router.get("/clusters/{cluster_id}/members")
async def get_cluster_members(cluster_id: int):
    """Get all devices in a cluster."""
    db = get_database()
    
    # Get cluster assignments
    conn = db._get_connection()
    assignments = conn.execute("""
        SELECT ca.endpoint_id, s.switch_id, s.flow_count,
               i.user_name, i.device_name, i.ad_groups
        FROM cluster_assignments ca
        JOIN sketches s ON ca.endpoint_id = s.endpoint_id
        LEFT JOIN identity i ON s.endpoint_id = i.mac_address
        WHERE ca.cluster_id = ?
        ORDER BY s.flow_count DESC
    """, (cluster_id,)).fetchall()
    
    members = [dict(row) for row in assignments]
    
    return {
        "cluster_id": cluster_id,
        "members": members,
        "count": len(members),
    }


# Store matrix in session/cache (in production, use Redis or database)
_matrix_cache: Optional[Dict[str, Any]] = None


@router.post("/matrix/build")
async def build_matrix():
    """Build SGT matrix from current data."""
    global _matrix_cache
    
    try:
        # Load data
        import os
        default_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "..", "data", "raw", "trustsec_copilot_synth_campus"
        )
        dataset = load_dataset(default_path)
        
        # Build sketches
        store = build_sketches(dataset)
        enrich_sketches(store, dataset)
        
        # Cluster
        clusterer = EndpointClusterer(min_cluster_size=50, min_samples=10)
        result = clusterer.cluster(store)
        
        # Generate taxonomy
        taxonomy = generate_sgt_taxonomy(store, result)
        
        # Build matrix
        matrix = build_policy_matrix(dataset, store, result, taxonomy)
        
        # Convert to JSON-serializable format
        cells = []
        for (src_sgt, dst_sgt), cell in matrix.cells.items():
            cells.append({
                "src_sgt": src_sgt,
                "src_sgt_name": cell.src_sgt_name,
                "dst_sgt": dst_sgt,
                "dst_sgt_name": cell.dst_sgt_name,
                "total_flows": cell.total_flows,
                "total_bytes": cell.total_bytes,
                "top_ports": ", ".join([p[0] for p in cell.top_ports(3)]),
            })
        
        _matrix_cache = {
            "cells": cells,
            "sgt_values": matrix.sgt_values,
            "n_cells": matrix.n_cells,
        }
        
        return {
            "status": "success",
            "matrix": _matrix_cache,
        }
        
    except Exception as e:
        logger.error(f"Matrix build failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/matrix")
async def get_matrix():
    """Get the built SGT matrix."""
    if _matrix_cache is None:
        raise HTTPException(
            status_code=404,
            detail="Matrix not built. Call POST /api/clustering/matrix/build first."
        )
    return _matrix_cache


class IncrementalAssignmentRequest(BaseModel):
    """Request for incremental cluster assignment."""
    endpoint_id: str


class IncrementalAssignmentResponse(BaseModel):
    """Response from incremental assignment."""
    endpoint_id: str
    cluster_id: int
    confidence: float
    distance: float
    sgt_value: Optional[int] = None


@router.post("/incremental-assign", response_model=IncrementalAssignmentResponse)
async def incremental_assign_endpoint(request: IncrementalAssignmentRequest):
    """
    Assign a new endpoint to an existing cluster using incremental clustering.
    
    This provides a fast path (<100ms) for assigning new endpoints without
    running full clustering.
    
    Note: Full implementation requires sketch reconstruction from database.
    This endpoint is a placeholder for MVP.
    """
    try:
        # TODO: Implement sketch reconstruction from database
        # For now, return not implemented
        raise HTTPException(
            status_code=501,
            detail="Incremental assignment requires sketch reconstruction from database - not yet implemented in MVP"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in incremental assignment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending-assignments")
async def get_pending_assignments(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of endpoints to return"),
):
    """
    Get endpoints that are waiting for cluster assignment.
    
    These are endpoints that have been seen (have sketches) but haven't been
    assigned to a cluster yet.
    """
    try:
        db = get_database()
        conn = db._get_connection()
        
        # Find endpoints with sketches but no cluster assignment
        query = """
            SELECT DISTINCT s.endpoint_id, s.first_seen, s.last_seen, s.flow_count
            FROM sketches s
            LEFT JOIN cluster_assignments ca ON s.endpoint_id = ca.endpoint_id
            WHERE ca.endpoint_id IS NULL
            ORDER BY s.first_seen DESC
            LIMIT ?
        """
        cursor = conn.execute(query, (limit,))
        endpoints = [dict(row) for row in cursor.fetchall()]
        
        return {
            "endpoints": endpoints,
            "count": len(endpoints),
        }
        
    except Exception as e:
        logger.error(f"Error getting pending assignments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

