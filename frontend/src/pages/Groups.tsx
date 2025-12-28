import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { Search, Tag, Users } from 'lucide-react'
import GroupDetailModal from '../components/GroupDetailModal'

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

export default function Groups() {
  const [search, setSearch] = useState('')
  const [hasSgtFilter, setHasSgtFilter] = useState<string>('')
  const [page, setPage] = useState(0)
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null)
  const limit = 50

  // Get group stats
  const { data: stats } = useQuery({
    queryKey: ['groupStats'],
    queryFn: async () => {
      const response = await apiClient.getGroupStats()
      return response.data
    },
  })

  // Get groups with filters
  const { data, isLoading, error } = useQuery({
    queryKey: ['groups', search, hasSgtFilter, page],
    queryFn: async () => {
      const params: any = {
        limit,
        offset: page * limit,
      }
      if (search) params.search = search
      if (hasSgtFilter !== '') {
        params.has_sgt = hasSgtFilter === 'true'
      }

      const response = await apiClient.getGroups(params)
      return response.data
    },
  })

  const groups: Group[] = data?.groups || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / limit)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Groups</h1>
        {stats && (
          <div className="text-sm text-gray-600">
            Total: <span className="font-semibold">{stats.total_groups || 0}</span> groups |{' '}
            <span className="font-semibold">{stats.total_endpoints || 0}</span> devices
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by label or SGT name..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(0)
              }}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
            />
          </div>

          {/* SGT Filter */}
          <select
            value={hasSgtFilter}
            onChange={(e) => {
              setHasSgtFilter(e.target.value)
              setPage(0)
            }}
            className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
          >
            <option value="">All Groups</option>
            <option value="true">With SGT</option>
            <option value="false">Without SGT</option>
          </select>
        </div>
      </div>

      {/* Groups Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading groups...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">Error loading groups</div>
        ) : groups.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No groups found</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Group
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      SGT Assignment
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Members
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Updated
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {groups.map((group) => (
                    <tr
                      key={group.cluster_id}
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => setSelectedGroupId(group.cluster_id)}
                    >
                      {/* Group Info */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            Cluster {group.cluster_id}
                          </div>
                          {group.cluster_label && (
                            <div className="text-sm text-gray-500">{group.cluster_label}</div>
                          )}
                        </div>
                      </td>

                      {/* SGT Assignment */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        {group.sgt_value !== null && group.sgt_value !== undefined ? (
                          <div className="flex items-center">
                            <Tag className="h-4 w-4 text-blue-500 mr-2" />
                            <div>
                              <div className="text-sm font-medium text-gray-900">
                                SGT {group.sgt_value}
                              </div>
                              {group.sgt_name && (
                                <div className="text-xs text-gray-500">{group.sgt_name}</div>
                              )}
                            </div>
                          </div>
                        ) : (
                          <span className="text-sm text-gray-400 italic">Not assigned</span>
                        )}
                      </td>

                      {/* Members */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <Users className="h-4 w-4 text-gray-400 mr-2" />
                          <span className="text-sm text-gray-900">
                            {group.endpoint_count.toLocaleString()} devices
                          </span>
                        </div>
                      </td>

                      {/* Updated */}
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {group.updated_at
                          ? new Date(group.updated_at).toLocaleDateString()
                          : 'N/A'}
                      </td>

                      {/* Actions */}
                      <td
                        className="px-6 py-4 whitespace-nowrap text-sm font-medium"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={() => setSelectedGroupId(group.cluster_id)}
                          className="text-clarion-blue hover:text-clarion-blue-dark"
                        >
                          View Details
                        </button>
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
                  <span className="font-medium">{Math.min((page + 1) * limit, total)}</span> of{' '}
                  <span className="font-medium">{total}</span> groups
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

      {/* Group Detail Modal */}
      {selectedGroupId !== null && (
        <GroupDetailModal
          clusterId={selectedGroupId}
          onClose={() => setSelectedGroupId(null)}
        />
      )}
    </div>
  )
}
