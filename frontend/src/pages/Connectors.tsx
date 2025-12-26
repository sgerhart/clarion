import { Outlet, Link, useLocation } from 'react-router-dom'

// Flexible connector configuration - can be extended with new connector types
export interface ConnectorConfig {
  id: string
  name: string
  type: 'ise' | 'ad' | 'iot' | 'custom'
  status: 'connected' | 'disconnected' | 'error'
  description: string
  href: string
}

// Define available connectors - easily extensible
const connectors: ConnectorConfig[] = [
  {
    id: 'ise',
    name: 'ISE pxGrid',
    type: 'ise',
    status: 'disconnected',
    description: 'Cisco ISE pxGrid connector for identity and SGT data',
    href: '/connectors/ise',
  },
  {
    id: 'ad',
    name: 'Active Directory',
    type: 'ad',
    status: 'disconnected',
    description: 'LDAP connector for users, groups, and device information',
    href: '/connectors/ad',
  },
  {
    id: 'iot',
    name: 'IoT Connectors',
    type: 'iot',
    status: 'disconnected',
    description: 'IoT device connectors (MediGate, ClearPass, custom)',
    href: '/connectors/iot',
  },
]

export default function Connectors() {
  const location = useLocation()

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Connectors</h1>
      </div>

      {/* Connector list */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {connectors.map((connector) => {
          const isActive = location.pathname === connector.href
          return (
            <Link
              key={connector.id}
              to={connector.href}
              className={`
                bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow
                ${isActive ? 'ring-2 ring-clarion-blue' : ''}
              `}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-semibold">{connector.name}</h3>
                <div
                  className={`
                    h-3 w-3 rounded-full
                    ${
                      connector.status === 'connected'
                        ? 'bg-green-500'
                        : connector.status === 'error'
                        ? 'bg-red-500'
                        : 'bg-gray-300'
                    }
                  `}
                />
              </div>
              <p className="text-sm text-gray-600">{connector.description}</p>
              <div className="mt-4">
                <span
                  className={`
                    text-xs px-2 py-1 rounded
                    ${
                      connector.status === 'connected'
                        ? 'bg-green-100 text-green-800'
                        : connector.status === 'error'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-gray-100 text-gray-800'
                    }
                  `}
                >
                  {connector.status === 'connected' ? 'Connected' : 
                   connector.status === 'error' ? 'Error' : 'Not Connected'}
                </span>
              </div>
            </Link>
          )
        })}
      </div>

      {/* Sub-pages */}
      <Outlet />
    </div>
  )
}

