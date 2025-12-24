import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Network, Layers, Grid3x3, Shield, Home } from 'lucide-react'
import ClarionLogo from '/clarion.jpg'

interface LayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Network Flows', href: '/flows', icon: Network },
  { name: 'Clusters', href: '/clusters', icon: Layers },
  { name: 'SGT Matrix', href: '/matrix', icon: Grid3x3 },
  { name: 'Policy Builder', href: '/policies', icon: Shield },
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="w-full">
          <div className="flex items-center justify-between h-16 px-4">
            <div className="flex items-center">
              <img src={ClarionLogo} alt="Clarion" className="h-12 w-auto object-contain" />
            </div>
            <div className="flex items-center space-x-4">
              <div className="h-3 w-3 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-gray-600">System Online</span>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 bg-white border-r border-gray-200 min-h-[calc(100vh-4rem)]">
          <nav className="p-4 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`
                    flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors
                    ${
                      isActive
                        ? 'bg-clarion-blue text-white'
                        : 'text-gray-700 hover:bg-gray-100'
                    }
                  `}
                >
                  <Icon className="h-5 w-5" />
                  <span>{item.name}</span>
                </Link>
              )
            })}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  )
}

