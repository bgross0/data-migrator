import { useState } from 'react'
import StatusOverlay, { StatusStep } from './StatusOverlay'

interface SheetSplitterProps {
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

export default function SheetSplitter({ sheetId, onSplitComplete }: SheetSplitterProps) {
  const [isPreviewing, setIsPreviewing] = useState(false)
  const [isSplitting, setIsSplitting] = useState(false)
  const [preview, setPreview] = useState<ModelGroup[] | null>(null)
  const [error, setError] = useState<string>('')
  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [splittingSteps, setSplittingSteps] = useState<StatusStep[]>([])
  const [splittingProgress, setSplittingProgress] = useState(0)

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

    const steps: StatusStep[] = [
      { id: 'split', label: 'Splitting sheet into model-specific files...', status: 'in_progress' }
    ]
    setSplittingSteps(steps)
    setSplittingProgress(5)

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

      if (!response.ok || !data.success) {
        const message = data?.detail || data?.error || 'Split failed'
        if (data?.errors) {
          data.errors.forEach((err: string) => console.error('Split error:', err))
        }
        throw new Error(message)
      }

      setSplittingSteps(steps.map(step => ({ ...step, status: 'complete' })))
      setSplittingProgress(100)

      setTimeout(() => {
        setPreview(null)
        setSelectedModels([])
        onSplitComplete(data)
        setIsSplitting(false)
      }, 400)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Split failed'
      setError(message)
      setSplittingSteps([
        { id: 'split', label: 'Splitting sheet into model-specific files...', status: 'error', detail: message }
      ])
      setSplittingProgress(0)
      setTimeout(() => setIsSplitting(false), 600)
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
          <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12M8 12h12M8 17h12M3 7h.01M3 12h.01M3 17h.01" />
          </svg>
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
          <svg className="w-5 h-5 text-red-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
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
                        {isSelected && <span className="text-white text-xs">✓</span>}
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
          <span className="text-4xl text-gray-400 mx-auto block mb-4">📊</span>
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

      {/* Loading Overlay for Split Operation */}
      <StatusOverlay
        isOpen={isSplitting}
        title="Splitting Sheet"
        steps={splittingSteps}
        progress={splittingProgress}
      />
    </div>
  )
}
