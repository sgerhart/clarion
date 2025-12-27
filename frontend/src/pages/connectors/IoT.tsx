export default function IoTConnectors() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4">IoT Connectors</h2>
      <p className="text-gray-600 mb-4">
        Configure IoT device connectors for MediGate, ClearPass, and custom solutions.
      </p>
      
      <div className="space-y-4">
        <div className="border border-gray-200 rounded-lg p-4">
          <h3 className="font-semibold mb-2">MediGate</h3>
          <p className="text-sm text-gray-600 mb-3">Medical device management connector</p>
          <div className="flex items-center space-x-2 mb-2">
            <div className="h-3 w-3 bg-gray-300 rounded-full"></div>
            <span className="text-sm text-gray-600">Not Configured</span>
          </div>
          <button className="text-sm text-clarion-blue hover:underline">
            Configure MediGate Connector
          </button>
        </div>

        <div className="border border-gray-200 rounded-lg p-4">
          <h3 className="font-semibold mb-2">ClearPass</h3>
          <p className="text-sm text-gray-600 mb-3">Device profiling and policy connector</p>
          <div className="flex items-center space-x-2 mb-2">
            <div className="h-3 w-3 bg-gray-300 rounded-full"></div>
            <span className="text-sm text-gray-600">Not Configured</span>
          </div>
          <button className="text-sm text-clarion-blue hover:underline">
            Configure ClearPass Connector
          </button>
        </div>

        <div className="border border-gray-200 rounded-lg p-4">
          <h3 className="font-semibold mb-2">Custom Connector</h3>
          <p className="text-sm text-gray-600 mb-3">Add a custom IoT connector</p>
          <button className="text-sm text-clarion-blue hover:underline">
            Add Custom Connector
          </button>
        </div>
      </div>
    </div>
  )
}


