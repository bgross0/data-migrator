import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { datasetsApi } from '@/services/api'

export default function Upload() {
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [uploading, setUploading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    setUploading(true)
    try {
      const dataset = await datasetsApi.upload(file, name || undefined)
      navigate(`/datasets/${dataset.id}`)
    } catch (error) {
      console.error('Upload failed:', error)
      alert('Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  return (
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

          <button
            type="submit"
            disabled={!file || uploading}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {uploading ? 'Uploading...' : 'Upload & Profile'}
          </button>
        </form>
      </div>
    </div>
  )
}
