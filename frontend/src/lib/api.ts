import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface Sketch {
  endpoint_id: string
  switch_id: string
  flow_count: number
  unique_peers: number
  unique_ports: number
  bytes_in: number
  bytes_out: number
  last_seen: number
}

export interface NetFlowRecord {
  src_ip: string
  dst_ip: string
  src_port: number
  dst_port: number
  protocol: number
  bytes: number
  packets: number
  flow_start: number
  flow_end: number
  switch_id?: string
  src_mac?: string
  dst_mac?: string
  src_sgt?: number
  dst_sgt?: number
  vlan_id?: number
}

export interface Cluster {
  cluster_id: number
  cluster_label?: string
  sgt_value?: number
  sgt_name?: string
  endpoint_count: number
}

export interface ClusterMember {
  endpoint_id: string
  switch_id: string
  flow_count: number
  user_name?: string
  device_name?: string
  ad_groups?: string
}

export interface SGTMatrixCell {
  src_sgt: number
  src_sgt_name: string
  dst_sgt: number
  dst_sgt_name: string
  total_flows: number
  total_bytes: number
  top_ports: string
}

export const apiClient = {
  // Health
  health: () => api.get('/health'),

  // Sketches
  getSketches: (switchId?: string, limit = 1000) =>
    api.get('/edge/sketches', { params: { switch_id: switchId, limit } }),
  getSketchStats: () => api.get('/edge/sketches/stats'),

  // NetFlow
  getNetFlow: (limit = 1000, since?: number) =>
    api.get('/netflow/netflow', { params: { limit, since } }),

  // Clusters
  getClusters: () => api.get('/clustering/clusters'),
  getClusterMembers: (clusterId: number) =>
    api.get(`/clustering/clusters/${clusterId}/members`),

  // SGT Matrix
  buildMatrix: () => api.post('/clustering/matrix/build'),
  getMatrix: () => api.get('/clustering/matrix'),

  // Policies
  generatePolicies: () => api.post('/policy/generate'),
  getPolicies: () => api.get('/policy/policies'),

  // Devices
  getDevices: (params?: {
    switch_id?: string
    cluster_id?: number
    device_type?: string
    search?: string
    limit?: number
    offset?: number
  }) => api.get('/devices', { params }),
  getDevice: (endpointId: string) => api.get(`/devices/${endpointId}`),
  getDeviceStats: () => api.get('/devices/stats'),
  getDeviceFlows: (endpointId: string, params?: { limit?: number; offset?: number }) =>
    api.get(`/devices/${endpointId}/flows`, { params }),
  updateDevice: (endpointId: string, data: { cluster_id?: number; sgt_value?: number }) =>
    api.put(`/devices/${endpointId}`, data),

  // Groups
  getGroups: (params?: {
    search?: string
    has_sgt?: boolean
    limit?: number
    offset?: number
  }) => api.get('/groups', { params }),
  getGroup: (clusterId: number) => api.get(`/groups/${clusterId}`),
  updateGroup: (clusterId: number, data: {
    cluster_label?: string
    sgt_value?: number
    sgt_name?: string
  }) => api.put(`/groups/${clusterId}`, data),
  getGroupStats: () => api.get('/groups/stats'),

  // Visualization
  getFlowGraphData: (limit?: number, includeLocations?: boolean) =>
    api.get('/viz/flow-graph', { params: { limit, include_locations: includeLocations ?? true } }),

  // Topology
  getLocations: (params?: { parent_id?: string; type?: string; search?: string }) =>
    api.get('/topology/locations', { params }),
  getLocation: (locationId: string) => api.get(`/topology/locations/${locationId}`),
  createLocation: (data: any) => api.post('/topology/locations', data),
  updateLocation: (locationId: string, data: any) => api.put(`/topology/locations/${locationId}`, data),
  deleteLocation: (locationId: string) => api.delete(`/topology/locations/${locationId}`),
  
  getAddressSpaces: () => api.get('/topology/address-spaces'),
  createAddressSpace: (data: any) => api.post('/topology/address-spaces', data),
  updateAddressSpace: (spaceId: string, data: any) => api.put(`/topology/address-spaces/${spaceId}`, data),
  deleteAddressSpace: (spaceId: string) => api.delete(`/topology/address-spaces/${spaceId}`),
  
  getSubnets: (params?: { location_id?: string; address_space_id?: string }) =>
    api.get('/topology/subnets', { params }),
  createSubnet: (data: any) => api.post('/topology/subnets', data),
  updateSubnet: (subnetId: string, data: any) => api.put(`/topology/subnets/${subnetId}`, data),
  deleteSubnet: (subnetId: string) => api.delete(`/topology/subnets/${subnetId}`),
  
  getSwitches: (params?: { location_id?: string; search?: string }) =>
    api.get('/topology/switches', { params }),
  createSwitch: (data: any) => api.post('/topology/switches', data),
  updateSwitch: (switchId: string, data: any) => api.put(`/topology/switches/${switchId}`, data),
  deleteSwitch: (switchId: string) => api.delete(`/topology/switches/${switchId}`),
  
  getTopologyHierarchy: () => api.get('/topology/hierarchy'),
  resolveIpToSubnet: (ip: string) => api.get('/topology/resolve-ip', { params: { ip } }),

  // Collectors
  getCollectors: (params?: { type?: string; enabled?: boolean }) =>
    api.get('/collectors', { params }),
  getCollector: (collectorId: string) => api.get(`/collectors/${collectorId}`),
  createCollector: (data: any) => api.post('/collectors', data),
  updateCollector: (collectorId: string, data: any) =>
    api.put(`/collectors/${collectorId}`, data),
  deleteCollector: (collectorId: string) => api.delete(`/collectors/${collectorId}`),
  getCollectorMetrics: (collectorId: string) =>
    api.get(`/collectors/${collectorId}/metrics`),
  getCollectorHealth: (collectorId: string) =>
    api.get(`/collectors/${collectorId}/health`),

  // Policy Recommendations
  generateClusterRecommendation: (clusterId: number, minPercentage?: number) =>
    api.post(`/policy/recommendations/cluster/${clusterId}`, null, { params: { min_percentage: minPercentage } }),
  generateDeviceRecommendation: (endpointId: string, newClusterId: number, oldClusterId?: number) =>
    api.post(`/policy/recommendations/device/${endpointId}`, null, { params: { new_cluster_id: newClusterId, old_cluster_id: oldClusterId } }),
  getPolicyRecommendations: (params?: {
    status?: string
    cluster_id?: number
    endpoint_id?: string
    limit?: number
    offset?: number
  }) => api.get('/policy/recommendations', { params }),
  getPolicyRecommendation: (recommendationId: number) =>
    api.get(`/policy/recommendations/${recommendationId}`),
  updatePolicyRecommendationStatus: (recommendationId: number, status: string) =>
    api.put(`/policy/recommendations/${recommendationId}/status`, { status }),
  deletePolicyRecommendation: (recommendationId: number) =>
    api.delete(`/policy/recommendations/${recommendationId}`),

  // ISE Policy Export
  exportISEConfig: (recommendationId: number, format: 'json' | 'xml' | 'cli' | 'all' = 'json') =>
    api.get(`/policy/recommendations/${recommendationId}/ise-config`, {
      params: { format },
      responseType: format === 'json' || format === 'all' ? 'json' : 'blob',
    }),
  getDeploymentGuide: (recommendationId: number) =>
    api.get(`/policy/recommendations/${recommendationId}/ise-config/deployment-guide`, {
      responseType: 'blob',
    }),
}

export default api
