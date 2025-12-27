"""
Visualization Endpoints

Endpoints for generating visualization data (clusters, policy matrix, flow graphs, etc.)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging
import numpy as np

try:
    from sklearn.manifold import TSNE
    from sklearn.decomposition import PCA
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from clarion.storage import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


class ClusterVisualizationRequest(BaseModel):
    """Request for cluster visualization."""
    method: str = "pca"  # "pca", "tsne", "umap"
    n_components: int = 2
    perplexity: Optional[float] = None  # For t-SNE


class FlowGraphNode(BaseModel):
    """Flow graph node with enriched data."""
    id: str  # IP address or MAC
    label: str
    node_type: str  # "device", "location"
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    user_name: Optional[str] = None
    cluster_id: Optional[int] = None
    cluster_label: Optional[str] = None
    sgt_value: Optional[int] = None
    location_path: Optional[str] = None  # e.g., "Campus: Main > Building: 2 > IDF: 1"
    switch_id: Optional[str] = None
    flow_count: int = 0
    bytes_in: int = 0
    bytes_out: int = 0


class FlowGraphLink(BaseModel):
    """Flow graph link/edge."""
    source: str
    target: str
    flow_count: int
    total_bytes: int
    protocols: List[int]
    top_ports: List[str]


@router.get("/flow-graph")
async def get_flow_graph_data(
    limit: int = Query(500, ge=1, le=5000, description="Maximum number of flows to process"),
    include_locations: bool = Query(True, description="Include location hierarchy"),
):
    """
    Get flow graph data with enriched node information including locations.
    
    Returns nodes and links for network graph visualization with:
    - Device information (IP, MAC, name, type, user)
    - Cluster/SGT assignment
    - Location hierarchy
    - Flow statistics
    """
    db = get_database()
    conn = db._get_connection()
    
    try:
        # Get recent flows
        flows = db.get_recent_netflow(limit=limit)
        
        if not flows:
            return {
                "nodes": [],
                "links": [],
            }
        
        # Build nodes map with enriched data
        nodes_map: Dict[str, Dict[str, Any]] = {}
        links: List[Dict[str, Any]] = []
        
        # Get all unique IPs from flows
        all_ips = set()
        ip_to_flows: Dict[str, List[Dict]] = {}
        
        for flow in flows:
            src_ip = str(flow.get('src_ip', ''))
            dst_ip = str(flow.get('dst_ip', ''))
            
            if src_ip:
                all_ips.add(src_ip)
                if src_ip not in ip_to_flows:
                    ip_to_flows[src_ip] = []
                ip_to_flows[src_ip].append(flow)
            
            if dst_ip:
                all_ips.add(dst_ip)
                if dst_ip not in ip_to_flows:
                    ip_to_flows[dst_ip] = []
                ip_to_flows[dst_ip].append(flow)
        
        # Enrich nodes with identity, cluster, and location data
        for ip in all_ips:
            # Get identity data
            identity = db.get_identity(ip)
            mac = identity.get('mac_address') if identity else None
            
            # Get device info from sketches (if MAC available)
            device_info = None
            if mac:
                sketch = db.get_sketch(mac)
                if sketch:
                    device_info = {
                        'flow_count': sketch.get('flow_count', 0),
                        'bytes_in': sketch.get('bytes_in', 0),
                        'bytes_out': sketch.get('bytes_out', 0),
                        'switch_id': sketch.get('switch_id'),
                    }
            
            # Get cluster assignment (from MAC)
            cluster_id = None
            cluster_label = None
            sgt_value = None
            if mac:
                cluster_cursor = conn.execute("""
                    SELECT ca.cluster_id, c.cluster_label, c.sgt_value
                    FROM cluster_assignments ca
                    LEFT JOIN clusters c ON ca.cluster_id = c.cluster_id
                    WHERE ca.endpoint_id = ?
                """, (mac,))
                cluster_row = cluster_cursor.fetchone()
                if cluster_row:
                    cluster_id = cluster_row[0]
                    cluster_label = cluster_row[1]
                    sgt_value = cluster_row[2]
            
            # Build location path (if topology data available)
            location_path = None
            if include_locations:
                # Try to get location from subnet
                location_cursor = conn.execute("""
                    SELECT l.name, l.type, l.parent_id
                    FROM subnets s
                    LEFT JOIN locations l ON s.location_id = l.location_id
                    WHERE ? LIKE REPLACE(s.cidr, '%', '') || '%'
                    LIMIT 1
                """, (ip,))
                # This is simplified - real implementation would need proper IP subnet matching
                # For now, we'll leave location_path as None
            
            # Calculate flow statistics for this IP
            ip_flows = ip_to_flows.get(ip, [])
            bytes_in = sum(f.get('bytes', 0) for f in ip_flows if f.get('dst_ip') == ip)
            bytes_out = sum(f.get('bytes', 0) for f in ip_flows if f.get('src_ip') == ip)
            
            # Determine device type
            device_type = None
            device_name = identity.get('device_name') if identity else None
            if device_name:
                device_name_lower = device_name.lower()
                if 'server' in device_name_lower or 'svr' in device_name_lower:
                    device_type = 'server'
                elif 'laptop' in device_name_lower:
                    device_type = 'laptop'
                elif 'printer' in device_name_lower:
                    device_type = 'printer'
                elif 'iot' in device_name_lower or 'camera' in device_name_lower:
                    device_type = 'iot'
                elif 'phone' in device_name_lower or 'mobile' in device_name_lower:
                    device_type = 'mobile'
            
            # Create node
            nodes_map[ip] = {
                'id': ip,
                'label': device_name or ip.split('.')[-1] if '.' in ip else ip,
                'node_type': 'device',
                'ip_address': ip,
                'mac_address': mac,
                'device_name': device_name,
                'device_type': device_type,
                'user_name': identity.get('user_name') if identity else None,
                'cluster_id': cluster_id,
                'cluster_label': cluster_label,
                'sgt_value': sgt_value,
                'location_path': location_path,
                'switch_id': device_info.get('switch_id') if device_info else None,
                'flow_count': len(ip_flows),
                'bytes_in': bytes_in,
                'bytes_out': bytes_out,
            }
        
        # Build links
        link_map: Dict[tuple, Dict[str, Any]] = {}
        
        for flow in flows:
            src_ip = str(flow.get('src_ip', ''))
            dst_ip = str(flow.get('dst_ip', ''))
            
            if not src_ip or not dst_ip:
                continue
            
            key = (src_ip, dst_ip)
            if key not in link_map:
                link_map[key] = {
                    'source': src_ip,
                    'target': dst_ip,
                    'flow_count': 0,
                    'total_bytes': 0,
                    'protocols': set(),
                    'ports': set(),
                }
            
            link_map[key]['flow_count'] += 1
            link_map[key]['total_bytes'] += flow.get('bytes', 0)
            link_map[key]['protocols'].add(flow.get('protocol', 0))
            if flow.get('dst_port'):
                link_map[key]['ports'].add(str(flow.get('dst_port')))
        
        # Convert link_map to list
        for key, link_data in link_map.items():
            links.append({
                'source': link_data['source'],
                'target': link_data['target'],
                'flow_count': link_data['flow_count'],
                'total_bytes': link_data['total_bytes'],
                'protocols': list(link_data['protocols']),
                'top_ports': sorted(list(link_data['ports']))[:5],  # Top 5 ports
            })
        
        nodes = list(nodes_map.values())
        
        return {
            "nodes": nodes,
            "links": links,
        }
        
    except Exception as e:
        logger.error(f"Error generating flow graph data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clusters")
async def visualize_clusters(request: ClusterVisualizationRequest):
    """
    Generate 2D projection of clusters for visualization.
    
    Returns coordinates for plotting clusters in 2D space.
    """
    if not HAS_SKLEARN:
        raise HTTPException(
            status_code=503,
            detail="scikit-learn not available for visualization"
        )
    
    # TODO: Load actual feature matrix from clustering results
    # For now, return example structure
    
    return {
        "method": request.method,
        "coordinates": [],
        "labels": [],
        "clusters": {},
        "message": "Visualization endpoint - requires clustering results",
    }


@router.get("/matrix/heatmap")
async def policy_matrix_heatmap():
    """
    Get policy matrix data for heatmap visualization.
    
    Returns SGT × SGT matrix with flow counts.
    """
    # TODO: Return actual policy matrix
    return {
        "src_sgts": [],
        "dst_sgts": [],
        "matrix": [],
        "message": "Policy matrix heatmap - requires policy generation",
    }


@router.get("/clusters/distribution")
async def cluster_distribution():
    """Get cluster size distribution for bar chart."""
    # TODO: Return actual cluster distribution
    return {
        "clusters": {},
        "total_endpoints": 0,
        "noise_count": 0,
    }


@router.get("/endpoints/timeline")
async def endpoint_timeline(
    endpoint_id: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
):
    """Get timeline data for endpoint activity."""
    # TODO: Return actual timeline data
    return {
        "endpoint_id": endpoint_id,
        "timeline": [],
        "hours": hours,
    }
