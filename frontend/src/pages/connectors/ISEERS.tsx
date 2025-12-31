import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../lib/api'
import { 
  Loader2, AlertCircle, CheckCircle2, XCircle, Save, RefreshCw
} from 'lucide-react'
import type { Connector } from '../Connectors'

export default function ISEERSConnector() {
  // Route path is /connectors/ise-ers, so we know the connector ID
  const actualConnectorId = 'ise_ers'
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
    ise_url: '',
    ise_username: '',
    ise_password: '',
    verify_ssl: false,
  })

  // Initialize form from connector config
  useEffect(() => {
    if (connector?.config) {
      setFormData({
        ise_url: connector.config.ise_url || '',
        ise_username: connector.config.ise_username || '',
        ise_password: '', // Don't populate password
        verify_ssl: connector.config.verify_ssl === true,
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

  // Sync ISE config mutation
  const syncMutation = useMutation({
    mutationFn: async () => {
      return apiClient.syncIseConfig({
        ise_url: formData.ise_url,
        ise_username: formData.ise_username,
        ise_password: formData.ise_password,
        verify_ssl: formData.verify_ssl,
      })
    },
    onSuccess: (data) => {
      alert(`ISE configuration synced successfully! SGTs: ${data.data.sgts_synced}, Profiles: ${data.data.profiles_synced}, Policies: ${data.data.policies_synced}`)
    },
    onError: (error: any) => {
      alert(`Error syncing ISE configuration: ${error.response?.data?.detail || error.message}`)
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
          <h2 className="text-2xl font-semibold mb-2">ISE ERS API Connector</h2>
          <p className="text-sm text-gray-600">
            Configure Cisco ISE ERS API for policy deployment and configuration sync
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
              ISE URL *
            </label>
            <input
              type="text"
              value={formData.ise_url}
              onChange={(e) => setFormData({ ...formData, ise_url: e.target.value })}
              placeholder="https://192.168.10.31"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              required
            />
            <p className="text-xs text-gray-500 mt-1">ISE server URL (port optional, defaults to 443 for HTTPS). Example: https://ise.example.com</p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Username *
            </label>
            <input
              type="text"
              value={formData.ise_username}
              onChange={(e) => setFormData({ ...formData, ise_username: e.target.value })}
              placeholder="admin"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Password *
            </label>
            <input
              type="password"
              value={formData.ise_password}
              onChange={(e) => setFormData({ ...formData, ise_password: e.target.value })}
              placeholder="••••••••"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
          
          <div>
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
        
        <div className="flex space-x-3 mt-6">
          <button
            onClick={() => configureMutation.mutate()}
            disabled={configureMutation.isPending || !formData.ise_url || !formData.ise_username || !formData.ise_password}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {configureMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            <span>Save Configuration</span>
          </button>
          
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending || !formData.ise_url || !formData.ise_username || !formData.ise_password}
            className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
          >
            {syncMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            <span>Sync ISE Configuration</span>
          </button>
        </div>
        
        {syncMutation.isSuccess && (
          <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center space-x-2 text-green-800">
              <CheckCircle2 className="h-5 w-5" />
              <span>ISE configuration synced successfully!</span>
            </div>
          </div>
        )}
        
        {syncMutation.isError && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center space-x-2 text-red-800">
              <XCircle className="h-5 w-5" />
              <span>Error syncing ISE configuration. Check credentials and network.</span>
            </div>
          </div>
        )}
      </div>

      {/* Information */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-semibold mb-2">About ISE ERS API Connector</h3>
        <div className="text-sm text-gray-600 space-y-2">
          <p>
            The ISE ERS API connector allows Clarion to:
          </p>
          <ul className="list-disc list-inside space-y-1 ml-4">
            <li>Sync existing ISE TrustSec configuration (SGTs, Authorization Profiles, Policies)</li>
            <li>Deploy policy recommendations directly to ISE</li>
            <li>Support brownfield deployments by understanding existing ISE configuration</li>
          </ul>
          <p className="mt-2">
            <strong>Note:</strong> This connector runs in the main API service and does not require a separate container.
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

