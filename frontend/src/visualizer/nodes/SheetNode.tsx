import { memo } from 'react'
import { NodeProps } from 'reactflow'
import { BaseNode } from './BaseNode'

export const SheetNode = memo((props: NodeProps) => {
  const enhancedData = {
    ...props.data,
    nodeType: 'Sheet',
    subtitle: props.data.sheetName || 'Spreadsheet',
    stats: props.data.n_rows ? {
      rows: props.data.n_rows,
      cols: props.data.n_cols
    } : undefined
  }

  return <BaseNode {...props} data={enhancedData} icon="📊" color="bg-emerald-500" />
})

SheetNode.displayName = 'SheetNode'
