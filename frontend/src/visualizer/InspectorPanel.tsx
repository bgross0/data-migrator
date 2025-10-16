import { useGraphStore } from './useGraphStore'
import { Node } from 'reactflow'

export function InspectorPanel() {
  const { nodes, selectedNodeId, updateNodeData, deleteNode } = useGraphStore()

  const selectedNode = nodes.find(n => n.id === selectedNodeId)

  if (!selectedNode) {
    return (
      <div className="w-80 bg-white border-l border-gray-200 p-4">
        <div className="text-center text-gray-500 mt-8">
          <div className="text-4xl mb-2">👈</div>
          <p className="text-sm">Select a node to view details</p>
        </div>
      </div>
    )
  }

  return (
    <div className="w-80 bg-white border-l border-gray-200 p-4 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-900">Node Inspector</h3>
        <button
          onClick={() => deleteNode(selectedNode.id)}
          className="text-red-600 hover:text-red-800 text-sm"
        >
          Delete
        </button>
      </div>

      {/* Node type badge */}
      <div className="mb-4">
        <span className="inline-block px-3 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
          {selectedNode.type || 'field'}
        </span>
      </div>

      {/* Label editor */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Label
        </label>
        <input
          type="text"
          value={selectedNode.data.label || ''}
          onChange={(e) => updateNodeData(selectedNode.id, { label: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Type-specific fields */}
      {renderTypeSpecificFields(selectedNode, updateNodeData)}

      {/* Position (read-only) */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">Position</h4>
        <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
          <div>
            <span className="font-medium">X:</span> {Math.round(selectedNode.position.x)}
          </div>
          <div>
            <span className="font-medium">Y:</span> {Math.round(selectedNode.position.y)}
          </div>
        </div>
      </div>

      {/* Data preview */}
      {selectedNode.data.sampleValues && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Sample Values</h4>
          <div className="bg-gray-50 rounded p-2 text-xs max-h-32 overflow-y-auto">
            {selectedNode.data.sampleValues.slice(0, 5).map((value: any, idx: number) => (
              <div key={idx} className="py-1 text-gray-700 truncate">
                {String(value)}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Validation errors */}
      {selectedNode.data.error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          <div className="font-semibold mb-1">Error</div>
          {selectedNode.data.error}
        </div>
      )}

      {/* Warnings */}
      {selectedNode.data.warning && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-700">
          <div className="font-semibold mb-1">Warning</div>
          {selectedNode.data.warning}
        </div>
      )}
    </div>
  )
}

function renderTypeSpecificFields(node: Node, updateNodeData: (id: string, data: any) => void) {
  switch (node.type) {
    case 'sheet':
      return (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Sheet Name
            </label>
            <input
              type="text"
              value={node.data.sheetName || ''}
              onChange={(e) => updateNodeData(node.id, { sheetName: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          {node.data.n_rows && (
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-600">Rows:</span>{' '}
                <span className="font-semibold">{node.data.n_rows}</span>
              </div>
              <div>
                <span className="text-gray-600">Columns:</span>{' '}
                <span className="font-semibold">{node.data.n_cols}</span>
              </div>
            </div>
          )}
        </div>
      )

    case 'field':
      return (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Field Name
            </label>
            <input
              type="text"
              value={node.data.fieldName || ''}
              onChange={(e) => updateNodeData(node.id, { fieldName: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Data Type
            </label>
            <select
              value={node.data.dtype || 'char'}
              onChange={(e) => updateNodeData(node.id, { dtype: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="char">Char</option>
              <option value="text">Text</option>
              <option value="integer">Integer</option>
              <option value="float">Float</option>
              <option value="boolean">Boolean</option>
              <option value="date">Date</option>
              <option value="datetime">DateTime</option>
            </select>
          </div>
        </div>
      )

    case 'model':
      return (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Odoo Model
          </label>
          <input
            type="text"
            value={node.data.odooModel || ''}
            onChange={(e) => updateNodeData(node.id, { odooModel: e.target.value })}
            placeholder="e.g., res.partner"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      )

    case 'transform':
      return (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Transform Type
            </label>
            <select
              value={node.data.transformId || 'trim'}
              onChange={(e) => updateNodeData(node.id, { transformId: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="trim">Trim</option>
              <option value="lower">Lowercase</option>
              <option value="upper">Uppercase</option>
              <option value="phone_normalize">Phone Normalize</option>
              <option value="email_normalize">Email Normalize</option>
              <option value="date_parse">Date Parse</option>
              <option value="regex_extract">Regex Extract</option>
            </select>
          </div>
        </div>
      )

    case 'loader':
      return (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Target Model
            </label>
            <input
              type="text"
              value={node.data.odooModel || ''}
              onChange={(e) => updateNodeData(node.id, { odooModel: e.target.value })}
              placeholder="e.g., res.partner"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Upsert Key
            </label>
            <input
              type="text"
              value={node.data.upsertKey?.join(', ') || 'external_id'}
              onChange={(e) => updateNodeData(node.id, { upsertKey: e.target.value.split(',').map(s => s.trim()) })}
              placeholder="external_id"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      )

    case 'join':
      return (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Left Key
            </label>
            <input
              type="text"
              value={node.data.leftKey || ''}
              onChange={(e) => updateNodeData(node.id, { leftKey: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Right Model
            </label>
            <input
              type="text"
              value={node.data.rightModel || ''}
              onChange={(e) => updateNodeData(node.id, { rightModel: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Right Field
            </label>
            <input
              type="text"
              value={node.data.rightField || ''}
              onChange={(e) => updateNodeData(node.id, { rightField: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      )

    default:
      return null
  }
}
