import { memo } from 'react'
import { NodeProps } from 'reactflow'
import { BaseNode } from './BaseNode'

export const LoaderNode = memo((props: NodeProps) => {
  const enhancedData = {
    ...props.data,
    nodeType: 'Loader',
    subtitle: props.data.odooModel || 'Import to Odoo',
    stats: props.data.rowsImported ? {
      imported: props.data.rowsImported
    } : undefined
  }

  return <BaseNode {...props} data={enhancedData} icon="💾" color="bg-indigo-500" />
})

LoaderNode.displayName = 'LoaderNode'
