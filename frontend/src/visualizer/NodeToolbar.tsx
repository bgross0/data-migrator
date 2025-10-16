import { useGraphStore } from './useGraphStore'

interface NodeTemplate {
  kind: string
  label: string
  icon: string
  color: string
  description: string
}

const nodeTemplates: NodeTemplate[] = [
  {
    kind: 'sheet',
    label: 'Sheet',
    icon: '📊',
    color: 'bg-emerald-500',
    description: 'Data source / spreadsheet'
  },
  {
    kind: 'field',
    label: 'Field',
    icon: '📝',
    color: 'bg-blue-500',
    description: 'Column or field mapping'
  },
  {
    kind: 'transform',
    label: 'Transform',
    icon: '⚙️',
    color: 'bg-orange-500',
    description: 'Data transformation'
  },
  {
    kind: 'model',
    label: 'Model',
    icon: '🏛️',
    color: 'bg-purple-500',
    description: 'Odoo model'
  },
  {
    kind: 'loader',
    label: 'Loader',
    icon: '💾',
    color: 'bg-indigo-500',
    description: 'Import to Odoo'
  },
  {
    kind: 'validator',
    label: 'Validator',
    icon: '✓',
    color: 'bg-green-500',
    description: 'Data validation'
  },
  {
    kind: 'join',
    label: 'Join',
    icon: '🔗',
    color: 'bg-teal-500',
    description: 'Lookup / relationship'
  }
]

export function NodeToolbar() {
  const { addNode, nodes } = useGraphStore()

  const handleAddNode = (template: NodeTemplate) => {
    const nodeId = `${template.kind}-${Date.now()}`

    // Calculate position (offset from existing nodes)
    const yOffset = nodes.length * 100

    const newNode = {
      id: nodeId,
      type: template.kind,
      position: { x: 100, y: yOffset },
      data: {
        label: `New ${template.label}`,
        nodeType: template.label
      }
    }

    addNode(newNode)
  }

  return (
    <div className="absolute left-4 top-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3 w-48 z-10">
      <h3 className="text-xs font-bold text-gray-700 mb-3 uppercase tracking-wide">
        Add Nodes
      </h3>

      <div className="space-y-2">
        {nodeTemplates.map((template) => (
          <button
            key={template.kind}
            onClick={() => handleAddNode(template)}
            className="w-full flex items-center gap-2 p-2 rounded hover:bg-gray-50 border border-gray-200 transition-colors text-left group"
            title={template.description}
          >
            <span className="text-lg">{template.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900 truncate">
                {template.label}
              </div>
              <div className="text-xs text-gray-500 truncate group-hover:text-gray-700">
                {template.description}
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="mt-3 pt-3 border-t border-gray-200">
        <div className="text-xs text-gray-500">
          <div className="font-semibold mb-1">Tips:</div>
          <ul className="list-disc list-inside space-y-1">
            <li>Click to add node</li>
            <li>Drag nodes to position</li>
            <li>Click node to edit</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
