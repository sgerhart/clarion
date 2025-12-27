import { ReactNode, useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  Home, 
  Network, 
  Layers, 
  Grid3x3, 
  Shield, 
  MapPin,
  Database,
  Plug,
  Settings,
  Activity,
  FileText,
  ClipboardList,
  Server
} from 'lucide-react'
import ClarionLogo from '/clarion.jpg'
import ClarionIcon from '/clarionicon.jpg'

interface LayoutProps {
  children: ReactNode
}

interface NavItem {
  name: string
  href: string
  icon: any
  subItems?: NavItem[]
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Devices', href: '/devices', icon: Server },
  { name: 'Groups', href: '/groups', icon: Layers },
  { name: 'Network Flows', href: '/flows', icon: Network },
  { 
    name: 'Policy', 
    href: '/policy', 
    icon: Shield,
    subItems: [
      { name: 'SGT Mappings', href: '/policy/sgts', icon: Grid3x3 },
      { name: 'Access Rules', href: '/policy/rules', icon: Shield },
      { name: 'Policy Matrix', href: '/policy/matrix', icon: Grid3x3 },
      { name: 'Policy Builder', href: '/policy/builder', icon: Shield },
      { name: 'Impact Analysis', href: '/policy/impact', icon: Activity },
    ]
  },
  { name: 'Topology', href: '/topology', icon: MapPin },
  { 
    name: 'Data Sources', 
    href: '/data-sources', 
    icon: Database,
    subItems: [
      { name: 'Edge Agents', href: '/data-sources/agents', icon: Server },
      { name: 'NetFlow Collectors', href: '/data-sources/collectors', icon: Database },
      { name: 'Overview', href: '/data-sources/overview', icon: Activity },
    ]
  },
  { 
    name: 'Connectors', 
    href: '/connectors', 
    icon: Plug,
    subItems: [
      { name: 'ISE pxGrid', href: '/connectors/ise', icon: Plug },
      { name: 'Active Directory', href: '/connectors/ad', icon: Plug },
      { name: 'IoT Connectors', href: '/connectors/iot', icon: Plug },
    ]
  },
  { 
    name: 'Settings', 
    href: '/settings', 
    icon: Settings,
    subItems: [
      { name: 'Global Settings', href: '/settings/global', icon: Settings },
      { name: 'Clustering', href: '/settings/clustering', icon: Layers },
      { name: 'Policy', href: '/settings/policy', icon: Shield },
      { name: 'System', href: '/settings/system', icon: Settings },
    ]
  },
  { name: 'Monitoring', href: '/monitoring', icon: Activity },
  { name: 'Audit/Logs', href: '/audit', icon: ClipboardList },
  { name: 'Reports/Export', href: '/reports', icon: FileText },
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  
  // Auto-expand parent items if a sub-item is active
  const activeParents = navigation
    .filter(item => item.subItems?.some(sub => location.pathname === sub.href))
    .map(item => item.name)
  
  const [expandedItems, setExpandedItems] = useState<string[]>(activeParents)

  // Update expanded items when location changes
  useEffect(() => {
    setExpandedItems(prev => {
      const newParents = navigation
        .filter(item => item.subItems?.some(sub => location.pathname === sub.href))
        .map(item => item.name)
      // Merge with existing expanded items, keeping manually expanded ones
      const merged = [...new Set([...prev, ...newParents])]
      return merged
    })
  }, [location.pathname])

  const toggleExpanded = (itemName: string) => {
    setExpandedItems(prev => 
      prev.includes(itemName) 
        ? prev.filter(name => name !== itemName)
        : [...prev, itemName]
    )
  }

  const isItemActive = (item: NavItem): boolean => {
    if (location.pathname === item.href) return true
    if (item.subItems) {
      return item.subItems.some(subItem => location.pathname === subItem.href)
    }
    return false
  }

  const isSubItemActive = (subItem: NavItem): boolean => {
    return location.pathname === subItem.href
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="w-full">
          <div className="flex items-center justify-between h-16 px-4">
            <div className="flex items-center space-x-3">
              <img src={ClarionIcon} alt="Clarion Icon" className="h-8 w-8 object-contain" />
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
        <aside className="w-64 bg-white border-r border-gray-200 min-h-[calc(100vh-4rem)] overflow-y-auto">
          <nav className="p-4 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = isItemActive(item)
              const isExpanded = expandedItems.includes(item.name)
              
              return (
                <div key={item.name}>
                  {item.subItems ? (
                    <>
                      <button
                        onClick={() => toggleExpanded(item.name)}
                        className={`
                          w-full flex items-center justify-between px-4 py-3 rounded-lg text-sm font-medium transition-colors
                          ${
                            isActive
                              ? 'bg-clarion-blue text-white'
                              : 'text-gray-700 hover:bg-gray-100'
                          }
                        `}
                      >
                        <div className="flex items-center space-x-3">
                          <Icon className="h-5 w-5" />
                          <span>{item.name}</span>
                        </div>
                        <svg
                          className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                      {isExpanded && (
                        <div className="ml-4 mt-1 space-y-1">
                          {item.subItems.map((subItem) => {
                            const SubIcon = subItem.icon
                            const isSubActive = isSubItemActive(subItem)
                            return (
                              <Link
                                key={subItem.name}
                                to={subItem.href}
                                className={`
                                  flex items-center space-x-3 px-4 py-2 rounded-lg text-sm transition-colors
                                  ${
                                    isSubActive
                                      ? 'bg-blue-100 text-clarion-blue font-medium'
                                      : 'text-gray-600 hover:bg-gray-50'
                                  }
                                `}
                              >
                                <SubIcon className="h-4 w-4" />
                                <span>{subItem.name}</span>
                              </Link>
                            )
                          })}
                        </div>
                      )}
                    </>
                  ) : (
                    <Link
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
                  )}
                </div>
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
