export default function Monitoring() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Monitoring</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">API Health</h3>
          <div className="flex items-center space-x-2">
            <div className="h-3 w-3 bg-green-500 rounded-full"></div>
            <span className="text-2xl font-bold text-gray-900">Healthy</span>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Database</h3>
          <div className="flex items-center space-x-2">
            <div className="h-3 w-3 bg-green-500 rounded-full"></div>
            <span className="text-2xl font-bold text-gray-900">Connected</span>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Active Agents</h3>
          <span className="text-2xl font-bold text-gray-900">0</span>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Flows/Hour</h3>
          <span className="text-2xl font-bold text-gray-900">0</span>
        </div>
      </div>
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">System Health</h2>
        <p className="text-gray-600">Detailed monitoring dashboard - Coming soon</p>
      </div>
    </div>
  )
}

