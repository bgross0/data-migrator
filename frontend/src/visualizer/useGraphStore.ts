import { create } from 'zustand'
import { Node, Edge, Connection, addEdge, applyNodeChanges, applyEdgeChanges, NodeChange, EdgeChange } from 'reactflow'
import { GraphSpec } from '@/types/graph'

interface GraphState {
  // Graph data
  graphId: string | null
  graphName: string
  graphVersion: number
  nodes: Node[]
  edges: Edge[]

  // UI state
  selectedNodeId: string | null
  selectedEdgeId: string | null
  isValidating: boolean
  isSaving: boolean
  isDirty: boolean

  // Actions
  setGraphId: (id: string | null) => void
  setGraphName: (name: string) => void
  loadGraph: (spec: GraphSpec) => void
  exportGraph: () => GraphSpec

  // Node/Edge mutations
  onNodesChange: (changes: NodeChange[]) => void
  onEdgesChange: (changes: EdgeChange[]) => void
  onConnect: (connection: Connection) => void
  addNode: (node: Node) => void
  deleteNode: (nodeId: string) => void
  updateNodeData: (nodeId: string, data: Partial<Node['data']>) => void

  // Selection
  setSelectedNode: (nodeId: string | null) => void
  setSelectedEdge: (edgeId: string | null) => void

  // State flags
  setValidating: (isValidating: boolean) => void
  setSaving: (isSaving: boolean) => void
  setDirty: (isDirty: boolean) => void

  // Clear/Reset
  clearGraph: () => void
}

export const useGraphStore = create<GraphState>((set, get) => ({
  // Initial state
  graphId: null,
  graphName: 'Untitled Graph',
  graphVersion: 1,
  nodes: [],
  edges: [],
  selectedNodeId: null,
  selectedEdgeId: null,
  isValidating: false,
  isSaving: false,
  isDirty: false,

  // Setters
  setGraphId: (id) => set({ graphId: id }),
  setGraphName: (name) => set({ graphName: name, isDirty: true }),

  loadGraph: (spec: GraphSpec) => {
    // Convert GraphSpec to React Flow format
    const flowNodes: Node[] = spec.nodes.map(node => ({
      id: node.id,
      type: node.kind, // Use kind as type for custom nodes
      position: node.position || { x: 0, y: 0 },
      data: {
        label: node.label,
        ...node.data
      }
    }))

    const flowEdges: Edge[] = spec.edges.map(edge => ({
      id: edge.id,
      source: edge.from,
      target: edge.to,
      type: edge.kind === 'map' ? 'default' : 'smoothstep',
      animated: edge.kind === 'flow',
      data: edge.data,
      style: {
        stroke: getEdgeColor(edge.kind)
      }
    }))

    set({
      graphId: spec.id,
      graphName: spec.name,
      graphVersion: spec.version,
      nodes: flowNodes,
      edges: flowEdges,
      isDirty: false
    })
  },

  exportGraph: (): GraphSpec => {
    const state = get()

    // Convert React Flow format back to GraphSpec
    const graphNodes = state.nodes.map(node => ({
      id: node.id,
      kind: node.type as any || 'field',
      label: node.data.label || node.id,
      data: node.data,
      position: node.position
    }))

    const graphEdges = state.edges.map(edge => ({
      id: edge.id,
      from: edge.source,
      to: edge.target,
      kind: (edge.data?.kind || 'map') as any,
      data: edge.data
    }))

    return {
      id: state.graphId || `graph-${Date.now()}`,
      name: state.graphName,
      version: state.graphVersion,
      nodes: graphNodes,
      edges: graphEdges,
      metadata: {
        lastModified: new Date().toISOString()
      }
    }
  },

  // Node/Edge changes (React Flow callbacks)
  onNodesChange: (changes) => {
    set({
      nodes: applyNodeChanges(changes, get().nodes),
      isDirty: true
    })
  },

  onEdgesChange: (changes) => {
    set({
      edges: applyEdgeChanges(changes, get().edges),
      isDirty: true
    })
  },

  onConnect: (connection) => {
    set({
      edges: addEdge({
        ...connection,
        type: 'smoothstep',
        animated: true
      }, get().edges),
      isDirty: true
    })
  },

  addNode: (node) => {
    set({
      nodes: [...get().nodes, node],
      isDirty: true
    })
  },

  deleteNode: (nodeId) => {
    set({
      nodes: get().nodes.filter(n => n.id !== nodeId),
      edges: get().edges.filter(e => e.source !== nodeId && e.target !== nodeId),
      selectedNodeId: get().selectedNodeId === nodeId ? null : get().selectedNodeId,
      isDirty: true
    })
  },

  updateNodeData: (nodeId, data) => {
    set({
      nodes: get().nodes.map(node =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...data } }
          : node
      ),
      isDirty: true
    })
  },

  // Selection
  setSelectedNode: (nodeId) => set({ selectedNodeId: nodeId, selectedEdgeId: null }),
  setSelectedEdge: (edgeId) => set({ selectedEdgeId: edgeId, selectedNodeId: null }),

  // State flags
  setValidating: (isValidating) => set({ isValidating }),
  setSaving: (isSaving) => set({ isSaving }),
  setDirty: (isDirty) => set({ isDirty }),

  // Clear/Reset
  clearGraph: () => set({
    graphId: null,
    graphName: 'Untitled Graph',
    graphVersion: 1,
    nodes: [],
    edges: [],
    selectedNodeId: null,
    selectedEdgeId: null,
    isDirty: false
  })
}))

// Helper function for edge colors
function getEdgeColor(kind: string): string {
  switch (kind) {
    case 'map': return '#3b82f6' // blue
    case 'flow': return '#10b981' // green
    case 'depends': return '#f59e0b' // amber
    case 'filter': return '#ef4444' // red
    default: return '#6b7280' // gray
  }
}
