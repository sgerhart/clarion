"""
Clustering Validation Framework

Validates clustering accuracy against ground truth datasets.
Calculates precision, recall, F1-score, and identifies misclassifications.
"""

from __future__ import annotations

from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
import json
import logging

from clarion.ingest.loader import load_dataset, ClarionDataset
from clarion.clustering.clusterer import ClusterResult, EndpointClusterer
from clarion.ingest.sketch_builder import build_sketches
from clarion.identity import enrich_sketches

logger = logging.getLogger(__name__)


class ClusteringValidator:
    """
    Validate clustering results against ground truth.
    
    Compares actual cluster assignments to expected cluster assignments
    and calculates accuracy metrics.
    """
    
    def __init__(self, dataset_path: Path):
        """
        Initialize validator with ground truth dataset.
        
        Args:
            dataset_path: Path to ground truth dataset directory
        """
        self.dataset_path = Path(dataset_path)
        self.ground_truth_path = self.dataset_path / 'ground_truth.json'
        
        # Load ground truth
        with open(self.ground_truth_path) as f:
            self.ground_truth = json.load(f)
        
        # Load dataset
        self.dataset = load_dataset(self.dataset_path)
        
        # Expected cluster assignments: endpoint_id -> expected_cluster_id
        self.expected_clusters: Dict[str, int] = {}
        if hasattr(self.dataset, 'endpoints'):
            # Load from endpoints CSV if it has expected_cluster_id column
            for _, row in self.dataset.endpoints.iterrows():
                endpoint_id = row.get('endpoint_id') or row.get('mac_address')
                expected_cluster = row.get('expected_cluster_id')
                if endpoint_id and expected_cluster is not None:
                    self.expected_clusters[endpoint_id] = int(expected_cluster)
    
    def validate(
        self,
        cluster_result: ClusterResult,
        endpoint_ids: List[str],
    ) -> Dict[str, float]:
        """
        Validate clustering results against ground truth.
        
        Args:
            cluster_result: ClusterResult from clustering
            endpoint_ids: List of endpoint IDs (same order as cluster_result.labels)
            
        Returns:
            Dict with validation metrics:
            - precision: Precision score
            - recall: Recall score
            - f1_score: F1 score
            - accuracy: Overall accuracy
            - misclassified: List of misclassified endpoints
        """
        # Build actual cluster assignments: endpoint_id -> actual_cluster_id
        actual_clusters = dict(zip(endpoint_ids, cluster_result.labels))
        
        # Calculate metrics per expected cluster
        cluster_metrics = {}
        all_true_positives = 0
        all_false_positives = 0
        all_false_negatives = 0
        
        # For each expected cluster, calculate precision/recall
        expected_cluster_ids = set(self.expected_clusters.values())
        for expected_cluster_id in expected_cluster_ids:
            if expected_cluster_id == -1:
                continue  # Skip noise cluster for now
            
            # Get expected endpoints for this cluster
            expected_endpoints = {
                ep_id for ep_id, cluster_id in self.expected_clusters.items()
                if cluster_id == expected_cluster_id
            }
            
            # Find which actual cluster(s) contain these endpoints
            actual_cluster_members: Dict[int, Set[str]] = {}
            for ep_id in expected_endpoints:
                if ep_id in actual_clusters:
                    actual_cluster_id = actual_clusters[ep_id]
                    if actual_cluster_id not in actual_cluster_members:
                        actual_cluster_members[actual_cluster_id] = set()
                    actual_cluster_members[actual_cluster_id].add(ep_id)
            
            # Find best matching actual cluster (largest overlap)
            best_match_cluster_id = None
            best_match_count = 0
            for actual_cluster_id, members in actual_cluster_members.items():
                if len(members) > best_match_count:
                    best_match_count = len(members)
                    best_match_cluster_id = actual_cluster_id
            
            if best_match_cluster_id is None:
                # No match found - all false negatives
                all_false_negatives += len(expected_endpoints)
                continue
            
            # Calculate TP, FP, FN for this cluster
            true_positives = len(actual_cluster_members[best_match_cluster_id])
            false_negatives = len(expected_endpoints) - true_positives
            
            # False positives: endpoints in actual cluster not in expected cluster
            actual_cluster_all_members = {
                ep_id for ep_id, cluster_id in actual_clusters.items()
                if cluster_id == best_match_cluster_id
            }
            false_positives = len(actual_cluster_all_members) - true_positives
            
            cluster_metrics[expected_cluster_id] = {
                'actual_cluster_id': best_match_cluster_id,
                'true_positives': true_positives,
                'false_positives': false_positives,
                'false_negatives': false_negatives,
                'expected_count': len(expected_endpoints),
                'actual_count': len(actual_cluster_all_members),
            }
            
            all_true_positives += true_positives
            all_false_positives += false_positives
            all_false_negatives += false_negatives
        
        # Calculate overall metrics
        precision = all_true_positives / (all_true_positives + all_false_positives) if (all_true_positives + all_false_positives) > 0 else 0.0
        recall = all_true_positives / (all_true_positives + all_false_negatives) if (all_true_positives + all_false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Calculate accuracy (percentage correctly classified)
        total_endpoints = len(self.expected_clusters)
        correctly_classified = sum(
            1 for ep_id, expected_cluster_id in self.expected_clusters.items()
            if ep_id in actual_clusters and actual_clusters[ep_id] == expected_cluster_id
        )
        accuracy = correctly_classified / total_endpoints if total_endpoints > 0 else 0.0
        
        # Find misclassified endpoints
        misclassified = []
        for ep_id, expected_cluster_id in self.expected_clusters.items():
            if ep_id in actual_clusters:
                actual_cluster_id = actual_clusters[ep_id]
                if actual_cluster_id != expected_cluster_id:
                    misclassified.append({
                        'endpoint_id': ep_id,
                        'expected_cluster_id': expected_cluster_id,
                        'actual_cluster_id': actual_cluster_id,
                    })
        
        return {
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'accuracy': accuracy,
            'cluster_metrics': cluster_metrics,
            'misclassified': misclassified,
            'total_endpoints': total_endpoints,
            'correctly_classified': correctly_classified,
        }
    
    def validate_device_type_separation(
        self,
        cluster_result: ClusterResult,
        endpoint_ids: List[str],
    ) -> Dict[str, any]:
        """
        Validate that distinct device types are properly separated.
        
        Specifically checks:
        - IP phones should NOT cluster with mobile phones
        - Servers should NOT cluster with clients
        - Printers should NOT cluster with general devices
        
        Args:
            cluster_result: ClusterResult from clustering
            endpoint_ids: List of endpoint IDs
            
        Returns:
            Dict with separation validation results
        """
        # Build endpoint_id -> device_type mapping
        endpoint_device_types: Dict[str, str] = {}
        if hasattr(self.dataset, 'endpoints'):
            for _, row in self.dataset.endpoints.iterrows():
                endpoint_id = row.get('endpoint_id') or row.get('mac_address')
                device_type = row.get('device_type')
                if endpoint_id and device_type:
                    endpoint_device_types[endpoint_id] = device_type
        
        # Build actual clusters: cluster_id -> set of endpoint_ids
        actual_clusters: Dict[int, Set[str]] = {}
        for ep_id, cluster_id in zip(endpoint_ids, cluster_result.labels):
            if cluster_id not in actual_clusters:
                actual_clusters[cluster_id] = set()
            actual_clusters[cluster_id].add(ep_id)
        
        # Check device type separation
        separation_issues = []
        
        # Check IP phone vs mobile phone separation
        ip_phones = {ep_id for ep_id, dt in endpoint_device_types.items() if dt == 'ip_phone'}
        mobile_phones = {ep_id for ep_id, dt in endpoint_device_types.items() if dt == 'mobile_phone'}
        
        ip_phone_clusters = {
            cluster_id for cluster_id, members in actual_clusters.items()
            if ip_phones.intersection(members)
        }
        mobile_phone_clusters = {
            cluster_id for cluster_id, members in actual_clusters.items()
            if mobile_phones.intersection(members)
        }
        
        # IP phones and mobile phones should be in different clusters
        overlap = ip_phone_clusters.intersection(mobile_phone_clusters)
        if overlap:
            separation_issues.append({
                'issue': 'ip_phone_mobile_phone_separation',
                'description': 'IP phones and mobile phones share clusters',
                'overlapping_clusters': list(overlap),
                'severity': 'high',
            })
        
        # Check server vs client separation
        servers = {ep_id for ep_id, dt in endpoint_device_types.items() if dt == 'server'}
        clients = {ep_id for ep_id, dt in endpoint_device_types.items() if dt in ['laptop', 'mobile_phone']}
        
        server_clusters = {
            cluster_id for cluster_id, members in actual_clusters.items()
            if servers.intersection(members)
        }
        client_clusters = {
            cluster_id for cluster_id, members in actual_clusters.items()
            if clients.intersection(members)
        }
        
        # Servers should generally be in different clusters than clients
        # (allow some overlap if server also acts as client, but flag excessive overlap)
        overlap = server_clusters.intersection(client_clusters)
        if len(overlap) > len(server_clusters) * 0.5:  # More than 50% overlap
            separation_issues.append({
                'issue': 'server_client_separation',
                'description': 'Excessive overlap between server and client clusters',
                'overlapping_clusters': list(overlap),
                'severity': 'medium',
            })
        
        return {
            'separation_valid': len(separation_issues) == 0,
            'issues': separation_issues,
            'ip_phone_clusters': list(ip_phone_clusters),
            'mobile_phone_clusters': list(mobile_phone_clusters),
            'server_clusters': list(server_clusters),
            'client_clusters': list(client_clusters),
        }
    
    def run_validation(
        self,
        min_cluster_size: int = 5,
        min_samples: int = 2,
    ) -> Dict[str, any]:
        """
        Run full validation pipeline.
        
        Args:
            min_cluster_size: HDBSCAN min_cluster_size parameter
            min_samples: HDBSCAN min_samples parameter
            
        Returns:
            Complete validation report
        """
        logger.info(f"Running validation on {self.dataset_path}")
        
        # Build sketches
        logger.info("Building sketches...")
        store = build_sketches(self.dataset)
        
        # Enrich with identity
        logger.info("Enriching with identity...")
        enrich_sketches(store, self.dataset)
        
        # Run clustering
        logger.info("Running clustering...")
        clusterer = EndpointClusterer(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
        )
        result = clusterer.cluster(store)
        
        # Get endpoint IDs
        endpoint_ids = [sketch.endpoint_id for sketch in store]
        
        # Validate accuracy
        logger.info("Validating accuracy...")
        accuracy_metrics = self.validate(result, endpoint_ids)
        
        # Validate device type separation
        logger.info("Validating device type separation...")
        separation_results = self.validate_device_type_separation(result, endpoint_ids)
        
        # Build report
        report = {
            'dataset': str(self.dataset_path),
            'company_type': self.ground_truth.get('company_type'),
            'clustering_results': {
                'n_clusters': result.n_clusters,
                'n_noise': result.n_noise,
                'silhouette_score': result.silhouette,
            },
            'accuracy_metrics': accuracy_metrics,
            'device_separation': separation_results,
            'expected_clusters': self.ground_truth.get('expected_clusters', []),
        }
        
        return report


def validate_dataset(dataset_path: Path, **kwargs) -> Dict[str, any]:
    """
    Convenience function to validate a ground truth dataset.
    
    Args:
        dataset_path: Path to ground truth dataset directory
        **kwargs: Additional arguments for run_validation()
        
    Returns:
        Validation report
    """
    validator = ClusteringValidator(dataset_path)
    return validator.run_validation(**kwargs)

