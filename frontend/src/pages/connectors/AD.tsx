import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../lib/api'
import { 
  Loader2, AlertCircle, Save
} from 'lucide-react'
import type { Connector } from '../Connectors'

export default function ADConnector() {
  // Route path is /connectors/ad, so we know the connector ID
  const actualConnectorId = 'ad'
  const queryClient = useQueryClient()
  
  // Fetch connector data
  const { data: connector, isLoading, error } = useQuery({
    queryKey: ['connector', actualConnectorId],
    queryFn: async () => {
      const response = await apiClient.getConnector(actualConnectorId)
      return response.data as Connector
    },
  })

  // Form state
  const [formData, setFormData] = useState({
    domain_controller: '',
    port: 389,
    base_dn: '',
    bind_dn: '',
    bind_password: '',
    use_ssl: false,
    verify_ssl: false,
    sync_schedule: '*/30 * * * *', // Every 30 minutes
    sync_user_details: true,
    sync_ad_groups: true,
    sync_computer_objects: true,
  })

  // Initialize form from connector config
  useEffect(() => {
    if (connector?.config) {
      setFormData({
        domain_controller: connector.config.domain_controller || '',
        port: connector.config.port || 389,
        base_dn: connector.config.base_dn || '',
        bind_dn: connector.config.bind_dn || '',
        bind_password: '', // Don't populate password
        use_ssl: connector.config.use_ssl === true,
        verify_ssl: connector.config.verify_ssl === true,
        sync_schedule: connector.config.sync_schedule || '*/30 * * * *',
        sync_user_details: connector.config.sync_user_details !== false,
        sync_ad_groups: connector.config.sync_ad_groups !== false,
        sync_computer_objects: connector.config.sync_computer_objects !== false,
      })
    }
  }, [connector])

  // Configure connector mutation
  const configureMutation = useMutation({
    mutationFn: async () => {
      return apiClient.configureConnector(actualConnectorId, formData, false)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connector', actualConnectorId] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      alert('Configuration saved successfully')
    },
    onError: (error: any) => {
      alert(`Error saving configuration: ${error.response?.data?.detail || error.message}`)
    },
  })

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'connected':
        return 'bg-green-500'
      case 'enabled':
        return 'bg-blue-500'
      case 'error':
        return 'bg-red-500'
      default:
        return 'bg-gray-300'
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        <span className="ml-2 text-gray-600">Loading connector...</span>
      </div>
    )
  }

  if (error || !connector) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center space-x-2 text-red-800">
          <AlertCircle className="h-5 w-5" />
          <span>Error loading connector: {error ? (error as any).message : 'Connector not found'}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold mb-2">Active Directory Connector</h2>
          <p className="text-sm text-gray-600">
            Configure LDAP connection for user, group, and device information sync
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={`h-3 w-3 rounded-full ${getStatusColor(connector.status)}`} />
            <span className="text-sm font-medium capitalize">{connector.status || 'disabled'}</span>
          </div>
        </div>
      </div>

      {/* Configuration Form */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-semibold mb-4">Connection Settings</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Domain Controller Hostname / IP *
            </label>
            <input
              type="text"
              value={formData.domain_controller}
              onChange={(e) => setFormData({ ...formData, domain_controller: e.target.value })}
              placeholder="dc.example.com or 192.168.1.10"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Port *
            </label>
            <input
              type="number"
              value={formData.port}
              onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) || 389 })}
              placeholder={formData.use_ssl ? "636" : "389"}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              required
            />
            <p className="text-xs text-gray-500 mt-1">389 for LDAP, 636 for LDAPS</p>
          </div>
          
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Base DN *
            </label>
            <input
              type="text"
              value={formData.base_dn}
              onChange={(e) => setFormData({ ...formData, base_dn: e.target.value })}
              placeholder="DC=example,DC=com"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Bind DN (Service Account) *
            </label>
            <input
              type="text"
              value={formData.bind_dn}
              onChange={(e) => setFormData({ ...formData, bind_dn: e.target.value })}
              placeholder="CN=service-account,CN=Users,DC=example,DC=com"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Bind Password *
            </label>
            <input
              type="password"
              value={formData.bind_password}
              onChange={(e) => setFormData({ ...formData, bind_password: e.target.value })}
              placeholder="••••••••"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
          
          <div className="md:col-span-2 space-y-2">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={formData.use_ssl}
                onChange={(e) => setFormData({ ...formData, use_ssl: e.target.checked, port: e.target.checked ? 636 : 389 })}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Use SSL/TLS (LDAPS)</span>
            </label>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={formData.verify_ssl}
                onChange={(e) => setFormData({ ...formData, verify_ssl: e.target.checked })}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Verify SSL Certificate</span>
            </label>
          </div>
        </div>
        
        {/* Sync Settings */}
        <div className="border-t pt-6 mt-6">
          <h3 className="text-lg font-semibold mb-4">Sync Settings</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sync Schedule (Cron Expression)
              </label>
              <input
                type="text"
                value={formData.sync_schedule}
                onChange={(e) => setFormData({ ...formData, sync_schedule: e.target.value })}
                placeholder="*/30 * * * *"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">Examples: */30 * * * * (every 30 min), 0 * * * * (hourly)</p>
            </div>
            
            <div className="space-y-2">
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={formData.sync_user_details}
                  onChange={(e) => setFormData({ ...formData, sync_user_details: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Sync User Details</span>
              </label>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={formData.sync_ad_groups}
                  onChange={(e) => setFormData({ ...formData, sync_ad_groups: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Sync AD Groups</span>
              </label>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={formData.sync_computer_objects}
                  onChange={(e) => setFormData({ ...formData, sync_computer_objects: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Sync Computer Objects</span>
              </label>
            </div>
          </div>
        </div>
        
        <div className="flex space-x-3 mt-6">
          <button
            onClick={() => configureMutation.mutate()}
            disabled={configureMutation.isPending || !formData.domain_controller || !formData.base_dn || !formData.bind_dn || !formData.bind_password}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {configureMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            <span>Save Configuration</span>
          </button>
        </div>
      </div>

      {/* Information */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-semibold mb-2">About AD Connector</h3>
        <div className="text-sm text-gray-600 space-y-2">
          <p>
            The Active Directory connector allows Clarion to:
          </p>
          <ul className="list-disc list-inside space-y-1 ml-4">
            <li>Sync user details (email, department, title, display name)</li>
            <li>Sync AD group memberships</li>
            <li>Map devices to users via computer objects</li>
            <li>Enrich user database with organizational information</li>
          </ul>
          <p className="mt-2">
            <strong>Note:</strong> This connector runs in the main API service and does not require a separate container. LDAP queries are performed on a schedule.
          </p>
        </div>
      </div>

      {/* Status Information */}
      {connector.last_error && (
        <div className="border-t pt-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start space-x-2">
              <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
              <div>
                <h4 className="font-medium text-red-800">Last Error</h4>
                <p className="text-sm text-red-600 mt-1">{connector.last_error}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
