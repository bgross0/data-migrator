/**
 * Shared type definitions for GraphSpec
 * Mirror these types in backend/app/schemas/graph.py
 */

export type NodeKind = 'sheet' | 'model' | 'field' | 'transform' | 'join' | 'loader' | 'validator'

export type EdgeKind = 'map' | 'flow' | 'depends' | 'filter'

export interface GraphSpec {
  id: string                      // graph run id / version
  name: string
  version: number
  nodes: GraphNode[]
  edges: GraphEdge[]
  metadata?: Record<string, any>  // layout, author, tags
}

export interface GraphNode {
  id: string
  kind: NodeKind
  label: string
  data: {
    // sheet
    sheetName?: string
    samplePath?: string            // local tmp or GDrive URL
    // model/field
    odooModel?: string             // 'res.partner', 'crm.lead', ...
    fieldName?: string             // 'email', 'phone', ...
    sourceColumn?: string          // source column name
    dtype?: string                 // 'char','int','date',...
    // transform
    transformId?: string           // 'trim','regex','map','phone_e164','date_parse'
    params?: Record<string, any>
    // join/lookup
    leftKey?: string               // 'sheet.col'
    rightModel?: string
    rightField?: string            // key to join on
    // loader
    upsertKey?: string[]           // ['external_id'] or natural key
  }
  position?: { x: number; y: number } // React Flow layout
}

export interface GraphEdge {
  id: string
  from: string   // node id (source)
  to: string     // node id (target)
  kind: EdgeKind
  data?: {
    sourceColumn?: string          // for column→field edges
    transformChain?: string[]      // optional inline transforms
  }
}

// For React Flow compatibility
export interface FlowNode extends GraphNode {
  position: { x: number; y: number }
  type?: string  // custom node type for React Flow
}

export interface FlowEdge extends Omit<GraphEdge, 'from' | 'to'> {
  source: string  // React Flow uses 'source' instead of 'from'
  target: string  // React Flow uses 'target' instead of 'to'
  type?: string
  animated?: boolean
  style?: Record<string, any>
}

// Validation result
export interface GraphValidation {
  valid: boolean
  errors: ValidationError[]
  warnings: ValidationWarning[]
}

export interface ValidationError {
  nodeId?: string
  edgeId?: string
  message: string
  type: 'missing_field' | 'type_mismatch' | 'circular_dependency' | 'invalid_config'
}

export interface ValidationWarning {
  nodeId?: string
  edgeId?: string
  message: string
  type: 'low_confidence' | 'missing_transform' | 'performance'
}

// Run status
export interface GraphRun {
  id: string
  graphId: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  startedAt: string
  finishedAt?: string
  progress: number
  logs: RunLog[]
  stats?: {
    nodesProcessed: number
    totalNodes: number
    rowsImported: number
    errors: number
  }
}

export interface RunLog {
  timestamp: string
  level: 'debug' | 'info' | 'warning' | 'error'
  nodeId?: string
  message: string
}
