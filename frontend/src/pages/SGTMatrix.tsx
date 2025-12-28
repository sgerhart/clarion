import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Plot from 'react-plotly.js'
import { apiClient, SGTMatrixCell } from '../lib/api'
import { RefreshCw } from 'lucide-react'

export default function SGTMatrix() {
  const queryClient = useQueryClient()
  const [matrixData, setMatrixData] = useState<any>(null)

  const buildMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.buildMatrix()
      return response.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['matrix'] })
      if (data?.matrix) {
        processMatrixData(data.matrix)
      }
    },
  })

  // Matrix response query (disabled, only used for manual refresh)
  useQuery({
    queryKey: ['matrix'],
    queryFn: () => apiClient.getMatrix(),
    enabled: false, // Only fetch when explicitly requested
  })

  const processMatrixData = (data: any) => {
    const cells: SGTMatrixCell[] = data.cells || []
    const sgtList = Array.from(
      new Set([...cells.map((c) => c.src_sgt), ...cells.map((c) => c.dst_sgt)])
    ).sort((a, b) => a - b)

    const matrix: number[][] = []
    const labels: string[] = []

    sgtList.forEach((srcSgt) => {
      const row: number[] = []
      sgtList.forEach((dstSgt) => {
        const cell = cells.find((c) => c.src_sgt === srcSgt && c.dst_sgt === dstSgt)
        row.push(cell?.total_flows || 0)
      })
      matrix.push(row)
      labels.push(`SGT-${srcSgt}`)
    })

    setMatrixData({ matrix, labels, cells, sgtList })
  }

  const handleBuild = () => {
    buildMutation.mutate()
  }

  if (matrixData) {
    const { matrix, labels, cells, sgtList } = matrixData
    const totalFlows = cells.reduce((sum: number, c: SGTMatrixCell) => sum + c.total_flows, 0)

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">SGT Communication Matrix</h1>
            <p className="text-gray-600 mt-1">
              Visualize traffic patterns between Security Group Tags
            </p>
          </div>
          <button
            onClick={handleBuild}
            disabled={buildMutation.isPending}
            className="flex items-center space-x-2 px-4 py-2 bg-clarion-blue text-white rounded-lg hover:bg-opacity-90 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${buildMutation.isPending ? 'animate-spin' : ''}`} />
            <span>Rebuild Matrix</span>
          </button>
        </div>

        <div className="grid grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-600">Matrix Cells</p>
            <p className="text-2xl font-bold text-gray-900">{cells.length}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-600">Unique SGTs</p>
            <p className="text-2xl font-bold text-gray-900">{sgtList.length}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-600">Total Flows</p>
            <p className="text-2xl font-bold text-gray-900">{totalFlows.toLocaleString()}</p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            SGT × SGT Heatmap
          </h2>
          <Plot
            data={[
              {
                z: matrix,
                x: labels,
                y: labels,
                type: 'heatmap',
                colorscale: 'Viridis',
                showscale: true,
                colorbar: {
                  title: 'Flows',
                },
              },
            ]}
            layout={{
              width: 800,
              height: 700,
              title: 'SGT Communication Matrix',
              xaxis: { title: 'Destination SGT' },
              yaxis: { title: 'Source SGT' },
            }}
            config={{ responsive: true }}
          />
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Matrix Details</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Source SGT
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Dest SGT
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Flows
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Bytes
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Top Ports
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {cells
                  .sort((a, b) => b.total_flows - a.total_flows)
                  .map((cell, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {cell.src_sgt} ({cell.src_sgt_name})
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {cell.dst_sgt} ({cell.dst_sgt_name})
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {cell.total_flows.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {(cell.total_bytes / 1024 / 1024).toFixed(2)} MB
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {cell.top_ports || '-'}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">SGT Communication Matrix</h1>
        <p className="text-gray-600 mt-1">
          Visualize traffic patterns between Security Group Tags
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center">
        <p className="text-gray-500 mb-4">
          Click the button below to build the SGT communication matrix
        </p>
        <button
          onClick={handleBuild}
          disabled={buildMutation.isPending}
          className="flex items-center space-x-2 px-6 py-3 bg-clarion-blue text-white rounded-lg hover:bg-opacity-90 disabled:opacity-50 mx-auto"
        >
          <RefreshCw className={`h-5 w-5 ${buildMutation.isPending ? 'animate-spin' : ''}`} />
          <span>{buildMutation.isPending ? 'Building Matrix...' : 'Build/Refresh Matrix'}</span>
        </button>
        {buildMutation.isError && (
          <p className="text-red-500 mt-4">
            Error building matrix. Please try again.
          </p>
        )}
      </div>
    </div>
  )
}

