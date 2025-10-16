import { memo } from 'react'
import { NodeProps } from 'reactflow'
import { BaseNode } from './BaseNode'

export const JoinNode = memo((props: NodeProps) => {
  const enhancedData = {
    ...props.data,
    nodeType: 'Join',
    subtitle: `${props.data.leftKey || 'key'} → ${props.data.rightField || 'field'}`,
  }

  return <BaseNode {...props} data={enhancedData} icon="🔗" color="bg-teal-500" />
})

JoinNode.displayName = 'JoinNode'
