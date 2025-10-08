import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { datasetsApi } from '@/services/api'

interface Dataset {
  id: number
  name: string
  created_at: string
  sheets: Array<{ name: string; n_rows: number; n_cols: number }>
}

export default function Dashboard() {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading, setLoading] = useState(true)

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

  if (loading) {
    return <div>Loading...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Datasets</h1>
        <Link
          to="/upload"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Upload New File
        </Link>
      </div>

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
            <Link
              key={dataset.id}
              to={`/datasets/${dataset.id}`}
              className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
            >
              <h3 className="text-xl font-semibold mb-2">{dataset.name}</h3>
              <p className="text-sm text-gray-500 mb-4">
                {new Date(dataset.created_at).toLocaleDateString()}
              </p>
              <div className="text-sm text-gray-600">
                {dataset.sheets.length} sheet(s)
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
