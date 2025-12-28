import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'
import { apiClient } from '../lib/api'
import { useQuery } from '@tanstack/react-query'

interface FlowGraphNode {
  id: string
  label: string
  node_type: string
  ip_address?: string
  mac_address?: string
  device_name?: string
  device_type?: string
  user_name?: string
  cluster_id?: number
  cluster_label?: string
  sgt_value?: number
  location_path?: string
  switch_id?: string
  flow_count: number
  bytes_in: number
  bytes_out: number
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

interface FlowGraphLink {
  source: string | FlowGraphNode
  target: string | FlowGraphNode
  flow_count: number
  total_bytes: number
  protocols: number[]
  top_ports: string[]
}

interface FlowGraphProps {
  limit?: number
  onNodeClick?: (node: FlowGraphNode | null) => void
}

export default function FlowGraph({ limit = 500, onNodeClick }: FlowGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const simulationRef = useRef<d3.Simulation<FlowGraphNode, FlowGraphLink> | null>(null)
  const [selectedNode, setSelectedNode] = useState<FlowGraphNode | null>(null)
  const [hoveredNode, setHoveredNode] = useState<FlowGraphNode | null>(null)
  const [isPaused, setIsPaused] = useState(false)

  // Get flow graph data from API
  const { data: graphData, isLoading } = useQuery({
    queryKey: ['flowGraph', limit],
    queryFn: async () => {
      const response = await apiClient.getFlowGraphData(limit)
      return response.data
    },
  })

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || !graphData || isLoading) return

    const container = containerRef.current
    const width = container.clientWidth
    const height = Math.max(600, window.innerHeight * 0.7)

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    // Set up zoom behavior - require Ctrl/Cmd+wheel for zoom, allow page scrolling
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .filter((event) => {
        // Only allow zoom with Ctrl/Cmd+wheel to prevent interference with page scrolling
        if (event.type === 'wheel') {
          return (event as WheelEvent).ctrlKey || (event as WheelEvent).metaKey
        }
        // Disable drag-to-pan on background to prevent conflicts with page scrolling
        return false
      })
      .on('zoom', (evt) => {
        g.attr('transform', evt.transform)
      })

    svg
      .attr('width', width)
      .attr('height', height)
      .call(zoom as any)

    // Create container group for zoom/pan
    const g = svg.append('g')

    // Create tooltip div
    const tooltip = d3
      .select('body')
      .append('div')
      .attr('class', 'flow-graph-tooltip')
      .style('opacity', 0)
      .style('position', 'absolute')
      .style('background', 'rgba(0, 0, 0, 0.85)')
      .style('color', 'white')
      .style('padding', '10px')
      .style('border-radius', '6px')
      .style('pointer-events', 'none')
      .style('font-size', '12px')
      .style('z-index', 1000)
      .style('max-width', '300px')
      .style('box-shadow', '0 4px 6px rgba(0,0,0,0.3)')

    const nodes: FlowGraphNode[] = graphData.nodes || []
    const links: FlowGraphLink[] = graphData.links || []

    // Convert string IDs to node objects for links
    const nodesMap = new Map<string, FlowGraphNode>()
    nodes.forEach((node) => {
      nodesMap.set(node.id, node)
    })

    // Convert link source/target strings to node objects
    const linkData = links.map((link) => ({
      source: nodesMap.get(typeof link.source === 'string' ? link.source : link.source.id) || link.source,
      target: nodesMap.get(typeof link.target === 'string' ? link.target : link.target.id) || link.target,
      flow_count: link.flow_count,
      total_bytes: link.total_bytes,
      protocols: link.protocols,
      top_ports: link.top_ports,
    })).filter((l) => l.source && l.target)

    // Color scale for device types
    const deviceTypeColors: Record<string, string> = {
      server: '#3b82f6', // blue
      laptop: '#10b981', // green
      printer: '#f59e0b', // amber
      iot: '#8b5cf6', // purple
      mobile: '#ec4899', // pink
    }

    const defaultColor = '#6b7280' // gray

