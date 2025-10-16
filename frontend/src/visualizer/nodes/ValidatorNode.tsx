import { memo } from 'react'
import { NodeProps } from 'reactflow'
import { BaseNode } from './BaseNode'

export const ValidatorNode = memo((props: NodeProps) => {
  const enhancedData = {
    ...props.data,
    nodeType: 'Validator',
    subtitle: props.data.validationType || 'Data Validation',
  }

  return <BaseNode {...props} data={enhancedData} icon="✓" color="bg-green-500" />
})

ValidatorNode.displayName = 'ValidatorNode'
