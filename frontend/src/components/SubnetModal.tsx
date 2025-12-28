import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { X } from 'lucide-react'

interface Subnet {
  subnet_id: string
  name: string
  cidr: string
  address_space_id: string
  location_id?: string
  vlan_id?: number
  description?: string
}


interface SubnetModalProps {
  subnetId?: string | null
  onClose: () => void
}

export default function SubnetModal({ subnetId, onClose }: SubnetModalProps) {
  const queryClient = useQueryClient()
  const isEdit = !!subnetId

  const [formData, setFormData] = useState({
    subnet_id: '',
    name: '',
    cidr: '',
    address_space_id: '',
    location_id: '',
    vlan_id: '',
    description: '',
  })

  // Fetch data
  const { data: subnetsData } = useQuery({
    queryKey: ['topology', 'subnets'],
    queryFn: async () => {
      const response = await apiClient.getSubnets()
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

  const { data: addressSpacesData } = useQuery({
    queryKey: ['topology', 'address-spaces'],
    queryFn: async () => {
      const response = await apiClient.getAddressSpaces()
      // Return the full response data structure to match Topology page
      return response.data
    },
  })

  useEffect(() => {
    if (isEdit && subnetId && subnetsData) {
      // Extract subnets array from response data structure
      const subnets = Array.isArray(subnetsData?.subnets) ? subnetsData.subnets : []
      const subnet = subnets.find((s: Subnet) => s.subnet_id === subnetId)
      if (subnet) {
        setFormData({
          subnet_id: subnet.subnet_id,
          name: subnet.name,
          cidr: subnet.cidr,
          address_space_id: subnet.address_space_id,
          location_id: subnet.location_id || '',
          vlan_id: subnet.vlan_id?.toString() || '',
          description: subnet.description || '',
        })
      }
    }
  }, [isEdit, subnetId, subnetsData])

  const [error, setError] = useState<string | null>(null)

  const createMutation = useMutation({
    mutationFn: async (data: any) => {
      return apiClient.createSubnet(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topology', 'subnets'] })
      onClose()
    },
    onError: (err: any) => {
      const message = err?.response?.data?.detail || err?.message || 'Failed to create subnet'
      setError(message)
    },
  })

  const updateMutation = useMutation({
    mutationFn: async (data: any) => {
      return apiClient.updateSubnet(subnetId!, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topology', 'subnets'] })
      queryClient.invalidateQueries({ queryKey: ['subnet', subnetId] })
      onClose()
    },
    onError: (err: any) => {
      const message = err?.response?.data?.detail || err?.message || 'Failed to update subnet'
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

    if (!formData.address_space_id) {
      setError('Address Space is required')
      return
    }

    if (isEdit) {
      const submitData: any = {
        name: formData.name,
        cidr: formData.cidr,
        address_space_id: formData.address_space_id,
        location_id: formData.location_id,
        vlan_id: formData.vlan_id ? parseInt(formData.vlan_id) : undefined,
        description: formData.description || undefined,
      }
      updateMutation.mutate(submitData)
    } else {
      const submitData: any = {
        subnet_id: formData.subnet_id || `subnet-${Date.now()}`,
        name: formData.name,
        cidr: formData.cidr,
        address_space_id: formData.address_space_id,
        location_id: formData.location_id,
        vlan_id: formData.vlan_id ? parseInt(formData.vlan_id) : undefined,
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
            {isEdit ? 'Edit Subnet' : 'Create Subnet'}
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
              Subnet ID {!isEdit && <span className="text-red-500">*</span>}
            </label>
            <input
              type="text"
              value={formData.subnet_id}
              onChange={(e) => setFormData({ ...formData, subnet_id: e.target.value })}
              required={!isEdit}
              disabled={isEdit}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., bldg2-idf1-user"
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
              placeholder="e.g., Building 2 - IDF 1 - User Network"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              CIDR <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.cidr}
              onChange={(e) => setFormData({ ...formData, cidr: e.target.value })}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
              placeholder="e.g., 10.1.2.0/24"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Address Space <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.address_space_id}
                onChange={(e) => setFormData({ ...formData, address_space_id: e.target.value })}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select address space</option>
                {(Array.isArray(addressSpacesData?.address_spaces) ? addressSpacesData.address_spaces : []).map((space: { space_id: string; name: string; cidr: string }) => (
                  <option key={space.space_id} value={space.space_id}>
                    {space.name} ({space.cidr})
                  </option>
                ))}
              </select>
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
                {(Array.isArray(locationsData?.locations) ? locationsData.locations : []).map((loc: { location_id: string; name: string; type: string }) => (
                  <option key={loc.location_id} value={loc.location_id}>
                    {loc.name} ({loc.type})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              VLAN ID
            </label>
            <input
              type="number"
              value={formData.vlan_id}
              onChange={(e) => setFormData({ ...formData, vlan_id: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., 100"
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

