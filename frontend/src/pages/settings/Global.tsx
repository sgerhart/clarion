export default function GlobalSettings() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">Global Settings</h2>
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Base SGT Value
          </label>
          <input
            type="number"
            defaultValue="2"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
          <p className="text-xs text-gray-500 mt-1">Starting SGT value for auto-assignment</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Default Policy Action
          </label>
          <select className="w-full px-3 py-2 border border-gray-300 rounded-md">
            <option>Deny</option>
            <option>Permit</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Require Approval for Recommendations
          </label>
          <label className="flex items-center">
            <input type="checkbox" className="mr-2" defaultChecked />
            <span className="text-sm text-gray-600">Require admin approval before applying policies</span>
          </label>
        </div>
        <button className="px-4 py-2 bg-clarion-blue text-white rounded-md hover:bg-blue-700">
          Save Settings
        </button>
      </div>
    </div>
  )
}

