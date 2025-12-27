import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { Search, Filter, Server, User, Building, Tag } from 'lucide-react'
import { Link } from 'react-router-dom'
import DeviceDetailModal from '../components/DeviceDetailModal'

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

export default function Devices() {
  const [search, setSearch] = useState('')
  const [switchFilter, setSwitchFilter] = useState<string>('')
  const [clusterFilter, setClusterFilter] = useState<string>('')
  const [deviceTypeFilter, setDeviceTypeFilter] = useState<string>('')
  const [page, setPage] = useState(0)
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null)
  const limit = 50

  // Get device stats for filters
  const { data: stats } = useQuery({
    queryKey: ['deviceStats'],
    queryFn: async () => {
      const response = await apiClient.getDeviceStats()
      return response.data
    },
  })

  // Get devices with filters
  const { data, isLoading, error } = useQuery({
    queryKey: ['devices', search, switchFilter, clusterFilter, deviceTypeFilter, page],
    queryFn: async () => {
      const params: any = {
        limit,
        offset: page * limit,
      }
      if (search) params.search = search
      if (switchFilter) params.switch_id = switchFilter
      if (clusterFilter) params.cluster_id = parseInt(clusterFilter)
      if (deviceTypeFilter) params.device_type = deviceTypeFilter

      const response = await apiClient.getDevices(params)
      return response.data
    },
  })

  const devices: Device[] = data?.devices || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / limit)

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

  const getDeviceTypeIcon = (deviceType?: string) => {
    if (!deviceType) return <Server className="h-4 w-4" />
    const type = deviceType.toLowerCase()
    if (type === 'server') return <Server className="h-4 w-4 text-blue-500" />
    if (type === 'laptop') return <User className="h-4 w-4 text-green-500" />
    return <Building className="h-4 w-4 text-gray-500" />
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Devices</h1>
        {stats && (
          <div className="text-sm text-gray-600">
            Total: <span className="font-semibold">{stats.total_devices || 0}</span> devices
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by MAC, IP, or name..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(0)
              }}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
            />
          </div>

          {/* Switch filter */}
          <select
            value={switchFilter}
            onChange={(e) => {
              setSwitchFilter(e.target.value)
              setPage(0)
            }}
            className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
          >
            <option value="">All Switches</option>
            {stats?.by_switch && Object.keys(stats.by_switch).map((switchId) => (
              <option key={switchId} value={switchId}>
                {switchId} ({stats.by_switch[switchId]})
              </option>
            ))}
          </select>

          {/* Cluster filter */}
          <select
            value={clusterFilter}
            onChange={(e) => {
              setClusterFilter(e.target.value)
              setPage(0)
            }}
            className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
          >
            <option value="">All Clusters</option>
            {stats?.by_cluster && Object.keys(stats.by_cluster).map((clusterId) => (
              <option key={clusterId} value={clusterId}>
                Cluster {clusterId} ({stats.by_cluster[clusterId]})
              </option>
            ))}
          </select>

          {/* Device type filter */}
          <select
            value={deviceTypeFilter}
            onChange={(e) => {
              setDeviceTypeFilter(e.target.value)
              setPage(0)
            }}
            className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
          >
            <option value="">All Device Types</option>
            <option value="server">Servers</option>
            <option value="laptop">Laptops</option>
            <option value="printer">Printers</option>
            <option value="iot">IoT Devices</option>
          </select>
        </div>
      </div>

      {/* Device Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading devices...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">Error loading devices</div>
        ) : devices.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No devices found</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Device
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Identity
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Behavior
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Traffic
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Assignment
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Seen
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {devices.map((device) => (
                    <tr
                      key={device.endpoint_id}
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => setSelectedDeviceId(device.endpoint_id)}
                    >
                      {/* Device Info */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          {getDeviceTypeIcon(device.device_type)}
                          <div className="ml-3">
                            <div className="text-sm font-medium text-gray-900 font-mono">
                              {device.endpoint_id}
                            </div>
                            {device.device_name && (
                              <div className="text-sm text-gray-500">{device.device_name}</div>
                            )}
                            {device.switch_id && (
                              <div className="text-xs text-gray-400">Switch: {device.switch_id}</div>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* Identity */}
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900">
                          {device.ip_address && (
                            <div className="font-mono">{device.ip_address}</div>
                          )}
                          {device.user_name && (
                            <div className="text-gray-600">{device.user_name}</div>
                          )}
                          {device.ise_profile && (
                            <div className="text-xs text-blue-600">ISE: {device.ise_profile}</div>
                          )}
                          {device.ad_groups && device.ad_groups.length > 0 && (
                            <div className="text-xs text-gray-500 mt-1">
                              {device.ad_groups.slice(0, 2).join(', ')}
                              {device.ad_groups.length > 2 && ` +${device.ad_groups.length - 2}`}
                            </div>
                          )}
                        </div>
                      </td>

                      {/* Behavior */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          <div>Flows: {device.flow_count.toLocaleString()}</div>
                          <div className="text-gray-600">
                            Peers: {device.unique_peers} | Ports: {device.unique_ports}
                          </div>
                        </div>
                      </td>

                      {/* Traffic */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm">
                          <div className="text-gray-900">
                            ↓ {formatBytes(device.bytes_in)}
                          </div>
                          <div className="text-gray-600">
                            ↑ {formatBytes(device.bytes_out)}
                          </div>
                        </div>
                      </td>

                      {/* Assignment */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        {device.cluster_id !== null && device.cluster_id !== undefined ? (
                          <div>
                            <Link
                              to={`/groups`}
                              className="text-sm font-medium text-clarion-blue hover:underline"
                            >
                              Cluster {device.cluster_id}
                            </Link>
                            {device.cluster_label && (
                              <div className="text-xs text-gray-500">{device.cluster_label}</div>
                            )}
                            {device.sgt_value !== null && device.sgt_value !== undefined && (
                              <div className="flex items-center mt-1">
                                <Tag className="h-3 w-3 text-gray-400 mr-1" />
                                <span className="text-xs text-gray-600">
                                  SGT {device.sgt_value}
                                  {device.sgt_name && ` - ${device.sgt_name}`}
                                </span>
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-sm text-gray-400">Unassigned</span>
                        )}
                      </td>

                      {/* Last Seen */}
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatTimestamp(device.last_seen)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="bg-gray-50 px-6 py-3 flex items-center justify-between border-t border-gray-200">
                <div className="text-sm text-gray-700">
                  Showing <span className="font-medium">{page * limit + 1}</span> to{' '}
                  <span className="font-medium">
                    {Math.min((page + 1) * limit, total)}
                  </span>{' '}
                  of <span className="font-medium">{total}</span> devices
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                    className="px-4 py-2 text-sm border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                    disabled={page >= totalPages - 1}
                    className="px-4 py-2 text-sm border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Device Detail Modal */}
      {selectedDeviceId && (
        <DeviceDetailModal
          deviceId={selectedDeviceId}
          onClose={() => setSelectedDeviceId(null)}
        />
      )}
    </div>
  )
}
