// Export all node types
import { SheetNode } from './SheetNode'
import { FieldNode } from './FieldNode'
import { TransformNode } from './TransformNode'
import { ModelNode } from './ModelNode'
import { LoaderNode } from './LoaderNode'
import { ValidatorNode } from './ValidatorNode'
import { JoinNode } from './JoinNode'

export { BaseNode } from './BaseNode'
export { SheetNode, FieldNode, TransformNode, ModelNode, LoaderNode, ValidatorNode, JoinNode }

// Node type registry for React Flow
export const nodeTypes = {
  sheet: SheetNode,
  field: FieldNode,
  transform: TransformNode,
  model: ModelNode,
  loader: LoaderNode,
  validator: ValidatorNode,
  join: JoinNode,
}
