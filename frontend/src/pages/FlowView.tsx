import { useParams, Link, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { ReactFlowProvider } from 'reactflow'
import { FlowCanvas } from '@/visualizer/FlowCanvas'
import { useGraphStore } from '@/visualizer/useGraphStore'
import { datasetsApi, graphsApi } from '@/services/api'
import { Mapping, Dataset } from '@/types/mapping'
import { GraphSpec, GraphValidation } from '@/types/graph'

export default function FlowView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [validationResult, setValidationResult] = useState<GraphValidation | null>(null)
  const [lastRunId, setLastRunId] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)

  const {
    loadGraph,
    exportGraph,
    isDirty,
    graphId,
    graphName,
    setGraphId,
    isSaving,
    setSaving,
    isValidating,
    setValidating,
  } = useGraphStore((state) => ({
    loadGraph: state.loadGraph,
    exportGraph: state.exportGraph,
    isDirty: state.isDirty,
    graphId: state.graphId,
    graphName: state.graphName,
    setGraphId: state.setGraphId,
    isSaving: state.isSaving,
    setSaving: state.setSaving,
    isValidating: state.isValidating,
    setValidating: state.setValidating,
  }))

  useEffect(() => {
    loadDataAndGenerateGraph()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const loadDataAndGenerateGraph = async () => {
    setLoading(true)
    setActionMessage(null)
    setErrorMessage(null)
    try {
      const datasetData = await datasetsApi.get(Number(id))
      setDataset(datasetData)

      const response = await fetch(`/api/v1/datasets/${id}/mappings`)
      const data = await response.json()
      const mappings: Mapping[] = data.mappings || []

      const graphSpec = generateGraphFromMappings(datasetData, mappings)
      loadGraph(graphSpec)
    } catch (error) {
      console.error('Failed to load data:', error)
      setErrorMessage('Failed to load dataset or mappings.')
    } finally {
      setLoading(false)
    }
  }

  const ensureGraphSaved = async (): Promise<string> => {
    const spec = exportGraph()
    const payload = {
      name: spec.name,
      nodes: spec.nodes,
      edges: spec.edges,
      metadata: {
        ...(spec.metadata || {}),
        datasetId: dataset?.id,
        lastModified: new Date().toISOString(),
      },
    }

    setSaving(true)
    setErrorMessage(null)

    try {
      if (graphId) {
        const updated = await graphsApi.update(graphId, payload)
        setGraphId(updated.id)
        useGraphStore.setState({
          graphVersion: updated.version ?? 1,
          graphName: updated.name ?? spec.name,
        })
        setDirty(false)
        return updated.id
      }

      const created = await graphsApi.create(payload)
      setGraphId(created.id)
      useGraphStore.setState({
        graphVersion: created.version ?? 1,
        graphName: created.name ?? spec.name,
      })
      setDirty(false)
      return created.id
    } catch (error) {
      console.error('Failed to save graph', error)
      setErrorMessage('Failed to save graph. Please try again.')
      throw error
    } finally {
      setSaving(false)
    }
  }

  const handleSave = async () => {
    try {
      const savedGraphId = await ensureGraphSaved()
      setActionMessage(`Graph saved (ID: ${savedGraphId})`)
      setValidationResult(null)
    } catch {
      // Errors handled in ensureGraphSaved
    }
  }

  const handleValidate = async () => {
    try {
      const savedGraphId = await ensureGraphSaved()
      setValidating(true)
      const result = await graphsApi.validate(savedGraphId)
      setValidationResult(result)
      if (result.valid) {
        setActionMessage('Graph validation succeeded. Ready to run.')
        setErrorMessage(null)
      } else {
        setErrorMessage('Validation uncovered issues. Review the details below.')
        setActionMessage(null)
      }
    } catch {
      // ensureGraphSaved already set error state
    } finally {
      setValidating(false)
    }
  }

  const handleRun = async () => {
    try {
      const savedGraphId = await ensureGraphSaved()
      setIsRunning(true)
      const response = await graphsApi.run(savedGraphId, dataset?.id)
      setActionMessage(`Graph execution queued (Run ID: ${response.id})`)
      setErrorMessage(null)
      setValidationResult(null)
      setLastRunId(response.id)
      navigate(`/runs?runId=${response.id}`)
    } catch (error) {
      console.error('Failed to run graph', error)
      if (!errorMessage) {
        setErrorMessage('Failed to execute graph. Please check configuration and try again.')
      }
    } finally {
      setIsRunning(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="mb-4 text-4xl">⚙️</div>
          <div className="text-gray-600">Loading flow...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen flex-col">
      <div className="border-b border-gray-200 bg-white px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to={`/mappings/${id}`}
              className="text-sm text-blue-600 hover:underline"
            >
              ← Back to Mappings
            </Link>
            <h1 className="text-xl font-bold text-gray-900">
              Flow View: {graphName || dataset?.name}
            </h1>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleValidate}
              disabled={isSaving || isRunning}
              className="rounded bg-yellow-600 px-4 py-2 text-sm text-white hover:bg-yellow-700 disabled:cursor-not-allowed disabled:bg-gray-400"
            >
              {isValidating ? 'Validating…' : 'Validate'}
            </button>
            <button
              onClick={handleSave}
              disabled={!isDirty || isSaving}
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-400"
            >
              {isSaving ? 'Saving…' : 'Save'}
            </button>
            <button
              onClick={handleRun}
              disabled={isRunning || isSaving}
              className="rounded bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-gray-400"
            >
              {isRunning ? 'Running…' : 'Run Import'}
            </button>
          </div>
        </div>

        {(actionMessage || errorMessage) && (
          <div className="mt-3 space-y-2 text-sm">
            {actionMessage && (
              <div className="rounded border border-green-200 bg-green-50 px-4 py-2 text-green-700">
                {actionMessage}
                {lastRunId && (
                  <button
                    onClick={() => navigate(`/runs?runId=${lastRunId}`)}
                    className="ml-3 underline"
                  >
                    View run
                  </button>
                )}
              </div>
            )}
            {errorMessage && (
              <div className="rounded border border-red-200 bg-red-50 px-4 py-2 text-red-700">
                {errorMessage}
              </div>
            )}
          </div>
        )}

        {validationResult && (
          <div className="mt-3 rounded border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-900">
            <p className="font-semibold">
              Validation {validationResult.valid ? 'passed' : 'found issues'}
            </p>
            {!validationResult.valid && validationResult.errors.length > 0 && (
              <ul className="mt-2 list-disc pl-5">
                {validationResult.errors.map((err, idx) => (
                  <li key={`${err.nodeId || err.edgeId || 'error'}-${idx}`}>
                    {err.message}
                  </li>
                ))}
              </ul>
            )}
            {validationResult.warnings.length > 0 && (
              <>
                <p className="mt-3 font-semibold">Warnings</p>
                <ul className="mt-1 list-disc pl-5">
                  {validationResult.warnings.map((warn, idx) => (
                    <li key={`${warn.nodeId || warn.edgeId || 'warn'}-${idx}`}>
                      {warn.message}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </div>

      <div className="flex-1">
        <ReactFlowProvider>
          <FlowCanvas />
        </ReactFlowProvider>
      </div>
    </div>
  )
}

function generateGraphFromMappings(dataset: Dataset, mappings: Mapping[]): GraphSpec {
  const nodes: GraphSpec['nodes'] = []
  const edges: GraphSpec['edges'] = []

  const sheetMap = new Map<number, { sheet: any; mappings: Mapping[] }>()

  dataset.sheets?.forEach((sheet) => {
    const sheetMappings = mappings.filter(
      (m) =>
        m.sheet_id === sheet.id &&
        (m.status === 'confirmed' || m.status === 'pending')
    )
    if (sheetMappings.length > 0) {
      sheetMap.set(sheet.id, { sheet, mappings: sheetMappings })
    }
  })

  let yOffset = 0

  sheetMap.forEach(({ sheet, mappings: sheetMappings }, sheetId) => {
    const sheetNodeId = `sheet-${sheetId}`
    nodes.push({
      id: sheetNodeId,
      kind: 'sheet',
      label: sheet.name,
      data: {
        sheetName: sheet.name,
      },
      position: { x: 0, y: yOffset },
    })

    const modelGroups = new Map<string, Mapping[]>()
    sheetMappings.forEach((mapping) => {
      if (mapping.target_model) {
        const existing = modelGroups.get(mapping.target_model) || []
        existing.push(mapping)
        modelGroups.set(mapping.target_model, existing)
      }
    })

    let modelOffset = 0

    modelGroups.forEach((modelMappings, targetModel) => {
      const modelNodeId = `model-${targetModel}-${sheetId}`
      nodes.push({
        id: modelNodeId,
        kind: 'model',
        label: targetModel,
        data: {
          odooModel: targetModel,
        },
        position: { x: 750, y: yOffset + modelOffset },
      })

      modelMappings.forEach((mapping, idx) => {
        const sourceFieldNodeId = `source-field-${mapping.id}`
        nodes.push({
          id: sourceFieldNodeId,
          kind: 'field',
          label: mapping.header_name,
          data: {
            fieldName: mapping.header_name,
            sourceColumn: mapping.header_name,
            status: mapping.status,
          },
          position: { x: 250, y: yOffset + modelOffset + idx * 80 },
        })

        if (mapping.target_field) {
          const targetFieldNodeId = `target-field-${mapping.id}`
          nodes.push({
            id: targetFieldNodeId,
            kind: 'field',
            label: mapping.target_field,
            data: {
              fieldName: mapping.target_field,
              odooModel: mapping.target_model,
              status: mapping.status,
            },
            position: { x: 500, y: yOffset + modelOffset + idx * 80 },
          })

          edges.push({
            id: `edge-source-target-${mapping.id}`,
            from: sourceFieldNodeId,
            to: targetFieldNodeId,
            kind: 'map',
            data: {
              mappingId: mapping.id,
            },
          })

          edges.push({
            id: `edge-target-model-${mapping.id}`,
            from: targetFieldNodeId,
            to: modelNodeId,
            kind: 'flow',
          })
        }

        edges.push({
          id: `edge-sheet-source-${mapping.id}`,
          from: sheetNodeId,
          to: sourceFieldNodeId,
          kind: 'flow',
          data: {
            sourceColumn: mapping.header_name,
          },
        })

        if (mapping.transforms && mapping.transforms.length > 0) {
          mapping.transforms.forEach((transform: any, tIdx: number) => {
            const transformNodeId = `transform-${transform.id}`
            nodes.push({
              id: transformNodeId,
              kind: 'transform',
              label: transform.fn,
              data: {
                transformId: transform.fn,
                params: transform.params,
              },
              position: {
                x: 375,
                y: yOffset + modelOffset + idx * 80 + tIdx * 60,
              },
            })

            const sourceId =
              tIdx === 0
                ? sourceFieldNodeId
                : `transform-${mapping.transforms![tIdx - 1].id}`
            edges.push({
              id: `edge-transform-${transform.id}`,
              from: sourceId,
              to: transformNodeId,
              kind: 'flow',
            })
          })

          if (mapping.target_field) {
            const lastTransform = mapping.transforms[mapping.transforms.length - 1]
            edges.push({
              id: `edge-transform-target-${mapping.id}`,
              from: `transform-${lastTransform.id}`,
              to: `target-field-${mapping.id}`,
              kind: 'flow',
            })
          }
        }
      })

      const loaderNodeId = `loader-${targetModel}-${sheetId}`
      nodes.push({
        id: loaderNodeId,
        kind: 'loader',
        label: `Load ${targetModel}`,
        data: {
          odooModel: targetModel,
          upsertKey: ['external_id'],
        },
        position: { x: 1000, y: yOffset + modelOffset },
      })

      edges.push({
        id: `edge-model-loader-${targetModel}-${sheetId}`,
        from: modelNodeId,
        to: loaderNodeId,
        kind: 'flow',
      })

      modelOffset += modelMappings.length * 80 + 100
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
      generatedAt: new Date().toISOString(),
    },
  }
}
