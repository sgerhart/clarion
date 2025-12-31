import { Outlet, Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { Loader2, AlertCircle, CheckCircle2, XCircle } from 'lucide-react'

// Connector interface matching API response
export interface Connector {
  connector_id: string
  name: string
  type: string
  enabled: boolean
  status: string
  config?: Record<string, any>
  description?: string
  last_connected?: string
  last_error?: string
  error_count: number
  container_status?: string
  certificates?: {
    has_client_cert: boolean
    has_client_key: boolean
    has_ca_cert: boolean
  }
}

export default function Connectors() {
  const location = useLocation()
  
  // Check if we're on a child route (not the index)
  const isDetailView = location.pathname !== '/connectors' && location.pathname !== '/connectors/'

  // Fetch connectors from API
  const { data: connectorsData, isLoading, error } = useQuery({
    queryKey: ['connectors'],
    queryFn: async () => {
      const response = await apiClient.getConnectors()
      return response.data.connectors as Connector[]
    },
    refetchInterval: 30000, // Refetch every 30 seconds for status updates
  })

  const getStatusColor = (status: string) => {
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

  const getStatusLabel = (connector: Connector) => {
    if (connector.enabled && connector.status === 'connected') {
      return 'Connected'
    }
    if (connector.enabled && connector.status === 'error') {
      return 'Error'
    }
    if (connector.enabled && connector.status === 'connecting') {
      return 'Connecting'
    }
    if (connector.enabled) {
      return 'Enabled'
    }
    return 'Disabled'
  }

  const getStatusIcon = (connector: Connector) => {
    if (connector.enabled && connector.status === 'connected') {
      return <CheckCircle2 className="h-4 w-4 text-green-500" />
    }
    if (connector.enabled && connector.status === 'error') {
      return <XCircle className="h-4 w-4 text-red-500" />
    }
    if (connector.enabled) {
      return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
    }
    return null
  }

  // If we're on a detail view, only show the Outlet (child route)
  if (isDetailView) {
    return <Outlet />
  }

  // Otherwise show the connector list (index view)
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Connectors</h1>
        {error && (
          <div className="flex items-center space-x-2 text-red-600 text-sm">
            <AlertCircle className="h-4 w-4" />
            <span>Error loading connectors</span>
          </div>
        )}
      </div>

      {/* Connector list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          <span className="ml-2 text-gray-600">Loading connectors...</span>
        </div>
      ) : connectorsData && connectorsData.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          {(() => {
            const isePxgrid = connectorsData.find(c => c.connector_id === 'ise_pxgrid')
            const iseErs = connectorsData.find(c => c.connector_id === 'ise_ers')
            const otherConnectors = connectorsData.filter(c => c.connector_id !== 'ise_pxgrid' && c.connector_id !== 'ise_ers')
            
            return (
              <>
                {/* Combined ISE connector card */}
                {(isePxgrid || iseErs) && (
                  <Link
                    to="/connectors/ise"
                    className={`
                      bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow
                      ${location.pathname === '/connectors/ise' ? 'ring-2 ring-blue-500' : ''}
                    `}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-lg font-semibold">ISE</h3>
                      <div className="flex items-center space-x-2">
                        {(isePxgrid?.enabled || iseErs?.enabled) && (
                          <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                        )}
                        <div className={`h-3 w-3 rounded-full ${
                          (isePxgrid?.enabled && isePxgrid.status === 'connected') || 
                          (iseErs?.enabled && iseErs.status === 'connected')
                            ? 'bg-green-500'
                            : (isePxgrid?.enabled || iseErs?.enabled)
                            ? 'bg-blue-500'
                            : 'bg-gray-300'
                        }`} />
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 mb-4">Cisco ISE ERS API and pxGrid connector</p>
                    
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500">Status</span>
                        <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-800">
                          {((isePxgrid?.enabled && isePxgrid.status === 'connected') || 
                            (iseErs?.enabled && iseErs.status === 'connected'))
                            ? 'Connected'
                            : (isePxgrid?.enabled || iseErs?.enabled)
                            ? 'Enabled'
                            : 'Disabled'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500">Components</span>
                        <span className="text-xs text-gray-600">ERS API, pxGrid</span>
                      </div>
                    </div>
                  </Link>
                )}
                
                {/* Other connectors */}
                {otherConnectors.map((connector) => {
                  const routeMap: { [key: string]: string } = {
                    'ad': 'ad',
                    'iot_medigate': 'iot',
                  }
                  const routePath = routeMap[connector.connector_id] || connector.connector_id.replace('_', '-')
                  const isActive = location.pathname === `/connectors/${routePath}`
                  return (
                    <Link
                      key={connector.connector_id}
                      to={`/connectors/${routePath}`}
                      className={`
                        bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow
                        ${isActive ? 'ring-2 ring-blue-500' : ''}
                      `}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-lg font-semibold">{connector.name}</h3>
                        <div className="flex items-center space-x-2">
                          {getStatusIcon(connector)}
                          <div
                            className={`
                              h-3 w-3 rounded-full
                              ${getStatusColor(connector.status)}
                            `}
                          />
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mb-4">{connector.description}</p>
                      
                      {/* Status and configuration info */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-500">Status</span>
                          <span
                            className={`
                              text-xs px-2 py-1 rounded
                              ${
                                connector.enabled && connector.status === 'connected'
                                  ? 'bg-green-100 text-green-800'
                                  : connector.enabled && connector.status === 'error'
                                  ? 'bg-red-100 text-red-800'
                                  : connector.enabled
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-gray-100 text-gray-800'
                              }
                            `}
                          >
                            {getStatusLabel(connector)}
                          </span>
                        </div>
                        
                        {connector.config && (
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-gray-500">Configured</span>
                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                          </div>
                        )}
                        
                        {connector.container_status && (
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-gray-500">Container</span>
                            <span className={`text-xs ${
                              connector.container_status === 'running' ? 'text-green-600' : 'text-gray-600'
                            }`}>
                              {connector.container_status}
                            </span>
                          </div>
                        )}
                        
                        {connector.last_error && (
                          <div className="mt-2 text-xs text-red-600 truncate" title={connector.last_error}>
                            {connector.last_error}
                          </div>
                        )}
                      </div>
                    </Link>
                  )
                })}
              </>
            )
          })()}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <p className="text-gray-600">No connectors available</p>
        </div>
      )}

      {/* Sub-pages */}
      <Outlet />
    </div>
  )
}
