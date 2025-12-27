export default function ADConnector() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">Active Directory Connector</h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Connection Status
          </label>
          <div className="flex items-center space-x-2">
            <div className="h-3 w-3 bg-gray-300 rounded-full"></div>
            <span className="text-sm text-gray-600">Not Connected</span>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Domain Controller
          </label>
          <input
            type="text"
            placeholder="dc.example.com"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Port
          </label>
          <input
            type="number"
            placeholder="389"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Base DN
          </label>
          <input
            type="text"
            placeholder="DC=example,DC=com"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Sync Schedule
          </label>
          <select className="w-full px-3 py-2 border border-gray-300 rounded-md">
            <option>Every 15 minutes</option>
            <option>Every 30 minutes</option>
            <option>Every hour</option>
            <option>Daily</option>
          </select>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-clarion-blue text-white rounded-md hover:bg-blue-700">
            Test Connection
          </button>
          <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300">
            Save Configuration
          </button>
        </div>
      </div>
    </div>
  )
}


