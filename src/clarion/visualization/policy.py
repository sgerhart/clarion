"""
Policy Visualization

Visualize policy matrix, SGACL coverage, and policy relationships.
"""

from __future__ import annotations

from typing import List, Dict, Optional, Tuple
import numpy as np
import logging

try:
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False

from clarion.policy.matrix import PolicyMatrix
from clarion.policy.sgacl import SGACLPolicy

logger = logging.getLogger(__name__)


def plot_policy_matrix_heatmap(
    matrix: PolicyMatrix,
    title: str = "SGT × SGT Policy Matrix",
    save_path: Optional[str] = None,
) -> None:
    """
    Plot policy matrix as a heatmap.
    
    Args:
        matrix: PolicyMatrix object
        title: Plot title
        save_path: Optional path to save figure
    """
    if not HAS_PLOTTING:
        logger.warning("matplotlib not available, skipping plot")
        return
    
    src_sgts, dst_sgts, flow_matrix = matrix.to_heatmap_data()
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    im = ax.imshow(flow_matrix, cmap='YlOrRd', aspect='auto')
    
    # Set ticks
    ax.set_xticks(range(len(dst_sgts)))
    ax.set_yticks(range(len(src_sgts)))
    ax.set_xticklabels([f"SGT {s}" for s in dst_sgts], rotation=45, ha='right')
    ax.set_yticklabels([f"SGT {s}" for s in src_sgts])
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Flow Count', rotation=270, labelpad=20)
    
    # Add text annotations for non-zero cells
    for i in range(len(src_sgts)):
        for j in range(len(dst_sgts)):
            if flow_matrix[i][j] > 0:
                ax.text(
                    j, i,
                    f'{flow_matrix[i][j]}',
                    ha='center',
                    va='center',
                    color='black' if flow_matrix[i][j] < np.max(flow_matrix) * 0.5 else 'white',
                    fontsize=8,
                )
    
    ax.set_xlabel("Destination SGT")
    ax.set_ylabel("Source SGT")
    ax.set_title(title)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved policy matrix heatmap to {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_sgacl_coverage(
    policies: List[SGACLPolicy],
    title: str = "SGACL Coverage",
    save_path: Optional[str] = None,
) -> None:
    """
    Plot SGACL policy coverage as a bar chart.
    
    Args:
        policies: List of SGACL policies
        title: Plot title
        save_path: Optional path to save figure
    """
    if not HAS_PLOTTING:
        logger.warning("matplotlib not available, skipping plot")
        return
    
    policy_names = [p.name for p in policies]
    coverage_ratios = [p.coverage_ratio() for p in policies]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    bars = ax.barh(policy_names, coverage_ratios, color='steelblue', alpha=0.7)
    
    # Add value labels
    for i, (bar, ratio) in enumerate(zip(bars, coverage_ratios)):
        ax.text(
            ratio,
            bar.get_y() + bar.get_height() / 2,
            f'{ratio*100:.1f}%',
            ha='left' if ratio < 0.5 else 'right',
            va='center',
        )
    
    ax.set_xlabel("Coverage Ratio")
    ax.set_ylabel("Policy")
    ax.set_title(title)
    ax.set_xlim(0, 1)
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved coverage plot to {save_path}")
    else:
        plt.show()
    
    plt.close()


def create_policy_plotly(
    matrix: PolicyMatrix,
) -> go.Figure:
    """
    Create interactive Plotly heatmap for policy matrix.
    
    Args:
        matrix: PolicyMatrix object
        
    Returns:
        Plotly figure object
    """
    if not HAS_PLOTTING:
        raise ImportError("plotly not available")
    
    src_sgts, dst_sgts, flow_matrix = matrix.to_heatmap_data()
    
    # Create hover text
    hover_text = []
    for i, src in enumerate(src_sgts):
        row = []
        for j, dst in enumerate(dst_sgts):
            cell = matrix.get_cell(src, dst)
            if cell:
                text = (
                    f"Source: SGT {src}<br>"
                    f"Destination: SGT {dst}<br>"
                    f"Flows: {cell.total_flows:,}<br>"
                    f"Bytes: {cell.total_bytes:,}<br>"
                    f"Ports: {len(cell.observed_ports)}"
                )
            else:
                text = f"Source: SGT {src}<br>Destination: SGT {dst}<br>No traffic"
            row.append(text)
        hover_text.append(row)
    
    fig = go.Figure(data=go.Heatmap(
        z=flow_matrix,
        x=[f"SGT {s}" for s in dst_sgts],
        y=[f"SGT {s}" for s in src_sgts],
        colorscale='YlOrRd',
        text=hover_text,
        hovertemplate='%{text}<extra></extra>',
        colorbar=dict(title="Flow Count"),
    ))
    
    fig.update_layout(
        title="SGT × SGT Policy Matrix",
        xaxis_title="Destination SGT",
        yaxis_title="Source SGT",
        width=1000,
        height=800,
    )
    
    return fig


