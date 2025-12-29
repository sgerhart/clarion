import { useState } from 'react'
import { X, Server, Key, Lock, CheckCircle, AlertCircle } from 'lucide-react'

interface ISEDeploymentModalProps {
  isOpen: boolean
  onClose: () => void
  onDeploy: (config: {
    ise_url: string
    ise_username: string
    ise_password: string
    verify_ssl: boolean
    create_sgt_if_missing: boolean
  }) => Promise<void>
  recommendationName?: string
}

export default function ISEDeploymentModal({
  isOpen,
  onClose,
  onDeploy,
  recommendationName,
}: ISEDeploymentModalProps) {
  const [iseUrl, setIseUrl] = useState('https://192.168.10.31:9060')
  const [iseUsername, setIseUsername] = useState('admin')
  const [isePassword, setIsePassword] = useState('C!sco#123')
  const [verifySsl, setVerifySsl] = useState(false)
  const [createSgtIfMissing, setCreateSgtIfMissing] = useState(true)
  const [isDeploying, setIsDeploying] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleDeploy = async () => {
    if (!iseUrl || !iseUsername || !isePassword) {
      setError('Please fill in all required fields')
      return
    }

    setIsDeploying(true)
    setError(null)

    try {
      await onDeploy({
        ise_url: iseUrl,
        ise_username: iseUsername,
        ise_password: isePassword,
        verify_ssl: verifySsl,
        create_sgt_if_missing: createSgtIfMissing,
      })
      onClose()
    } catch (err: any) {
      setError(err.message || 'Failed to deploy to ISE')
    } finally {
      setIsDeploying(false)
    }
  }

  const handleCancel = () => {
    setError(null)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Deploy to ISE</h2>
          <button
            onClick={handleCancel}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={isDeploying}
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {recommendationName && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p className="text-sm text-blue-800">
                <strong>Policy:</strong> {recommendationName}
              </p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start space-x-2">
              <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            {/* ISE URL */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Server className="h-4 w-4 inline mr-1" />
                ISE Server URL
              </label>
              <input
                type="text"
                value={iseUrl}
                onChange={(e) => setIseUrl(e.target.value)}
                placeholder="https://192.168.10.31:9060"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isDeploying}
              />
              <p className="text-xs text-gray-500 mt-1">
                ERS API typically runs on port 9060
              </p>
            </div>

            {/* ISE Username */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Key className="h-4 w-4 inline mr-1" />
                Username
              </label>
              <input
                type="text"
                value={iseUsername}
                onChange={(e) => setIseUsername(e.target.value)}
                placeholder="admin"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isDeploying}
              />
            </div>

            {/* ISE Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Lock className="h-4 w-4 inline mr-1" />
                Password
              </label>
              <input
                type="password"
                value={isePassword}
                onChange={(e) => setIsePassword(e.target.value)}
                placeholder="Enter ISE admin password"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isDeploying}
              />
            </div>

            {/* Options */}
            <div className="space-y-2 pt-2">
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={verifySsl}
                  onChange={(e) => setVerifySsl(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  disabled={isDeploying}
                />
                <span className="text-sm text-gray-700">Verify SSL certificates</span>
              </label>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={createSgtIfMissing}
                  onChange={(e) => setCreateSgtIfMissing(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  disabled={isDeploying}
                />
                <span className="text-sm text-gray-700">Create SGT if it doesn't exist</span>
              </label>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 bg-gray-50">
          <button
            onClick={handleCancel}
            disabled={isDeploying}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            onClick={handleDeploy}
            disabled={isDeploying || !iseUrl || !iseUsername || !isePassword}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {isDeploying ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Deploying...</span>
              </>
            ) : (
              <>
                <CheckCircle className="h-4 w-4" />
                <span>Deploy to ISE</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

