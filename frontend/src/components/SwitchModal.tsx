import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { X } from 'lucide-react'

interface Switch {
  switch_id: string
  name: string
  location_id: string
  model?: string
  management_ip?: string
  serial_number?: string
  description?: string
}

interface Location {
  location_id: string
  name: string
  type: string
}

interface SwitchModalProps {
  switchId?: string | null
  onClose: () => void
}

export default function SwitchModal({ switchId, onClose }: SwitchModalProps) {
  const queryClient = useQueryClient()
  const isEdit = !!switchId

  const [formData, setFormData] = useState({
    switch_id: '',
    name: '',
    location_id: '',
    model: '',
    management_ip: '',
    serial_number: '',
    description: '',
  })

  // Fetch data
  const { data: switchesData } = useQuery({
    queryKey: ['topology', 'switches'],
    queryFn: async () => {
      const response = await apiClient.getSwitches()
      // Return the full response data structure to match Topology page
      return response.data
    },
  })

  const { data: locationsData } = useQuery({
    queryKey: ['topology', 'locations'],
    queryFn: async () => {
      const response = await apiClient.getLocations()
      // Return the full response data structure to match Topology page
      return response.data
    },
  })

  useEffect(() => {
    if (isEdit && switchId && switchesData) {
      // Extract switches array from response data structure
      const switches = Array.isArray(switchesData?.switches) ? switchesData.switches : []
      const sw = switches.find(s => s.switch_id === switchId)
      if (sw) {
        setFormData({
          switch_id: sw.switch_id,
          name: sw.name,
          location_id: sw.location_id,
          model: sw.model || '',
          management_ip: sw.management_ip || '',
          serial_number: sw.serial_number || '',
          description: sw.description || '',
        })
      }
    }
  }, [isEdit, switchId, switchesData])

  const [error, setError] = useState<string | null>(null)

  const createMutation = useMutation({
    mutationFn: async (data: any) => {
      return apiClient.createSwitch(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topology', 'switches'] })
      onClose()
    },
    onError: (err: any) => {
      const message = err?.response?.data?.detail || err?.message || 'Failed to create switch'
      setError(message)
    },
  })

  const updateMutation = useMutation({
    mutationFn: async (data: any) => {
      return apiClient.updateSwitch(switchId!, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topology', 'switches'] })
      queryClient.invalidateQueries({ queryKey: ['switch', switchId] })
      onClose()
    },
    onError: (err: any) => {
      const message = err?.response?.data?.detail || err?.message || 'Failed to update switch'
      setError(message)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!formData.location_id) {
      setError('Location is required')
      return
    }

    if (isEdit) {
      const submitData: any = {
        name: formData.name,
        location_id: formData.location_id,
        model: formData.model || undefined,
        management_ip: formData.management_ip || undefined,
        serial_number: formData.serial_number || undefined,
        description: formData.description || undefined,
      }
      updateMutation.mutate(submitData)
    } else {
      const submitData: any = {
        switch_id: formData.switch_id || `switch-${Date.now()}`,
        name: formData.name,
        location_id: formData.location_id,
        model: formData.model || undefined,
        management_ip: formData.management_ip || undefined,
        serial_number: formData.serial_number || undefined,
        description: formData.description || undefined,
      }
      createMutation.mutate(submitData)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">
            {isEdit ? 'Edit Switch' : 'Create Switch'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Switch ID {!isEdit && <span className="text-red-500">*</span>}
            </label>
            <input
              type="text"
              value={formData.switch_id}
              onChange={(e) => setFormData({ ...formData, switch_id: e.target.value })}
              required={!isEdit}
              disabled={isEdit}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., SW001"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., switch-bldg2-idf1"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Location <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.location_id}
              onChange={(e) => setFormData({ ...formData, location_id: e.target.value })}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select location</option>
              {(Array.isArray(locationsData?.locations) ? locationsData.locations : []).map((loc) => (
                <option key={loc.location_id} value={loc.location_id}>
                  {loc.name} ({loc.type})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Model
              </label>
              <input
                type="text"
                value={formData.model}
                onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Catalyst 9300"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Management IP
              </label>
              <input
                type="text"
                value={formData.management_ip}
                onChange={(e) => setFormData({ ...formData, management_ip: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                placeholder="e.g., 10.1.2.1"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Serial Number
            </label>
            <input
              type="text"
              value={formData.serial_number}
              onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Optional serial number"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Optional description"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending || updateMutation.isPending
                ? 'Saving...'
                : isEdit
                ? 'Update'
                : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

