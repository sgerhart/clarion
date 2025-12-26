import { Outlet, Link, useLocation } from 'react-router-dom'

const subPages = [
  { name: 'Overview', href: '/data-sources/overview' },
  { name: 'Edge Agents', href: '/data-sources/agents' },
  { name: 'NetFlow Collectors', href: '/data-sources/collectors' },
]

export default function DataSources() {
  const location = useLocation()

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Data Sources</h1>
      
      {/* Sub-navigation tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          {subPages.map((page) => {
            const isActive = location.pathname === page.href
            return (
              <Link
                key={page.href}
                to={page.href}
                className={`
                  pb-4 px-1 border-b-2 font-medium text-sm transition-colors
                  ${
                    isActive
                      ? 'border-clarion-blue text-clarion-blue'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                {page.name}
              </Link>
            )
          })}
        </nav>
      </div>

      <Outlet />
    </div>
  )
}

