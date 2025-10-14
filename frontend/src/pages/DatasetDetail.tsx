import { useParams, Link, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { datasetsApi, modulesApi } from '@/services/api'
import ModuleSelector from '@/components/ModuleSelector'
import SheetSplitter from '@/components/SheetSplitter'
import CleaningReport from '@/components/CleaningReport'
import CleanedDataPreview from '@/components/CleanedDataPreview'

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

interface CleaningReportResponse {
  dataset_id: number
  profiling_status: string
  cleaning_report: Record<string, unknown>
}

interface CleanedSheetPreview {
  columns: string[]
  data: Record<string, unknown>[]
  total_rows: number
}

interface CleanedDataPreviewResponse {
  dataset_id: number
  cleaned_file_path: string
  sheets: Record<string, CleanedSheetPreview>
  limit: number
}

interface ModuleSummary {
  dataset_id: number
  selected_modules: string[]
  detected_domain?: string | null
  model_count: number
  models: string[]
}

interface ModuleSuggestionDetails {
  column_count: number
  analyzed_columns: string[]
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
  const [selectedModules, setSelectedModules] = useState<string[]>([])
  const [suggestedModules, setSuggestedModules] = useState<string[]>([])
  const [showModuleSelector, setShowModuleSelector] = useState(false)
  const [showSheetSplitter, setShowSheetSplitter] = useState(false)
  const [datasetWithModules, setDatasetWithModules] = useState<any>(null)
  const [showCleaningReport, setShowCleaningReport] = useState(false)
  const [cleaningReportLoading, setCleaningReportLoading] = useState(false)
  const [cleaningReportData, setCleaningReportData] = useState<CleaningReportResponse | null>(null)
  const [cleaningReportError, setCleaningReportError] = useState<string | null>(null)
  const [showCleanedPreview, setShowCleanedPreview] = useState(false)
  const [cleanedPreviewLoading, setCleanedPreviewLoading] = useState(false)
  const [cleanedPreviewData, setCleanedPreviewData] = useState<CleanedDataPreviewResponse | null>(null)
  const [cleanedPreviewError, setCleanedPreviewError] = useState<string | null>(null)
  const [previewLimit, setPreviewLimit] = useState(50)
  const [moduleSummary, setModuleSummary] = useState<ModuleSummary | null>(null)
  const [moduleSuggestionDetails, setModuleSuggestionDetails] = useState<ModuleSuggestionDetails | null>(null)
  const [moduleStatus, setModuleStatus] = useState<string | null>(null)
  const [moduleError, setModuleError] = useState<string | null>(null)
  const [moduleSaving, setModuleSaving] = useState(false)

  useEffect(() => {
    loadDataset()
  }, [id])

  const loadDataset = async () => {
    if (!id) {
      setLoading(false)
      return
    }
    try {
      setModuleStatus(null)
      const response = await fetch(`/api/v1/datasets/${id}`)
      const data = await response.json()
      setDataset(data)
      setDatasetWithModules(data)

      await refreshModuleSummary()

      // Load module suggestions
      try {
        setSuggestedModules([])
        setModuleSuggestionDetails(null)
        const suggestionsResponse: any = await modulesApi.suggestModules(Number(id))
        setSuggestedModules(suggestionsResponse.suggested_modules || [])
        setModuleSuggestionDetails({
          column_count: suggestionsResponse.column_count ?? 0,
          analyzed_columns: suggestionsResponse.analyzed_columns || [],
        })
      } catch (moduleError) {
        console.error('Failed to load module suggestions:', moduleError)
      }
    } catch (error) {
      console.error('Failed to load dataset:', error)
    } finally {
      setLoading(false)
    }
  }

  const refreshModuleSummary = async (): Promise<ModuleSummary | null> => {
    if (!id) {
      return null
    }

    const datasetId = Number(id)
    try {
      setModuleError(null)
      const response: any = await modulesApi.getDatasetModules(datasetId)
      const summary: ModuleSummary = {
        dataset_id: response.dataset_id,
        selected_modules: response.selected_modules || [],
        detected_domain: response.detected_domain ?? null,
        model_count: response.model_count ?? 0,
        models: response.models || [],
      }
      setSelectedModules(summary.selected_modules)
      setModuleSummary(summary)
      return summary
    } catch (error) {
      const message = extractErrorMessage(error, 'Failed to load module metadata')
      console.error('Failed to load modules:', error)
      setModuleError(message)
      setModuleSummary(null)
      setSelectedModules([])
      return null
    }
  }

  useEffect(() => {
    if (!showCleaningReport || cleaningReportLoading || cleaningReportData || cleaningReportError || !id) {
      return
    }

    const datasetId = Number(id)
    setCleaningReportLoading(true)
    setCleaningReportError(null)

    datasetsApi
      .getCleaningReport(datasetId)
      .then((response) => {
        setCleaningReportData(response)
      })
      .catch((error) => {
        setCleaningReportError(extractErrorMessage(error, 'Failed to load cleaning report'))
      })
      .finally(() => setCleaningReportLoading(false))
  }, [showCleaningReport, cleaningReportLoading, cleaningReportData, cleaningReportError, id])

  useEffect(() => {
    if (!showCleanedPreview || cleanedPreviewLoading || cleanedPreviewError || !id) {
      return
    }

    if (cleanedPreviewData && cleanedPreviewData.limit === previewLimit) {
      return
    }

    const datasetId = Number(id)
    setCleanedPreviewLoading(true)
    setCleanedPreviewError(null)

    datasetsApi
      .getCleanedDataPreview(datasetId, previewLimit)
      .then((response) => {
        setCleanedPreviewData(response)
      })
      .catch((error) => {
        setCleanedPreviewError(extractErrorMessage(error, 'Failed to load cleaned data preview'))
      })
      .finally(() => setCleanedPreviewLoading(false))
  }, [showCleanedPreview, cleanedPreviewLoading, cleanedPreviewData, cleanedPreviewError, id, previewLimit])

  const updateDatasetModules = async (modules: string[]) => {
    if (!id) {
      return
    }

    setModuleSaving(true)
    setModuleError(null)
    setModuleStatus(null)

    try {
      await modulesApi.setDatasetModules(Number(id), modules)
      setDatasetWithModules((prev: any) => (prev ? { ...prev, selected_modules: modules } : null))

      const summary = await refreshModuleSummary()
      if (summary) {
        const selectedCount = summary.selected_modules.length
        const scopedModels = summary.model_count
        setModuleStatus(
          selectedCount
            ? `Saved ${selectedCount} module${selectedCount === 1 ? '' : 's'} (${scopedModels} models in scope).`
            : 'Cleared module selection; showing full model catalog.'
        )
      } else {
        setModuleStatus('Module selection updated.')
      }
    } catch (error) {
      console.error('Failed to update modules:', error)
      const message = extractErrorMessage(error, 'Failed to update modules')
      setModuleError(message)
    } finally {
      setModuleSaving(false)
    }
  }

  const handleSplitComplete = () => {
    setShowSheetSplitter(false)
    // Reload dataset to show new sheets
    loadDataset()
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

  const suggestionDiffers =
    !!moduleSummary &&
    suggestedModules.length > 0 &&
    !areSelectionsEqual(suggestedModules, moduleSummary.selected_modules)

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
              <div key={sheet.id} className="border border-gray-200 rounded p-4 flex justify-between items-center">
                <div>
                  <h3 className="font-semibold text-lg">{sheet.name}</h3>
                  <div className="flex gap-6 mt-2 text-sm text-gray-600">
                    <span>{sheet.n_rows.toLocaleString()} rows</span>
                    <span>{sheet.n_cols} columns</span>
                  </div>
                </div>
                <a
                  href={`/api/v1/sheets/${sheet.id}/download`}
                  download
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download CSV
                </a>
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

      <div className="flex gap-4 flex-wrap">
        <Link
          to={`/datasets/${id}/mappings`}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Configure Mappings
        </Link>
        
        {/* Module Selection Toggle */}
        {datasetWithModules && (
          <button
            onClick={() => setShowModuleSelector(!showModuleSelector)}
            className={`px-4 py-2 rounded ${
              selectedModules.length > 0 
                ? 'bg-green-600 text-white hover:bg-green-700' 
                : 'bg-gray-600 text-white hover:bg-gray-700'
            }`}
          >
            {selectedModules.length > 0 
              ? `${selectedModules.length} Modules Selected` 
              : 'Select Modules'
            }
          </button>
        )}

        {/* Sheet Splitting Toggle */}
        {dataset?.sheets && dataset.sheets.length > 0 && (
          <button
            onClick={() => setShowSheetSplitter(!showSheetSplitter)}
            className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
          >
            Split Sheets
          </button>
        )}
        <Link
          to={`/datasets/${id}/import`}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
        >
          Import to Odoo
        </Link>
        <a
          href={`/api/v1/datasets/${id}/download-cleaned`}
          download
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Download Cleaned Data
        </a>
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

      {/* Module Selection Section */}
      {showModuleSelector && datasetWithModules && (
        <div className="mt-8">
          <ModuleSelector
            selectedModules={selectedModules}
            onModulesChange={updateDatasetModules}
            suggestedModules={suggestedModules}
            saving={moduleSaving}
          />
        </div>
      )}

      {moduleError && (
        <div className="mt-6 flex flex-col md:flex-row md:items-center md:justify-between gap-3 border border-red-200 bg-red-50 text-red-700 rounded px-4 py-3 text-sm">
          <span>{moduleError}</span>
          <button
            onClick={() => {
              setModuleError(null)
              refreshModuleSummary()
            }}
            className="px-3 py-1 text-sm border border-red-300 rounded hover:bg-red-100"
          >
            Retry
          </button>
        </div>
      )}

      {moduleStatus && !moduleError && (
        <div className="mt-6 text-sm text-green-700 bg-green-50 border border-green-200 rounded px-4 py-3">
          {moduleStatus}
        </div>
      )}

      {moduleSummary && (
        <div className="mt-6 bg-white rounded-lg shadow p-6 space-y-5">
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-800">Module Selection Summary</h2>
              <p className="text-sm text-gray-600 mt-1">
                Focus the mapper on the modules that matter for this dataset.
              </p>
              {moduleSuggestionDetails && moduleSuggestionDetails.column_count > 0 && (
                <p className="text-xs text-gray-500 mt-2">
                  Suggestions analyzed {moduleSuggestionDetails.column_count} columns (sample:{' '}
                  {moduleSuggestionDetails.analyzed_columns.slice(0, 3).join(', ') || 'n/a'}).
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full bg-gray-100 text-gray-700 text-xs uppercase tracking-wide">
                {moduleSummary.detected_domain
                  ? formatSnakeCaseLabel(moduleSummary.detected_domain)
                  : 'Domain Pending'}
              </span>
              {moduleSaving && (
                <span className="text-xs text-gray-500">Updating…</span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Modules Selected
              </p>
              <p className="text-2xl font-semibold text-gray-900 mt-2">
                {moduleSummary.selected_modules.length}
              </p>
            </div>
            <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Models In Scope
              </p>
              <p className="text-2xl font-semibold text-gray-900 mt-2">
                {moduleSummary.model_count}
              </p>
              <p className="text-xs text-gray-500 mt-2">
                {moduleSummary.selected_modules.length
                  ? 'Filtered by selected modules'
                  : 'Full catalog available'}
              </p>
            </div>
            <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                AI Suggestions
              </p>
              <p className="text-2xl font-semibold text-gray-900 mt-2">
                {suggestedModules.length}
              </p>
              <p className="text-xs text-gray-500 mt-2">
                {suggestedModules.length
                  ? 'Use "Use Suggested" to apply'
                  : 'No suggestions yet'}
              </p>
            </div>
          </div>

          {moduleSummary.selected_modules.length > 0 ? (
            <div>
              <p className="text-sm font-medium text-gray-700">Selected module groups</p>
              <div className="flex flex-wrap gap-2 mt-3">
                {moduleSummary.selected_modules.map((module) => (
                  <span
                    key={module}
                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full"
                  >
                    {formatSnakeCaseLabel(module)}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-600">
              No modules selected yet. Apply AI suggestions or pick from the catalog to trim the
              mapping list.
            </div>
          )}

          {moduleSummary.models.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700">
                Sample models ({Math.min(moduleSummary.models.length, 8)} of {moduleSummary.model_count})
              </p>
              <div className="flex flex-wrap gap-2 mt-3">
                {moduleSummary.models.slice(0, 8).map((model) => (
                  <span
                    key={model}
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
                  >
                    {model}
                  </span>
                ))}
              </div>
            </div>
          )}

          {suggestionDiffers && suggestedModules.length > 0 && (
            <div className="text-sm text-blue-700 bg-blue-50 border border-blue-200 rounded px-3 py-2">
              AI suggests selecting{' '}
              {formatModuleSuggestionsPreview(suggestedModules)}. Use the button above to apply the
              recommendation.
            </div>
          )}
        </div>
      )}

      {/* Sheet Splitter Section */}
      {showSheetSplitter && dataset?.sheets && dataset.sheets.length > 0 && (
        <div className="mt-8">
          <SheetSplitter
            sheetId={dataset.sheets[0].id}
            onSplitComplete={handleSplitComplete}
          />
        </div>
      )}

      <div className="mt-10 space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold text-gray-800">Cleaning Report</h2>
              <p className="text-sm text-gray-600 mt-1">
                Review the automated cleaning steps applied during profiling.
              </p>
            </div>
            <button
              onClick={() => setShowCleaningReport((prev) => !prev)}
              className="px-4 py-2 text-sm rounded border border-gray-300 hover:bg-gray-50"
            >
              {showCleaningReport ? 'Hide Report' : 'View Report'}
            </button>
          </div>

          {showCleaningReport && (
            <div className="mt-4">
              {cleaningReportLoading && (
                <div className="text-sm text-gray-600">Loading cleaning report...</div>
              )}
              {cleaningReportError && (
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 border border-red-200 bg-red-50 text-red-700 rounded p-3 text-sm">
                  <span>{cleaningReportError}</span>
                  <button
                    onClick={() => {
                      setCleaningReportError(null)
                      setCleaningReportData(null)
                    }}
                    className="px-3 py-1 text-sm border border-red-300 text-red-700 rounded hover:bg-red-100"
                  >
                    Retry
                  </button>
                </div>
              )}
              {!cleaningReportLoading && !cleaningReportError && cleaningReportData && (
                <CleaningReport
                  status={cleaningReportData.profiling_status}
                  report={cleaningReportData.cleaning_report}
                />
              )}
              {!cleaningReportLoading && !cleaningReportError && !cleaningReportData && (
                <div className="text-sm text-gray-500">
                  Cleaning report is not available for this dataset.
                </div>
              )}
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold text-gray-800">Cleaned Data Preview</h2>
              <p className="text-sm text-gray-600 mt-1">
                Inspect a sample of the cleaned dataset before exporting or importing.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-600">
                Preview rows:
                <select
                  value={previewLimit}
                  onChange={(event) => {
                    const limit = Number(event.target.value)
                    setPreviewLimit(limit)
                    setCleanedPreviewData(null)
                  }}
                  className="ml-2 border border-gray-300 rounded px-2 py-1 text-sm"
                  disabled={!showCleanedPreview}
                >
                  {[25, 50, 100, 250].map((limitOption) => (
                    <option key={limitOption} value={limitOption}>
                      {limitOption}
                    </option>
                  ))}
                </select>
              </label>
              <button
                onClick={() => setShowCleanedPreview((prev) => !prev)}
                className="px-4 py-2 text-sm rounded border border-gray-300 hover:bg-gray-50"
              >
                {showCleanedPreview ? 'Hide Preview' : 'View Preview'}
              </button>
            </div>
          </div>

          {showCleanedPreview && (
            <div className="mt-4">
              {cleanedPreviewLoading && (
                <div className="text-sm text-gray-600">Loading cleaned data preview...</div>
              )}
              {cleanedPreviewError && (
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 border border-red-200 bg-red-50 text-red-700 rounded p-3 text-sm">
                  <span>{cleanedPreviewError}</span>
                  <button
                    onClick={() => {
                      setCleanedPreviewError(null)
                      setCleanedPreviewData(null)
                    }}
                    className="px-3 py-1 text-sm border border-red-300 text-red-700 rounded hover:bg-red-100"
                  >
                    Retry
                  </button>
                </div>
              )}
              {!cleanedPreviewLoading && !cleanedPreviewError && cleanedPreviewData && (
                <CleanedDataPreview
                  sheets={cleanedPreviewData.sheets}
                  limit={cleanedPreviewData.limit}
                />
              )}
              {!cleanedPreviewLoading && !cleanedPreviewError && !cleanedPreviewData && (
                <div className="text-sm text-gray-500">
                  Cleaned data preview is not available for this dataset.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const extractErrorMessage = (error: unknown, fallback: string) => {
  if (typeof error === 'object' && error && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response
    if (response?.data?.detail) {
      return response.data.detail
    }
  }

  if (error instanceof Error) {
    return error.message
  }

  return fallback
}

const areSelectionsEqual = (first: string[], second: string[]) => {
  if (first.length !== second.length) {
    return false
  }
  const sortedFirst = [...first].sort()
  const sortedSecond = [...second].sort()
  return sortedFirst.every((value, index) => value === sortedSecond[index])
}

const formatSnakeCaseLabel = (value?: string | null) => {
  if (!value) {
    return ''
  }
  return value
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

const formatModuleSuggestionsPreview = (modules: string[], limit = 4) => {
  if (!modules.length) {
    return 'no modules'
  }
  const shown = modules.slice(0, limit)
  const preview = shown
    .map((module) => formatSnakeCaseLabel(module) || module)
    .join(', ')
  const remainder = modules.length - shown.length
  return remainder > 0 ? `${preview} +${remainder} more` : preview
}
