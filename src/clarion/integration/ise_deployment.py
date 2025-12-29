"""
ISE Policy Deployment Service

Service for deploying Clarion policy recommendations to Cisco ISE via ERS API.
Handles SGT creation, authorization profiles, and authorization policies.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from clarion.integration.ise_client import ISEClient, ISEAuthenticationError, ISEAPIError
from clarion.policy.recommendation import PolicyRecommendation, PolicyRule
from clarion.storage import get_database

logger = logging.getLogger(__name__)


class ISEDeploymentError(Exception):
    """Raised when ISE deployment fails."""
    pass


class ISEDeploymentService:
    """
    Service for deploying policy recommendations to ISE.
    
    Handles the full deployment workflow:
    1. Create SGTs in ISE (if they don't exist)
    2. Create authorization profiles that assign SGTs
    3. Create authorization policies with conditions
    4. Track deployment status
    
    Example:
        >>> service = ISEDeploymentService(
        ...     ise_url="https://192.168.10.31",
        ...     ise_username="admin",
        ...     ise_password="password"
        ... )
        >>> result = service.deploy_recommendation(recommendation)
    """
    
    def __init__(
        self,
        ise_url: str,
        ise_username: str,
        ise_password: str,
        verify_ssl: bool = False,
    ):
        """
        Initialize ISE deployment service.
        
        Args:
            ise_url: ISE server URL (e.g., "https://192.168.10.31")
            ise_username: ISE admin username
            ise_password: ISE admin password
            verify_ssl: Whether to verify SSL certificates
        """
        self.ise_client = ISEClient(
            base_url=ise_url,
            username=ise_username,
            password=ise_password,
            verify_ssl=verify_ssl,
        )
        self.db = get_database()
    
    def deploy_recommendation(
        self,
        recommendation: PolicyRecommendation,
        create_sgt_if_missing: bool = True,
    ) -> Dict[str, Any]:
        """
        Deploy a policy recommendation to ISE.
        
        Args:
            recommendation: PolicyRecommendation to deploy
            create_sgt_if_missing: If True, create SGT in ISE if it doesn't exist
            
        Returns:
            Deployment result with status and details
            
        Raises:
            ISEDeploymentError: If deployment fails
        """
        logger.info(f"Deploying policy recommendation {recommendation.id} to ISE")
        
        try:
            deployment_result = {
                "recommendation_id": recommendation.id,
                "deployment_status": "in_progress",
                "steps_completed": [],
                "errors": [],
                "created_resources": {},
                "deployed_at": datetime.utcnow().isoformat(),
            }
            
            # Step 1: Ensure SGT exists in ISE
            sgt_value = recommendation.recommended_sgt
            sgt_name = recommendation.recommended_sgt_name or f"SGT-{sgt_value}"
            
            if create_sgt_if_missing:
                existing_sgt = self.ise_client.get_sgt(value=sgt_value)
                if not existing_sgt:
                    logger.info(f"Creating SGT {sgt_value} ({sgt_name}) in ISE")
                    try:
                        created_sgt = self.ise_client.create_sgt(
                            name=sgt_name,
                            value=sgt_value,
                            description=f"Created by Clarion from cluster {recommendation.cluster_id}",
                        )
                        deployment_result["steps_completed"].append("sgt_created")
                        deployment_result["created_resources"]["sgt"] = {
                            "name": sgt_name,
                            "value": sgt_value,
                            "id": created_sgt.get("id"),
                        }
                    except ISEAPIError as e:
                        # SGT might already exist with different name, or other error
                        error_msg = f"Failed to create SGT: {e}"
                        logger.warning(error_msg)
                        deployment_result["errors"].append(error_msg)
                        if "duplicate" not in str(e).lower():
                            raise ISEDeploymentError(error_msg)
                else:
                    logger.info(f"SGT {sgt_value} already exists in ISE")
                    deployment_result["steps_completed"].append("sgt_exists")
            
            # Step 2: Create authorization profile
            profile_name = f"Assign-SGT-{sgt_value}"
            try:
                created_profile = self.ise_client.create_authorization_profile(
                    name=profile_name,
                    sgt_value=sgt_value,
                    description=f"Assign SGT {sgt_value} ({sgt_name}) - Created by Clarion",
                )
                deployment_result["steps_completed"].append("profile_created")
                deployment_result["created_resources"]["authorization_profile"] = {
                    "name": profile_name,
                    "id": created_profile.get("id"),
                }
            except ISEAPIError as e:
                # Profile might already exist - try to continue
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    logger.warning(f"Authorization profile {profile_name} may already exist, continuing...")
                    deployment_result["steps_completed"].append("profile_exists")
                else:
                    error_msg = f"Failed to create authorization profile: {e}"
                    logger.error(error_msg)
                    deployment_result["errors"].append(error_msg)
                    raise ISEDeploymentError(error_msg)
            
            # Step 3: Create authorization policy
            policy_name = recommendation.policy_rule.name
            condition = recommendation.policy_rule.to_ise_condition_string()
            
            try:
                created_policy = self.ise_client.create_authorization_policy(
                    name=policy_name,
                    condition=condition,
                    profile_name=profile_name,
                    description=recommendation.policy_rule.justification,
                )
                deployment_result["steps_completed"].append("policy_created")
                deployment_result["created_resources"]["authorization_policy"] = {
                    "name": policy_name,
                    "id": created_policy.get("id"),
                }
            except ISEAPIError as e:
                error_msg = f"Failed to create authorization policy: {e}"
                logger.error(error_msg)
                deployment_result["errors"].append(error_msg)
                raise ISEDeploymentError(error_msg)
            
            # Mark deployment as successful
            deployment_result["deployment_status"] = "success"
            logger.info(f"✅ Successfully deployed recommendation {recommendation.id} to ISE")
            
            # Store deployment record in database
            self._store_deployment_record(recommendation.id, deployment_result)
            
            return deployment_result
            
        except Exception as e:
            error_msg = f"ISE deployment failed: {e}"
            logger.error(error_msg, exc_info=True)
            deployment_result = {
                "recommendation_id": recommendation.id,
                "deployment_status": "failed",
                "error": str(e),
                "deployed_at": datetime.utcnow().isoformat(),
            }
            self._store_deployment_record(recommendation.id, deployment_result)
            raise ISEDeploymentError(error_msg) from e
    
    def _store_deployment_record(self, recommendation_id: Optional[int], deployment_result: Dict) -> None:
        """Store deployment record in database."""
        # TODO: Add deployment_history table to database schema
        # For now, we'll store deployment status in policy_recommendations table
        if recommendation_id:
            conn = self.db._get_connection()
            conn.execute("""
                UPDATE policy_recommendations
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (deployment_result.get("deployment_status", "deployed"), recommendation_id))
            conn.commit()
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to ISE server.
        
        Returns:
            Connection test result
        """
        try:
            is_connected = self.ise_client.test_connection()
            return {
                "status": "success" if is_connected else "failed",
                "connected": is_connected,
                "ise_url": self.ise_client.base_url,
            }
        except Exception as e:
            return {
                "status": "failed",
                "connected": False,
                "error": str(e),
                "ise_url": self.ise_client.base_url,
            }

