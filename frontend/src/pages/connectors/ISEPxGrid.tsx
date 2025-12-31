import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../lib/api'
import api from '../../lib/api'
import { 
  Loader2, AlertCircle, CheckCircle2, XCircle, Save, Power, 
  Upload, Trash2, Shield, Key, FileText 
} from 'lucide-react'
import type { Connector } from '../Connectors'

export default function ISEPxGridConnector() {
  // Route path is /connectors/ise-pxgrid, so we know the connector ID
  const actualConnectorId = 'ise_pxgrid'
  const queryClient = useQueryClient()
  
  // Fetch connector data
  const { data: connector, isLoading, error } = useQuery({
    queryKey: ['connector', actualConnectorId],
    queryFn: async () => {
      const response = await apiClient.getConnector(actualConnectorId)
      return response.data as Connector
    },
    refetchInterval: 10000, // Refetch every 10 seconds for status updates
  })

  // Form state
  const [formData, setFormData] = useState({
    ise_hostname: '',
    username: '',
    password: '',
    client_name: 'clarion-pxgrid-client',
    port: 8910,
    use_ssl: true,
    verify_ssl: false,
  })

  // Initialize form from connector config
  useEffect(() => {
    if (connector?.config) {
      setFormData({
        ise_hostname: connector.config.ise_hostname || '',
        username: connector.config.username || '',
        password: '', // Don't populate password
        client_name: connector.config.client_name || 'clarion-pxgrid-client',
        port: connector.config.port || 8910,
        use_ssl: connector.config.use_ssl !== false,
        verify_ssl: connector.config.verify_ssl === true,
      })
    }
  }, [connector])

  // Certificate upload state
  const [certFiles, setCertFiles] = useState<{ [key: string]: File | null }>({
    client_cert: null,
    client_key: null,
    ca_cert: null,
  })

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

  // Enable connector mutation
  const enableMutation = useMutation({
    mutationFn: async () => {
      return apiClient.enableConnector(actualConnectorId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connector', actualConnectorId] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      alert('Connector enabled. Container is starting...')
    },
    onError: (error: any) => {
      alert(`Error enabling connector: ${error.response?.data?.detail || error.message}`)
    },
  })

  // Disable connector mutation
  const disableMutation = useMutation({
    mutationFn: async () => {
      return apiClient.disableConnector(actualConnectorId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connector', actualConnectorId] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      alert('Connector disabled. Container stopped.')
    },
    onError: (error: any) => {
      alert(`Error disabling connector: ${error.response?.data?.detail || error.message}`)
    },
  })

  // Test connection mutation
  const testConnectionMutation = useMutation({
    mutationFn: async () => {
      // Use direct API call to pxGrid test connection endpoint
      return api.post('/pxgrid/test-connection', {
        ise_hostname: formData.ise_hostname,
        username: formData.username,
        password: formData.password,
        client_name: formData.client_name,
        use_ssl: formData.use_ssl,
        verify_ssl: formData.verify_ssl,
        port: formData.port,
      })
    },
  })

  // Certificate upload mutations
  const uploadCertMutation = useMutation({
    mutationFn: async ({ certType, file }: { certType: string; file: File }) => {
      return apiClient.uploadCertificate(actualConnectorId, certType, file)
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['connector', actualConnectorId] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      alert('Certificate uploaded successfully')
      // Clear the file input
      setCertFiles({ ...certFiles, [variables.certType]: null })
    },
    onError: (error: any) => {
      alert(`Error uploading certificate: ${error.response?.data?.detail || error.message}`)
    },
  })

  const handleCertUpload = (certType: string) => {
    const file = certFiles[certType]
    if (file) {
      uploadCertMutation.mutate({ certType, file })
    }
  }

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'connected':
        return 'bg-green-500'
      case 'enabled':
        return 'bg-blue-500'
      case 'error':
        return 'bg-red-500'
      case 'connecting':
        return 'bg-yellow-500'
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
          <h2 className="text-2xl font-semibold mb-2">ISE pxGrid Connector</h2>
          <p className="text-sm text-gray-600">
            Configure Cisco ISE pxGrid connection for real-time session and endpoint events
          </p>
        </div>
        <div className="flex items-center space-x-4">
          {/* Status indicator */}
          <div className="flex items-center space-x-2">
            <div className={`h-3 w-3 rounded-full ${getStatusColor(connector.status)}`} />
            <span className="text-sm font-medium capitalize">{connector.status || 'disabled'}</span>
          </div>
          
          {/* Enable/Disable toggle */}
          {connector.enabled ? (
            <button
              onClick={() => disableMutation.mutate()}
              disabled={disableMutation.isPending}
              className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
            >
              {disableMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Power className="h-4 w-4" />
              )}
              <span>Disable</span>
            </button>
          ) : (
            <button
              onClick={() => enableMutation.mutate()}
              disabled={enableMutation.isPending || !connector.config}
              className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
            >
              {enableMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Power className="h-4 w-4" />
              )}
              <span>Enable</span>
            </button>
          )}
        </div>
      </div>

      {/* Configuration Form */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-semibold mb-4">Connection Settings</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              ISE Hostname / IP *
            </label>
            <input
              type="text"
              value={formData.ise_hostname}
              onChange={(e) => setFormData({ ...formData, ise_hostname: e.target.value })}
              placeholder="192.168.10.31"
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
              onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) || 8910 })}
              placeholder="8910"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Username *
            </label>
            <input
              type="text"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              placeholder="pxgrid-admin"
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
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              placeholder="••••••••"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Client Name *
            </label>
            <input
              type="text"
              value={formData.client_name}
              onChange={(e) => setFormData({ ...formData, client_name: e.target.value })}
              placeholder="clarion-pxgrid-client"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
          
          <div className="space-y-2">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={formData.use_ssl}
                onChange={(e) => setFormData({ ...formData, use_ssl: e.target.checked })}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Use SSL/TLS</span>
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
        
        <div className="flex space-x-3 mt-6">
          <button
            onClick={() => configureMutation.mutate()}
            disabled={configureMutation.isPending || !formData.ise_hostname || !formData.username || !formData.password}
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
            onClick={() => testConnectionMutation.mutate()}
            disabled={testConnectionMutation.isPending || !formData.ise_hostname || !formData.username || !formData.password}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50"
          >
            {testConnectionMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin inline mr-2" />
            ) : null}
            Test Connection
          </button>
          
          {testConnectionMutation.isSuccess && (
            <div className="flex items-center space-x-2 text-green-600">
              <CheckCircle2 className="h-5 w-5" />
              <span>Connection successful!</span>
            </div>
          )}
          
          {testConnectionMutation.isError && (
            <div className="flex items-center space-x-2 text-red-600">
              <XCircle className="h-5 w-5" />
              <span>Connection failed. Check credentials and network.</span>
            </div>
          )}
        </div>
      </div>

      {/* Certificate Management */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <Shield className="h-5 w-5 mr-2" />
          Certificates (Optional - for certificate-based authentication)
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Upload certificates for certificate-based pxGrid authentication. Required for production deployments.
        </p>
        
        <div className="space-y-4">
          {(['client_cert', 'client_key', 'ca_cert'] as const).map((certType) => {
            const hasCert = connector.certificates?.[`has_${certType}` as keyof typeof connector.certificates] || false
            const certLabels: { [key: string]: { label: string; icon: any } } = {
              client_cert: { label: 'Client Certificate', icon: FileText },
              client_key: { label: 'Client Private Key', icon: Key },
              ca_cert: { label: 'CA Certificate', icon: Shield },
            }
            const { label, icon: Icon } = certLabels[certType] || { label: certType, icon: FileText }
            
            return (
              <div key={certType} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <Icon className="h-5 w-5 text-gray-600" />
                    <span className="font-medium">{label}</span>
                    {hasCert && (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    )}
                  </div>
                </div>
                
                {hasCert ? (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-green-600">Certificate uploaded</span>
                    <button
                      onClick={async () => {
                        if (confirm(`Delete ${label}?`)) {
                          try {
                            await apiClient.deleteCertificate(actualConnectorId, certType)
                            queryClient.invalidateQueries({ queryKey: ['connector', actualConnectorId] })
                            alert('Certificate deleted')
                          } catch (error: any) {
                            alert(`Error deleting certificate: ${error.response?.data?.detail || error.message}`)
                          }
                        }
                      }}
                      className="text-sm text-red-600 hover:text-red-700 flex items-center space-x-1"
                    >
                      <Trash2 className="h-4 w-4" />
                      <span>Delete</span>
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <input
                        type="file"
                        accept=".crt,.pem,.key,.cer"
                        onChange={(e) => {
                          const file = e.target.files?.[0]
                          if (file) {
                            setCertFiles({ ...certFiles, [certType]: file })
                          }
                        }}
                        className="text-sm text-gray-600 file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                        key={certType + (certFiles[certType] ? '1' : '0')} // Reset input after upload
                      />
                      {certFiles[certType] && (
                        <button
                          onClick={() => handleCertUpload(certType)}
                          disabled={uploadCertMutation.isPending}
                          className="flex items-center space-x-1 px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                        >
                          {uploadCertMutation.isPending ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Upload className="h-3 w-3" />
                          )}
                          <span>Upload</span>
                        </button>
                      )}
                    </div>
                    {certFiles[certType] && (
                      <p className="text-xs text-gray-500">
                        Selected: {certFiles[certType]?.name}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )
          })}
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
      
      {connector.last_connected && (
        <div className="border-t pt-6">
          <div className="text-sm text-gray-600">
            Last connected: {new Date(connector.last_connected).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  )
}

