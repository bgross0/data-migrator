import { useParams } from 'react-router-dom'

export default function Import() {
  const { id } = useParams()

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Import to Odoo</h1>
      <p className="text-gray-500">TODO: Import execution UI for dataset #{id}</p>
    </div>
  )
}
