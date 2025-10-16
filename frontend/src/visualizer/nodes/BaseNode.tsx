import { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'

interface BaseNodeProps extends NodeProps {
  icon?: string
  color?: string
  showHandles?: boolean
}

export const BaseNode = memo(({ data, icon, color = 'bg-blue-500', showHandles = true }: BaseNodeProps) => {
  return (
    <div className="relative">
      {showHandles && (
        <>
          <Handle type="target" position={Position.Left} className="w-3 h-3" />
          <Handle type="source" position={Position.Right} className="w-3 h-3" />
        </>
      )}

      <div className={`rounded-lg shadow-md border-2 ${
        data.status === 'pending' ? 'border-dashed border-yellow-400' :
        data.status === 'confirmed' ? 'border-solid border-green-400' :
        'border-gray-200'
      } bg-white min-w-[150px] transition-all hover:shadow-lg ${data.isSelected ? 'ring-2 ring-blue-400' : ''}`}>
        {/* Header */}
        <div className={`${color} text-white px-3 py-2 rounded-t-lg flex items-center gap-2`}>
          {icon && <span className="text-lg">{icon}</span>}
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium opacity-75 uppercase tracking-wide">
              {data.nodeType || 'Node'}
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="px-3 py-2">
          <div className="font-semibold text-sm text-gray-900 truncate">
            {data.label}
          </div>

          {data.subtitle && (
            <div className="text-xs text-gray-500 mt-1 truncate">
              {data.subtitle}
            </div>
          )}

          {data.stats && (
            <div className="flex gap-2 mt-2 text-xs text-gray-600">
              {Object.entries(data.stats).map(([key, value]) => (
                <div key={key} className="flex items-center gap-1">
                  <span className="font-medium">{String(value)}</span>
                  <span className="opacity-75">{key}</span>
                </div>
              ))}
            </div>
          )}

          {data.error && (
            <div className="mt-2 text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
              {data.error}
            </div>
          )}

          {data.warning && (
            <div className="mt-2 text-xs text-yellow-600 bg-yellow-50 px-2 py-1 rounded">
              {data.warning}
            </div>
          )}
        </div>

        {/* Status indicator */}
        {data.status && (
          <div className="px-3 pb-2">
            <div className={`text-xs px-2 py-1 rounded-full inline-block ${
              data.status === 'completed' ? 'bg-green-100 text-green-700' :
              data.status === 'running' ? 'bg-blue-100 text-blue-700' :
              data.status === 'failed' ? 'bg-red-100 text-red-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {data.status}
            </div>
          </div>
        )}
      </div>
    </div>
  )
})

BaseNode.displayName = 'BaseNode'
