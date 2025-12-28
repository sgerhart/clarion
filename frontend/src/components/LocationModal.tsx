import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { X } from 'lucide-react'

interface Location {
  location_id: string
  name: string
  type: string
  parent_id?: string
  address?: string
  latitude?: number
  longitude?: number
  site_type?: string
  contact_name?: string
  contact_phone?: string
  contact_email?: string
  timezone?: string
  metadata?: Record<string, any>
}

interface LocationModalProps {
  locationId?: string | null
  parentId?: string | null
  onClose: () => void
}

export default function LocationModal({ locationId, parentId, onClose }: LocationModalProps) {
  const queryClient = useQueryClient()
  const isEdit = !!locationId

  const [formData, setFormData] = useState({
    location_id: '',
    name: '',
    type: 'CAMPUS',
    parent_id: parentId || '',
    address: '',
    latitude: '',
    longitude: '',
    site_type: '',
    contact_name: '',
    contact_phone: '',
    contact_email: '',
    timezone: '',
  })

  // Fetch location data if editing
  const { data: locationData } = useQuery({
    queryKey: ['location', locationId],
    queryFn: async () => {
      if (!locationId) return null
      const response = await apiClient.getLocation(locationId)
      return response.data.location as Location
    },
    enabled: isEdit && !!locationId,
  })

  // Initialize form when location data loads
  useEffect(() => {
    if (locationData) {
      setFormData({
        location_id: locationData.location_id,
        name: locationData.name,
        type: locationData.type,
        parent_id: locationData.parent_id || '',
        address: locationData.address || '',
        latitude: locationData.latitude?.toString() || '',
        longitude: locationData.longitude?.toString() || '',
        site_type: locationData.site_type || '',
        contact_name: locationData.contact_name || '',
        contact_phone: locationData.contact_phone || '',
        contact_email: locationData.contact_email || '',
        timezone: locationData.timezone || '',
      })
    } else if (!isEdit) {
      // Set default parent_id for new locations
      if (parentId) {
        setFormData(prev => ({ ...prev, parent_id: parentId }))
      }
    }
  }, [locationData, isEdit, parentId])

  // Fetch available parent locations
  const { data: locationsData } = useQuery({
    queryKey: ['topology', 'locations'],
    queryFn: async () => {
      const response = await apiClient.getLocations()
      // Return the full response data structure to match Topology page
      return response.data
    },
  })

  const [error, setError] = useState<string | null>(null)

  const createMutation = useMutation({
    mutationFn: async (data: any) => {
      return apiClient.createLocation(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topology', 'locations'] })
      queryClient.invalidateQueries({ queryKey: ['topology', 'hierarchy'] })
      onClose()
    },
    onError: (err: any) => {
      const message = err?.response?.data?.detail || err?.message || 'Failed to create location'
      setError(message)
    },
  })

  const updateMutation = useMutation({
    mutationFn: async (data: any) => {
      return apiClient.updateLocation(locationId!, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topology', 'locations'] })
      queryClient.invalidateQueries({ queryKey: ['location', locationId] })
      queryClient.invalidateQueries({ queryKey: ['topology', 'hierarchy'] })
      onClose()
    },
    onError: (err: any) => {
      const message = err?.response?.data?.detail || err?.message || 'Failed to update location'
      setError(message)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const submitData: any = {
      location_id: formData.location_id || `loc-${Date.now()}`,
      name: formData.name,
      type: formData.type,
      address: formData.address || undefined,
      site_type: formData.site_type || undefined,
      contact_name: formData.contact_name || undefined,
      contact_phone: formData.contact_phone || undefined,
      contact_email: formData.contact_email || undefined,
      timezone: formData.timezone || undefined,
    }

    if (formData.parent_id) {
      submitData.parent_id = formData.parent_id
    }

    if (formData.latitude) {
      submitData.latitude = parseFloat(formData.latitude)
    }

    if (formData.longitude) {
      submitData.longitude = parseFloat(formData.longitude)
    }

    if (isEdit) {
      updateMutation.mutate(submitData)
    } else {
      createMutation.mutate(submitData)
    }
  }

  // Extract locations array from response data structure
  const locations = Array.isArray(locationsData?.locations) ? locationsData.locations : []
  
  const availableParents = locations.filter((loc: Location) => 
    loc.location_id !== locationId && 
    (formData.type === 'BUILDING' ? loc.type === 'CAMPUS' :
     formData.type === 'IDF' ? loc.type === 'BUILDING' :
     formData.type === 'ROOM' ? ['IDF', 'BUILDING'].includes(loc.type) :
     !loc.parent_id) // For top-level locations, only show other top-level
  )

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">
            {isEdit ? 'Edit Location' : 'Create Location'}
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
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Location ID {!isEdit && <span className="text-red-500">*</span>}
              </label>
              <input
                type="text"
                value={formData.location_id}
                onChange={(e) => setFormData({ ...formData, location_id: e.target.value })}
                required={!isEdit}
                disabled={isEdit}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., campus-main"
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
                placeholder="e.g., Main Campus"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Type <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="CAMPUS">Campus</option>
                <option value="BRANCH">Branch</option>
                <option value="REMOTE_SITE">Remote Site</option>
                <option value="BUILDING">Building</option>
                <option value="IDF">IDF</option>
                <option value="ROOM">Room</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Parent Location
              </label>
              <select
                value={formData.parent_id}
                onChange={(e) => setFormData({ ...formData, parent_id: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">None (Top Level)</option>
                {availableParents.map((loc: Location) => (
                  <option key={loc.location_id} value={loc.location_id}>
                    {loc.name} ({loc.type})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Address
            </label>
            <input
              type="text"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="123 Main St, City, State ZIP"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Latitude
              </label>
              <input
                type="number"
                step="any"
                value={formData.latitude}
                onChange={(e) => setFormData({ ...formData, latitude: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="40.7128"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Longitude
              </label>
              <input
                type="number"
                step="any"
                value={formData.longitude}
                onChange={(e) => setFormData({ ...formData, longitude: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="-74.0060"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Site Type
            </label>
            <input
              type="text"
              value={formData.site_type}
              onChange={(e) => setFormData({ ...formData, site_type: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., HEADQUARTERS, BRANCH_OFFICE, WAREHOUSE"
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contact Name
              </label>
              <input
                type="text"
                value={formData.contact_name}
                onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contact Phone
              </label>
              <input
                type="text"
                value={formData.contact_phone}
                onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contact Email
              </label>
              <input
                type="email"
                value={formData.contact_email}
                onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Timezone
            </label>
            <input
              type="text"
              value={formData.timezone}
              onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., America/New_York"
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

