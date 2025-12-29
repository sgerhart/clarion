import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { X, User, Mail, Building, Briefcase, Server, Users, Clock, Shield, TrendingUp, AlertTriangle, Activity } from 'lucide-react'

interface UserDetailModalProps {
  userId: string
  onClose: () => void
}

export default function UserDetailModal({ userId, onClose }: UserDetailModalProps) {
  const { data: user, isLoading, error } = useQuery({
    queryKey: ['user', userId],
    queryFn: async () => {
      const response = await apiClient.getUser(userId)
      return response.data
    },
  })

  const formatTimestamp = (ts?: string) => {
    if (!ts) return 'Never'
    return new Date(ts).toLocaleString()
  }

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold">User Details</h2>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
          </div>
          <div className="p-6 flex items-center justify-center">
            <div className="text-gray-500">Loading user details...</div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !user) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold">User Details</h2>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
          </div>
          <div className="p-6">
            <div className="text-red-600">
              Error loading user: {error instanceof Error ? error.message : 'User not found'}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">{user.display_name || user.username}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* User Information */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center">
              <User className="h-5 w-5 mr-2" />
              User Information
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Username</label>
                <p className="text-gray-900">{user.username}</p>
              </div>
              {user.email && (
                <div>
                  <label className="text-sm font-medium text-gray-500 flex items-center">
                    <Mail className="h-4 w-4 mr-1" />
                    Email
                  </label>
                  <p className="text-gray-900">{user.email}</p>
                </div>
              )}
              {user.display_name && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Display Name</label>
                  <p className="text-gray-900">{user.display_name}</p>
                </div>
              )}
              {user.department && (
                <div>
                  <label className="text-sm font-medium text-gray-500 flex items-center">
                    <Building className="h-4 w-4 mr-1" />
                    Department
                  </label>
                  <p className="text-gray-900">{user.department}</p>
                </div>
              )}
              {user.title && (
                <div>
                  <label className="text-sm font-medium text-gray-500 flex items-center">
                    <Briefcase className="h-4 w-4 mr-1" />
                    Title
                  </label>
                  <p className="text-gray-900">{user.title}</p>
                </div>
              )}
              <div>
                <label className="text-sm font-medium text-gray-500">User ID</label>
                <p className="text-gray-900 font-mono text-sm">{user.user_id}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Source</label>
                <p className="text-gray-900">{user.source || 'manual'}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500 flex items-center">
                  <Clock className="h-4 w-4 mr-1" />
                  First Seen
                </label>
                <p className="text-gray-900">{formatTimestamp(user.first_seen)}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500 flex items-center">
                  <Clock className="h-4 w-4 mr-1" />
                  Last Seen
                </label>
                <p className="text-gray-900">{formatTimestamp(user.last_seen)}</p>
              </div>
            </div>
          </div>

          {/* AD Groups */}
          {user.ad_groups && user.ad_groups.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                <Users className="h-5 w-5 mr-2" />
                AD Groups ({user.ad_groups.length})
              </h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex flex-wrap gap-2">
                  {user.ad_groups.map((group: any) => (
                    <span
                      key={group.group_id || group.group_name}
                      className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800"
                    >
                      {group.group_name || group.group_id}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* User SGT Assignment */}
          <UserSGTSection userId={userId} />

          {/* Traffic Pattern */}
          <UserTrafficSection userId={userId} />

          {/* SGT Recommendation */}
          <UserRecommendationSection userId={userId} />

          {/* Associated Devices */}
          {user.devices && user.devices.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                <Server className="h-5 w-5 mr-2" />
                Associated Devices ({user.devices.length})
              </h3>
              <div className="bg-gray-50 rounded-lg overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                        Device
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                        Association Type
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                        Last Associated
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {user.devices.map((device: any, idx: number) => (
                      <tr key={idx}>
                        <td className="px-4 py-3">
                          {/* Try to get device name from sketches/identity, fallback to endpoint_id */}
                          {device.device_name ? (
                            <div>
                              <div className="text-sm font-medium text-gray-900">{device.device_name}</div>
                              <div className="text-xs font-mono text-gray-500">{device.endpoint_id}</div>
                            </div>
                          ) : (
                            <div className="text-sm font-mono text-gray-900">{device.endpoint_id}</div>
                          )}
                          {device.ip_address && (
                            <div className="text-xs text-gray-500 mt-0.5">{device.ip_address}</div>
                          )}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            {device.association_type || 'manual'}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                          {formatTimestamp(device.last_associated)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// User SGT Assignment Section
function UserSGTSection({ userId }: { userId: string }) {
  const queryClient = useQueryClient()
  
  const { data: sgtData, isLoading } = useQuery({
    queryKey: ['userSGT', userId],
    queryFn: async () => {
      try {
        const response = await apiClient.getUserSGT(userId)
        return response.data
      } catch (error: any) {
        if (error.response?.status === 404) {
          return null // No SGT assignment
        }
        throw error
      }
    },
  })

  const unassignMutation = useMutation({
    mutationFn: () => apiClient.unassignUserSGT(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userSGT', userId] })
      queryClient.invalidateQueries({ queryKey: ['user', userId] })
    },
  })

  if (isLoading) {
    return (
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <Shield className="h-5 w-5 mr-2" />
          SGT Assignment
        </h3>
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <Shield className="h-5 w-5 mr-2" />
        SGT Assignment
      </h3>
      <div className="bg-gray-50 rounded-lg p-4">
        {sgtData ? (
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-gray-500">Current SGT</div>
              <div className="text-2xl font-bold text-gray-900">
                {sgtData.sgt_value} {sgtData.sgt_name && `(${sgtData.sgt_name})`}
              </div>
              {sgtData.assigned_by && (
                <div className="text-sm text-gray-500 mt-1">
                  Assigned by: {sgtData.assigned_by}
                  {sgtData.confidence && ` (${(sgtData.confidence * 100).toFixed(0)}% confidence)`}
                </div>
              )}
            </div>
            <button
              onClick={() => {
                if (confirm('Are you sure you want to unassign this SGT?')) {
                  unassignMutation.mutate()
                }
              }}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm font-medium"
            >
              Unassign
            </button>
          </div>
        ) : (
          <div className="text-gray-500">No SGT assignment</div>
        )}
      </div>
    </div>
  )
}

// User Traffic Pattern Section
function UserTrafficSection({ userId }: { userId: string }) {
  const { data: trafficData, isLoading } = useQuery({
    queryKey: ['userTraffic', userId],
    queryFn: async () => {
      const response = await apiClient.getUserTrafficPattern(userId)
      return response.data
    },
  })

  if (isLoading) {
    return (
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <Activity className="h-5 w-5 mr-2" />
          Traffic Pattern
        </h3>
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!trafficData || trafficData.total_flows === 0) {
    return (
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <Activity className="h-5 w-5 mr-2" />
          Traffic Pattern
        </h3>
        <div className="bg-gray-50 rounded-lg p-4 text-gray-500">
          No traffic data available
        </div>
      </div>
    )
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const totalBytes = (trafficData.total_bytes_in || 0) + (trafficData.total_bytes_out || 0)

  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <Activity className="h-5 w-5 mr-2" />
        Traffic Pattern
      </h3>
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <div className="text-sm font-medium text-gray-500">Total Flows</div>
            <div className="text-xl font-bold text-gray-900">{trafficData.total_flows?.toLocaleString() || 0}</div>
          </div>
          <div>
            <div className="text-sm font-medium text-gray-500">Total Bytes</div>
            <div className="text-xl font-bold text-gray-900">{formatBytes(totalBytes)}</div>
          </div>
          <div>
            <div className="text-sm font-medium text-gray-500">Unique Peers</div>
            <div className="text-xl font-bold text-gray-900">{trafficData.unique_peers?.toLocaleString() || 0}</div>
          </div>
          <div>
            <div className="text-sm font-medium text-gray-500">Unique Services</div>
            <div className="text-xl font-bold text-gray-900">{trafficData.unique_services || 0}</div>
          </div>
        </div>
        {trafficData.top_ports && trafficData.top_ports.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="text-sm font-medium text-gray-500 mb-2">Top Ports</div>
            <div className="flex flex-wrap gap-2">
              {trafficData.top_ports.slice(0, 10).map((port: any, idx: number) => (
                <span
                  key={idx}
                  className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                >
                  {typeof port === 'object' ? port.port : port}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// User SGT Recommendation Section
function UserRecommendationSection({ userId }: { userId: string }) {
  const queryClient = useQueryClient()
  
  const { data: recommendation, isLoading } = useQuery({
    queryKey: ['userRecommendation', userId],
    queryFn: async () => {
      try {
        const response = await apiClient.getUserSGTRecommendation(userId)
        return response.data
      } catch (error: any) {
        if (error.response?.status === 404) {
          return null // No recommendation available
        }
        throw error
      }
    },
  })

  const assignMutation = useMutation({
    mutationFn: (sgtValue: number) => apiClient.assignUserSGT(userId, sgtValue, 'recommendation', recommendation?.confidence),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userSGT', userId] })
      queryClient.invalidateQueries({ queryKey: ['user', userId] })
    },
  })

  if (isLoading) {
    return (
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <TrendingUp className="h-5 w-5 mr-2" />
          SGT Recommendation
        </h3>
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!recommendation) {
    return (
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <TrendingUp className="h-5 w-5 mr-2" />
          SGT Recommendation
        </h3>
        <div className="bg-gray-50 rounded-lg p-4 text-gray-500">
          No recommendation available (insufficient data)
        </div>
      </div>
    )
  }

  const getRecommendationBadgeColor = (type: string) => {
    switch (type) {
      case 'traffic_aligned':
        return 'bg-green-100 text-green-800'
      case 'traffic_diverges':
        return 'bg-yellow-100 text-yellow-800'
      case 'security_concern':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-blue-100 text-blue-800'
    }
  }

  const getRecommendationLabel = (type: string) => {
    switch (type) {
      case 'traffic_aligned':
        return 'Traffic Aligned'
      case 'traffic_diverges':
        return 'Traffic Diverges'
      case 'security_concern':
        return 'Security Concern'
      default:
        return type
    }
  }

  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <TrendingUp className="h-5 w-5 mr-2" />
        SGT Recommendation
      </h3>
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center gap-3">
              <div>
                <div className="text-sm font-medium text-gray-500">Recommended SGT</div>
                <div className="text-2xl font-bold text-gray-900">
                  {recommendation.recommended_sgt} {recommendation.recommended_sgt_name && `(${recommendation.recommended_sgt_name})`}
                </div>
              </div>
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getRecommendationBadgeColor(recommendation.recommendation_type)}`}>
                {getRecommendationLabel(recommendation.recommendation_type)}
              </span>
              {recommendation.confidence && (
                <div className="text-sm text-gray-500">
                  {(recommendation.confidence * 100).toFixed(0)}% confidence
                </div>
              )}
            </div>
          </div>
          <button
            onClick={() => {
              if (confirm(`Assign SGT ${recommendation.recommended_sgt} to this user?`)) {
                assignMutation.mutate(recommendation.recommended_sgt)
              }
            }}
            disabled={assignMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
          >
            {assignMutation.isPending ? 'Assigning...' : 'Assign SGT'}
          </button>
        </div>

        {recommendation.justification && (
          <div className="mb-4 p-3 bg-white rounded border border-gray-200">
            <div className="text-sm text-gray-700">{recommendation.justification}</div>
          </div>
        )}

        {recommendation.ad_group_based_sgt && (
          <div className="mb-2 text-sm">
            <span className="text-gray-500">AD Group Based SGT: </span>
            <span className="font-medium">{recommendation.ad_group_based_sgt} {recommendation.ad_group_based_sgt_name && `(${recommendation.ad_group_based_sgt_name})`}</span>
          </div>
        )}

        {recommendation.traffic_suggested_sgt && (
          <div className="mb-2 text-sm">
            <span className="text-gray-500">Traffic Suggested SGT: </span>
            <span className="font-medium">{recommendation.traffic_suggested_sgt} {recommendation.traffic_suggested_sgt_name && `(${recommendation.traffic_suggested_sgt_name})`}</span>
          </div>
        )}

        {recommendation.security_concerns && recommendation.security_concerns.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex items-center text-red-600 mb-2">
              <AlertTriangle className="h-4 w-4 mr-2" />
              <span className="text-sm font-medium">Security Concerns</span>
            </div>
            <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
              {recommendation.security_concerns.map((concern: string, idx: number) => (
                <li key={idx}>{concern}</li>
              ))}
            </ul>
          </div>
        )}

        {recommendation.primary_ad_groups && recommendation.primary_ad_groups.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="text-sm font-medium text-gray-500 mb-2">Primary AD Groups</div>
            <div className="flex flex-wrap gap-2">
              {recommendation.primary_ad_groups.map((group: string, idx: number) => (
                <span
                  key={idx}
                  className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                >
                  {group}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

