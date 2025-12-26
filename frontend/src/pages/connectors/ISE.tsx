export default function ISEConnector() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">ISE pxGrid Connector</h2>
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
            Hostname / IP
          </label>
          <input
            type="text"
            placeholder="ise.example.com"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Port
          </label>
          <input
            type="number"
            placeholder="8910"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Topic Subscriptions
          </label>
          <div className="space-y-2">
            <label className="flex items-center">
              <input type="checkbox" className="mr-2" />
              <span className="text-sm">Session Topic</span>
            </label>
            <label className="flex items-center">
              <input type="checkbox" className="mr-2" />
              <span className="text-sm">Endpoint Topic</span>
            </label>
          </div>
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

