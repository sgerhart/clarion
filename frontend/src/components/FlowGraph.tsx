import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { NetFlowRecord } from '../lib/api'

interface FlowGraphProps {
  flows: NetFlowRecord[]
}

export default function FlowGraph({ flows }: FlowGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current || flows.length === 0) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const width = svgRef.current.clientWidth || 800
    const height = 600
    svg.attr('width', width).attr('height', height)

    // Build graph
    const nodes = new Map<string, { id: string; flows: number }>()
    const links: Array<{ source: string; target: string; flows: number; bytes: number }> = []

    flows.forEach((flow) => {
      const src = flow.src_ip
      const dst = flow.dst_ip

      if (!nodes.has(src)) {
        nodes.set(src, { id: src, flows: 0 })
      }
      if (!nodes.has(dst)) {
        nodes.set(dst, { id: dst, flows: 0 })
      }

      nodes.get(src)!.flows++
      nodes.get(dst)!.flows++

      const existingLink = links.find((l) => l.source === src && l.target === dst)
      if (existingLink) {
        existingLink.flows++
        existingLink.bytes += flow.bytes
      } else {
        links.push({ source: src, target: dst, flows: 1, bytes: flow.bytes })
      }
    })

    const nodeArray = Array.from(nodes.values())
    const linkArray = links

    // Create force simulation
    const simulation = d3
      .forceSimulation(nodeArray)
      .force(
        'link',
        d3
          .forceLink(linkArray)
          .id((d: any) => d.id)
          .distance(100)
      )
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))

    // Draw links
    const link = svg
      .append('g')
      .selectAll('line')
      .data(linkArray)
      .enter()
      .append('line')
      .attr('stroke', '#94a3b8')
      .attr('stroke-width', (d) => Math.sqrt(d.flows) * 2)
      .attr('stroke-opacity', 0.6)

    // Draw nodes
    const node = svg
      .append('g')
      .selectAll('circle')
      .data(nodeArray)
      .enter()
      .append('circle')
      .attr('r', (d) => Math.sqrt(d.flows) * 3 + 5)
      .attr('fill', '#3b82f6')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .call(
        d3
          .drag<any, any>()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended)
      )

    // Add labels
    const label = svg
      .append('g')
      .selectAll('text')
      .data(nodeArray)
      .enter()
      .append('text')
      .text((d) => d.id.split('.').pop() || d.id)
      .attr('font-size', '10px')
      .attr('fill', '#374151')
      .attr('text-anchor', 'middle')
      .attr('dy', 20)

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y)

      node.attr('cx', (d: any) => d.x).attr('cy', (d: any) => d.y)

      label.attr('x', (d: any) => d.x).attr('y', (d: any) => d.y)
    })

    function dragstarted(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart()
      d.fx = d.x
      d.fy = d.y
    }

    function dragged(event: any, d: any) {
      d.fx = event.x
      d.fy = event.y
    }

    function dragended(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0)
      d.fx = null
      d.fy = null
    }
  }, [flows])

  return (
    <div className="w-full">
      <svg ref={svgRef} className="w-full border border-gray-200 rounded-lg" />
    </div>
  )
}

