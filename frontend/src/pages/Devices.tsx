import { useQuery } from '@tanstack/react-query'

export default function Devices() {
  const { isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: async () => {
      // TODO: Replace with actual devices endpoint when available
      return { devices: [], total: 0 }
    },
  })

  if (isLoading) {
    return <div>Loading devices...</div>
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Devices</h1>
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-600">Device management page - Coming soon</p>
        <p className="text-sm text-gray-500 mt-2">
          This page will show all devices with filters, search, and device details.
        </p>
      </div>
    </div>
  )
}

