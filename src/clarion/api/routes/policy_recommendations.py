"""
Policy Recommendation API Routes

Endpoints for ISE policy recommendations including:
- Generate recommendations for clusters
- Generate recommendations for device cluster changes
- List pending recommendations
- Update recommendation status
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json

from clarion.policy.recommendation import PolicyRecommendationEngine, PolicyRecommendation
from clarion.policy.authorization_exporter import ISEAuthorizationPolicyExporter
from clarion.integration.ise_deployment import ISEDeploymentService, ISEDeploymentError
from clarion.storage import get_database
from fastapi.responses import Response, JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Request/Response Models ==========

class PolicyConditionResponse(BaseModel):
    """Policy condition response."""
    type: str
    value: str
    operator: str
    ise_expression: str


class PolicyRuleResponse(BaseModel):
    """Policy rule response."""
    name: str
    conditions: List[PolicyConditionResponse]
    action: str
    sgt_value: int
    justification: str
    ise_condition_string: str


class PolicyRecommendationResponse(BaseModel):
    """Policy recommendation response."""
    id: Optional[int] = None
    cluster_id: int
    recommended_sgt: int
    recommended_sgt_name: Optional[str] = None
    policy_rule: PolicyRuleResponse
    devices_affected: int = 0
    ad_groups_affected: List[str] = []
    device_profiles_affected: List[str] = []
    device_types_affected: List[str] = []
    status: str = "pending"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    endpoint_id: Optional[str] = None
    old_cluster_id: Optional[int] = None
    old_sgt: Optional[int] = None


class PolicyRecommendationStatusUpdate(BaseModel):
    """Request to update recommendation status."""
    status: str = Field(..., description="Status: pending, accepted, rejected, deployed")


class ISEDeploymentRequest(BaseModel):
    """Request to deploy policy recommendation to ISE."""
    ise_url: str = Field(..., description="ISE server URL (e.g., https://192.168.10.31)")
    ise_username: str = Field(..., description="ISE admin username")
    ise_password: str = Field(..., description="ISE admin password")
    verify_ssl: bool = Field(False, description="Verify SSL certificates")
    create_sgt_if_missing: bool = Field(True, description="Create SGT in ISE if it doesn't exist")


# ========== Policy Recommendation Endpoints ==========

@router.post("/policy/recommendations/cluster/{cluster_id}", response_model=PolicyRecommendationResponse)
async def generate_cluster_recommendation(
    cluster_id: int,
    min_percentage: float = Query(0.5, ge=0.0, le=1.0, description="Minimum percentage threshold for attributes"),
    replace_existing: bool = Query(False, description="Replace existing pending recommendation if one exists"),
):
    """
    Generate policy recommendation for a cluster.
    
    Analyzes cluster members to identify common attributes (AD groups, device types, etc.)
    and generates an ISE authorization policy rule recommendation.
    
    If a pending recommendation already exists for this cluster, it will be kept unless
    replace_existing=True is specified.
    """
    try:
        db = get_database()
        
        # Check if a pending recommendation already exists
        existing_recs = db.list_policy_recommendations(
            cluster_id=cluster_id,
            status='pending',
            limit=1
        )
        
        if existing_recs and not replace_existing:
            # Return the existing recommendation instead of creating a new one
            rec_data = existing_recs[0]
            # Convert to response model
            policy_rule = PolicyRuleResponse(
                name=rec_data['policy_rule_name'],
                conditions=[
                    PolicyConditionResponse(**cond) for cond in rec_data['policy_rule_conditions']
                ],
                action=rec_data['policy_rule_action'],
                sgt_value=rec_data['recommended_sgt'],
                justification=rec_data.get('policy_rule_justification', ''),
                ise_condition_string=' OR '.join([
                    cond.get('ise_expression', '') for cond in rec_data['policy_rule_conditions']
                ]),
            )
            
            # Handle None values
            ad_groups = rec_data.get('ad_groups_affected') or []
            device_profiles = rec_data.get('device_profiles_affected') or []
            device_types = rec_data.get('device_types_affected') or []
            
            if isinstance(ad_groups, str):
                ad_groups = json.loads(ad_groups) if ad_groups else []
            if isinstance(device_profiles, str):
                device_profiles = json.loads(device_profiles) if device_profiles else []
            if isinstance(device_types, str):
                device_types = json.loads(device_types) if device_types else []
            
            existing_recommendation = PolicyRecommendationResponse(
                id=rec_data['id'],
                cluster_id=rec_data['cluster_id'],
                recommended_sgt=rec_data['recommended_sgt'],
                recommended_sgt_name=rec_data.get('recommended_sgt_name'),
                policy_rule=policy_rule,
                devices_affected=rec_data.get('devices_affected', 0) or 0,
                ad_groups_affected=ad_groups if isinstance(ad_groups, list) else [],
                device_profiles_affected=device_profiles if isinstance(device_profiles, list) else [],
                device_types_affected=device_types if isinstance(device_types, list) else [],
                status=rec_data['status'],
                created_at=rec_data.get('created_at'),
                updated_at=rec_data.get('updated_at'),
                endpoint_id=rec_data.get('endpoint_id'),
                old_cluster_id=rec_data.get('old_cluster_id'),
                old_sgt=rec_data.get('old_sgt'),
            )
            return existing_recommendation
        
        engine = PolicyRecommendationEngine(db)
        
        recommendation = engine.generate_cluster_recommendation(cluster_id, min_percentage)
        
        if not recommendation:
            raise HTTPException(
                status_code=404,
                detail=f"Cluster {cluster_id} not found or has no recommended SGT"
            )
        
        # Store the recommendation
        recommendation.id = db.store_policy_recommendation(
            cluster_id=recommendation.cluster_id,
            recommended_sgt=recommendation.recommended_sgt,
            recommended_sgt_name=recommendation.recommended_sgt_name,
            policy_rule_name=recommendation.policy_rule.name,
            policy_rule_conditions=[cond.to_dict() for cond in recommendation.policy_rule.conditions],
            policy_rule_action=recommendation.policy_rule.action,
            policy_rule_justification=recommendation.policy_rule.justification,
            devices_affected=recommendation.devices_affected,
            ad_groups_affected=recommendation.ad_groups_affected,
            device_profiles_affected=recommendation.device_profiles_affected,
            device_types_affected=recommendation.device_types_affected,
            endpoint_id=recommendation.endpoint_id,
            old_cluster_id=recommendation.old_cluster_id,
            old_sgt=recommendation.old_sgt,
            status=recommendation.status,
        )
        
        return PolicyRecommendationResponse(**recommendation.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating cluster recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/policy/recommendations/device/{endpoint_id}", response_model=PolicyRecommendationResponse)
async def generate_device_recommendation(
    endpoint_id: str,
    new_cluster_id: int = Query(..., description="New cluster ID for the device"),
    old_cluster_id: Optional[int] = Query(None, description="Previous cluster ID (if known)"),
):
    """
    Generate policy recommendation when a device is moved to a new cluster.
    
    This is typically called automatically when a device's cluster assignment changes.
    """
    try:
        db = get_database()
        engine = PolicyRecommendationEngine(db)
        
        recommendation = engine.generate_device_recommendation(
            endpoint_id=endpoint_id,
            new_cluster_id=new_cluster_id,
            old_cluster_id=old_cluster_id,
        )
        
        if not recommendation:
            raise HTTPException(
                status_code=404,
                detail=f"Could not generate recommendation for device {endpoint_id} in cluster {new_cluster_id}"
            )
        
        # Store the recommendation
        recommendation.id = db.store_policy_recommendation(
            cluster_id=recommendation.cluster_id,
            recommended_sgt=recommendation.recommended_sgt,
            recommended_sgt_name=recommendation.recommended_sgt_name,
            policy_rule_name=recommendation.policy_rule.name,
            policy_rule_conditions=[cond.to_dict() for cond in recommendation.policy_rule.conditions],
            policy_rule_action=recommendation.policy_rule.action,
            policy_rule_justification=recommendation.policy_rule.justification,
            devices_affected=recommendation.devices_affected,
            ad_groups_affected=recommendation.ad_groups_affected,
            device_profiles_affected=recommendation.device_profiles_affected,
            device_types_affected=recommendation.device_types_affected,
            endpoint_id=recommendation.endpoint_id,
            old_cluster_id=recommendation.old_cluster_id,
            old_sgt=recommendation.old_sgt,
            status=recommendation.status,
        )
        
        return PolicyRecommendationResponse(**recommendation.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating device recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policy/recommendations", response_model=List[PolicyRecommendationResponse])
async def list_policy_recommendations(
    status: Optional[str] = Query(None, description="Filter by status: pending, accepted, rejected, deployed"),
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    endpoint_id: Optional[str] = Query(None, description="Filter by endpoint ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of recommendations to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List policy recommendations with optional filters."""
    try:
        db = get_database()
        recommendations_data = db.list_policy_recommendations(
            status=status,
            cluster_id=cluster_id,
            endpoint_id=endpoint_id,
            limit=limit,
            offset=offset,
        )
        
        # Convert to response models
        recommendations = []
        for rec_data in recommendations_data:
            # Build PolicyRuleResponse from stored data
            policy_rule = PolicyRuleResponse(
                name=rec_data['policy_rule_name'],
                conditions=[
                    PolicyConditionResponse(**cond) for cond in rec_data['policy_rule_conditions']
                ],
                action=rec_data['policy_rule_action'],
                sgt_value=rec_data['recommended_sgt'],
                justification=rec_data.get('policy_rule_justification', ''),
                ise_condition_string=' OR '.join([
                    cond.get('ise_expression', '') for cond in rec_data['policy_rule_conditions']
                ]),
            )
            
            # Handle None values - convert to empty lists for list fields
            ad_groups = rec_data.get('ad_groups_affected') or []
            device_profiles = rec_data.get('device_profiles_affected') or []
            device_types = rec_data.get('device_types_affected') or []
            
            # If stored as JSON string, parse it
            if isinstance(ad_groups, str):
                ad_groups = json.loads(ad_groups) if ad_groups else []
            if isinstance(device_profiles, str):
                device_profiles = json.loads(device_profiles) if device_profiles else []
            if isinstance(device_types, str):
                device_types = json.loads(device_types) if device_types else []
            
            recommendation = PolicyRecommendationResponse(
                id=rec_data['id'],
                cluster_id=rec_data['cluster_id'],
                recommended_sgt=rec_data['recommended_sgt'],
                recommended_sgt_name=rec_data.get('recommended_sgt_name'),
                policy_rule=policy_rule,
                devices_affected=rec_data.get('devices_affected', 0) or 0,
                ad_groups_affected=ad_groups if isinstance(ad_groups, list) else [],
                device_profiles_affected=device_profiles if isinstance(device_profiles, list) else [],
                device_types_affected=device_types if isinstance(device_types, list) else [],
                status=rec_data['status'],
                created_at=rec_data.get('created_at'),
                updated_at=rec_data.get('updated_at'),
                endpoint_id=rec_data.get('endpoint_id'),
                old_cluster_id=rec_data.get('old_cluster_id'),
                old_sgt=rec_data.get('old_sgt'),
            )
            recommendations.append(recommendation)
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error listing policy recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policy/recommendations/{recommendation_id}", response_model=PolicyRecommendationResponse)
async def get_policy_recommendation(recommendation_id: int):
    """Get a specific policy recommendation by ID."""
    try:
        db = get_database()
        rec_data = db.get_policy_recommendation(recommendation_id)
        
        if not rec_data:
            raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")
        
        # Build PolicyRuleResponse from stored data
        policy_rule = PolicyRuleResponse(
            name=rec_data['policy_rule_name'],
            conditions=[
                PolicyConditionResponse(**cond) for cond in rec_data['policy_rule_conditions']
            ],
            action=rec_data['policy_rule_action'],
            sgt_value=rec_data['recommended_sgt'],
            justification=rec_data.get('policy_rule_justification', ''),
            ise_condition_string=' OR '.join([
                cond.get('ise_expression', '') for cond in rec_data['policy_rule_conditions']
            ]),
        )
        
        recommendation = PolicyRecommendationResponse(
            id=rec_data['id'],
            cluster_id=rec_data['cluster_id'],
            recommended_sgt=rec_data['recommended_sgt'],
            recommended_sgt_name=rec_data.get('recommended_sgt_name'),
            policy_rule=policy_rule,
            devices_affected=rec_data.get('devices_affected', 0),
            ad_groups_affected=rec_data.get('ad_groups_affected', []),
            device_profiles_affected=rec_data.get('device_profiles_affected', []),
            device_types_affected=rec_data.get('device_types_affected', []),
            status=rec_data['status'],
            created_at=rec_data.get('created_at'),
            updated_at=rec_data.get('updated_at'),
            endpoint_id=rec_data.get('endpoint_id'),
            old_cluster_id=rec_data.get('old_cluster_id'),
            old_sgt=rec_data.get('old_sgt'),
        )
        
        return recommendation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting policy recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/policy/recommendations/{recommendation_id}/status", response_model=PolicyRecommendationResponse)
