import { Outlet, Link, useLocation } from 'react-router-dom'

const settingsPages = [
  { name: 'Global Settings', href: '/settings/global' },
  { name: 'Clustering', href: '/settings/clustering' },
  { name: 'Policy', href: '/settings/policy' },
  { name: 'System', href: '/settings/system' },
]

export default function Settings() {
  const location = useLocation()

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      
      {/* Sub-navigation tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          {settingsPages.map((page) => {
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