    // Create force simulation with lower alpha to stabilize faster
    const simulation = d3
      .forceSimulation<FlowGraphNode>(nodes)
      .force(
        'link',
        d3
          .forceLink<FlowGraphNode, FlowGraphLink>(linkData)
          .id((d) => d.id)
          .distance((link) => {
            // Distance based on flow count (more flows = closer)
            const linkFlowCount = (link as FlowGraphLink).flow_count || 0
            return 80 + (120 / (1 + Math.log(linkFlowCount + 1)))
          })
      )
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius((node) => Math.sqrt((node as FlowGraphNode).flow_count) * 5 + 25))
      .alpha(1)
      .alphaDecay(0.0228) // Faster decay for quicker stabilization
      .alphaMin(0.001) // Lower minimum to stop sooner

    simulationRef.current = simulation

    // Stop simulation after it stabilizes (or pause it when needed)
    simulation.on('end', () => {
      setIsPaused(true)
    })

    // Draw links
    const link = g
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(linkData)
      .enter()
      .append('line')
      .attr('stroke', '#94a3b8')
      .attr('stroke-width', (d) => Math.sqrt(d.flow_count) * 1.5 + 1)
      .attr('stroke-opacity', 0.4)
      .attr('marker-end', 'url(#arrowhead)')
      .style('pointer-events', 'none') // Links shouldn't intercept mouse events

    // Add arrowhead marker
    svg
      .append('defs')
      .append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 25)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#94a3b8')

    // Draw nodes
    const node = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('circle')
      .data(nodes)
      .enter()
      .append('circle')
      .attr('r', (d) => Math.sqrt(d.flow_count) * 3 + 10)
      .attr('fill', (d) => {
        if (d.device_type && deviceTypeColors[d.device_type]) {
          return deviceTypeColors[d.device_type]
        }
        return defaultColor
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .on('mouseover', function (event, d) {
        // Pause simulation when hovering to prevent movement
        if (simulationRef.current) {
          simulationRef.current.alphaTarget(0).restart()
          // Fix the hovered node position temporarily
          d.fx = d.x
          d.fy = d.y
        }
        
        setHoveredNode(d)
        tooltip.transition().duration(150).style('opacity', 0.95)
        tooltip
          .html(`
            <div style="font-weight: bold; margin-bottom: 6px; font-size: 13px;">${d.device_name || d.label}</div>
            ${d.ip_address ? `<div style="margin-bottom: 3px;">📍 IP: <span style="font-family: monospace;">${d.ip_address}</span></div>` : ''}
            ${d.mac_address ? `<div style="margin-bottom: 3px;">🔗 MAC: <span style="font-family: monospace; font-size: 11px;">${d.mac_address}</span></div>` : ''}
            ${d.device_type ? `<div style="margin-bottom: 3px;">💻 Type: ${d.device_type}</div>` : ''}
            ${d.user_name ? `<div style="margin-bottom: 3px;">👤 User: ${d.user_name}</div>` : ''}
            ${d.cluster_label ? `<div style="margin-bottom: 3px;">📦 Cluster: ${d.cluster_label}</div>` : ''}
            ${d.sgt_value !== null && d.sgt_value !== undefined ? `<div style="margin-bottom: 3px;">🏷️ SGT: ${d.sgt_value}</div>` : ''}
            ${d.location_path ? `<div style="margin-bottom: 3px;">🏢 Location: ${d.location_path}</div>` : ''}
            ${d.switch_id ? `<div style="margin-bottom: 3px;">🔌 Switch: ${d.switch_id}</div>` : ''}
            <div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.3);">
              <div style="margin-bottom: 2px;">📊 Flows: ${d.flow_count.toLocaleString()}</div>
              <div>⬇️ ${formatBytes(d.bytes_in)} | ⬆️ ${formatBytes(d.bytes_out)}</div>
            </div>
          `)
          .style('left', event.pageX + 15 + 'px')
          .style('top', event.pageY - 10 + 'px')
        
        // Highlight node
        d3.select(this).attr('stroke-width', 4).attr('stroke', '#3b82f6')
      })
      .on('mousemove', (event) => {
        tooltip
          .style('left', event.pageX + 15 + 'px')
          .style('top', event.pageY - 10 + 'px')
      })
      .on('mouseout', function (_event, d) {
        // Unfix node position when not hovering
        d.fx = null
        d.fy = null
        
        setHoveredNode(null)
        tooltip.transition().duration(200).style('opacity', 0)
        
        // Reset highlight unless it's selected
        if (selectedNode?.id !== d.id) {
          d3.select(this).attr('stroke-width', 2).attr('stroke', '#fff')
        }
      })
      .on('click', function (event, d) {
        event.stopPropagation()
        
        // Fix selected node position
        if (selectedNode && selectedNode.id === d.id) {
          // Deselect
          setSelectedNode(null)
          d.fx = null
          d.fy = null
          // Notify parent component
          if (onNodeClick) {
            onNodeClick(null)
          }
        } else {
          // Select new node
          if (selectedNode) {
            // Unfix previous selection
            const prevNode = nodes.find((n) => n.id === selectedNode.id)
            if (prevNode) {
              prevNode.fx = null
              prevNode.fy = null
            }
          }
          setSelectedNode(d)
          d.fx = d.x
          d.fy = d.y
          // Notify parent component
          if (onNodeClick) {
            onNodeClick(d)
          }
        }
        
        // Stop simulation movement
        if (simulationRef.current) {
          simulationRef.current.alphaTarget(0).restart()
        }
      })
      .call(
        d3
          .drag<SVGCircleElement, FlowGraphNode>()
          .filter((event) => {
            // Only allow dragging with left mouse button (not during zoom/pan)
            // Don't interfere with page scrolling or text selection
            return (event as MouseEvent).button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey
          })
          .on('start', function (event, d) {
            event.sourceEvent?.preventDefault() // Prevent text selection
            if (!event.active && simulationRef.current) {
              simulationRef.current.alphaTarget(0.3).restart()
            }
            d.fx = d.x
            d.fy = d.y
          })
          .on('drag', function (event, d) {
            event.sourceEvent?.preventDefault() // Prevent text selection
            d.fx = event.x
            d.fy = event.y
            if (simulationRef.current) {
              simulationRef.current.alphaTarget(0.3).restart()
            }
          })
          .on('end', function (event, _d) {
            if (!event.active && simulationRef.current) {
              simulationRef.current.alphaTarget(0)
            }
            // Keep position fixed after drag
            // User can click again to unfix if needed
          })
      )

    // Add labels
    const label = g
      .append('g')
      .attr('class', 'labels')
      .selectAll('text')
      .data(nodes)
      .enter()
      .append('text')
      .text((d) => d.label)
      .attr('font-size', '11px')
      .attr('fill', '#374151')
      .attr('text-anchor', 'middle')
      .attr('pointer-events', 'none')
      .style('user-select', 'none')
      .style('font-weight', (d) => (hoveredNode?.id === d.id || selectedNode?.id === d.id ? 'bold' : 'normal'))
      .style('font-size', (d) => (hoveredNode?.id === d.id || selectedNode?.id === d.id ? '13px' : '11px'))

    // Update selected node styling
    node.style('stroke-width', (d) => {
      if (selectedNode?.id === d.id) return 4
      if (hoveredNode?.id === d.id) return 4
      return 2
    }).style('stroke', (d) => {
      if (selectedNode?.id === d.id) return '#3b82f6'
      if (hoveredNode?.id === d.id) return '#3b82f6'
      return '#fff'
    })

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => (d.source as FlowGraphNode).x || 0)
        .attr('y1', (d: any) => (d.source as FlowGraphNode).y || 0)
        .attr('x2', (d: any) => (d.target as FlowGraphNode).x || 0)
        .attr('y2', (d: any) => (d.target as FlowGraphNode).y || 0)

      node
        .attr('cx', (d) => d.x || 0)
        .attr('cy', (d) => d.y || 0)

      label
        .attr('x', (d) => d.x || 0)
        .attr('y', (d) => (d.y || 0) + 28)
    })

    // Cleanup
    return () => {
      tooltip.remove()
      if (simulationRef.current) {
        simulationRef.current.stop()
      }
    }
  }, [graphData, isLoading, selectedNode, limit])

  // Update hovered node styling when selection changes
  useEffect(() => {
    if (!svgRef.current) return
    
    const svg = d3.select(svgRef.current)
    const node = svg.selectAll<SVGCircleElement, FlowGraphNode>('.nodes circle')
    
    node
      .style('stroke-width', (d) => {
        if (selectedNode?.id === d.id) return 4
        if (hoveredNode?.id === d.id) return 4
        return 2
      })
      .style('stroke', (d) => {
        if (selectedNode?.id === d.id) return '#3b82f6'
        if (hoveredNode?.id === d.id) return '#3b82f6'
        return '#fff'
      })
  }, [selectedNode, hoveredNode])

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const handleZoomIn = () => {
    if (!svgRef.current) return
    const svg = d3.select(svgRef.current)
    svg.transition().duration(200).call((d3.zoom<SVGSVGElement, unknown>() as any).scaleBy, 1.5)
  }

  const handleZoomOut = () => {
    if (!svgRef.current) return
    const svg = d3.select(svgRef.current)
    svg.transition().duration(200).call((d3.zoom<SVGSVGElement, unknown>() as any).scaleBy, 1 / 1.5)
  }

  const handleResetZoom = () => {
    if (!svgRef.current) return
    const svg = d3.select(svgRef.current)
    svg.transition().duration(750).call((d3.zoom<SVGSVGElement, unknown>() as any).transform, d3.zoomIdentity)
  }

  if (isLoading) {
    return (
      <div className="w-full h-96 flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200">
        <div className="text-gray-500">Loading flow graph...</div>
      </div>
    )
  }

  return (
    <div className="w-full space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        {/* Device Type Legend */}
        <div className="flex items-center flex-wrap gap-4 text-sm text-gray-600">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span>Server</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span>Laptop</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-amber-500"></div>
            <span>Printer</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-purple-500"></div>
            <span>IoT</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-pink-500"></div>
            <span>Mobile</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-gray-500"></div>
            <span>Other</span>
          </div>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleZoomIn}
            className="px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-clarion-blue"
            title="Zoom In"
          >
            +
          </button>
          <button
            onClick={handleZoomOut}
            className="px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-clarion-blue"
            title="Zoom Out"
          >
            −
          </button>
          <button
            onClick={handleResetZoom}
            className="px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-clarion-blue"
            title="Reset Zoom"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Instructions */}
      <div className="text-xs text-gray-500 bg-blue-50 border border-blue-200 rounded-md p-2">
        💡 <strong>Controls:</strong> Ctrl/Cmd + Scroll to zoom • Drag nodes to reposition • Click node for details • Hover for info • Use zoom buttons below
        {isPaused && <span className="ml-2 text-green-600">• Graph stabilized</span>}
      </div>

      {/* Graph Container */}
      <div
        ref={containerRef}
        className="w-full border border-gray-200 rounded-lg bg-white overflow-hidden relative"
        style={{ height: '70vh', minHeight: '600px' }}
      >
        <svg 
          ref={svgRef} 
          className="w-full h-full" 
          style={{ cursor: 'default', touchAction: 'none' }}
          onWheel={(e) => {
            // Allow page scrolling when not holding Ctrl/Cmd
            // D3 zoom filter will handle Ctrl/Cmd+wheel
            if (!e.ctrlKey && !e.metaKey) {
              // Let the event bubble up for normal page scrolling
              return
            }
          }}
        />
      </div>

      {/* Selected Node Info */}
      {selectedNode && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-blue-900">Selected Device</h3>
            <button
              onClick={() => {
                if (selectedNode) {
                  selectedNode.fx = null
                  selectedNode.fy = null
                }
                setSelectedNode(null)
                // Notify parent component
                if (onNodeClick) {
                  onNodeClick(null)
                }
              }}
              className="text-blue-600 hover:text-blue-800 text-xl leading-none"
            >
              ×
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Name:</span>
              <div className="font-medium">{selectedNode.device_name || selectedNode.label}</div>
            </div>
            <div>
              <span className="text-gray-600">IP:</span>
              <div className="font-mono font-medium">{selectedNode.ip_address}</div>
            </div>
            {selectedNode.user_name && (
              <div>
                <span className="text-gray-600">User:</span>
                <div className="font-medium">{selectedNode.user_name}</div>
              </div>
            )}
            {selectedNode.cluster_label && (
              <div>
                <span className="text-gray-600">Cluster:</span>
                <div className="font-medium">{selectedNode.cluster_label}</div>
              </div>
            )}
            {selectedNode.sgt_value !== null && selectedNode.sgt_value !== undefined && (
              <div>
                <span className="text-gray-600">SGT:</span>
                <div className="font-medium">{selectedNode.sgt_value}</div>
              </div>
            )}
            {selectedNode.location_path && (
              <div className="col-span-2">
                <span className="text-gray-600">Location:</span>
                <div className="font-medium">{selectedNode.location_path}</div>
              </div>
            )}
            <div>
              <span className="text-gray-600">Flows:</span>
              <div className="font-medium">{selectedNode.flow_count.toLocaleString()}</div>
            </div>
            <div>
              <span className="text-gray-600">Traffic:</span>
              <div className="font-medium">
                {formatBytes(selectedNode.bytes_in + selectedNode.bytes_out)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
