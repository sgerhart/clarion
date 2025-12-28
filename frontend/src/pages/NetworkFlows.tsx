import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient, NetFlowRecord } from '../lib/api'
import FlowGraph from '../components/FlowGraph'
import FlowTable from '../components/FlowTable'

export default function NetworkFlows() {
  const [limit, setLimit] = useState(1000)
  const [protocolFilter, setProtocolFilter] = useState<string>('All')
  const [srcDevice, setSrcDevice] = useState('')
  const [dstDevice, setDstDevice] = useState('')
  const [selectedNode, setSelectedNode] = useState<{ ip_address?: string; mac_address?: string } | null>(null)

  const { data: flowsData, isLoading } = useQuery({
    queryKey: ['netflow', limit],
    queryFn: async () => {
      const response = await apiClient.getNetFlow(limit)
      return response.data
    },
  })

  const flows: NetFlowRecord[] = flowsData?.records || []

  const protocolMap: Record<number, string> = {
    6: 'TCP',
    17: 'UDP',
    1: 'ICMP',
  }

  const filteredFlows = flows.filter((flow) => {
    if (protocolFilter !== 'All') {
      const protoName = protocolMap[flow.protocol] || ''
      if (protoName !== protocolFilter) return false
    }
    if (srcDevice && !flow.src_ip.includes(srcDevice)) return false
    if (dstDevice && !flow.dst_ip.includes(dstDevice)) return false
    
    // Filter by selected node (if a node is selected in the graph)
    if (selectedNode) {
      let matchesSelectedNode = false
      
      // Match by IP address
      if (selectedNode.ip_address) {
        matchesSelectedNode = flow.src_ip === selectedNode.ip_address || flow.dst_ip === selectedNode.ip_address
      }
      
      // Match by MAC address if IP didn't match and MAC is available
      if (!matchesSelectedNode && selectedNode.mac_address) {
        matchesSelectedNode = Boolean(
          (flow.src_mac && flow.src_mac === selectedNode.mac_address) ||
          (flow.dst_mac && flow.dst_mac === selectedNode.mac_address)
        )
      }
      
      if (!matchesSelectedNode) return false
    }
    
    return true
  })

  const totalBytes = filteredFlows.reduce((sum, f) => sum + f.bytes, 0)
  const uniqueSrcIPs = new Set(filteredFlows.map((f) => f.src_ip)).size
  const uniqueDstIPs = new Set(filteredFlows.map((f) => f.dst_ip)).size

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Network Flows</h1>
        <p className="text-gray-600 mt-1">
          Device-to-device traffic flows with metadata
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max Flows
            </label>
            <input
              type="number"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
              min={100}
              max={10000}
              step={100}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Protocol
            </label>
            <select
              value={protocolFilter}
              onChange={(e) => setProtocolFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
            >
              <option>All</option>
              <option>TCP</option>
              <option>UDP</option>
              <option>ICMP</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source Device (IP)
            </label>
            <input
              type="text"
              value={srcDevice}
              onChange={(e) => setSrcDevice(e.target.value)}
              placeholder="e.g., 10.0.0.1"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Destination Device (IP)
            </label>
            <input
              type="text"
              value={dstDevice}
              onChange={(e) => setDstDevice(e.target.value)}
              placeholder="e.g., 10.0.0.2"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-clarion-blue focus:border-transparent"
            />
          </div>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p className="text-sm text-gray-600">Total Flows</p>
          <p className="text-2xl font-bold text-gray-900">
            {filteredFlows.length.toLocaleString()}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p className="text-sm text-gray-600">Unique Source IPs</p>
          <p className="text-2xl font-bold text-gray-900">{uniqueSrcIPs}</p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p className="text-sm text-gray-600">Unique Dest IPs</p>
          <p className="text-2xl font-bold text-gray-900">{uniqueDstIPs}</p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p className="text-sm text-gray-600">Total Bytes</p>
          <p className="text-2xl font-bold text-gray-900">
            {(totalBytes / 1024 / 1024).toFixed(2)} MB
          </p>
        </div>
      </div>

      {/* Flow Graph */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Flow Graph Visualization
          </h2>
          {selectedNode && (
            <div className="text-sm text-blue-600 bg-blue-50 px-3 py-1 rounded-md">
              Showing flows for: {selectedNode.ip_address || selectedNode.mac_address}
              <button
                onClick={() => setSelectedNode(null)}
                className="ml-2 text-blue-800 hover:text-blue-900"
              >
                × Clear filter
              </button>
            </div>
          )}
        </div>
        <FlowGraph 
          limit={limit} 
          onNodeClick={(node) => {
            if (node) {
              setSelectedNode({
                ip_address: node.ip_address,
                mac_address: node.mac_address,
              })
            } else {
              setSelectedNode(null)
            }
          }}
        />
      </div>

      {/* Flow Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Flow Details (5/9-tuple)
        </h2>
        {isLoading ? (
          <div className="text-center py-8 text-gray-500">Loading flows...</div>
        ) : filteredFlows.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No flows found. Load data or connect edge agents.
          </div>
        ) : (
          <FlowTable flows={filteredFlows} />
        )}
      </div>
    </div>
  )
}

