import { useState } from 'react'
import { Split, Download, AlertTriangle, CheckCircle, FileSpreadsheet } from 'lucide-react'

interface SheetSplitterProps {
  datasetId: number
  sheetId: number
  onSplitComplete: (result: SplitResult) => void
}

interface ModelGroup {
  model: string
  display_name: string
  column_count: number
  columns: string[]
  record_count: number
}

interface SplitResult {
  success: boolean
  created_sheets: Array<{
    id: number
    name: string
    model: string
    rows: number
    columns: number
    file_path: string
  }>
  errors?: string[]
}

export default function SheetSplitter({ datasetId, sheetId, onSplitComplete }: SheetSplitterProps) {
  const [isPreviewing, setIsPreviewing] = useState(false)
  const [isSplitting, setIsSplitting] = useState(false)
  const [preview, setPreview] = useState<ModelGroup[] | null>(null)
  const [error, setError] = useState<string>('')
  const [selectedModels, setSelectedModels] = useState<string[]>([])

  const loadPreview = async () => {
    setIsPreviewing(true)
    setError('')

    try {
      const response = await fetch(`/api/v1/sheets/${sheetId}/preview-split`)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to preview split')
      }

      if (data.can_split) {
        setPreview(data.models)
        setSelectedModels(data.models.map((m: ModelGroup) => m.model))
      } else {
        setError(data.error || 'Cannot split this sheet')
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to load preview')
    } finally {
      setIsPreviewing(false)
    }
  }

  const executeSplit = async () => {
    if (selectedModels.length === 0) {
      setError('Please select at least one model to split')
      return
    }

    setIsSplitting(true)
    setError('')

    try {
      const response = await fetch(`/api/v1/sheets/${sheetId}/split`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          models: selectedModels,
          delete_original: false
        })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Split failed')
      }

      if (data.success) {
        setPreview(null)
        setSelectedModels([])
        onSplitComplete(data)
      } else {
        setError(data.error || 'Split failed')
        if (data.errors) {
          data.errors.forEach((err: string) => console.error('Split error:', err))
        }
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Split failed')
    } finally {
      setIsSplitting(false)
    }
  }

  const downloadSplitSheet = async (sheetData: any) => {
    try {
      const response = await fetch(`/api/v1/sheets/${sheetData.id}/download`)
      if (!response.ok) {
        throw new Error('Download failed')
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${sheetData.name}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Download failed:', error)
      alert('Download failed')
    }
  }

  const toggleModel = (model: string) => {
    if (selectedModels.includes(model)) {
      setSelectedModels(selectedModels.filter(m => m !== model))
    } else {
      setSelectedModels([...selectedModels, model])
    }
  }

  return (
    <div className="bg-white rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Split className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold">Sheet Splitter</h3>
        </div>
        {!preview && (
          <button
            onClick={loadPreview}
            disabled={isPreviewing}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {isPreviewing ? 'Loading...' : 'Preview Split'}
          </button>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
          <div>
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      )}

      {/* Preview State */}
      {preview && (
        <div className="space-y-6">
          {/* Models to Split */}
          <div>
            <h4 className="font-medium mb-3">Models Detected ({preview.length})</h4>
            <div className="space-y-3">
              {preview.map((model) => {
                const isSelected = selectedModels.includes(model.model)
                
                return (
                  <div
                    key={model.model}
                    className={`border rounded-lg p-4 cursor-pointer transition-all ${
                      isSelected 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => toggleModel(model.model)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h5 className="font-medium">{model.display_name}</h5>
                          <span className="text-sm text-gray-600">({model.model})</span>
                        </div>
                        <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                          <span>{model.column_count} columns</span>
                          <span>{model.record_count} records</span>
                        </div>
                        <div className="mt-2">
                          <div className="text-xs text-gray-500 mb-1">Columns:</div>
                          <div className="flex flex-wrap gap-1">
                            {model.columns.slice(0, 10).map((col) => (
                              <span key={col} className="px-2 py-0.5 bg-gray-100 rounded text-xs">
                                {col}
                              </span>
                            ))}
                            {model.columns.length > 10 && (
                              <span className="px-2 py-0.5 bg-gray-100 rounded text-xs">
                                +{model.columns.length - 10} more
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                        isSelected ? 'border-blue-500 bg-blue-500' : 'border-gray-300'
                      }`}>
                        {isSelected && <CheckCircle className="w-3 h-3 text-white" />}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Split Actions */}
          <div className="flex items-center justify-between pt-4 border-t">
            <div className="text-sm text-gray-600">
              {selectedModels.length} model{selectedModels.length !== 1 ? 's' : ''} selected for splitting
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  setPreview(null)
                  setSelectedModels([])
                }}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={executeSplit}
                disabled={isSplitting || selectedModels.length === 0}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {isSplitting ? 'Splitting...' : `Split ${selectedModels.length} Model${selectedModels.length !== 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Instructions */}
      {!preview && !error && (
        <div className="text-center py-8">
          <FileSpreadsheet className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h4 className="font-medium text-gray-900 mb-2">Split Multi-Model Sheet</h4>
          <p className="text-gray-600 mb-4">
            Split a sheet containing multiple Odoo models into separate files per model
          </p>
          <div className="text-sm text-gray-500 max-w-md mx-auto">
            <p className="mb-2">This feature will:</p>
            <ul className="text-left space-y-1">
              <li>• Analyze confirmed mappings to detect different models</li>
              <li>• Group columns by target model</li>
              <li>• Create separate CSV files for each model</li>
              <li>• Map column names to Odoo field names</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
