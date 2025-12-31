import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../lib/api'
import { 
  Loader2, AlertCircle, CheckCircle2, XCircle, Save, Power, 
  Shield, Key, FileText, RefreshCw
} from 'lucide-react'
import type { Connector } from '../Connectors'

export default function ISEConnector() {
  const queryClient = useQueryClient()
  
  // Track which tab is active (ers or pxgrid)
  const [activeTab, setActiveTab] = useState<'ers' | 'pxgrid'>('ers')
  
  // Fetch both connectors
  const { data: ersConnector, isLoading: ersLoading, error: ersError } = useQuery({
    queryKey: ['connector', 'ise_ers'],
    queryFn: async () => {
      const response = await apiClient.getConnector('ise_ers')
      return response.data as Connector
    },
  })
  
  const { data: pxgridConnector, isLoading: pxgridLoading, error: pxgridError } = useQuery({
    queryKey: ['connector', 'ise_pxgrid'],
    queryFn: async () => {
      const response = await apiClient.getConnector('ise_pxgrid')
      return response.data as Connector
    },
    refetchInterval: 10000, // Refetch every 10 seconds for status updates
  })

  // ERS Form state
  const [ersFormData, setErsFormData] = useState({
    ise_url: '',
    ise_username: '',
    ise_password: '',
    verify_ssl: false,
  })

  // pxGrid Form state
  const [pxgridFormData, setPxgridFormData] = useState({
    ise_hostname: '',
    username: '',
    password: '',
    client_name: 'clarion-pxgrid-client',
    port: 8910,
    use_ssl: true,
    verify_ssl: false,
  })

  // Initialize forms from connector configs
  useEffect(() => {
    if (ersConnector?.config) {
      setErsFormData({
        ise_url: ersConnector.config.ise_url || '',
        ise_username: ersConnector.config.ise_username || '',
        ise_password: '', // Don't populate password
        verify_ssl: ersConnector.config.verify_ssl === true,
      })
    }
  }, [ersConnector])

  useEffect(() => {
    if (pxgridConnector?.config) {
      setPxgridFormData({
        ise_hostname: pxgridConnector.config.ise_hostname || '',
        username: pxgridConnector.config.username || '',
        password: '', // Don't populate password
        client_name: pxgridConnector.config.client_name || 'clarion-pxgrid-client',
        port: pxgridConnector.config.port || 8910,
        use_ssl: pxgridConnector.config.use_ssl !== false,
        verify_ssl: pxgridConnector.config.verify_ssl === true,
      })
    }
  }, [pxgridConnector])

  // Certificate selection state for pxGrid (only client_cert needed)
  const [selectedCertificates, setSelectedCertificates] = useState<{ [key: string]: number | null }>({
    client_cert: null,
  })

  // ========== ERS Mutations ==========
  
  const configureERSMutation = useMutation({
    mutationFn: async () => {
      return apiClient.configureConnector('ise_ers', ersFormData, false)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connector', 'ise_ers'] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      alert('ERS API configuration saved successfully')
    },
    onError: (error: any) => {
      alert(`Error saving configuration: ${error.response?.data?.detail || error.message}`)
    },
  })

  const enableERSMutation = useMutation({
    mutationFn: async () => {
      return apiClient.enableConnector('ise_ers')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connector', 'ise_ers'] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      alert('ERS API connector enabled')
    },
    onError: (error: any) => {
      alert(`Error enabling connector: ${error.response?.data?.detail || error.message}`)
    },
  })

  const disableERSMutation = useMutation({
    mutationFn: async () => {
      return apiClient.disableConnector('ise_ers')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connector', 'ise_ers'] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      alert('ERS API connector disabled')
    },
    onError: (error: any) => {
      alert(`Error disabling connector: ${error.response?.data?.detail || error.message}`)
    },
  })

  const syncIseConfigMutation = useMutation({
    mutationFn: async () => {
      // Use saved configuration from connector
      return apiClient.syncIseConfig({
        use_saved_config: true,
      })
    },
    onSuccess: (data) => {
      alert(`✅ ISE configuration synced successfully! SGTs: ${data.data.sgts_synced}, Profiles: ${data.data.profiles_synced}, Policies: ${data.data.policies_synced}`)
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.detail || error.message
      alert(`❌ Error syncing ISE configuration: ${errorMsg}`)
    },
  })

  // ========== pxGrid Mutations ==========

  const configurePxgridMutation = useMutation({
    mutationFn: async () => {
      return apiClient.configureConnector('ise_pxgrid', pxgridFormData, false)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connector', 'ise_pxgrid'] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      alert('pxGrid configuration saved successfully')
    },
    onError: (error: any) => {
      alert(`Error saving configuration: ${error.response?.data?.detail || error.message}`)
    },
  })

  const enablePxgridMutation = useMutation({
    mutationFn: async () => {
      return apiClient.enableConnector('ise_pxgrid')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connector', 'ise_pxgrid'] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      alert('pxGrid connector enabled. Container is starting...')
    },
    onError: (error: any) => {
      alert(`Error enabling connector: ${error.response?.data?.detail || error.message}`)
    },
  })

  const disablePxgridMutation = useMutation({
    mutationFn: async () => {
      return apiClient.disableConnector('ise_pxgrid')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connector', 'ise_pxgrid'] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      alert('pxGrid connector disabled. Container stopped.')
    },
    onError: (error: any) => {
      alert(`Error disabling connector: ${error.response?.data?.detail || error.message}`)
    },
  })

  const testPxgridConnectionMutation = useMutation({
    mutationFn: async () => {
      return apiClient.testConnectorConnection('ise_pxgrid')
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['connector', 'ise_pxgrid'] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      alert(data.data.connected 
        ? `✅ ${data.data.message}` 
        : `❌ ${data.data.message || 'Connection test failed'}`)
    },
    onError: (error: any) => {
      alert(`❌ Connection test failed: ${error.response?.data?.detail || error.message}`)
    },
  })
  
  const testERSConnectionMutation = useMutation({
    mutationFn: async () => {
      return apiClient.testConnectorConnection('ise_ers')
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['connector', 'ise_ers'] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      alert(data.data.connected 
        ? `✅ ${data.data.message}` 
        : `❌ ${data.data.message || 'Connection test failed'}`)
    },
    onError: (error: any) => {
      alert(`❌ Connection test failed: ${error.response?.data?.detail || error.message}`)
    },
  })

  // Fetch available certificates
  const { data: certificatesData } = useQuery({
    queryKey: ['certificates'],
    queryFn: async () => {
      const response = await apiClient.getCertificates()
      return response.data.certificates as Array<{
        id: number
        name: string
        cert_type: string
        description?: string
      }>
    },
  })

  // Fetch assigned certificates for pxGrid connector
  const { data: assignedCertsData } = useQuery({
    queryKey: ['connector-certificates', 'ise_pxgrid'],
    queryFn: async () => {
      try {
        const response = await apiClient.getConnectorCertificates('ise_pxgrid')
        return response.data.certificates as {
          client_cert?: { certificate_id: number; name: string }
          client_key?: { certificate_id: number; name: string }
          ca_cert?: { certificate_id: number; name: string }
        }
      } catch {
        return {}
      }
    },
  })

  // Initialize selected certificates from assigned certificates
  useEffect(() => {
    if (assignedCertsData) {
      setSelectedCertificates({
        client_cert: assignedCertsData.client_cert?.certificate_id || null,
      })
    }
  }, [assignedCertsData])

  // Assign certificate mutation
  const assignCertMutation = useMutation({
    mutationFn: async ({ certType, certificateId }: { certType: string; certificateId: number }) => {
      return apiClient.assignCertificateToConnector('ise_pxgrid', certificateId, certType)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connector-certificates', 'ise_pxgrid'] })
      queryClient.invalidateQueries({ queryKey: ['connector', 'ise_pxgrid'] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      // State already updated in handleCertSelection, just confirm
      alert('Certificate assigned successfully')
    },
    onError: (error: any) => {
      alert(`Error assigning certificate: ${error.response?.data?.detail || error.message}`)
    },
  })

  // Unassign certificate mutation
  const unassignCertMutation = useMutation({
    mutationFn: async (certType: string) => {
      return apiClient.unassignCertificateFromConnector('ise_pxgrid', certType)
    },
    onSuccess: (_, certType) => {
      queryClient.invalidateQueries({ queryKey: ['connector-certificates', 'ise_pxgrid'] })
      queryClient.invalidateQueries({ queryKey: ['connector', 'ise_pxgrid'] })
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      setSelectedCertificates((prev) => ({ ...prev, [certType]: null }))
      alert('Certificate unassigned successfully')
    },
    onError: (error: any) => {
      alert(`Error unassigning certificate: ${error.response?.data?.detail || error.message}`)
    },
  })

  const handleCertSelection = (certType: string, certificateId: number | null) => {
    // Store previous value for potential rollback
    const previousCertId = selectedCertificates[certType as keyof typeof selectedCertificates]
    
    // Update local state immediately for responsive UI
    setSelectedCertificates((prev) => ({ ...prev, [certType]: certificateId }))
    
    if (certificateId === null) {
      // Unassign if selecting "None"
      if (previousCertId !== null) {
        unassignCertMutation.mutate(certType, {
          onError: () => {
            // Revert state on error
            setSelectedCertificates((prev) => ({ ...prev, [certType]: previousCertId }))
          },
        })
      }
    } else {
      // Assign certificate
      assignCertMutation.mutate({ certType, certificateId }, {
        onError: () => {
          // Revert state on error
          setSelectedCertificates((prev) => ({ ...prev, [certType]: previousCertId }))
        },
      })
    }
  }

  // Helper functions
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

  const isLoading = (activeTab === 'ers' ? ersLoading : pxgridLoading)
  const error = (activeTab === 'ers' ? ersError : pxgridError)
  const connector = (activeTab === 'ers' ? ersConnector : pxgridConnector)

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
      <div>
        <h2 className="text-2xl font-semibold mb-2">ISE Connector</h2>
        <p className="text-sm text-gray-600">
          Configure Cisco ISE ERS API and pxGrid connections
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('ers')}
            className={`
              pb-4 px-1 border-b-2 font-medium text-sm transition-colors
              ${
                activeTab === 'ers'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            ERS API
          </button>
          <button
            onClick={() => setActiveTab('pxgrid')}
            className={`
              pb-4 px-1 border-b-2 font-medium text-sm transition-colors
              ${
                activeTab === 'pxgrid'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            pxGrid
          </button>
        </nav>
      </div>

      {/* ERS API Tab Content */}
      {activeTab === 'ers' && ersConnector && (
        <div className="space-y-6">
          {/* Status and Enable/Disable */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className={`h-3 w-3 rounded-full ${getStatusColor(ersConnector.status)}`} />
              <span className="text-sm font-medium capitalize">{ersConnector.status || 'disabled'}</span>
            </div>
            
            {ersConnector.enabled ? (
              <button
                onClick={() => disableERSMutation.mutate()}
                disabled={disableERSMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 flex items-center space-x-2"
              >
                <XCircle className="h-4 w-4" />
                <span>Disable</span>
              </button>
            ) : (
              <button
                onClick={() => enableERSMutation.mutate()}
                disabled={enableERSMutation.isPending}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 flex items-center space-x-2"
              >
                <Power className="h-4 w-4" />
                <span>Enable</span>
              </button>
            )}
          </div>

          {/* Configuration Form */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                ISE Server URL *
              </label>
              <input
                type="text"
                value={ersFormData.ise_url}
                onChange={(e) => setErsFormData({ ...ersFormData, ise_url: e.target.value })}
                placeholder="https://192.168.10.31"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                ISE server URL (port optional, defaults to 443 for HTTPS). Example: https://ise.example.com
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username *
              </label>
              <input
                type="text"
                value={ersFormData.ise_username}
                onChange={(e) => setErsFormData({ ...ersFormData, ise_username: e.target.value })}
                placeholder="admin"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password *
              </label>
              <input
                type="password"
                value={ersFormData.ise_password}
                onChange={(e) => setErsFormData({ ...ersFormData, ise_password: e.target.value })}
                placeholder="••••••••"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="ers-verify-ssl"
                checked={ersFormData.verify_ssl}
                onChange={(e) => setErsFormData({ ...ersFormData, verify_ssl: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="ers-verify-ssl" className="ml-2 block text-sm text-gray-700">
                Verify SSL certificate
              </label>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-3">
            <button
              onClick={() => configureERSMutation.mutate()}
              disabled={configureERSMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
            >
              <Save className="h-4 w-4" />
              <span>Save Configuration</span>
            </button>
            
            <button
              onClick={() => testERSConnectionMutation.mutate()}
              disabled={testERSConnectionMutation.isPending || !ersConnector?.config}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 flex items-center space-x-2"
            >
              {testERSConnectionMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              <span>Test Connection</span>
            </button>
          </div>

          {/* Status Information and Sync */}
          <div className="border-t pt-4 space-y-4">
            {/* Sync ISE Configuration Button */}
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-1">Configuration Sync</h3>
                <p className="text-xs text-gray-500">
                  Sync existing SGTs, authorization profiles, and policies from ISE for brownfield deployment support.
                </p>
              </div>
              <button
                onClick={() => syncIseConfigMutation.mutate()}
                disabled={syncIseConfigMutation.isPending || !ersConnector?.config}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
                title={!ersConnector?.config ? "Please save the configuration first" : ""}
              >
                {syncIseConfigMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                <span>Sync ISE Configuration</span>
              </button>
            </div>

            {/* Connection Status */}
            {(ersConnector.last_connected || ersConnector.last_error) && (
              <div className="space-y-2">
                {ersConnector.last_connected && (
                  <div className="text-sm text-gray-600">
                    Last connected: {new Date(ersConnector.last_connected).toLocaleString()}
                  </div>
                )}
                {ersConnector.last_error && (
                  <div className="text-sm text-red-600">
                    Last error: {ersConnector.last_error}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* pxGrid Tab Content */}
      {activeTab === 'pxgrid' && pxgridConnector && (
        <div className="space-y-6">
          {/* Status and Enable/Disable */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className={`h-3 w-3 rounded-full ${getStatusColor(pxgridConnector.status)}`} />
              <span className="text-sm font-medium capitalize">{pxgridConnector.status || 'disabled'}</span>
            </div>
            
            {pxgridConnector.enabled ? (
              <button
                onClick={() => disablePxgridMutation.mutate()}
                disabled={disablePxgridMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 flex items-center space-x-2"
              >
                <XCircle className="h-4 w-4" />
                <span>Disable</span>
              </button>
            ) : (
              <button
                onClick={() => enablePxgridMutation.mutate()}
                disabled={enablePxgridMutation.isPending}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 flex items-center space-x-2"
              >
                <Power className="h-4 w-4" />
                <span>Enable</span>
              </button>
            )}
          </div>

          {/* Configuration Form */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                ISE Hostname / IP *
              </label>
              <input
                type="text"
                value={pxgridFormData.ise_hostname}
                onChange={(e) => setPxgridFormData({ ...pxgridFormData, ise_hostname: e.target.value })}
                placeholder="ise.example.com or 192.168.1.10"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username *
              </label>
              <input
                type="text"
                value={pxgridFormData.username}
                onChange={(e) => setPxgridFormData({ ...pxgridFormData, username: e.target.value })}
                placeholder="admin"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password *
              </label>
              <input
                type="password"
                value={pxgridFormData.password}
                onChange={(e) => setPxgridFormData({ ...pxgridFormData, password: e.target.value })}
                placeholder="••••••••"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Client Name
              </label>
              <input
                type="text"
                value={pxgridFormData.client_name}
                onChange={(e) => setPxgridFormData({ ...pxgridFormData, client_name: e.target.value })}
                placeholder="clarion-pxgrid-client"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Port
              </label>
              <input
                type="number"
                value={pxgridFormData.port}
                onChange={(e) => setPxgridFormData({ ...pxgridFormData, port: parseInt(e.target.value) || 8910 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="pxgrid-use-ssl"
                checked={pxgridFormData.use_ssl}
                onChange={(e) => setPxgridFormData({ ...pxgridFormData, use_ssl: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="pxgrid-use-ssl" className="ml-2 block text-sm text-gray-700">
                Use SSL/TLS
              </label>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="pxgrid-verify-ssl"
                checked={pxgridFormData.verify_ssl}
                onChange={(e) => setPxgridFormData({ ...pxgridFormData, verify_ssl: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="pxgrid-verify-ssl" className="ml-2 block text-sm text-gray-700">
                Verify SSL certificate
              </label>
            </div>
          </div>

          {/* Certificate Selection */}
          <div className="border-t pt-6">
            <h3 className="text-lg font-medium mb-2">Certificates</h3>
            <p className="text-sm text-gray-600 mb-4">
              Select client certificate for pxGrid authentication (client certificate for mutual TLS). 
              <a href="/settings/certificates" className="text-blue-600 hover:text-blue-700 ml-1">
                Manage certificates
              </a>
            </p>
            <div className="space-y-4">
              {['client_cert'].map((certType) => {
                const certLabels: { [key: string]: { label: string; icon: any; filterType: string; description?: string } } = {
                  client_cert: { label: 'Client Certificate', icon: FileText, filterType: 'client_cert' },
                  client_key: { label: 'Client Private Key', icon: Key, filterType: 'client_key' },
                  ca_cert: { label: 'Root/CA Certificate', icon: Shield, filterType: 'ca_cert', description: 'Root CA certificate that signed the ISE server certificate' },
                }
                const { label, icon: Icon, filterType, description } = certLabels[certType] || { label: certType, icon: FileText, filterType: certType, description: undefined }
                
                // Filter certificates by type
                const availableCerts = certificatesData?.filter(c => c.cert_type === filterType) || []
                const selectedCertId = selectedCertificates[certType]
                const selectedCert = availableCerts.find(c => c.id === selectedCertId)
                
                return (
                  <div key={certType} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <Icon className="h-5 w-5 text-gray-500" />
                        <div>
                          <span className="font-medium">{label}</span>
                          {description && (
                            <p className="text-xs text-gray-500 mt-0.5">{description}</p>
                          )}
                        </div>
                      </div>
                      {selectedCert && (
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                      )}
                    </div>
                    
                    <div className="flex space-x-2">
                      <select
                        value={selectedCertId || ''}
                        onChange={(e) => {
                          const certId = e.target.value ? parseInt(e.target.value) : null
                          handleCertSelection(certType, certId)
                        }}
                        disabled={assignCertMutation.isPending || unassignCertMutation.isPending}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                      >
                        <option value="">-- Select Certificate --</option>
                        {availableCerts.map((cert) => (
                          <option key={cert.id} value={cert.id}>
                            {cert.name} {cert.description ? `(${cert.description})` : ''}
                          </option>
                        ))}
                      </select>
                      {selectedCert && (
                        <button
                          onClick={() => {
                            if (confirm(`Unassign certificate "${selectedCert.name}"?`)) {
                              unassignCertMutation.mutate(certType)
                            }
                          }}
                          disabled={unassignCertMutation.isPending}
                          className="px-3 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 flex items-center space-x-1"
                        >
                          <XCircle className="h-4 w-4" />
                          <span>Unassign</span>
                        </button>
                      )}
                    </div>
                    {selectedCert && (
                      <p className="text-xs text-gray-500 mt-2">
                        Selected: {selectedCert.name}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-3">
            <button
              onClick={() => configurePxgridMutation.mutate()}
              disabled={configurePxgridMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
            >
              <Save className="h-4 w-4" />
              <span>Save Configuration</span>
            </button>
            
            <button
              onClick={() => testPxgridConnectionMutation.mutate()}
              disabled={testPxgridConnectionMutation.isPending || !pxgridConnector?.config}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 flex items-center space-x-2"
            >
              {testPxgridConnectionMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              <span>Test Connection</span>
            </button>
          </div>

          {/* Status Information */}
          {(pxgridConnector.last_connected || pxgridConnector.last_error) && (
            <div className="border-t pt-4 space-y-2">
              {pxgridConnector.last_connected && (
                <div className="text-sm text-gray-600">
                  Last connected: {new Date(pxgridConnector.last_connected).toLocaleString()}
                </div>
              )}
              {pxgridConnector.last_error && (
                <div className="text-sm text-red-600">
                  Last error: {pxgridConnector.last_error}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
