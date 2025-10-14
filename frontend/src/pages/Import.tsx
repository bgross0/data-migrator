import { useParams, Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { datasetsApi, runsApi } from '@/services/api'

export default function Import() {
  const { id } = useParams()
  const [dataset, setDataset] = useState<any>(null)
  const [runs, setRuns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    loadData()
  }, [id])

  const loadData = async () => {
    try {
      const [datasetData, runsData] = await Promise.all([
        datasetsApi.get(Number(id)),
        runsApi.list()
      ])
      setDataset(datasetData)
      setRuns(runsData.runs || [])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const startImport = async (dryRun = false) => {
    setImporting(true)
    try {
      const run = await runsApi.create(Number(id), { dry_run: dryRun })
      setRuns(prev => [run, ...prev])
    } catch (error) {
      console.error('Import failed:', error)
      alert('Import failed')
    } finally {
      setImporting(false)
    }
  }

  if (loading) {
    return <div className="p-6">Loading...</div>
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Import to Odoo</h1>
          <p className="text-gray-500">Dataset: {dataset?.name}</p>
        </div>
        <Link 
          to={`/datasets/${id}`}
          className="text-blue-600 hover:text-blue-700"
        >
          ← Back to Dataset
        </Link>
      </div>

      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Import Options</h2>
        <div className="flex gap-4">
          <button
            onClick={() => startImport(true)}
            disabled={importing}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {importing ? 'Running...' : 'Dry Run'}
          </button>
          <button
            onClick={() => startImport(false)}
            disabled={importing}
            className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700 disabled:opacity-50"
          >
            {importing ? 'Importing...' : 'Start Import'}
          </button>
        </div>
        <div className="mt-4 text-sm text-gray-600">
          <p><strong>Dry Run:</strong> Validates data without importing to Odoo</p>
          <p><strong>Start Import:</strong> Actually imports data to Odoo</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-xl font-semibold mb-4">Import History</h2>
        {runs.length === 0 ? (
          <p className="text-gray-500">No imports run yet</p>
        ) : (
          <div className="space-y-4">
            {runs.map((run) => (
              <div key={run.id} className="border rounded p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-medium">Import #{run.id}</h3>
                    <p className="text-sm text-gray-600">
                      Status: {run.status} • {run.created_at}
                    </p>
                    {run.dry_run && (
                      <span className="inline-block px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                        Dry Run
                      </span>
                    )}
                  </div>
                  <div className="text-right">
                    {run.status === 'completed' && (
                      <div>
                        <p className="text-green-600 font-medium">✅ Success</p>
                        <p className="text-sm">{run.records_processed} records</p>
                      </div>
                    )}
                    {run.status === 'failed' && (
                      <div>
                        <p className="text-red-600 font-medium">❌ Failed</p>
                        <p className="text-sm">{run.error_message}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
