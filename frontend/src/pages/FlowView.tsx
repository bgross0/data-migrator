import { useParams, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { ReactFlowProvider } from 'reactflow'
import { FlowCanvas } from '@/visualizer/FlowCanvas'
import { useGraphStore } from '@/visualizer/useGraphStore'
import { datasetsApi } from '@/services/api'
import { Mapping, Dataset } from '@/types/mapping'
import { GraphSpec } from '@/types/graph'

export default function FlowView() {
  const { id } = useParams<{ id: string }>()
  const [loading, setLoading] = useState(true)
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const { loadGraph, exportGraph, isDirty } = useGraphStore()

  useEffect(() => {
    loadDataAndGenerateGraph()
  }, [id])

  const loadDataAndGenerateGraph = async () => {
    try {
      // Load dataset and mappings
      const datasetData = await datasetsApi.get(Number(id))
      setDataset(datasetData)

      const response = await fetch(`/api/v1/datasets/${id}/mappings`)
      const data = await response.json()
      const mappings: Mapping[] = data.mappings || []

      // Generate GraphSpec from mappings
      const graphSpec = generateGraphFromMappings(datasetData, mappings)
      loadGraph(graphSpec)
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    const spec = exportGraph()
    // TODO: Call API to save graph
    console.log('Saving graph:', spec)
    useGraphStore.setState({ isDirty: false })
  }

  const handleValidate = async () => {
    const spec = exportGraph()
    // TODO: Call validation API
    console.log('Validating graph:', spec)
  }

  const handleRun = async () => {
    const spec = exportGraph()
    // TODO: Call run API
    console.log('Running graph:', spec)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-4xl mb-4">⚙️</div>
          <div className="text-gray-600">Loading flow...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Top nav */}
      <div className="bg-white border-b border-gray-200 px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to={`/mappings/${id}`}
              className="text-blue-600 hover:underline text-sm"
            >
              ← Back to Mappings
            </Link>
            <h1 className="text-xl font-bold text-gray-900">
              Flow View: {dataset?.name}
            </h1>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleValidate}
              className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 text-sm"
            >
              Validate
            </button>
            <button
              onClick={handleSave}
              disabled={!isDirty}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm"
            >
              Save
            </button>
            <button
              onClick={handleRun}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
            >
              Run Import
            </button>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1">
        <ReactFlowProvider>
          <FlowCanvas />
        </ReactFlowProvider>
      </div>
    </div>
  )
}

/**
 * Generate a GraphSpec from existing mappings
 * This creates a visual representation of the mapping flow
 */
