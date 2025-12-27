import { NetFlowRecord } from '../lib/api'

interface FlowTableProps {
  flows: NetFlowRecord[]
}

const protocolMap: Record<number, string> = {
  6: 'TCP',
  17: 'UDP',
  1: 'ICMP',
}

const portServiceMap: Record<number, string> = {
  80: 'HTTP',
  443: 'HTTPS',
  22: 'SSH',
  23: 'Telnet',
  25: 'SMTP',
  53: 'DNS',
  3306: 'MySQL',
  5432: 'PostgreSQL',
  3389: 'RDP',
  445: 'SMB',
  21: 'FTP',
  8080: 'HTTP-Alt',
}

export default function FlowTable({ flows }: FlowTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Source IP
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Dest IP
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Src Port
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Dst Port
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Protocol
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Service
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Bytes
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Packets
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Time
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {flows.slice(0, 100).map((flow, idx) => (
            <tr key={idx} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                {flow.src_ip}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                {flow.dst_ip}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {flow.src_port || '-'}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {flow.dst_port || '-'}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {protocolMap[flow.protocol] || `Proto-${flow.protocol}`}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {portServiceMap[flow.dst_port] || `Port-${flow.dst_port}`}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {flow.bytes.toLocaleString()}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {flow.packets.toLocaleString()}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {new Date(flow.flow_start * 1000).toLocaleTimeString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {flows.length > 100 && (
        <div className="px-6 py-4 text-sm text-gray-500 text-center">
          Showing first 100 of {flows.length} flows
        </div>
      )}
    </div>
  )
}


