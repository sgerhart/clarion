"""
Cluster Visualization

Visualize endpoint clusters using dimensionality reduction.
"""

from __future__ import annotations

from typing import List, Tuple, Optional, Dict
import numpy as np
import logging

try:
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False

from clarion.clustering.clusterer import ClusterResult
from clarion.clustering.features import FeatureExtractor

logger = logging.getLogger(__name__)


def plot_clusters_2d(
    features: np.ndarray,
    labels: np.ndarray,
    method: str = "pca",
    title: str = "Endpoint Clusters",
    save_path: Optional[str] = None,
) -> None:
    """
    Plot clusters in 2D using dimensionality reduction.
    
    Args:
        features: Feature matrix (n_samples, n_features)
        labels: Cluster labels (n_samples,)
        method: Reduction method ("pca", "tsne", "umap")
        title: Plot title
        save_path: Optional path to save figure
    """
    if not HAS_PLOTTING:
        logger.warning("matplotlib not available, skipping plot")
        return
    
    try:
        from sklearn.decomposition import PCA
        from sklearn.manifold import TSNE
        
        if method == "pca":
            reducer = PCA(n_components=2, random_state=42)
            coords = reducer.fit_transform(features)
        elif method == "tsne":
            reducer = TSNE(n_components=2, random_state=42, perplexity=30)
            coords = reducer.fit_transform(features)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Create plot
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Plot each cluster
        unique_labels = np.unique(labels)
        colors = plt.cm.tab20(np.linspace(0, 1, len(unique_labels)))
        
        for i, label in enumerate(unique_labels):
            mask = labels == label
            if label == -1:
                # Noise points
                ax.scatter(
                    coords[mask, 0],
                    coords[mask, 1],
                    c='gray',
                    alpha=0.3,
                    s=20,
                    label='Noise' if i == 0 else '',
                )
            else:
                ax.scatter(
                    coords[mask, 0],
                    coords[mask, 1],
                    c=[colors[i]],
                    alpha=0.6,
                    s=50,
                    label=f'Cluster {label}',
                )
        
        ax.set_xlabel(f"{method.upper()} Component 1")
        ax.set_ylabel(f"{method.upper()} Component 2")
        ax.set_title(title)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved cluster plot to {save_path}")
        else:
            plt.show()
        
        plt.close()
        
    except ImportError:
        logger.error("scikit-learn required for visualization")
    except Exception as e:
        logger.error(f"Failed to create cluster plot: {e}")


def plot_cluster_distribution(
    cluster_sizes: Dict[int, int],
    title: str = "Cluster Size Distribution",
    save_path: Optional[str] = None,
) -> None:
    """
    Plot cluster size distribution as a bar chart.
    
    Args:
        cluster_sizes: Dict mapping cluster_id to size
        title: Plot title
        save_path: Optional path to save figure
    """
    if not HAS_PLOTTING:
        logger.warning("matplotlib not available, skipping plot")
        return
    
    # Sort by cluster ID
    sorted_clusters = sorted(cluster_sizes.items())
    cluster_ids = [str(cid) for cid, _ in sorted_clusters]
    sizes = [size for _, size in sorted_clusters]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars = ax.bar(cluster_ids, sizes, color='steelblue', alpha=0.7)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.,
            height,
            f'{int(height)}',
            ha='center',
            va='bottom',
        )
    
    ax.set_xlabel("Cluster ID")
    ax.set_ylabel("Number of Endpoints")
    ax.set_title(title)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved distribution plot to {save_path}")
    else:
        plt.show()
    
    plt.close()


def create_cluster_plotly(
    features: np.ndarray,
    labels: np.ndarray,
    endpoint_ids: List[str],
    method: str = "pca",
) -> go.Figure:
    """
    Create interactive Plotly figure for clusters.
    
    Args:
        features: Feature matrix
        labels: Cluster labels
        endpoint_ids: Endpoint IDs for hover text
        method: Reduction method
        
    Returns:
        Plotly figure object
    """
    if not HAS_PLOTTING:
        raise ImportError("plotly not available")
    
    try:
        from sklearn.decomposition import PCA
        from sklearn.manifold import TSNE
        
        if method == "pca":
            reducer = PCA(n_components=2, random_state=42)
            coords = reducer.fit_transform(features)
        elif method == "tsne":
            reducer = TSNE(n_components=2, random_state=42, perplexity=30)
            coords = reducer.fit_transform(features)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Create figure
        fig = go.Figure()
        
        # Plot each cluster
        unique_labels = np.unique(labels)
        
        for label in unique_labels:
            mask = labels == label
            
            if label == -1:
                # Noise points
                fig.add_trace(go.Scatter(
                    x=coords[mask, 0],
                    y=coords[mask, 1],
                    mode='markers',
                    name='Noise',
                    marker=dict(
                        color='gray',
                        size=5,
                        opacity=0.5,
                    ),
                    text=[endpoint_ids[i] for i in np.where(mask)[0]],
                    hovertemplate='%{text}<br>%{x:.2f}, %{y:.2f}<extra></extra>',
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=coords[mask, 0],
                    y=coords[mask, 1],
                    mode='markers',
                    name=f'Cluster {label}',
                    marker=dict(
                        size=8,
                        opacity=0.7,
                    ),
                    text=[endpoint_ids[i] for i in np.where(mask)[0]],
                    hovertemplate='%{text}<br>Cluster: %{fullData.name}<br>%{x:.2f}, %{y:.2f}<extra></extra>',
                ))
        
        fig.update_layout(
            title=f"Endpoint Clusters ({method.upper()})",
            xaxis_title=f"{method.upper()} Component 1",
            yaxis_title=f"{method.upper()} Component 2",
            hovermode='closest',
            width=1000,
            height=800,
        )
        
        return fig
        
    except ImportError:
        raise ImportError("scikit-learn required for visualization")


