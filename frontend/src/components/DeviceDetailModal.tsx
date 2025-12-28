import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { X, Save, Edit2, User, Tag, Network, Activity } from 'lucide-react'
import { useState, useEffect } from 'react'

interface Device {
  endpoint_id: string
  switch_id?: string
  flow_count: number
  unique_peers: number
  unique_ports: number
  bytes_in: number
  bytes_out: number
  first_seen?: number
  last_seen?: number
  ip_address?: string
  user_name?: string
  device_name?: string
  device_type?: string
  ad_groups: string[]
  ise_profile?: string
  cluster_id?: number
  cluster_label?: string
  sgt_value?: number
  sgt_name?: string
}

interface DeviceDetailModalProps {
  deviceId: string
  onClose: () => void
}

export default function DeviceDetailModal({ deviceId, onClose }: DeviceDetailModalProps) {
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [editedClusterId, setEditedClusterId] = useState<number | null>(null)
  const [editedSgtValue, setEditedSgtValue] = useState<number | null>(null)

  // Get device details
  const { data: device, isLoading } = useQuery({
    queryKey: ['device', deviceId],
    queryFn: async () => {
      const response = await apiClient.getDevice(deviceId)
      return response.data as Device
    },
  })

  // Get clusters for dropdown
  const { data: clustersData } = useQuery({
    queryKey: ['clusters'],
    queryFn: async () => {
      const response = await apiClient.getClusters()
      return response.data
    },
  })

  // Get device flows
  const { data: flowsData, isLoading: flowsLoading } = useQuery({
    queryKey: ['deviceFlows', deviceId],
    queryFn: async () => {
      const response = await apiClient.getDeviceFlows(deviceId, { limit: 50 })
      return response.data
    },
    enabled: !!device,
  })

  // Update device mutation
  const updateMutation = useMutation({
    mutationFn: async (data: { cluster_id?: number; sgt_value?: number }) => {
      return apiClient.updateDevice(deviceId, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['device', deviceId] })
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      queryClient.invalidateQueries({ queryKey: ['clusters'] })
      setIsEditing(false)
    },
  })

  // Initialize edit values when device loads
  useEffect(() => {
    if (device) {
      setEditedClusterId(device.cluster_id ?? null)
      setEditedSgtValue(device.sgt_value ?? null)
    }
  }, [device])

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatTimestamp = (ts?: number) => {
    if (!ts) return 'Never'
    return new Date(ts * 1000).toLocaleString()
  }

  const handleSave = () => {
    updateMutation.mutate({
      cluster_id: editedClusterId ?? undefined,
      sgt_value: editedSgtValue ?? undefined,
    })
  }

  const handleCancel = () => {
    if (device) {
      setEditedClusterId(device.cluster_id ?? null)
      setEditedSgtValue(device.sgt_value ?? null)
    }
    setIsEditing(false)
  }

  if (isLoading || !device) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8">
          <div className="text-center">Loading device details...</div>
        </div>
      </div>
    )
  }

  const clusters = clustersData || []

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-4">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 font-mono">{device.endpoint_id}</h2>
              {device.device_name && (
                <p className="text-gray-600 mt-1">{device.device_name}</p>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {!isEditing && (
              <button
                onClick={() => setIsEditing(true)}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center space-x-2"
              >
                <Edit2 className="h-4 w-4" />
                <span>Edit</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column: Device Information */}
            <div className="space-y-6">
              {/* Identity Information */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <User className="h-5 w-5 mr-2" />
                  Identity Information
                </h3>
                <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                  {device.ip_address && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">IP Address</label>
                      <p className="text-gray-900 font-mono">{device.ip_address}</p>
                    </div>
                  )}
                  {device.user_name && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">User</label>
                      <p className="text-gray-900">{device.user_name}</p>
                    </div>
                  )}
                  {device.device_name && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Device Name</label>
                      <p className="text-gray-900">{device.device_name}</p>
                    </div>
                  )}
                  {device.ise_profile && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">ISE Profile</label>
                      <p className="text-gray-900">{device.ise_profile}</p>
                    </div>
                  )}
                  {device.ad_groups && device.ad_groups.length > 0 && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">AD Groups</label>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {device.ad_groups.map((group, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded"
                          >
                            {group}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Behavioral Metrics */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <Activity className="h-5 w-5 mr-2" />
                  Behavioral Metrics
                </h3>
                <div className="bg-gray-50 rounded-lg p-4 grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-500">Total Flows</label>
                    <p className="text-gray-900 text-xl font-semibold">
                      {device.flow_count.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Unique Peers</label>
                    <p className="text-gray-900 text-xl font-semibold">{device.unique_peers}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Unique Ports</label>
                    <p className="text-gray-900 text-xl font-semibold">{device.unique_ports}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Switch</label>
                    <p className="text-gray-900 font-mono">{device.switch_id || 'N/A'}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Bytes In</label>
                    <p className="text-gray-900">{formatBytes(device.bytes_in)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Bytes Out</label>
                    <p className="text-gray-900">{formatBytes(device.bytes_out)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">First Seen</label>
                    <p className="text-gray-900 text-sm">{formatTimestamp(device.first_seen)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-500">Last Seen</label>
                    <p className="text-gray-900 text-sm">{formatTimestamp(device.last_seen)}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Assignment & Flows */}
            <div className="space-y-6">
              {/* Cluster & SGT Assignment */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <Tag className="h-5 w-5 mr-2" />
                  Cluster & SGT Assignment
                </h3>
                <div className="bg-gray-50 rounded-lg p-4 space-y-4">
                  {isEditing ? (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Cluster
                        </label>
                        <select
                          value={editedClusterId ?? ''}
                          onChange={(e) =>
                            setEditedClusterId(
                              e.target.value ? parseInt(e.target.value) : null
                            )
                          }
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
                        >
                          <option value="">Unassigned</option>
                          {clusters.map((cluster: any) => (
                            <option key={cluster.cluster_id} value={cluster.cluster_id}>
                              Cluster {cluster.cluster_id} - {cluster.cluster_label || 'No label'}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          SGT Value
                        </label>
                        <input
                          type="number"
                          value={editedSgtValue ?? ''}
                          onChange={(e) =>
                            setEditedSgtValue(
                              e.target.value ? parseInt(e.target.value) : null
                            )
                          }
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
                          placeholder="Enter SGT value"
                        />
                      </div>
                      <div className="flex space-x-2 pt-2">
                        <button
                          onClick={handleSave}
                          disabled={updateMutation.isPending}
                          className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center justify-center space-x-2"
                        >
                          <Save className="h-4 w-4" />
                          <span>Save Changes</span>
                        </button>
                        <button
                          onClick={handleCancel}
                          className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
                        >
                          Cancel
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <div>
                        <label className="text-sm font-medium text-gray-500">Cluster</label>
                        {device.cluster_id !== null && device.cluster_id !== undefined ? (
                          <p className="text-gray-900">
                            Cluster {device.cluster_id}
                            {device.cluster_label && ` - ${device.cluster_label}`}
                          </p>
                        ) : (
                          <p className="text-gray-500 italic">Unassigned</p>
                        )}
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-500">SGT</label>
                        {device.sgt_value !== null && device.sgt_value !== undefined ? (
                          <p className="text-gray-900">
                            SGT {device.sgt_value}
                            {device.sgt_name && ` - ${device.sgt_name}`}
                          </p>
                        ) : (
                          <p className="text-gray-500 italic">Not assigned</p>
                        )}
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Recent Flows */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <Network className="h-5 w-5 mr-2" />
                  Recent Flows ({flowsData?.total || 0} total)
                </h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  {flowsLoading ? (
                    <div className="text-center text-gray-500 py-4">Loading flows...</div>
                  ) : flowsData && flowsData.flows && flowsData.flows.length > 0 ? (
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {flowsData.flows.map((flow: any, idx: number) => (
                        <div
                          key={idx}
                          className="bg-white rounded p-3 border border-gray-200 text-sm"
                        >
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <span className="text-gray-500">Source:</span>{' '}
                              <span className="font-mono">{flow.src_ip}</span>:
                              <span className="font-mono">{flow.src_port}</span>
                            </div>
                            <div>
                              <span className="text-gray-500">Dest:</span>{' '}
                              <span className="font-mono">{flow.dst_ip}</span>:
                              <span className="font-mono">{flow.dst_port}</span>
                            </div>
                            <div>
                              <span className="text-gray-500">Protocol:</span> {flow.protocol}
                            </div>
                            <div>
                              <span className="text-gray-500">Bytes:</span>{' '}
                              {formatBytes(flow.bytes || 0)}
                            </div>
                            {flow.src_sgt && (
                              <div>
                                <span className="text-gray-500">Src SGT:</span> {flow.src_sgt}
                              </div>
                            )}
                            {flow.dst_sgt && (
                              <div>
                                <span className="text-gray-500">Dst SGT:</span> {flow.dst_sgt}
                              </div>
                            )}
                          </div>
                          <div className="text-xs text-gray-400 mt-1">
                            {formatTimestamp(flow.flow_start)}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center text-gray-500 py-4">No flows found</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

