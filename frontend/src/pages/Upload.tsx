import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { datasetsApi, modulesApi, operationsApi } from '@/services/api'
import StatusOverlay, { StatusStep } from '@/components/StatusOverlay'
import ModuleSelector from '@/components/ModuleSelector'

export default function Upload() {
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadSteps, setUploadSteps] = useState<StatusStep[]>([])
  const [uploadProgress, setUploadProgress] = useState(0)
  const [selectedModules, setSelectedModules] = useState<string[]>([])
  const [showModuleSelector, setShowModuleSelector] = useState(false)
  
  const navigate = useNavigate()

  const DEFAULT_UPLOAD_STEPS: StatusStep[] = [
    { id: 'upload', label: 'Uploading file...', status: 'in_progress' },
    { id: 'profile', label: 'Analyzing columns and detecting types...', status: 'pending' },
    { id: 'complete', label: 'Profiling complete!', status: 'pending' }
  ]

  const pollOperationStatus = async (operationId: string) => {
    while (true) {
      const status = await operationsApi.getStatus(operationId)

      const steps = Array.isArray(status?.steps) && status.steps.length > 0
        ? status.steps.map((step: any) => ({
            id: String(step.id),
            label: step.label ?? '',
            status: (step.status ?? 'pending') as StatusStep['status'],
            detail: step.detail,
          }))
        : DEFAULT_UPLOAD_STEPS

      setUploadSteps(steps)

      if (typeof status?.progress === 'number') {
        setUploadProgress(status.progress)
      }

      if (status?.status === 'complete') {
        return status
      }

      if (status?.status === 'error') {
        const detail =
          status?.error ||
          steps.find((s: StatusStep) => s.status === 'error')?.detail ||
          'Upload failed'
        throw new Error(detail)
      }

      await new Promise((resolve) => setTimeout(resolve, 1000))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    setUploading(true)
    setUploadSteps(DEFAULT_UPLOAD_STEPS)
    setUploadProgress(5)

    try {
      const response = await datasetsApi.upload(file, name || undefined)
      const datasetId = response.id
      const operationId = response.operation_id

      if (operationId) {
        try {
          await pollOperationStatus(operationId)
          setUploadProgress(100)
        } catch (statusError) {
          setUploadSteps([
            {
              id: 'upload',
              label: 'Uploading file...',
              status: 'error',
              detail: statusError instanceof Error ? statusError.message : 'Upload failed'
            }
          ])
          throw statusError
        }
      } else {
        // No operation tracking available; mark steps as complete manually
        setUploadSteps(DEFAULT_UPLOAD_STEPS.map(step => ({ ...step, status: 'complete' })))
        setUploadProgress(100)
      }

      // Set selected modules if any were chosen
      if (selectedModules.length > 0) {
        try {
          await modulesApi.setDatasetModules(datasetId, selectedModules)
        } catch (moduleError) {
          console.error('Failed to set modules:', moduleError)
        }
      }

      // Small delay to show success state
      setTimeout(() => {
        setUploading(false)
        navigate(`/datasets/${datasetId}`)
      }, 600)

    } catch (error) {
      console.error('Upload failed:', error)
      setUploadSteps([
        {
          id: 'upload',
          label: 'Uploading file...',
          status: 'error',
          detail: error instanceof Error ? error.message : 'Upload failed'
        }
      ])
      alert('Upload failed. Please try again.')
      setUploading(false)
      setUploadProgress(0)
    }
  }

  return (
    <>
      <div>
        <h1 className="text-3xl font-bold mb-6">Upload File</h1>

        <div className="bg-white rounded-lg shadow p-8 max-w-2xl">
          <form onSubmit={handleSubmit}>
            <div className="mb-6">
              <label className="block text-sm font-medium mb-2">
                Dataset Name (optional)
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="My Dataset"
              />
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium mb-2">
                File (Excel or CSV)
              </label>
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="w-full"
                required
              />
            </div>

            {/* Module Selection */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium">
                  Odoo Modules (Optional)
                </label>
                <button
                  type="button"
                  onClick={() => setShowModuleSelector(!showModuleSelector)}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  {showModuleSelector ? 'Hide' : 'Show'} Module Selection
                </button>
              </div>
              {selectedModules.length > 0 && (
                <div className="text-sm text-gray-600 mb-2">
                  {selectedModules.length} module{selectedModules.length !== 1 ? 's' : ''} selected
                </div>
              )}
            </div>

            {showModuleSelector && (
              <div className="mb-6">
                <ModuleSelector
                  selectedModules={selectedModules}
                  onModulesChange={setSelectedModules}
                />
              </div>
            )}

            <button
              type="submit"
              disabled={!file || uploading}
              className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
            >
              {uploading ? 'Processing...' : 'Upload & Profile'}
            </button>
          </form>
        </div>
      </div>

      <StatusOverlay
        isOpen={uploading}
        title="Processing Upload"
        steps={uploadSteps}
        progress={uploadProgress}
      />
    </>
  )
}
