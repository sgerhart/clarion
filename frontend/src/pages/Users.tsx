import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { Search, User, Mail, Building, Shield } from 'lucide-react'
import UserDetailModal from '../components/UserDetailModal'

// User SGT Badge Component (for table display)
function UserSGTBadge({ userId }: { userId: string }) {
  const { data: sgtData } = useQuery({
    queryKey: ['userSGT', userId],
    queryFn: async () => {
      try {
        const response = await apiClient.getUserSGT(userId)
        return response.data
      } catch (error: any) {
        if (error.response?.status === 404) {
          return null
        }
        return null // Silently fail for table display
      }
    },
    staleTime: 60000, // Cache for 1 minute
  })

  if (!sgtData) {
    return <span className="text-sm text-gray-400">—</span>
  }

  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
      <Shield className="h-3 w-3 mr-1" />
      {sgtData.sgt_value}
    </span>
  )
}

interface User {
  user_id: string
  username: string
  email?: string
  display_name?: string
  department?: string
  title?: string
  is_active: boolean
  first_seen?: string
  last_seen?: string
  source?: string
}

export default function UsersPage() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
  const limit = 50

  // Get users with filters
  const { data, isLoading, error } = useQuery({
    queryKey: ['users', search, page],
    queryFn: async () => {
      const params: any = {
        limit,
        offset: page * limit,
      }
      if (search) params.search = search

      const response = await apiClient.getUsers(params)
      return response.data
    },
  })

  const users: User[] = data?.users || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / limit)

  const formatTimestamp = (ts?: string) => {
    if (!ts) return 'Never'
    return new Date(ts).toLocaleString()
  }

  if (error) {
    return (
      <div className="text-red-600">
        Error loading users: {error instanceof Error ? error.message : 'Unknown error'}
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Users</h1>
        {data && (
          <div className="text-sm text-gray-600">
            Total: <span className="font-semibold">{total}</span> users
          </div>
        )}
      </div>

      {/* Search and filters */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
          <input
            type="text"
            placeholder="Search by username, email, or display name..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(0)
            }}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
          />
        </div>
      </div>

      {/* Users table */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading users...</div>
      ) : users.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          {search ? 'No users found matching your search.' : 'No users found.'}
        </div>
      ) : (
        <>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Department
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Title
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Seen
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    SGT
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user) => (
                  <tr
                    key={user.user_id}
                    onClick={() => setSelectedUserId(user.user_id)}
                    className="hover:bg-gray-50 cursor-pointer"
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <User className="h-5 w-5 text-gray-400 mr-3" />
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {user.display_name || user.username}
                          </div>
                          {user.display_name && (
                            <div className="text-sm text-gray-500">{user.username}</div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {user.email ? (
                        <div className="flex items-center text-sm text-gray-900">
                          <Mail className="h-4 w-4 text-gray-400 mr-2" />
                          {user.email}
                        </div>
                      ) : (
                        <span className="text-sm text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {user.department ? (
                        <div className="flex items-center text-sm text-gray-900">
                          <Building className="h-4 w-4 text-gray-400 mr-2" />
                          {user.department}
                        </div>
                      ) : (
                        <span className="text-sm text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {user.title || <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatTimestamp(user.last_seen)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <UserSGTBadge userId={user.user_id} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {user.source || 'manual'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {user.is_active ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          Inactive
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Showing <span className="font-medium">{(page * limit) + 1}</span> to{' '}
                <span className="font-medium">{Math.min((page + 1) * limit, total)}</span> of{' '}
                <span className="font-medium">{total}</span> users
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* User detail modal */}
      {selectedUserId && (
        <UserDetailModal
          userId={selectedUserId}
          onClose={() => setSelectedUserId(null)}
        />
      )}
    </div>
  )
}

