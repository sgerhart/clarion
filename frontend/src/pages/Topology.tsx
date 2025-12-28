import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import {
  Building2,
  MapPin,
  Network,
  Server,
  Plus,
  Edit2,
  Trash2,
  ChevronRight,
  ChevronDown,
} from 'lucide-react'
import LocationModal from '../components/LocationModal'
import AddressSpaceModal from '../components/AddressSpaceModal'
import SubnetModal from '../components/SubnetModal'
import SwitchModal from '../components/SwitchModal'

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

interface Subnet {
  subnet_id: string
  name: string
  cidr: string
  address_space_id: string
  location_id?: string
  vlan_id?: number
  description?: string
}

interface Switch {
  switch_id: string
  name: string
  location_id: string
  model?: string
  management_ip?: string
  serial_number?: string
  description?: string
}

export default function Topology() {
  const queryClient = useQueryClient()
  const [selectedTab, setSelectedTab] = useState<'locations' | 'address-spaces' | 'subnets' | 'switches'>('locations')
  const [expandedLocations, setExpandedLocations] = useState<Set<string>>(new Set())
  
  // Modal states
  const [locationModal, setLocationModal] = useState<{ open: boolean; locationId?: string | null; parentId?: string | null }>({ open: false })
  const [addressSpaceModal, setAddressSpaceModal] = useState<{ open: boolean; spaceId?: string | null }>({ open: false })
  const [subnetModal, setSubnetModal] = useState<{ open: boolean; subnetId?: string | null }>({ open: false })
  const [switchModal, setSwitchModal] = useState<{ open: boolean; switchId?: string | null }>({ open: false })

  // Fetch locations
  const { data: locationsData } = useQuery({
    queryKey: ['topology', 'locations'],
    queryFn: async () => {
      const response = await apiClient.getLocations()
      return response.data
    },
  })

  // Fetch address spaces
  const { data: addressSpacesData } = useQuery({
    queryKey: ['topology', 'address-spaces'],
    queryFn: async () => {
      const response = await apiClient.getAddressSpaces()
      return response.data
    },
  })

  // Fetch subnets
  const { data: subnetsData } = useQuery({
    queryKey: ['topology', 'subnets'],
    queryFn: async () => {
      const response = await apiClient.getSubnets()
      return response.data
    },
  })

  // Fetch switches
  const { data: switchesData } = useQuery({
    queryKey: ['topology', 'switches'],
    queryFn: async () => {
      const response = await apiClient.getSwitches()
      return response.data
    },
  })

  // Delete mutations
  const deleteAddressSpaceMutation = useMutation({
    mutationFn: async (spaceId: string) => {
      return apiClient.deleteAddressSpace(spaceId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topology', 'address-spaces'] })
    },
  })

  const deleteSubnetMutation = useMutation({
    mutationFn: async (subnetId: string) => {
      return apiClient.deleteSubnet(subnetId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topology', 'subnets'] })
    },
  })

  const deleteSwitchMutation = useMutation({
    mutationFn: async (switchId: string) => {
      return apiClient.deleteSwitch(switchId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topology', 'switches'] })
    },
  })

  const handleDeleteAddressSpace = (spaceId: string) => {
    if (window.confirm('Are you sure you want to delete this address space?')) {
      deleteAddressSpaceMutation.mutate(spaceId)
    }
  }

  const handleDeleteSubnet = (subnetId: string) => {
    if (window.confirm('Are you sure you want to delete this subnet?')) {
      deleteSubnetMutation.mutate(subnetId)
    }
  }

  const handleDeleteSwitch = (switchId: string) => {
    if (window.confirm('Are you sure you want to delete this switch?')) {
      deleteSwitchMutation.mutate(switchId)
    }
  }

  // Extract arrays from response data
  const locations = Array.isArray(locationsData?.locations) ? locationsData.locations : []
  const addressSpaces = Array.isArray(addressSpacesData?.address_spaces) ? addressSpacesData.address_spaces : []
  const subnets = Array.isArray(subnetsData?.subnets) ? subnetsData.subnets : []
  const switches = Array.isArray(switchesData?.switches) ? switchesData.switches : []

  // Build location tree
  const locationMap = new Map<string, Location>()
  locations.forEach((loc: Location) => locationMap.set(loc.location_id, loc))

  const rootLocations = locations.filter((loc: Location) => !loc.parent_id)
  const childMap = new Map<string, Location[]>()
  locations.forEach((loc: Location) => {
    if (loc.parent_id) {
      if (!childMap.has(loc.parent_id)) {
        childMap.set(loc.parent_id, [])
      }
      childMap.get(loc.parent_id)!.push(loc)
    }
  })

  const toggleLocation = (locationId: string) => {
    const newExpanded = new Set(expandedLocations)
    if (newExpanded.has(locationId)) {
      newExpanded.delete(locationId)
    } else {
      newExpanded.add(locationId)
    }
    setExpandedLocations(newExpanded)
  }

  const renderLocationTree = (location: Location, level: number = 0) => {
    const children = childMap.get(location.location_id) || []
    const isExpanded = expandedLocations.has(location.location_id)
    const locationSubnets = subnets.filter((s: Subnet) => s.location_id === location.location_id)
    const locationSwitches = switches.filter((s: Switch) => s.location_id === location.location_id)

    return (
      <div key={location.location_id} className="ml-4">
        <div
          className={`flex items-center py-2 px-3 rounded hover:bg-gray-50 cursor-pointer ${
            level === 0 ? 'font-semibold' : ''
          }`}
          style={{ marginLeft: `${level * 20}px` }}
        >
          {children.length > 0 && (
            <button
              onClick={() => toggleLocation(location.location_id)}
              className="mr-2 text-gray-400 hover:text-gray-600"
            >
              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>
          )}
          {children.length === 0 && <div className="w-6 mr-2" />}
          
          {location.type === 'CAMPUS' && <Building2 className="h-4 w-4 text-blue-500 mr-2" />}
          {location.type === 'BRANCH' && <MapPin className="h-4 w-4 text-green-500 mr-2" />}
          {location.type === 'REMOTE_SITE' && <MapPin className="h-4 w-4 text-orange-500 mr-2" />}
          {location.type === 'BUILDING' && <Building2 className="h-4 w-4 text-purple-500 mr-2" />}
          {location.type === 'IDF' && <Network className="h-4 w-4 text-gray-500 mr-2" />}
          {location.type === 'ROOM' && <MapPin className="h-4 w-4 text-gray-400 mr-2" />}
          
          <span className="flex-1">{location.name}</span>
          <span className="text-xs text-gray-500 mr-2">({location.type})</span>
          {locationSubnets.length > 0 && (
            <span className="text-xs text-blue-600 mr-2">{locationSubnets.length} subnets</span>
          )}
          {locationSwitches.length > 0 && (
            <span className="text-xs text-green-600 mr-2">{locationSwitches.length} switches</span>
          )}
          <button 
            onClick={() => setLocationModal({ open: true, locationId: location.location_id, parentId: location.parent_id || undefined })}
            className="text-gray-400 hover:text-blue-600 ml-2"
          >
            <Edit2 className="h-4 w-4" />
          </button>
        </div>
        
        {isExpanded && children.length > 0 && (
          <div className="ml-4">
            {children.map((child: Location) => renderLocationTree(child, level + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Network Topology</h1>
        {selectedTab === 'locations' && (
          <button 
            onClick={() => setLocationModal({ open: true, locationId: null, parentId: null })}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Location
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {(['locations', 'address-spaces', 'subnets', 'switches'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setSelectedTab(tab)}
                className={`px-6 py-3 text-sm font-medium border-b-2 ${
                  selectedTab === tab
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1).replace('-', ' ')}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <div className="bg-white rounded-lg shadow">
        {selectedTab === 'locations' && (
          <div className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Location Hierarchy</h2>
              <button 
                onClick={() => setLocationModal({ open: true, locationId: null, parentId: null })}
                className="text-sm text-blue-600 hover:text-blue-700 flex items-center"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Location
              </button>
            </div>
            
            {rootLocations.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <Building2 className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>No locations configured</p>
                <p className="text-sm mt-2">Start by adding a Campus or Branch location</p>
              </div>
            ) : (
              <div className="space-y-1">
                {rootLocations.map(loc => renderLocationTree(loc))}
              </div>
            )}
          </div>
        )}

        {selectedTab === 'address-spaces' && (
          <div className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Address Spaces</h2>
              <button 
                onClick={() => setAddressSpaceModal({ open: true, spaceId: null })}
                className="text-sm text-blue-600 hover:text-blue-700 flex items-center"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Address Space
              </button>
            </div>
            
            {addressSpaces.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <Network className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>No address spaces configured</p>
                <p className="text-sm mt-2">Add your internal IP address ranges (e.g., 10.0.0.0/8)</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">CIDR</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {addressSpaces.map((space) => (
                      <tr key={space.space_id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">{space.name}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">{space.cidr}</td>
                        <td className="px-6 py-4 text-sm text-gray-500">{space.description || '-'}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <button 
                            onClick={() => setAddressSpaceModal({ open: true, spaceId: space.space_id })}
                            className="text-blue-600 hover:text-blue-900 mr-4"
                          >
                            <Edit2 className="h-4 w-4" />
                          </button>
                          <button 
                            onClick={() => handleDeleteAddressSpace(space.space_id)}
                            className="text-red-600 hover:text-red-900"
                            disabled={deleteAddressSpaceMutation.isPending}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {selectedTab === 'subnets' && (
          <div className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Subnets</h2>
              <button 
                onClick={() => setSubnetModal({ open: true, subnetId: null })}
                className="text-sm text-blue-600 hover:text-blue-700 flex items-center"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Subnet
              </button>
            </div>
            
            {subnets.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <Network className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>No subnets configured</p>
                <p className="text-sm mt-2">Add network segments and associate them with locations</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">CIDR</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">VLAN</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {subnets.map((subnet) => {
                      const location = locationMap.get(subnet.location_id || '')
                      return (
                        <tr key={subnet.subnet_id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">{subnet.name}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">{subnet.cidr}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {location ? location.name : '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {subnet.vlan_id ? `VLAN ${subnet.vlan_id}` : '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <button 
                              onClick={() => setSubnetModal({ open: true, subnetId: subnet.subnet_id })}
                              className="text-blue-600 hover:text-blue-900 mr-4"
                            >
                              <Edit2 className="h-4 w-4" />
                            </button>
                            <button 
                              onClick={() => handleDeleteSubnet(subnet.subnet_id)}
                              className="text-red-600 hover:text-red-900"
                              disabled={deleteSubnetMutation.isPending}
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {selectedTab === 'switches' && (
          <div className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Switches</h2>
              <button 
                onClick={() => setSwitchModal({ open: true, switchId: null })}
                className="text-sm text-blue-600 hover:text-blue-700 flex items-center"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Switch
              </button>
            </div>
            
            {switches.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <Server className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>No switches configured</p>
                <p className="text-sm mt-2">Add network switches and associate them with locations</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Switch ID</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Management IP</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {switches.map((sw) => {
                      const location = locationMap.get(sw.location_id)
                      return (
                        <tr key={sw.switch_id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">{sw.name}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">{sw.switch_id}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {location ? location.name : '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{sw.model || '-'}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                            {sw.management_ip || '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <button 
                              onClick={() => setSwitchModal({ open: true, switchId: sw.switch_id })}
                              className="text-blue-600 hover:text-blue-900 mr-4"
                            >
                              <Edit2 className="h-4 w-4" />
                            </button>
                            <button 
                              onClick={() => handleDeleteSwitch(sw.switch_id)}
                              className="text-red-600 hover:text-red-900"
                              disabled={deleteSwitchMutation.isPending}
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modals */}
      {locationModal.open && (
        <LocationModal
          locationId={locationModal.locationId}
          parentId={locationModal.parentId}
          onClose={() => setLocationModal({ open: false })}
        />
      )}
      {addressSpaceModal.open && (
        <AddressSpaceModal
          spaceId={addressSpaceModal.spaceId}
          onClose={() => setAddressSpaceModal({ open: false })}
        />
      )}
      {subnetModal.open && (
        <SubnetModal
          subnetId={subnetModal.subnetId}
          onClose={() => setSubnetModal({ open: false })}
        />
      )}
      {switchModal.open && (
        <SwitchModal
          switchId={switchModal.switchId}
          onClose={() => setSwitchModal({ open: false })}
        />
      )}
    </div>
  )
}
