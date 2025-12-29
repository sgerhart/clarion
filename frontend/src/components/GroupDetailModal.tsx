import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { X, Save, Edit2, Tag, Users, Server, User, Brain, Info } from 'lucide-react'
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

interface Group {
  cluster_id: number
  cluster_label?: string
  sgt_value?: number
  sgt_name?: string
  endpoint_count: number
  explanation?: string
  primary_reason?: string
  confidence?: number
  created_at?: string
  updated_at?: string
}

interface GroupMember {
  endpoint_id: string
  switch_id?: string
  ip_address?: string
  user_name?: string
  device_name?: string
  device_type?: string
  flow_count: number
  bytes_in: number
  bytes_out: number
}

interface GroupDetailModalProps {
  clusterId: number
  onClose: () => void
}

export default function GroupDetailModal({ clusterId, onClose }: GroupDetailModalProps) {
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [editedLabel, setEditedLabel] = useState<string>('')

  // Get group details
  const { data: groupData, isLoading } = useQuery({
    queryKey: ['group', clusterId],
    queryFn: async () => {
      const response = await apiClient.getGroup(clusterId)
      return response.data
    },
  })

  const group: Group | undefined = groupData?.group
  const members: GroupMember[] = groupData?.members || []

  // Update group mutation (cluster label only - SGTs are managed by ISE policies)
  const updateMutation = useMutation({
    mutationFn: async (data: {
      cluster_label?: string
    }) => {
      return apiClient.updateGroup(clusterId, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group', clusterId] })
      queryClient.invalidateQueries({ queryKey: ['groups'] })
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      setIsEditing(false)
    },
  })

  // Initialize edit values when group loads
  useEffect(() => {
    if (group) {
      setEditedLabel(group.cluster_label || '')
    }
  }, [group])

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const getDeviceTypeIcon = (deviceType?: string) => {
    if (!deviceType) return <Server className="h-4 w-4" />
    const type = deviceType.toLowerCase()
    if (type === 'server') return <Server className="h-4 w-4 text-blue-500" />
    if (type === 'laptop') return <User className="h-4 w-4 text-green-500" />
    return <Server className="h-4 w-4 text-gray-500" />
  }

  const handleSave = () => {
    updateMutation.mutate({
      cluster_label: editedLabel || undefined,
    })
  }

  const handleCancel = () => {
    if (group) {
      setEditedLabel(group.cluster_label || '')
    }
    setIsEditing(false)
  }

  if (isLoading || !group) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8">
          <div className="text-center">Loading group details...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-4">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                Cluster {group.cluster_id}
              </h2>
              {group.cluster_label && !isEditing && (
                <p className="text-gray-600 mt-1">{group.cluster_label}</p>
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
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column: Group Information */}
            <div className="lg:col-span-1 space-y-6">
              {/* Group Metadata */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <Tag className="h-5 w-5 mr-2" />
                  Group Information
                </h3>
                <div className="bg-gray-50 rounded-lg p-4 space-y-4">
                  {isEditing ? (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Cluster Label
                        </label>
                        <input
                          type="text"
                          value={editedLabel}
                          onChange={(e) => setEditedLabel(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
                          placeholder="Enter cluster label"
                        />
                      </div>
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                        <p className="text-sm text-blue-800">
                          <strong>Note:</strong> SGTs are assigned by Cisco ISE authorization policies 
                          and cannot be edited directly. To change SGT assignments for this group, 
                          update the corresponding ISE authorization policy. Clarion can help generate 
                          policy recommendations based on cluster analysis.
                        </p>
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
                        <label className="text-sm font-medium text-gray-500">Cluster ID</label>
                        <p className="text-gray-900 font-semibold">{group.cluster_id}</p>
                      </div>
                      {group.cluster_label && (
                        <div>
                          <label className="text-sm font-medium text-gray-500">Label</label>
                          <p className="text-gray-900">{group.cluster_label}</p>
                        </div>
                      )}
                      {group.sgt_value !== null && group.sgt_value !== undefined ? (
                        <>
                          <div>
                            <label className="text-sm font-medium text-gray-500">SGT Value</label>
                            <div>
                              <p className="text-gray-900 font-semibold">SGT {group.sgt_value}</p>
                              <p className="text-xs text-gray-500 mt-1">
                                Assigned by ISE authorization policy
                              </p>
                            </div>
                          </div>
                          {group.sgt_name && (
                            <div>
                              <label className="text-sm font-medium text-gray-500">SGT Name</label>
                              <p className="text-gray-900">{group.sgt_name}</p>
                            </div>
                          )}
                        </>
                      ) : (
                        <div>
                          <label className="text-sm font-medium text-gray-500">SGT</label>
                          <p className="text-gray-500 italic">Not assigned</p>
                        </div>
                      )}
                      <div>
                        <label className="text-sm font-medium text-gray-500">Member Count</label>
                        <p className="text-gray-900 font-semibold">
                          {members.length.toLocaleString()} devices
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Right Column: Members List and Explanation */}
            <div className="lg:col-span-2 space-y-6">
              {/* Members List */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <Users className="h-5 w-5 mr-2" />
                  Members ({members.length} devices)
                </h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  {members.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">No members in this group</div>
                  ) : (
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {members.map((member, idx) => (
                        <Link
                          key={idx}
                          to={`/devices`}
                          onClick={() => {
                            // Store device ID in sessionStorage to filter on devices page
                            sessionStorage.setItem('selectedDevice', member.endpoint_id)
                          }}
                        >
                          <div className="bg-white rounded p-3 border border-gray-200 hover:border-clarion-blue hover:shadow-md transition-all cursor-pointer">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-3 flex-1">
                                {getDeviceTypeIcon(member.device_type)}
                                <div className="flex-1 min-w-0">
                                  <div className="text-sm font-medium text-gray-900 font-mono truncate">
                                    {member.endpoint_id}
                                  </div>
                                  <div className="text-xs text-gray-500 space-x-2">
                                    {member.device_name && (
                                      <span>{member.device_name}</span>
                                    )}
                                    {member.ip_address && (
                                      <span className="font-mono">{member.ip_address}</span>
                                    )}
                                    {member.user_name && <span>• {member.user_name}</span>}
                                  </div>
                                </div>
                              </div>
                              <div className="text-right text-sm text-gray-600">
                                <div>{member.flow_count.toLocaleString()} flows</div>
                                <div className="text-xs text-gray-500">
                                  {formatBytes(member.bytes_in + member.bytes_out)} total
                                </div>
                              </div>
                            </div>
                          </div>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Cluster Explanation */}
              {(group.explanation || group.primary_reason) && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-center mb-3">
                    <Brain className="h-5 w-5 text-blue-600 mr-2" />
                    <h3 className="text-lg font-semibold text-blue-900">
                      Why These Devices Are Grouped
                    </h3>
                  </div>
                  
                  {group.primary_reason && (
                    <div className="mb-3">
                      <div className="text-sm font-medium text-blue-800 mb-1">
                        Primary Reason:
                      </div>
                      <div className="text-sm text-blue-900">{group.primary_reason}</div>
                    </div>
                  )}
                  
                  {group.explanation && (
                    <div className="mb-3">
                      <div className="text-sm font-medium text-blue-800 mb-2">
                        Detailed Explanation:
                      </div>
                      <div className="text-sm text-blue-900 whitespace-pre-line">
                        {group.explanation}
                      </div>
                    </div>
                  )}
                  
                  {group.confidence !== null && group.confidence !== undefined && (
                    <div className="mt-3 pt-3 border-t border-blue-300">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-blue-800">
                          Confidence Level:
                        </span>
                        <div className="flex items-center">
                          <div className="w-32 bg-blue-200 rounded-full h-2 mr-2">
                            <div
                              className={`h-2 rounded-full ${
                                (group.confidence || 0) >= 0.7
                                  ? 'bg-green-600'
                                  : (group.confidence || 0) >= 0.5
                                  ? 'bg-yellow-600'
                                  : 'bg-red-600'
                              }`}
                              style={{ width: `${(group.confidence || 0) * 100}%` }}
                            ></div>
                          </div>
                          <span className="text-sm font-semibold text-blue-900">
                            {((group.confidence || 0) * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <div className="mt-4 pt-3 border-t border-blue-300">
                    <div className="flex items-start">
                      <Info className="h-4 w-4 text-blue-600 mr-2 mt-0.5 flex-shrink-0" />
                      <div className="text-xs text-blue-800">
                        <strong>Policy Context:</strong> All devices in this group share the same SGT 
                        and will have identical SGACL policies applied, ensuring consistent network access 
                        controls based on their common characteristics and behaviors.
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

