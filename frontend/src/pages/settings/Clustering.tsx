export default function ClusteringSettings() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">Clustering Settings</h2>
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Minimum Cluster Size
          </label>
          <input
            type="number"
            defaultValue="50"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
          <p className="text-xs text-gray-500 mt-1">Minimum endpoints required to form a cluster</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Minimum Samples
          </label>
          <input
            type="number"
            defaultValue="10"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Clustering Algorithm
          </label>
          <select className="w-full px-3 py-2 border border-gray-300 rounded-md">
            <option>HDBSCAN (Recommended)</option>
            <option>K-Means</option>
            <option>DBSCAN</option>
          </select>
        </div>
        <button className="px-4 py-2 bg-clarion-blue text-white rounded-md hover:bg-blue-700">
          Save Settings
        </button>
      </div>
    </div>
  )
}

