import { useCallback, useEffect } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Panel,
  useReactFlow,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useGraphStore } from './useGraphStore'
import { nodeTypes } from './nodes'
import { applyAutoLayout } from './layout'
import { InspectorPanel } from './InspectorPanel'
import { NodeToolbar } from './NodeToolbar'

export function FlowCanvas() {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    setSelectedNode,
    setSelectedEdge,
    isDirty,
    graphName,
    setGraphName,
  } = useGraphStore()

  const reactFlowInstance = useReactFlow()

  // Handle node selection
  const onNodeClick = useCallback((_event: any, node: any) => {
    setSelectedNode(node.id)
  }, [setSelectedNode])

  // Handle edge selection
  const onEdgeClick = useCallback((_event: any, edge: any) => {
    setSelectedEdge(edge.id)
  }, [setSelectedEdge])

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
    setSelectedEdge(null)
  }, [setSelectedNode, setSelectedEdge])

  // Auto-layout handler
  const handleAutoLayout = useCallback(async () => {
    const layoutedNodes = await applyAutoLayout(nodes, edges)
    useGraphStore.setState({ nodes: layoutedNodes })

    // Fit view after layout
    setTimeout(() => {
      reactFlowInstance?.fitView({ padding: 0.2, duration: 400 })
    }, 50)
  }, [nodes, edges, reactFlowInstance])

  // Fit view on mount
  useEffect(() => {
    if (nodes.length > 0) {
      setTimeout(() => {
        reactFlowInstance?.fitView({ padding: 0.2 })
      }, 100)
    }
  }, []) // Only on mount

  return (
    <div className="flex h-screen">
      {/* Main canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-left"
        >
          <Background gap={16} size={1} />
          <Controls />
          <MiniMap
            nodeColor={(node) => {
              switch (node.type) {
                case 'sheet': return '#10b981'
                case 'field': return '#3b82f6'
                case 'transform': return '#f97316'
                case 'model': return '#a855f7'
                case 'loader': return '#6366f1'
                case 'join': return '#14b8a6'
                case 'validator': return '#22c55e'
                default: return '#9ca3af'
              }
            }}
            maskColor="rgba(0, 0, 0, 0.1)"
          />

          {/* Top toolbar */}
          <Panel position="top-left" className="bg-white rounded-lg shadow-lg border border-gray-200 p-3">
            <div className="flex items-center gap-4">
              {/* Graph name */}
              <input
                type="text"
                value={graphName}
                onChange={(e) => setGraphName(e.target.value)}
                className="px-3 py-1 border border-gray-300 rounded text-sm font-medium focus:ring-blue-500 focus:border-blue-500"
                placeholder="Graph name"
              />

              {/* Dirty indicator */}
              {isDirty && (
                <span className="text-xs text-orange-600 font-medium">
                  • Unsaved changes
                </span>
              )}
            </div>
          </Panel>

          {/* Controls panel */}
          <Panel position="top-right" className="bg-white rounded-lg shadow-lg border border-gray-200 p-3">
            <div className="flex gap-2">
              <button
                onClick={handleAutoLayout}
                className="px-3 py-1.5 bg-purple-600 text-white rounded text-sm hover:bg-purple-700 transition-colors"
                title="Auto-arrange nodes"
              >
                Auto Layout
              </button>

              <button
                onClick={() => reactFlowInstance?.fitView({ padding: 0.2, duration: 400 })}
                className="px-3 py-1.5 bg-gray-600 text-white rounded text-sm hover:bg-gray-700 transition-colors"
                title="Fit to view"
              >
                Fit View
              </button>
            </div>
          </Panel>

          {/* Stats panel */}
          <Panel position="bottom-right" className="bg-white rounded-lg shadow-lg border border-gray-200 p-3">
            <div className="flex gap-4 text-xs text-gray-600">
              <div>
                <span className="font-medium">{nodes.length}</span> nodes
              </div>
              <div>
                <span className="font-medium">{edges.length}</span> edges
              </div>
            </div>
          </Panel>

          {/* Node creation toolbar */}
          <NodeToolbar />
        </ReactFlow>
      </div>

      {/* Inspector panel */}
      <InspectorPanel />
    </div>
  )
}
