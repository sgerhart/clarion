import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../lib/api'
import { Play, Download } from 'lucide-react'

export default function PolicyBuilder() {
  const [selectedPolicyIdx, setSelectedPolicyIdx] = useState<number>(0)
  const queryClient = useQueryClient()

  const generateMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.generatePolicies()
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] })
    },
  })

  const { data: policiesData } = useQuery({
    queryKey: ['policies'],
    queryFn: async () => {
      const response = await apiClient.getPolicies()
      return response.data
    },
  })

  const policies = policiesData?.policies || []

  const selectedPolicy = policies[selectedPolicyIdx]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">SGACL Policy Builder</h1>
          <p className="text-gray-600 mt-1">
            Build and customize Security Group Access Control Lists
          </p>
        </div>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="flex items-center space-x-2 px-4 py-2 bg-clarion-blue text-white rounded-lg hover:bg-opacity-90 disabled:opacity-50"
        >
          <Play className="h-4 w-4" />
          <span>
            {generateMutation.isPending ? 'Generating...' : 'Generate Policies'}
          </span>
        </button>
      </div>

      {policies.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center">
          <p className="text-gray-500 mb-4">
            No policies found. Generate policies from the SGT matrix first.
          </p>
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="px-6 py-3 bg-clarion-blue text-white rounded-lg hover:bg-opacity-90 disabled:opacity-50"
          >
            Generate Policies
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Policies</h2>
              <div className="space-y-2">
                {policies.map((policy: any, idx: number) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedPolicyIdx(idx)}
                    className={`
                      w-full text-left px-4 py-3 rounded-lg transition-colors
                      ${
                        selectedPolicyIdx === idx
                          ? 'bg-clarion-blue text-white'
                          : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                      }
                    `}
                  >
                    <div className="font-medium">{policy.name}</div>
                    <div className="text-sm opacity-75">
                      SGT {policy.src_sgt} → SGT {policy.dst_sgt}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="lg:col-span-2">
            {selectedPolicy && (
              <div className="space-y-6">
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div>
                      <p className="text-sm text-gray-600">Source SGT</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {selectedPolicy.src_sgt}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Dest SGT</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {selectedPolicy.dst_sgt}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Action</p>
                      <p className="text-2xl font-bold text-gray-900 uppercase">
                        {selectedPolicy.action}
                      </p>
                    </div>
                  </div>
                  <p className="text-gray-700">
                    <span className="font-medium">Policy Name:</span> {selectedPolicy.name}
                  </p>
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">SGACL Rules</h2>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Action
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Protocol
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Source Port
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Dest Port
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Description
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {selectedPolicy.rules?.map((rule: any, idx: number) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {rule.action}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {rule.protocol}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {rule.src_port || 'Any'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {rule.dst_port || 'Any'}
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-500">
                              {rule.description || '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Export Policy</h2>
                  <div className="space-y-4">
                    <select className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-clarion-blue">
                      <option>Cisco CLI</option>
                      <option>ISE JSON</option>
                      <option>JSON</option>
                    </select>
                    <button className="flex items-center space-x-2 px-4 py-2 bg-clarion-blue text-white rounded-lg hover:bg-opacity-90">
                      <Download className="h-4 w-4" />
                      <span>Export</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

