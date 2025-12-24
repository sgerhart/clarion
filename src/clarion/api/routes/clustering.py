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