async def update_policy_recommendation_status(
    recommendation_id: int,
    update: PolicyRecommendationStatusUpdate,
):
    """Update the status of a policy recommendation."""
    try:
        db = get_database()
        
        # Validate status
        valid_statuses = ['pending', 'accepted', 'rejected', 'deployed']
        if update.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Check if recommendation exists
        rec_data = db.get_policy_recommendation(recommendation_id)
        if not rec_data:
            raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")
        
        # Update status
        db.update_policy_recommendation_status(recommendation_id, update.status)
        
        # Fetch updated recommendation
        rec_data = db.get_policy_recommendation(recommendation_id)
        
        # Build response
        policy_rule = PolicyRuleResponse(
            name=rec_data['policy_rule_name'],
            conditions=[
                PolicyConditionResponse(**cond) for cond in rec_data['policy_rule_conditions']
            ],
            action=rec_data['policy_rule_action'],
            sgt_value=rec_data['recommended_sgt'],
            justification=rec_data.get('policy_rule_justification', ''),
            ise_condition_string=' OR '.join([
                cond.get('ise_expression', '') for cond in rec_data['policy_rule_conditions']
            ]),
        )
        
        recommendation = PolicyRecommendationResponse(
            id=rec_data['id'],
            cluster_id=rec_data['cluster_id'],
            recommended_sgt=rec_data['recommended_sgt'],
            recommended_sgt_name=rec_data.get('recommended_sgt_name'),
            policy_rule=policy_rule,
            devices_affected=rec_data.get('devices_affected', 0),
            ad_groups_affected=rec_data.get('ad_groups_affected', []),
            device_profiles_affected=rec_data.get('device_profiles_affected', []),
            device_types_affected=rec_data.get('device_types_affected', []),
            status=rec_data['status'],
            created_at=rec_data.get('created_at'),
            updated_at=rec_data.get('updated_at'),
            endpoint_id=rec_data.get('endpoint_id'),
            old_cluster_id=rec_data.get('old_cluster_id'),
            old_sgt=rec_data.get('old_sgt'),
        )
        
        return recommendation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating policy recommendation status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/policy/recommendations/{recommendation_id}")
