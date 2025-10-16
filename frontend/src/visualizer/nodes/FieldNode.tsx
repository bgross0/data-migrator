import { memo } from 'react'
import { NodeProps } from 'reactflow'
import { BaseNode } from './BaseNode'

export const FieldNode = memo((props: NodeProps) => {
  const enhancedData = {
    ...props.data,
    nodeType: 'Field',
    subtitle: props.data.dtype || 'unknown type',
  }

  return <BaseNode {...props} data={enhancedData} icon="📝" color="bg-blue-500" />
})

FieldNode.displayName = 'FieldNode'
