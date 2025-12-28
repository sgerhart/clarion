import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../lib/api'
import { Plus, Trash2, Edit, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react'

interface Collector {
  collector_id: string
  name: string
  type: 'native' | 'agent'
  host: string
  http_port: number
  backend_url: string
  netflow_port?: number
  ipfix_port?: number
  batch_size?: number
  batch_interval_seconds?: number
  enabled: boolean
  description?: string
  status: 'online' | 'offline' | 'unknown'
  last_seen?: string
  metrics?: {
    total_received?: number
    total_sent?: number
    pending?: number
    errors?: number
  }
}

interface CollectorFormData {
  collector_id: string
  name: string
  type: 'native' | 'agent'
  host: string
  http_port: number
  backend_url: string
  netflow_port?: number
  ipfix_port?: number
  batch_size?: number
  batch_interval_seconds?: number
  description?: string
}

export default function NetFlowCollectors() {
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingCollector, setEditingCollector] = useState<Collector | null>(null)
  const queryClient = useQueryClient()

  const { data: collectors = [], isLoading, refetch } = useQuery({
    queryKey: ['collectors'],
    queryFn: async () => {
      const response = await apiClient.getCollectors()
      return response.data as Collector[]
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (collectorId: string) => {
      await apiClient.deleteCollector(collectorId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collectors'] })
    },
  })

  const createMutation = useMutation({
    mutationFn: async (data: CollectorFormData) => {
      await apiClient.createCollector(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collectors'] })
      setShowAddModal(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({ collectorId, data }: { collectorId: string; data: Partial<CollectorFormData> }) => {
      await apiClient.updateCollector(collectorId, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collectors'] })
      setEditingCollector(null)
    },
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'text-green-600 bg-green-50'
      case 'offline':
        return 'text-red-600 bg-red-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
        return <CheckCircle2 className="h-4 w-4" />
      case 'offline':
        return <AlertCircle className="h-4 w-4" />
      default:
        return <AlertCircle className="h-4 w-4" />
    }
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <p>Loading collectors...</p>
      </div>
    )
  }

  return (
    <div>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-semibold mb-2">NetFlow Collectors</h2>
            <p className="text-sm text-gray-600">
              Monitor and configure NetFlow/IPFIX collectors
            </p>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => refetch()}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 flex items-center space-x-2"
            >
              <RefreshCw className="h-4 w-4" />
              <span>Refresh</span>
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 text-sm font-medium text-white bg-clarion-blue rounded-md hover:bg-clarion-blue-dark flex items-center space-x-2"
            >
              <Plus className="h-4 w-4" />
              <span>Add Collector</span>
            </button>
          </div>
        </div>

        {collectors.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">No collectors registered</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 text-sm font-medium text-white bg-clarion-blue rounded-md hover:bg-clarion-blue-dark"
            >
              Add Your First Collector
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Host
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Metrics
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {collectors.map((collector) => (
                  <tr key={collector.collector_id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{collector.name}</div>
                      {collector.description && (
                        <div className="text-sm text-gray-500">{collector.description}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                        {collector.type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {collector.host}:{collector.http_port}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
                          collector.status
                        )}`}
                      >
                        {getStatusIcon(collector.status)}
                        <span className="ml-1">{collector.status}</span>
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {collector.metrics ? (
                        <div className="space-y-1">
                          <div>Received: {collector.metrics.total_received?.toLocaleString() || 0}</div>
                          <div>Sent: {collector.metrics.total_sent?.toLocaleString() || 0}</div>
                          {collector.metrics.errors !== undefined && collector.metrics.errors > 0 && (
                            <div className="text-red-600">Errors: {collector.metrics.errors}</div>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => setEditingCollector(collector)}
                          className="text-clarion-blue hover:text-clarion-blue-dark"
                        >
                          <Edit className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`Delete collector ${collector.name}?`)) {
                              deleteMutation.mutate(collector.collector_id)
                            }
                          }}
                          className="text-red-600 hover:text-red-900"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add/Edit Modal */}
      {(showAddModal || editingCollector) && (
        <CollectorModal
          collector={editingCollector || undefined}
          onClose={() => {
            setShowAddModal(false)
            setEditingCollector(null)
          }}
          onSave={(data) => {
            if (editingCollector) {
              updateMutation.mutate({ collectorId: editingCollector.collector_id, data })
            } else {
              createMutation.mutate(data as CollectorFormData)
            }
          }}
        />
      )}
    </div>
  )
}

function CollectorModal({
  collector,
  onClose,
  onSave,
}: {
  collector?: Collector
  onClose: () => void
  onSave: (data: Partial<CollectorFormData>) => void
}) {
  const [formData, setFormData] = useState<Partial<CollectorFormData>>({
    collector_id: collector?.collector_id || '',
    name: collector?.name || '',
    type: collector?.type || 'native',
    host: collector?.host || '',
    http_port: collector?.http_port || 8081,
    backend_url: collector?.backend_url || 'http://localhost:8000',
    netflow_port: collector?.netflow_port || 2055,
    ipfix_port: collector?.ipfix_port || 4739,
    batch_size: collector?.batch_size || 1000,
    batch_interval_seconds: collector?.batch_interval_seconds || 5.0,
    description: collector?.description || '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            {collector ? 'Edit Collector' : 'Add Collector'}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Collector ID</label>
              <input
                type="text"
                required
                disabled={!!collector}
                value={formData.collector_id}
                onChange={(e) => setFormData({ ...formData, collector_id: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Name</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Type</label>
              <select
                required
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value as 'native' | 'agent' })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
              >
                <option value="native">Native</option>
                <option value="agent">Agent</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Host</label>
              <input
                type="text"
                required
                value={formData.host}
                onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
                placeholder="localhost or IP address"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">HTTP Port</label>
              <input
                type="number"
                required
                value={formData.http_port}
                onChange={(e) => setFormData({ ...formData, http_port: parseInt(e.target.value) })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
              />
            </div>
            {formData.type === 'native' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700">NetFlow Port</label>
                  <input
                    type="number"
                    value={formData.netflow_port || ''}
                    onChange={(e) => setFormData({ ...formData, netflow_port: parseInt(e.target.value) || undefined })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">IPFIX Port</label>
                  <input
                    type="number"
                    value={formData.ipfix_port || ''}
                    onChange={(e) => setFormData({ ...formData, ipfix_port: parseInt(e.target.value) || undefined })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
                  />
                </div>
              </>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700">Description</label>
              <textarea
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
                rows={2}
              />
            </div>
            <div className="flex justify-end space-x-2 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-sm font-medium text-white bg-clarion-blue rounded-md hover:bg-clarion-blue-dark"
              >
                {collector ? 'Update' : 'Create'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
