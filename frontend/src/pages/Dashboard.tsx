import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { Activity, Network, Layers, Shield } from 'lucide-react'

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['sketchStats'],
    queryFn: async () => {
      try {
        const response = await apiClient.getSketchStats()
        return response.data
      } catch (error: any) {
        console.error('Error fetching sketch stats:', error)
        throw error
      }
    },
    retry: false,
    refetchOnWindowFocus: false,
  })

  const { data: clusters, isLoading: clustersLoading, error: clustersError } = useQuery({
    queryKey: ['clusters'],
    queryFn: async () => {
      try {
        const response = await apiClient.getClusters()
        return response.data || []
      } catch (error: any) {
        console.error('Error fetching clusters:', error)
        throw error
      }
    },
    retry: false,
    refetchOnWindowFocus: false,
  })

  const statsData = stats || {}
  const clustersData = Array.isArray(clusters) ? clusters : []

  if (statsLoading || clustersLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading dashboard data...</div>
      </div>
    )
  }

  if (statsError || clustersError) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">
          Error loading data: {statsError?.message || clustersError?.message}
        </p>
        <p className="text-sm text-red-600 mt-2">
          Make sure the backend API is running on http://localhost:8000
        </p>
      </div>
    )
  }

  const metrics = [
    {
      name: 'Total Endpoints',
      value: statsData.unique_endpoints?.toLocaleString() || '0',
      icon: Network,
      color: 'bg-blue-500',
    },
    {
      name: 'Total Flows',
      value: statsData.total_flows?.toLocaleString() || '0',
      icon: Activity,
      color: 'bg-green-500',
    },
    {
      name: 'Active Clusters',
      value: clustersData.length || 0,
      icon: Layers,
      color: 'bg-purple-500',
    },
    {
      name: 'Switches',
      value: statsData.total_switches || 0,
      icon: Shield,
      color: 'bg-orange-500',
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">System overview and metrics</p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((metric) => {
          const Icon = metric.icon
          return (
            <div
              key={metric.name}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">
                    {metric.name}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 mt-2">
                    {metric.value}
                  </p>
                </div>
                <div className={`${metric.color} p-3 rounded-lg`}>
                  <Icon className="h-6 w-6 text-white" />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* System Health */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          System Health
        </h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Database Status</span>
            <span className="px-3 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
              Healthy
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">API Status</span>
            <span className="px-3 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
              Online
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Latest Flow</span>
            <span className="text-sm text-gray-900">
              {statsData.latest_flow
                ? new Date(statsData.latest_flow * 1000).toLocaleString()
                : 'N/A'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

