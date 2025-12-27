export default function PolicySettings() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">Policy Settings</h2>
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Default SGACL Action
          </label>
          <select className="w-full px-3 py-2 border border-gray-300 rounded-md">
            <option>Deny</option>
            <option>Permit</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Auto-Apply Policies
          </label>
          <label className="flex items-center">
            <input type="checkbox" className="mr-2" />
            <span className="text-sm text-gray-600">Automatically apply approved policies</span>
          </label>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Impact Analysis Threshold
          </label>
          <input
            type="number"
            defaultValue="10"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
          <p className="text-xs text-gray-500 mt-1">Minimum flows affected to show warning</p>
        </div>
        <button className="px-4 py-2 bg-clarion-blue text-white rounded-md hover:bg-blue-700">
          Save Settings
        </button>
      </div>
    </div>
  )
}


