"""
Integration tests for clustering accuracy validation.

Tests the categorization engine against ground truth datasets
and validates clustering accuracy metrics.
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from clarion.ingest.loader import load_dataset
from clarion.ingest.sketch_builder import build_sketches
from clarion.identity import enrich_sketches
from clarion.clustering.clusterer import EndpointClusterer
from clarion.clustering.validator import ClusteringValidator


@pytest.fixture
def dataset_paths():
    """Return paths to all ground truth datasets."""
    base = Path(__file__).parent.parent.parent / "tests" / "data" / "ground_truth"
    return {
        "enterprise": base / "enterprise",
        "healthcare": base / "healthcare",
        "manufacturing": base / "manufacturing",
        "education": base / "education",
        "retail": base / "retail",
    }


@pytest.mark.parametrize("dataset_name", ["enterprise", "healthcare", "manufacturing", "education", "retail"])
def test_dataset_loads(dataset_paths, dataset_name):
    """Test that each ground truth dataset loads successfully."""
    dataset_path = dataset_paths[dataset_name]
    
    if not dataset_path.exists():
        pytest.skip(f"Dataset {dataset_name} not found at {dataset_path}")
    
    dataset = load_dataset(dataset_path)
    
    assert len(dataset.flows) > 0, f"{dataset_name}: No flows loaded"
    assert len(dataset.endpoints) > 0, f"{dataset_name}: No endpoints loaded"


@pytest.mark.parametrize("dataset_name", ["enterprise", "healthcare", "manufacturing", "education", "retail"])
def test_clustering_accuracy(dataset_paths, dataset_name):
    """
    Test clustering accuracy on ground truth datasets.
    
    Validates that the categorization engine achieves acceptable accuracy
    on known device groups.
    """
    dataset_path = dataset_paths[dataset_name]
    
    if not dataset_path.exists():
        pytest.skip(f"Dataset {dataset_name} not found at {dataset_path}")
    
    # Load dataset
    dataset = load_dataset(dataset_path)
    
    # Build sketches
    store = build_sketches(dataset)
    
    # Enrich with identity
    enrich_sketches(store, dataset)
    
    # Run clustering
    clusterer = EndpointClusterer(
        min_cluster_size=5,
        min_samples=2,
    )
    result = clusterer.cluster(store)
    
    # Get endpoint IDs
    endpoint_ids = [sketch.endpoint_id for sketch in store]
    
    # Validate accuracy
    validator = ClusteringValidator(dataset_path)
    metrics = validator.validate(result, endpoint_ids)
    
    # Check accuracy thresholds
    assert metrics['accuracy'] >= 0.70, f"{dataset_name}: Accuracy {metrics['accuracy']:.2%} below 70% threshold"
    assert metrics['precision'] >= 0.65, f"{dataset_name}: Precision {metrics['precision']:.2%} below 65% threshold"
    assert metrics['recall'] >= 0.60, f"{dataset_name}: Recall {metrics['recall']:.2%} below 60% threshold"
    assert metrics['f1_score'] >= 0.60, f"{dataset_name}: F1-score {metrics['f1_score']:.2%} below 60% threshold"
    
    print(f"\n{dataset_name} Clustering Results:")
    print(f"  Accuracy: {metrics['accuracy']:.2%}")
    print(f"  Precision: {metrics['precision']:.2%}")
    print(f"  Recall: {metrics['recall']:.2%}")
    print(f"  F1-Score: {metrics['f1_score']:.2%}")
    print(f"  Clusters Found: {result.n_clusters}")
    print(f"  Noise Points: {result.n_noise}")


@pytest.mark.parametrize("dataset_name", ["enterprise"])
def test_device_type_separation(dataset_paths, dataset_name):
    """
    Test that distinct device types are properly separated.
    
    Specifically validates IP phone vs mobile phone separation.
    """
    dataset_path = dataset_paths[dataset_name]
    
    if not dataset_path.exists():
        pytest.skip(f"Dataset {dataset_name} not found at {dataset_path}")
    
    # Load dataset
    dataset = load_dataset(dataset_path)
    
    # Build sketches
    store = build_sketches(dataset)
    
    # Enrich with identity
    enrich_sketches(store, dataset)
    
    # Run clustering
    clusterer = EndpointClusterer(
        min_cluster_size=5,
        min_samples=2,
    )
    result = clusterer.cluster(store)
    
    # Get endpoint IDs
    endpoint_ids = [sketch.endpoint_id for sketch in store]
    
    # Validate device type separation
    validator = ClusteringValidator(dataset_path)
    separation_results = validator.validate_device_type_separation(result, endpoint_ids)
    
    # IP phones and mobile phones should be in different clusters
    assert separation_results['separation_valid'], \
        f"{dataset_name}: Device type separation failed: {separation_results['issues']}"
    
    print(f"\n{dataset_name} Device Separation:")
    print(f"  Valid: {separation_results['separation_valid']}")
    print(f"  IP Phone Clusters: {separation_results['ip_phone_clusters']}")
    print(f"  Mobile Phone Clusters: {separation_results['mobile_phone_clusters']}")


def test_validation_framework():
    """Test that the validation framework works correctly."""
    dataset_path = Path(__file__).parent.parent.parent / "tests" / "data" / "ground_truth" / "enterprise"
    
    if not dataset_path.exists():
        pytest.skip("Enterprise dataset not found")
    
    validator = ClusteringValidator(dataset_path)
    
    # Load dataset and run clustering
    dataset = load_dataset(dataset_path)
    store = build_sketches(dataset)
    enrich_sketches(store, dataset)
    
    clusterer = EndpointClusterer(min_cluster_size=5, min_samples=2)
    result = clusterer.cluster(store)
    endpoint_ids = [sketch.endpoint_id for sketch in store]
    
    # Run validation
    report = validator.run_validation(min_cluster_size=5, min_samples=2)
    
    assert 'accuracy_metrics' in report
    assert 'device_separation' in report
    assert 'expected_clusters' in report
    
    print(f"\nValidation Report:")
    print(f"  Company Type: {report['company_type']}")
    print(f"  Clusters Found: {report['clustering_results']['n_clusters']}")
    print(f"  Accuracy: {report['accuracy_metrics']['accuracy']:.2%}")