async def delete_policy_recommendation(recommendation_id: int):
    """Delete a policy recommendation."""
    try:
        db = get_database()
        
        # Check if recommendation exists
        rec_data = db.get_policy_recommendation(recommendation_id)
        if not rec_data:
            raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")
        
        db.delete_policy_recommendation(recommendation_id)
        
        return {"message": f"Recommendation {recommendation_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting policy recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========== Helper Functions ==========

def _parse_datetime_string(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse datetime string from database (ISO format, may or may not have timezone)."""
    if not dt_str:
        return None
    try:
        # Try parsing with timezone first
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        try:
            # Try parsing without timezone
            return datetime.fromisoformat(dt_str)
        except ValueError:
            logger.warning(f"Could not parse datetime string: {dt_str}")
            return None


def _convert_db_rec_to_policy_recommendation(rec_data: Dict) -> PolicyRecommendation:
    """
    Convert database record to PolicyRecommendation object.
    
    Helper function to reconstruct PolicyRecommendation from database record.
    """
    from clarion.policy.recommendation import PolicyCondition, PolicyRule
    
    # Reconstruct PolicyConditions
    conditions = []
    for cond_dict in rec_data.get('policy_rule_conditions', []):
        conditions.append(PolicyCondition(
            type=cond_dict.get('type', ''),
            value=cond_dict.get('value', ''),
            operator=cond_dict.get('operator', 'EQUALS'),
        ))
    
    # Reconstruct PolicyRule
    policy_rule = PolicyRule(
        name=rec_data.get('policy_rule_name', ''),
        conditions=conditions,
        action=rec_data.get('policy_rule_action', ''),
        sgt_value=rec_data.get('recommended_sgt', 0),
        justification=rec_data.get('policy_rule_justification', ''),
    )
    
    # Reconstruct PolicyRecommendation
    recommendation = PolicyRecommendation(
        id=rec_data.get('id'),
        cluster_id=rec_data.get('cluster_id', 0),
        recommended_sgt=rec_data.get('recommended_sgt', 0),
        recommended_sgt_name=rec_data.get('recommended_sgt_name'),
        policy_rule=policy_rule,
        devices_affected=rec_data.get('devices_affected', 0),
        ad_groups_affected=rec_data.get('ad_groups_affected', []),
        device_profiles_affected=rec_data.get('device_profiles_affected', []),
        device_types_affected=rec_data.get('device_types_affected', []),
        status=rec_data.get('status', 'pending'),
        created_at=_parse_datetime_string(rec_data.get('created_at')),
        updated_at=_parse_datetime_string(rec_data.get('updated_at')),
        endpoint_id=rec_data.get('endpoint_id'),
        old_cluster_id=rec_data.get('old_cluster_id'),
        old_sgt=rec_data.get('old_sgt'),
    )
    
    return recommendation


# ========== ISE Policy Export Endpoints ==========

@router.get("/policy/recommendations/{recommendation_id}/ise-config")
async def export_ise_policy_config(
    recommendation_id: int,
    format: str = Query("json", regex="^(json|xml|cli|all)$", description="Export format: json, xml, cli, or all"),
):
    """
    Export ISE authorization policy configuration for a recommendation.
    
    Returns ISE-compatible policy configuration in the requested format.
    """
    try:
        db = get_database()
        
        # Get recommendation
        rec_data = db.get_policy_recommendation(recommendation_id)
        if not rec_data:
            raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")
        
        # Convert database record to PolicyRecommendation object
        recommendation = _convert_db_rec_to_policy_recommendation(rec_data)
        
        # Export using ISE exporter
        exporter = ISEAuthorizationPolicyExporter()
        export = exporter.export_recommendation(recommendation)
        
        # Return in requested format
        if format == "json":
            return JSONResponse(
                content=json.loads(export.json_config),
                headers={
                    "Content-Disposition": f'attachment; filename="ise_policy_{recommendation_id}.json"'
                }
            )
        elif format == "xml":
            return Response(
                content=export.xml_config,
                media_type="application/xml",
                headers={
                    "Content-Disposition": f'attachment; filename="ise_policy_{recommendation_id}.xml"'
                }
            )
        elif format == "cli":
            return Response(
                content=export.cli_config,
                media_type="text/plain",
                headers={
                    "Content-Disposition": f'attachment; filename="ise_policy_{recommendation_id}.txt"'
                }
            )
        else:  # format == "all"
            return {
                "json": json.loads(export.json_config),
                "xml": export.xml_config,
                "cli": export.cli_config,
                "deployment_guide": export.deployment_guide,
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting ISE policy config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policy/recommendations/{recommendation_id}/ise-config/deployment-guide")
async def get_deployment_guide(recommendation_id: int):
    """Get deployment guide for a policy recommendation."""
    try:
        db = get_database()
        
        # Get recommendation
        rec_data = db.get_policy_recommendation(recommendation_id)
        if not rec_data:
            raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")
        
        # Convert database record to PolicyRecommendation object
        recommendation = _convert_db_rec_to_policy_recommendation(rec_data)
        
        # Export using ISE exporter
        exporter = ISEAuthorizationPolicyExporter()
        export = exporter.export_recommendation(recommendation)
        
        return Response(
            content=export.deployment_guide,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="deployment_guide_{recommendation_id}.md"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating deployment guide: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/policy/recommendations/{recommendation_id}/deploy")
async def deploy_to_ise(
    recommendation_id: int,
    deployment_request: ISEDeploymentRequest,
):
    """
    Deploy a policy recommendation to ISE via ERS API.
    
    This endpoint will:
    1. Create SGT in ISE (if it doesn't exist)
    2. Create authorization profile that assigns the SGT
    3. Create authorization policy with the recommended conditions
    4. Track deployment status
    
    Args:
        recommendation_id: Policy recommendation ID to deploy
        deployment_request: ISE connection details and deployment options
    """
    try:
        db = get_database()
        
        # Get recommendation
        rec_data = db.get_policy_recommendation(recommendation_id)
        if not rec_data:
            raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")
        
        # Convert database record to PolicyRecommendation object
        recommendation = _convert_db_rec_to_policy_recommendation(rec_data)
        
        # Create deployment service
        deployment_service = ISEDeploymentService(
            ise_url=deployment_request.ise_url,
            ise_username=deployment_request.ise_username,
            ise_password=deployment_request.ise_password,
            verify_ssl=deployment_request.verify_ssl,
        )
        
        # Test connection first
        connection_test = deployment_service.test_connection()
        if not connection_test.get("connected"):
            raise HTTPException(
                status_code=400,
                detail=f"Failed to connect to ISE: {connection_test.get('error', 'Unknown error')}"
            )
        
        # Deploy the recommendation
        try:
            deployment_result = deployment_service.deploy_recommendation(
                recommendation=recommendation,
                create_sgt_if_missing=deployment_request.create_sgt_if_missing,
            )
            
            return {
                "success": True,
                "message": f"Successfully deployed recommendation {recommendation_id} to ISE",
                "deployment_result": deployment_result,
            }
            
        except ISEDeploymentError as e:
            logger.error(f"ISE deployment failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to deploy to ISE: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying to ISE: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

