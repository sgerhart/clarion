export default function Reports() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Reports & Export</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Policy Export</h2>
          <div className="space-y-3">
            <button className="w-full px-4 py-2 bg-clarion-blue text-white rounded-md hover:bg-blue-700">
              Export ISE ERS Format
            </button>
            <button className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300">
              Export Cisco CLI
            </button>
            <button className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300">
              Export JSON
            </button>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Reports</h2>
          <div className="space-y-3">
            <button className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300">
              Device Inventory Report
            </button>
            <button className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300">
              Policy Compliance Report
            </button>
            <button className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300">
              Clustering Analysis Report
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

