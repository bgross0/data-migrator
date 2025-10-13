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
  const [suggestedModules, setSuggestedModules] = useState<string[]>([])
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    setUploading(true)

    try {
      // Start upload - backend returns operation_id
      const response = await datasetsApi.upload(file, name || undefined)
      const operationId = response.operation_id
      const datasetId = response.id

      // Poll for real progress from backend
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`/api/v1/operations/${operationId}/status`)
          const status = await statusResponse.json()

          // Update steps and progress from REAL backend data
          setUploadSteps(status.steps || [])
          setUploadProgress(status.progress || 0)

          // Check if complete
          if (status.status === 'complete') {
            clearInterval(pollInterval)

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
              navigate(`/datasets/${datasetId}`)
            }, 800)
          } else if (status.status === 'error') {
            clearInterval(pollInterval)
            alert(`Upload failed: ${status.error}`)
            setUploading(false)
          }
        } catch (pollError) {
          console.error('Error polling status:', pollError)
          // Continue polling even if one request fails
        }
      }, 500) // Poll every 500ms for real-time feel

    } catch (error) {
      console.error('Upload failed:', error)
      alert('Upload failed. Please try again.')
      setUploading(false)
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
                  suggestedModules={suggestedModules}
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
        estimatedTime="About 15-30 seconds"
      />
    </>
  )
}
