import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient, Cluster, ClusterMember } from '../lib/api'

export default function Clusters() {
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null)

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Clusters & Devices</h1>
        <p className="text-gray-600 mt-1">
          View clusters and see which devices belong to each cluster
        </p>
      </div>

      {clusters.length === 0 ? (
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

