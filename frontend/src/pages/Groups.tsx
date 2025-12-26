import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/api'

export default function Groups() {
  const { data, isLoading } = useQuery({
    queryKey: ['groups'],
    queryFn: async () => {
      const response = await apiClient.getClusters()
      return response.data || []
    },
  })

  if (isLoading) {
    return <div>Loading groups...</div>
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Groups</h1>
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-600">Group management page</p>
        {data && (
          <div className="mt-4">
            <p className="text-sm text-gray-500">
              {data.length} groups found
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

