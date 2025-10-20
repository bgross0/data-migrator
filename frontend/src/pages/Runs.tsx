import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { graphsApi, runsApi } from '@/services/api'

type GraphRunStatus = {
  id: string
  graph_id: string
  dataset_id: number | null
  status: string
  progress: number
  started_at?: string | null
  finished_at?: string | null
  current_node?: string | null
  context?: Record<string, any>
  logs: Array<{ timestamp: string; level: string; message: string }>
  error_message?: string | null
  graphName?: string
}

type ImportRun = {
  id: number
  dataset_id: number
  status: string
  started_at: string
  finished_at?: string | null
  progress?: number
  error_message?: string | null
}

const POLL_INTERVAL_MS = 5_000

export default function Runs() {
  const location = useLocation()
  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search])
  const highlightedRunId = searchParams.get('runId')

  const [graphRuns, setGraphRuns] = useState<GraphRunStatus[]>([])
  const [importRuns, setImportRuns] = useState<ImportRun[]>([])
  const [graphsMeta, setGraphsMeta] = useState<Record<string, string>>({})
  const [selectedRunId, setSelectedRunId] = useState<string | null>(highlightedRunId)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    setSelectedRunId(highlightedRunId)
  }, [highlightedRunId])

  useEffect(() => {
    if (!graphRuns.some((run) => run.status === 'running' || run.status === 'queued')) {
      return
    }

    const interval = setInterval(() => {
      refreshActiveGraphRuns()
    }, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [graphRuns])

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [graphSpecs, importRunsResponse] = await Promise.all([
        graphsApi.list(),
        runsApi.list(),
      ])

      const nameMap = Object.fromEntries(graphSpecs.map((graph: any) => [graph.id, graph.name]))
      setGraphsMeta(nameMap)

      const graphRunsResponses = await Promise.all(
        graphSpecs.map(async (graph: any) => {
          const runs = await graphsApi.getRuns(graph.id)
          return runs.map((run: GraphRunStatus) => ({
            ...run,
            graphName: nameMap[run.graph_id] ?? graph.name ?? 'Graph',
          }))
        })
      )

      const flattenedRuns = graphRunsResponses.flat().sort((a, b) => {
        const aTime = a.started_at ? Date.parse(a.started_at) : 0
        const bTime = b.started_at ? Date.parse(b.started_at) : 0
        return bTime - aTime
      })

      setGraphRuns(flattenedRuns)
      setImportRuns(importRunsResponse.runs || [])
    } catch (err) {
      console.error('Failed to load runs', err)
      setError('Failed to load runs. Please refresh.')
    } finally {
      setLoading(false)
    }
  }

  const refreshActiveGraphRuns = async () => {
    const activeRuns = graphRuns.filter((run) => run.status === 'running' || run.status === 'queued')
    if (activeRuns.length === 0) {
      return
    }

    try {
      const updates = await Promise.all(activeRuns.map((run) => graphsApi.getRunStatus(run.id)))
      const updateMap = Object.fromEntries(
        updates.map((run: GraphRunStatus) => [
          run.id,
          {
            ...run,
            graphName: graphsMeta[run.graph_id] ?? run.graphName ?? 'Graph',
          },
        ])
      )

      setGraphRuns((prev) =>
        prev.map((run) => updateMap[run.id] ?? run)
      )
    } catch (err) {
      console.error('Failed to refresh runs', err)
    }
  }

  const selectedRun = selectedRunId
    ? graphRuns.find((run) => run.id === selectedRunId) ?? null
    : null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Run Dashboard</h1>
        <p className="text-gray-600">
          Track graph executions and legacy import runs in one place.
        </p>
      </div>

      {loading && (
        <div className="rounded border border-gray-200 bg-white p-4 text-gray-600">
          Loading runs…
        </div>
      )}

      {error && (
        <div className="rounded border border-red-200 bg-red-50 p-4 text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded border border-gray-200 bg-white p-4">
            <header className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Graph Runs</h2>
                <p className="text-sm text-gray-500">
                  Generated via Flow View or templates.
                </p>
              </div>
              <button
                className="text-sm text-blue-600 hover:underline"
                onClick={fetchData}
              >
                Refresh
              </button>
            </header>

            {graphRuns.length === 0 ? (
              <p className="text-sm text-gray-500">No graph runs yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Run ID</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Graph</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Status</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Progress</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Current Node</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Started</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {graphRuns.map((run) => {
                      const isHighlighted = run.id === selectedRunId
                      return (
                        <tr
                          key={run.id}
                          className={`cursor-pointer hover:bg-gray-50 ${isHighlighted ? 'bg-blue-50' : ''}`}
                          onClick={() => setSelectedRunId(run.id)}
                        >
                          <td className="px-4 py-2 font-mono text-xs">{run.id}</td>
                          <td className="px-4 py-2">{run.graphName}</td>
                          <td className="px-4 py-2">
                            <StatusBadge status={run.status} />
                          </td>
                          <td className="px-4 py-2">{run.progress ?? 0}%</td>
                          <td className="px-4 py-2 text-sm text-gray-600">
                            {run.current_node || '—'}
                          </td>
                          <td className="px-4 py-2 text-xs text-gray-500">
                            {run.started_at ? new Date(run.started_at).toLocaleString() : '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {selectedRun && (
              <div className="mt-4 rounded border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700">
                <h3 className="mb-2 text-base font-semibold text-gray-900">
                  Run Details ({selectedRun.id})
                </h3>
                <div className="space-y-2">
                  <DetailRow label="Graph">{selectedRun.graphName}</DetailRow>
                  <DetailRow label="Status">
                    <StatusBadge status={selectedRun.status} />
                  </DetailRow>
                  <DetailRow label="Progress">{selectedRun.progress ?? 0}%</DetailRow>
                  <DetailRow label="Current node">{selectedRun.current_node || '—'}</DetailRow>
                  {selectedRun.context && (
                    <>
                      <DetailRow label="Executed models">
                        {Array.isArray(selectedRun.context.executed_nodes)
                          ? selectedRun.context.executed_nodes.length
                          : 0}
                      </DetailRow>
                      {Array.isArray(selectedRun.context.failed_nodes) && (
                        <DetailRow label="Failed models">
                          {selectedRun.context.failed_nodes.length > 0
                            ? selectedRun.context.failed_nodes.join(', ')
                            : '0'}
                        </DetailRow>
                      )}
                      {typeof selectedRun.context.total_emitted === 'number' && (
                        <DetailRow label="Rows emitted">{selectedRun.context.total_emitted}</DetailRow>
                      )}
                    </>
                  )}
                  <DetailRow label="Started">
                    {selectedRun.started_at
                      ? new Date(selectedRun.started_at).toLocaleString()
                      : '—'}
                  </DetailRow>
                  <DetailRow label="Finished">
                    {selectedRun.finished_at
                      ? new Date(selectedRun.finished_at).toLocaleString()
                      : '—'}
                  </DetailRow>
                  {selectedRun.error_message && (
                    <DetailRow label="Error">
                      <span className="text-red-700">{selectedRun.error_message}</span>
                    </DetailRow>
                  )}

                  {selectedRun.logs?.length > 0 && (
                    <div>
                      <p className="font-medium text-gray-800">Recent logs</p>
                      <ul className="mt-2 space-y-1">
                        {selectedRun.logs.slice(-5).map((log, idx) => (
                          <li key={`${log.timestamp}-${idx}`}>
                            <span className="font-mono text-xs text-gray-500">
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </span>{' '}
                            <span className="uppercase text-gray-600">{log.level}</span>{' '}
                            {log.message}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>

          <section className="rounded border border-gray-200 bg-white p-4">
            <header className="mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Import Runs</h2>
              <p className="text-sm text-gray-500">
                Legacy import runs triggered directly against datasets.
              </p>
            </header>
            {importRuns.length === 0 ? (
              <p className="text-sm text-gray-500">No import runs yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Run ID</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Dataset</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Status</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Started</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-500">Finished</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {importRuns.map((run) => (
                      <tr key={run.id}>
                        <td className="px-4 py-2 font-mono text-xs">{run.id}</td>
                        <td className="px-4 py-2">Dataset #{run.dataset_id}</td>
                        <td className="px-4 py-2">
                          <StatusBadge status={run.status} />
                        </td>
                        <td className="px-4 py-2 text-xs text-gray-500">
                          {new Date(run.started_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-2 text-xs text-gray-500">
                          {run.finished_at ? new Date(run.finished_at).toLocaleString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase()
  const styles: Record<string, string> = {
    queued: 'bg-gray-100 text-gray-700',
    running: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    partial: 'bg-yellow-100 text-yellow-700',
    failed: 'bg-red-100 text-red-700',
  }

  return (
    <span className={`rounded px-2 py-1 text-xs font-semibold ${styles[normalized] ?? 'bg-gray-100 text-gray-700'}`}>
      {status}
    </span>
  )
}

function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 text-sm">
      <span className="font-medium text-gray-600">{label}</span>
      <span className="text-right text-gray-800">{children}</span>
    </div>
  )
}
