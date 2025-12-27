import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { X } from 'lucide-react'

interface AddressSpace {
  space_id: string
  name: string
  cidr: string
  description?: string
}

interface AddressSpaceModalProps {
  spaceId?: string | null
  onClose: () => void
}

export default function AddressSpaceModal({ spaceId, onClose }: AddressSpaceModalProps) {
  const queryClient = useQueryClient()
  const isEdit = !!spaceId

  const [formData, setFormData] = useState({
    space_id: '',
    name: '',
    cidr: '',
    description: '',
  })

  // Fetch address space data if editing
  const { data: spacesData } = useQuery({
    queryKey: ['topology', 'address-spaces'],
    queryFn: async () => {
      const response = await apiClient.getAddressSpaces()
      // Return the full response data structure to match Topology page
      return response.data
    },
  })

  useEffect(() => {
    if (isEdit && spaceId && spacesData) {
      const addressSpaces = Array.isArray(spacesData?.address_spaces) ? spacesData.address_spaces : []
      const space = addressSpaces.find(s => s.space_id === spaceId)
      if (space) {
        setFormData({
          space_id: space.space_id,
          name: space.name,
          cidr: space.cidr,
          description: space.description || '',
        })
      }
    }
  }, [isEdit, spaceId, spacesData])

  const createMutation = useMutation({
    mutationFn: async (data: any) => {
      return apiClient.createAddressSpace(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topology', 'address-spaces'] })
      onClose()
    },
  })

  const updateMutation = useMutation({
    mutationFn: async (data: any) => {
      return apiClient.updateAddressSpace(spaceId!, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topology', 'address-spaces'] })
      onClose()
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (isEdit) {
      const submitData = {
        name: formData.name,
        cidr: formData.cidr,
        description: formData.description || undefined,
      }
      updateMutation.mutate(submitData)
    } else {
      const submitData = {
        space_id: formData.space_id || `space-${Date.now()}`,
        name: formData.name,
        cidr: formData.cidr,
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
            {isEdit ? 'Edit Address Space' : 'Create Address Space'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {!isEdit && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Space ID <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.space_id}
                onChange={(e) => setFormData({ ...formData, space_id: e.target.value })}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., corp-network"
              />
            </div>
          )}

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
              placeholder="e.g., Corporate Network"
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
              placeholder="e.g., 10.0.0.0/8"
            />
            <p className="mt-1 text-xs text-gray-500">
              Enter IP address range in CIDR notation (e.g., 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
            </p>
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
              placeholder="Optional description of this address space"
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
              {(createMutation.isPending || updateMutation.isPending) ? 'Saving...' : isEdit ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

