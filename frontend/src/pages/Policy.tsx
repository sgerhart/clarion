import { Outlet, Link, useLocation } from 'react-router-dom'

const policyPages = [
  { name: 'SGT Mappings', href: '/policy/sgts' },
  { name: 'Access Rules', href: '/policy/rules' },
  { name: 'Policy Matrix', href: '/policy/matrix' },
  { name: 'Policy Builder', href: '/policy/builder' },
  { name: 'Impact Analysis', href: '/policy/impact' },
]

export default function Policy() {
  const location = useLocation()

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Policy Management</h1>
      
      {/* Sub-navigation tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          {policyPages.map((page) => {
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


