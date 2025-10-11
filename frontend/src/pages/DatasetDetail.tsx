import { useParams, Link, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { datasetsApi } from '@/services/api'

interface Sheet {
  id: number
  name: string
  n_rows: number
  n_cols: number
}

interface Dataset {
  id: number
  name: string
  sheets: Sheet[]
}

export default function DatasetDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [loading, setLoading] = useState(true)
  const [isExporting, setIsExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    loadDataset()
  }, [id])

  const loadDataset = async () => {
    try {
      const response = await fetch(`/api/v1/datasets/${id}`)
      const data = await response.json()
      setDataset(data)
    } catch (error) {
      console.error('Failed to load dataset:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleExportToOdooMigrate = async () => {
    setIsExporting(true)
    setExportError(null)

    try {
      const response = await fetch(
        `/api/v1/datasets/${id}/export/odoo-migrate`,
        { method: 'POST' }
      )

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Export failed')
      }

      // Download the ZIP file
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `dataset_${id}_odoo_migrate.zip`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export error:', error)
      setExportError(error instanceof Error ? error.message : 'Export failed')
    } finally {
      setIsExporting(false)
    }
  }

  const handleDelete = async () => {
    if (!id) return
    setDeleting(true)
    try {
      await datasetsApi.delete(parseInt(id))
      navigate('/')
    } catch (error) {
      console.error('Failed to delete dataset:', error)
      setExportError(error instanceof Error ? error.message : 'Failed to delete dataset')
      setDeleteConfirm(false)
    } finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return <div className="p-6">Loading...</div>
  }

  if (!dataset) {
    return <div className="p-6">Dataset not found</div>
  }

  return (
    <div>
      <Link to="/" className="text-blue-600 hover:underline text-sm mb-2 block">
        ← Back to Datasets
      </Link>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">{dataset.name}</h1>
        <button
          onClick={() => setDeleteConfirm(true)}
          className="text-red-600 hover:text-red-800 flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          Delete Dataset
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Sheets</h2>
        {dataset.sheets && dataset.sheets.length > 0 ? (
          <div className="space-y-3">
            {dataset.sheets.map((sheet) => (
              <div key={sheet.id} className="border border-gray-200 rounded p-4">
                <h3 className="font-semibold text-lg">{sheet.name}</h3>
                <div className="flex gap-6 mt-2 text-sm text-gray-600">
                  <span>{sheet.n_rows.toLocaleString()} rows</span>
                  <span>{sheet.n_cols} columns</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No sheets found</p>
        )}
      </div>

      {exportError && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          <p className="font-bold">Export Error</p>
          <p>{exportError}</p>
        </div>
      )}

      <div className="flex gap-4">
        <Link
          to={`/datasets/${id}/mappings`}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Configure Mappings
        </Link>
        <Link
          to={`/datasets/${id}/import`}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
        >
          Import to Odoo
        </Link>
        <button
          onClick={handleExportToOdooMigrate}
          disabled={isExporting}
          className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isExporting ? (
            <>
              <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Exporting...
            </>
          ) : (
            <>
              📦 Export to odoo-migrate
            </>
          )}
        </button>
      </div>

      {deleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold mb-4">Delete Dataset?</h3>
            <p className="text-gray-700 mb-6">
              Are you sure you want to delete this dataset? This will permanently delete all sheets, mappings, and associated data. This action cannot be undone.
            </p>
            <div className="flex gap-4 justify-end">
              <button
                onClick={() => setDeleteConfirm(false)}
                disabled={deleting}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
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
