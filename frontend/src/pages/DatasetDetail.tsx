import { useParams, Link } from 'react-router-dom'

export default function DatasetDetail() {
  const { id } = useParams()

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Dataset #{id}</h1>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Sheets</h2>
        <p className="text-gray-500">TODO: Show sheets and column profiles</p>
      </div>

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
      </div>
    </div>
  )
}
