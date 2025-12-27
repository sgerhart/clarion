export default function SystemSettings() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">System Settings</h2>
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Timezone
          </label>
          <select className="w-full px-3 py-2 border border-gray-300 rounded-md">
            <option>UTC</option>
            <option>America/New_York</option>
            <option>America/Chicago</option>
            <option>America/Los_Angeles</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Data Retention (Days)
          </label>
          <input
            type="number"
            defaultValue="90"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
          <p className="text-xs text-gray-500 mt-1">Number of days to retain flow data</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Logging Level
          </label>
          <select className="w-full px-3 py-2 border border-gray-300 rounded-md">
            <option>INFO</option>
            <option>DEBUG</option>
            <option>WARNING</option>
            <option>ERROR</option>
          </select>
        </div>
        <button className="px-4 py-2 bg-clarion-blue text-white rounded-md hover:bg-blue-700">
          Save Settings
        </button>
      </div>
    </div>
  )
}


