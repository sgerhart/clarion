"""
Policy Endpoints

Endpoints for policy generation, customization, and management.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import os

from clarion.ingest.loader import load_dataset
from clarion.ingest.sketch_builder import build_sketches
from clarion.identity import enrich_sketches
from clarion.clustering.clusterer import EndpointClusterer
from clarion.clustering.sgt_mapper import generate_sgt_taxonomy
from clarion.policy.matrix import build_policy_matrix
from clarion.policy.sgacl import SGACLGenerator

logger = logging.getLogger(__name__)

# Cache for policies (in production, use database)
_policies_cache: Optional[List[Dict]] = None

router = APIRouter()


class PolicyGenerationRequest(BaseModel):
    """Request to generate policies."""
    data_path: Optional[str] = None
    min_flow_count: int = 10
    min_flow_ratio: float = 0.01


class PolicySummary(BaseModel):
    """Summary of generated policies."""
    n_sgts: int
    n_sgacls: int
    n_matrix_cells: int
    total_flows: int


@router.post("/generate")
async def generate_policies(request: PolicyGenerationRequest):
    """
    Generate SGACL policies from clustering results.
    
    Requires clustering to be run first.
    """
    global _policies_cache
    
    try:
        # Load data
        if request.data_path:
            data_path = request.data_path
        else:
            data_path = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "..", "data", "raw", "trustsec_copilot_synth_campus"
            )
        
        dataset = load_dataset(data_path)
        
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
        
        # Generate policies
        generator = SGACLGenerator(
            min_flow_count=request.min_flow_count,
            min_flow_ratio=request.min_flow_ratio,
        )
        policies = generator.generate(matrix)
        
        # Convert to JSON-serializable format
        policies_list = []
        for policy in policies:
            policies_list.append({
                "name": policy.name,
                "src_sgt": policy.src_sgt,
                "dst_sgt": policy.dst_sgt,
                "action": policy.action,
                "rules": [r.to_dict() for r in policy.rules],
            })
        
        _policies_cache = policies_list
        
        return {
            "status": "success",
            "policies": policies_list,
            "count": len(policies_list),
        }
        
    except Exception as e:
        logger.error(f"Policy generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/matrix")
async def get_policy_matrix():
    """Get the SGT × SGT policy matrix."""
    # TODO: Return actual policy matrix
    return {
        "message": "Policy matrix endpoint - implementation in progress",
    }


@router.get("/policies")
async def get_policies():
    """List all generated SGACL policies."""
    global _policies_cache
    
    if _policies_cache is None:
        return {
            "policies": [],
            "count": 0,
        }
    
    return {
        "policies": _policies_cache,
        "count": len(_policies_cache),
    }


@router.get("/impact")
async def get_impact_analysis():
    """Get impact analysis for generated policies."""
    # TODO: Return actual impact analysis
    return {
        "message": "Impact analysis endpoint - implementation in progress",
    }

