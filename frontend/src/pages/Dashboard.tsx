import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { datasetsApi } from '@/services/api'
import QuickStart from '@/components/QuickStart'

interface Dataset {
  id: number
  name: string
  created_at: string
  sheets: Array<{ name: string; n_rows: number; n_cols: number }>
}

export default function Dashboard() {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDatasets()
  }, [])

  const loadDatasets = async () => {
    try {
      const response = await datasetsApi.list()
      setDatasets(response.datasets)
    } catch (error) {
      console.error('Failed to load datasets:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (datasetId: number) => {
    setDeleting(true)
    setError(null)
    try {
      await datasetsApi.delete(datasetId)
      setDeleteConfirm(null)
      await loadDatasets()
    } catch (error) {
      console.error('Failed to delete dataset:', error)
      setError(error instanceof Error ? error.message : 'Failed to delete dataset')
    } finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return <div>Loading...</div>
  }

  return (
    <div>
      {/* Quick Start Section */}
      <QuickStart />

      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Datasets</h1>
        <Link
          to="/upload"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Upload New File
        </Link>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          <p className="font-bold">Error</p>
          <p>{error}</p>
        </div>
      )}

      {datasets.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500 mb-4">No datasets yet</p>
          <Link
            to="/upload"
            className="text-blue-600 hover:underline"
          >
            Upload your first file
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {datasets.map((dataset) => (
            <div
              key={dataset.id}
              className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow relative"
            >
              <button
                onClick={(e) => {
                  e.preventDefault()
                  setDeleteConfirm(dataset.id)
                }}
                className="absolute top-4 right-4 text-red-600 hover:text-red-800"
                title="Delete dataset"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>

              <Link to={`/datasets/${dataset.id}`} className="block">
                <h3 className="text-xl font-semibold mb-2 pr-8">{dataset.name}</h3>
                <p className="text-sm text-gray-500 mb-4">
                  {new Date(dataset.created_at).toLocaleDateString()}
                </p>
                <div className="text-sm text-gray-600">
                  {dataset.sheets.length} sheet(s)
                </div>
              </Link>
            </div>
          ))}
        </div>
      )}

      {deleteConfirm !== null && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold mb-4">Delete Dataset?</h3>
            <p className="text-gray-700 mb-6">
              Are you sure you want to delete this dataset? This will permanently delete all sheets, mappings, and associated data. This action cannot be undone.
            </p>
            <div className="flex gap-4 justify-end">
              <button
                onClick={() => setDeleteConfirm(null)}
                disabled={deleting}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                disabled={deleting}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