function generateGraphFromMappings(dataset: Dataset, mappings: Mapping[]): GraphSpec {
  const nodes: GraphSpec['nodes'] = []
  const edges: GraphSpec['edges'] = []

  // Group mappings by sheet and target model
  const sheetMap = new Map<number, { sheet: any; mappings: Mapping[] }>()

  dataset.sheets?.forEach(sheet => {
    // Show ALL mappings (pending, confirmed) - not just confirmed
    const sheetMappings = mappings.filter(m =>
      m.sheet_id === sheet.id &&
      (m.status === 'confirmed' || m.status === 'pending')
    )
    if (sheetMappings.length > 0) {
      sheetMap.set(sheet.id, { sheet, mappings: sheetMappings })
    }
  })

  let yOffset = 0

  // Create nodes for each sheet → fields → models → loader
  sheetMap.forEach(({ sheet, mappings: sheetMappings }, sheetId) => {
    // Sheet node
    const sheetNodeId = `sheet-${sheetId}`
    nodes.push({
      id: sheetNodeId,
      kind: 'sheet',
      label: sheet.name,
      data: {
        sheetName: sheet.name
      },
      position: { x: 0, y: yOffset }
    })

    // Group by target model
    const modelGroups = new Map<string, Mapping[]>()
    sheetMappings.forEach(mapping => {
      if (mapping.target_model) {
        const existing = modelGroups.get(mapping.target_model) || []
        existing.push(mapping)
        modelGroups.set(mapping.target_model, existing)
      }
    })

    let modelOffset = 0

    modelGroups.forEach((modelMappings, targetModel) => {
      // Model node
      const modelNodeId = `model-${targetModel}-${sheetId}`
      nodes.push({
        id: modelNodeId,
        kind: 'model',
        label: targetModel,
        data: {
          odooModel: targetModel,
          subtitle: 'Odoo Model'
        },
        position: { x: 750, y: yOffset + modelOffset }
      })

      // Field nodes (source and target)
      modelMappings.forEach((mapping, idx) => {
        const sourceFieldNodeId = `source-field-${mapping.id}`
        const targetFieldNodeId = `target-field-${mapping.id}`

        // Source field node (from spreadsheet)
        nodes.push({
          id: sourceFieldNodeId,
          kind: 'field',
          label: mapping.header_name,
          data: {
            fieldName: mapping.header_name,
            sourceColumn: mapping.header_name,
            status: mapping.status,
            subtitle: 'Source Column',
            nodeType: 'Source Field'
          },
          position: { x: 250, y: yOffset + modelOffset + (idx * 80) }
        })

        // Target field node (Odoo field)
        if (mapping.target_field) {
          nodes.push({
            id: targetFieldNodeId,
            kind: 'field',
            label: mapping.target_field,
            data: {
              fieldName: mapping.target_field,
              odooModel: mapping.target_model,
              status: mapping.status,
              subtitle: `${mapping.target_model}`,
              nodeType: 'Target Field'
            },
            position: { x: 500, y: yOffset + modelOffset + (idx * 80) }
          })
        }

        // Edge: sheet → source field
        edges.push({
          id: `edge-sheet-source-${mapping.id}`,
          from: sheetNodeId,
          to: sourceFieldNodeId,
          kind: 'flow',
          data: {
            sourceColumn: mapping.header_name
          }
        })

        // Edge: source field → target field (or model if no target field)
        if (mapping.target_field) {
          edges.push({
            id: `edge-source-target-${mapping.id}`,
            from: sourceFieldNodeId,
            to: targetFieldNodeId,
            kind: 'map',
            data: {
              mappingId: mapping.id
            }
          })
        }

        // If there are transforms, create transform nodes between source and target
        if (mapping.transforms && mapping.transforms.length > 0) {
          mapping.transforms.forEach((transform: any, tIdx: number) => {
            const transformNodeId = `transform-${transform.id}`

            nodes.push({
              id: transformNodeId,
              kind: 'transform',
              label: transform.fn,
              data: {
                transformId: transform.fn,
                params: transform.params
              },
              position: { x: 375, y: yOffset + modelOffset + (idx * 80) + (tIdx * 60) }
            })

            // Edge: source field → first transform, or transform → transform
            const sourceId = tIdx === 0 ? sourceFieldNodeId : `transform-${mapping.transforms![tIdx - 1].id}`
            edges.push({
              id: `edge-transform-${transform.id}`,
              from: sourceId,
              to: transformNodeId,
              kind: 'flow'
            })
          })

          // Edge: last transform → target field
          if (mapping.target_field) {
            const lastTransform = mapping.transforms[mapping.transforms.length - 1]
            edges.push({
              id: `edge-transform-target-${mapping.id}`,
              from: `transform-${lastTransform.id}`,
              to: targetFieldNodeId,
              kind: 'flow'
            })
          }
        }

        // Edge: target field → model
        if (mapping.target_field) {
          edges.push({
            id: `edge-target-model-${mapping.id}`,
            from: targetFieldNodeId,
            to: modelNodeId,
            kind: 'flow'
          })
        }
      })

      // Loader node for this model
      const loaderNodeId = `loader-${targetModel}-${sheetId}`
      nodes.push({
        id: loaderNodeId,
        kind: 'loader',
        label: `Load ${targetModel}`,
        data: {
          odooModel: targetModel,
          upsertKey: ['external_id'],
          subtitle: 'Import to Odoo'
        },
        position: { x: 1000, y: yOffset + modelOffset }
      })

      // Edge: model → loader
      edges.push({
        id: `edge-model-loader-${targetModel}-${sheetId}`,
        from: modelNodeId,
        to: loaderNodeId,
        kind: 'flow'
      })

      modelOffset += (modelMappings.length * 80) + 100
    })

    yOffset += modelOffset + 200
  })

  return {
    id: `graph-${dataset.id}-${Date.now()}`,
    name: `${dataset.name} Flow`,
    version: 1,
    nodes,
    edges,
    metadata: {
      datasetId: dataset.id,
      generatedAt: new Date().toISOString()
    }
  }
}
