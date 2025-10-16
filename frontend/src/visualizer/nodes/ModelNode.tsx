import { memo } from 'react'
import { NodeProps } from 'reactflow'
import { BaseNode } from './BaseNode'

export const ModelNode = memo((props: NodeProps) => {
  const enhancedData = {
    ...props.data,
    nodeType: 'Model',
    subtitle: props.data.odooModel || 'Odoo Model',
  }

  return <BaseNode {...props} data={enhancedData} icon="🏛️" color="bg-purple-500" />
})

ModelNode.displayName = 'ModelNode'
