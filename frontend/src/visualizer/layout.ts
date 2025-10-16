import ELK, { ElkNode, ElkExtendedEdge } from 'elkjs/lib/elk.bundled.js'
import { Node, Edge } from 'reactflow'

const elk = new ELK()

// ELK layout options
const elkOptions = {
  'elk.algorithm': 'layered',
  'elk.layered.spacing.nodeNodeBetweenLayers': '100',
  'elk.spacing.nodeNode': '80',
  'elk.direction': 'RIGHT',
  'elk.layered.nodePlacement.strategy': 'SIMPLE',
  'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP'
}

export interface LayoutOptions {
  direction?: 'RIGHT' | 'DOWN' | 'LEFT' | 'UP'
  spacing?: number
}

/**
 * Apply ELK automatic layout to a graph
 */
export async function applyAutoLayout(
  nodes: Node[],
  edges: Edge[],
  options: LayoutOptions = {}
): Promise<Node[]> {
  const direction = options.direction || 'RIGHT'
  const spacing = options.spacing || 80

  // Convert React Flow nodes/edges to ELK format
  const elkNodes: ElkNode[] = nodes.map(node => ({
    id: node.id,
    width: getNodeWidth(node.type),
    height: getNodeHeight(node.type),
    // Pass through data
    properties: { ...node.data }
  }))

  const elkEdges: ElkExtendedEdge[] = edges.map(edge => ({
    id: edge.id,
    sources: [edge.source],
    targets: [edge.target]
  }))

  const graph: ElkNode = {
    id: 'root',
    layoutOptions: {
      ...elkOptions,
      'elk.direction': direction,
      'elk.spacing.nodeNode': spacing.toString()
    },
    children: elkNodes,
    edges: elkEdges
  }

  try {
    const layoutedGraph = await elk.layout(graph)

    // Convert back to React Flow nodes with new positions
    const layoutedNodes = nodes.map(node => {
      const elkNode = layoutedGraph.children?.find(n => n.id === node.id)
      if (elkNode && elkNode.x !== undefined && elkNode.y !== undefined) {
        return {
          ...node,
          position: {
            x: elkNode.x,
            y: elkNode.y
          }
        }
      }
      return node
    })

    return layoutedNodes
  } catch (error) {
    console.error('ELK layout failed:', error)
    return nodes // Return original nodes if layout fails
  }
}

/**
 * Get node width based on type
 */
function getNodeWidth(type: string | undefined): number {
  switch (type) {
    case 'sheet':
      return 200
    case 'model':
      return 180
    case 'field':
      return 160
    case 'transform':
      return 150
    case 'join':
      return 170
    case 'loader':
      return 180
    case 'validator':
      return 160
    default:
      return 150
  }
}

/**
 * Get node height based on type
 */
function getNodeHeight(type: string | undefined): number {
  switch (type) {
    case 'sheet':
      return 80
    case 'model':
      return 70
    case 'field':
      return 60
    case 'transform':
      return 70
    case 'join':
      return 70
    case 'loader':
      return 70
    case 'validator':
      return 60
    default:
      return 60
  }
}

/**
 * Hook to apply layout on demand
 */
export function useLayout(
  nodes: Node[],
  edges: Edge[],
  setNodes: (nodes: Node[]) => void,
  options: LayoutOptions = {}
) {
  const applyLayout = async () => {
    if (nodes.length === 0) return

    const layoutedNodes = await applyAutoLayout(nodes, edges, options)
    setNodes(layoutedNodes)
  }

  return applyLayout
}

/**
 * Calculate dagre layout (alternative to ELK)
 * Simpler but less powerful - good for small graphs
 */
export function applySimpleLayout(nodes: Node[], edges: Edge[]): Node[] {
  // Group nodes by level (based on incoming edges)
  const levels: Map<string, number> = new Map()
  const visited = new Set<string>()

  const calculateLevel = (nodeId: string, currentLevel: number = 0) => {
    if (visited.has(nodeId)) return
    visited.add(nodeId)

    const existingLevel = levels.get(nodeId) || 0
    levels.set(nodeId, Math.max(existingLevel, currentLevel))

    // Find outgoing edges
    const outgoing = edges.filter(e => e.source === nodeId)
    outgoing.forEach(edge => {
      calculateLevel(edge.target, currentLevel + 1)
    })
  }

  // Start from nodes with no incoming edges
  const sourceNodes = nodes.filter(node =>
    !edges.some(edge => edge.target === node.id)
  )

  sourceNodes.forEach(node => calculateLevel(node.id, 0))

  // Calculate positions
  const levelGroups: Map<number, string[]> = new Map()
  nodes.forEach(node => {
    const level = levels.get(node.id) || 0
    const group = levelGroups.get(level) || []
    group.push(node.id)
    levelGroups.set(level, group)
  })

  const layoutedNodes = nodes.map(node => {
    const level = levels.get(node.id) || 0
    const group = levelGroups.get(level) || []
    const indexInLevel = group.indexOf(node.id)

    return {
      ...node,
      position: {
        x: level * 250,
        y: indexInLevel * 100
      }
    }
  })

  return layoutedNodes
}
