import { memo } from 'react'
import { NodeProps } from 'reactflow'
import { BaseNode } from './BaseNode'

export const TransformNode = memo((props: NodeProps) => {
  const enhancedData = {
    ...props.data,
    nodeType: 'Transform',
    subtitle: props.data.transformId || 'transformation',
  }

  return <BaseNode {...props} data={enhancedData} icon="⚙️" color="bg-orange-500" />
})

TransformNode.displayName = 'TransformNode'
