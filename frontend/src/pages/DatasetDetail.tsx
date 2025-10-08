import { useParams, Link } from 'react-router-dom'
import { useState } from 'react'

export default function DatasetDetail() {
  const { id } = useParams()
  const [isExporting, setIsExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

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

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Dataset #{id}</h1>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Sheets</h2>
        <p className="text-gray-500">TODO: Show sheets and column profiles</p>
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
    </div>
  )
}
