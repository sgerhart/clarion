import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient, Cluster, ClusterMember } from '../lib/api'
import { User, Users } from 'lucide-react'

export default function Clusters() {
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null)
  const [showUserClusters, setShowUserClusters] = useState(false)

  const { data: clustersData } = useQuery({
    queryKey: ['clusters'],
    queryFn: async () => {
      const response = await apiClient.getClusters()
      return Array.isArray(response.data) ? response.data : []
    },
  })

  const { data: membersData } = useQuery({
    queryKey: ['clusterMembers', selectedClusterId],
    queryFn: async () => {
      const response = await apiClient.getClusterMembers(selectedClusterId!)
      return response.data
    },
    enabled: selectedClusterId !== null,
  })

  const clusters: Cluster[] = Array.isArray(clustersData) ? clustersData : []
  const members: ClusterMember[] = membersData?.members || []

  const selectedCluster = clusters.find((c) => c.cluster_id === selectedClusterId)

  // Get user clusters
  const { data: userClustersData } = useQuery({
    queryKey: ['userClusters'],
    queryFn: async () => {
      const response = await apiClient.getUserClusters()
      return response.data
    },
  })

  const userClusters = userClustersData?.clusters || []

  // Get users in selected device cluster
  const { data: clusterUsersData } = useQuery({
    queryKey: ['clusterUsers', selectedClusterId],
    queryFn: async () => {
      const response = await apiClient.getClusterUsersFromDevices(selectedClusterId!)
      return response.data
    },
    enabled: selectedClusterId !== null && !showUserClusters,
  })

  const clusterUsers = clusterUsersData?.users || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Clusters & Devices</h1>
          <p className="text-gray-600 mt-1">
            View device clusters and user clusters
          </p>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={() => setShowUserClusters(false)}
            className={`px-4 py-2 rounded-lg ${
              !showUserClusters
                ? 'bg-clarion-blue text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Device Clusters
          </button>
          <button
            onClick={() => setShowUserClusters(true)}
            className={`px-4 py-2 rounded-lg flex items-center space-x-2 ${
              showUserClusters
                ? 'bg-clarion-blue text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <Users className="h-4 w-4" />
            <span>User Clusters</span>
          </button>
        </div>
      </div>

      {showUserClusters ? (
        // User Clusters View
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <Users className="h-5 w-5 mr-2" />
                User Clusters
              </h2>
              {userClusters.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <p>No user clusters found.</p>
                  <button
                    onClick={async () => {
                      try {
                        await apiClient.generateUserClusters()
                        window.location.reload()
                      } catch (error) {
                        alert('Error generating user clusters')
                      }
                    }}
                    className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Generate User Clusters
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {userClusters.map((cluster: any) => (
                    <div
                      key={cluster.cluster_id}
                      className="bg-gray-50 rounded-lg p-3 border border-gray-200"
                    >
                      <div className="font-medium text-gray-900">{cluster.name}</div>
                      <div className="text-sm text-gray-600 mt-1">
                        {cluster.user_count} users
                      </div>
                      {cluster.primary_department && (
                        <div className="text-xs text-gray-500 mt-1">
                          {cluster.primary_department}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                User Clusters Overview
              </h2>
              <p className="text-gray-600 mb-4">
                User clusters group users by their AD groups and departments. 
                These clusters help identify which users should receive User SGT assignments.
              </p>
              {userClusters.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <p>No user clusters found. Click "Generate User Clusters" to create them.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {userClusters.map((cluster: any) => (
                    <div key={cluster.cluster_id} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <h3 className="font-semibold text-gray-900">{cluster.name}</h3>
                      <p className="text-sm text-gray-600 mt-1">{cluster.user_count} users</p>
                      {cluster.primary_ad_group && (
                        <p className="text-xs text-gray-500 mt-1">AD Group: {cluster.primary_ad_group}</p>
                      )}
                      {cluster.primary_department && (
                        <p className="text-xs text-gray-500">Dept: {cluster.primary_department}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : clusters.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center">
          <p className="text-gray-500">No clusters found. Run clustering first.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Cluster List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Select Cluster
              </h2>
              <div className="space-y-2">
                {clusters
                  .filter((c) => c.cluster_id !== -1)
                  .map((cluster) => (
                    <button
                      key={cluster.cluster_id}
                      onClick={() => setSelectedClusterId(cluster.cluster_id)}
                      className={`
                        w-full text-left px-4 py-3 rounded-lg transition-colors
                        ${
                          selectedClusterId === cluster.cluster_id
                            ? 'bg-clarion-blue text-white'
                            : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                        }
                      `}
                    >
                      <div className="font-medium">
                        {cluster.cluster_label || `Cluster ${cluster.cluster_id}`}
                      </div>
                      <div className="text-sm opacity-75">
                        SGT {cluster.sgt_value || 'N/A'} • {cluster.endpoint_count} devices
                      </div>
                    </button>
                  ))}
              </div>
            </div>
          </div>

          {/* Cluster Details */}
          <div className="lg:col-span-2">
            {selectedCluster ? (
              <div className="space-y-6">
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div>
                      <p className="text-sm text-gray-600">Cluster ID</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {selectedCluster.cluster_id}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">SGT Value</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {selectedCluster.sgt_value || 'N/A'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Device Count</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {selectedCluster.endpoint_count}
                      </p>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <p>
                      <span className="font-medium text-gray-700">Label:</span>{' '}
                      <span className="text-gray-900">
                        {selectedCluster.cluster_label || 'Unnamed'}
                      </span>
                    </p>
                    <p>
                      <span className="font-medium text-gray-700">SGT Name:</span>{' '}
                      <span className="text-gray-900">
                        {selectedCluster.sgt_name || 'N/A'}
                      </span>
                    </p>
                  </div>
                </div>

                {/* Users in Cluster */}
                {clusterUsers.length > 0 && (
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                      <User className="h-5 w-5 mr-2" />
                      Users in This Cluster ({clusterUsers.length})
                    </h2>
                    <div className="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
                      <div className="space-y-2">
                        {clusterUsers.slice(0, 20).map((user: any) => (
                          <div key={user.user_id} className="flex items-center justify-between py-2 border-b border-gray-200 last:border-0">
                            <div className="flex-1">
                              <p className="text-sm font-medium text-gray-900">
                                {user.display_name || user.username}
                              </p>
                              <p className="text-xs text-gray-500">{user.email || user.username}</p>
                              {user.department && (
                                <p className="text-xs text-gray-400">{user.department}</p>
                              )}
                            </div>
                            <div className="text-right">
                              <p className="text-xs text-gray-500">{user.device_count} device{user.device_count !== 1 ? 's' : ''}</p>
                              {user.ad_groups && user.ad_groups.length > 0 && (
                                <p className="text-xs text-gray-400 mt-1">
                                  {user.ad_groups.slice(0, 2).join(', ')}
                                  {user.ad_groups.length > 2 && ` +${user.ad_groups.length - 2}`}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                        {clusterUsers.length > 20 && (
                          <p className="text-xs text-gray-500 text-center pt-2">
                            Showing 20 of {clusterUsers.length} users
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">
                    Devices in This Cluster
                  </h2>
                  {members.length === 0 ? (
                    <p className="text-gray-500">No devices found in this cluster.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                              Endpoint ID
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                              Switch
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                              Flows
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                              User
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                              Device
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {members.map((member, idx) => (
                            <tr key={idx} className="hover:bg-gray-50">
                              <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                                {member.endpoint_id}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {member.switch_id}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {member.flow_count.toLocaleString()}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {member.user_name || '-'}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {member.device_name || '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center">
                <p className="text-gray-500">Select a cluster to view details</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

