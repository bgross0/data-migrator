interface SheetPreview {
  columns: string[]
  data: Record<string, unknown>[]
  total_rows: number
}

interface CleanedDataPreviewProps {
  sheets: Record<string, SheetPreview>
  limit: number
}

export default function CleanedDataPreview({ sheets, limit }: CleanedDataPreviewProps) {
  const sheetNames = Object.keys(sheets || {})

  if (!sheetNames.length) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 text-sm text-gray-500">
        No cleaned data preview is available for this dataset.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {sheetNames.map((name) => {
        const sheet = sheets[name]
        return (
          <div key={name} className="bg-white rounded-lg border border-gray-200">
            <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">{name}</h3>
                <p className="text-sm text-gray-500">
                  Showing up to {limit.toLocaleString()} rows · Total rows: {sheet.total_rows.toLocaleString()}
                </p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {sheet.columns.map((column) => (
                      <th
                        key={column}
                        scope="col"
                        className="px-4 py-2 text-left font-semibold text-gray-600 whitespace-nowrap"
                      >
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  {sheet.data.map((row, rowIndex) => (
                    <tr key={`${name}-row-${rowIndex}`} className="hover:bg-gray-50">
                      {sheet.columns.map((column) => (
                        <td key={`${name}-${column}-${rowIndex}`} className="px-4 py-2 text-gray-700 whitespace-nowrap">
                          <span className="font-mono text-xs">
                            {formatPreviewValue(row[column])}
                          </span>
                        </td>
                      ))}
                    </tr>
                  ))}
                  {!sheet.data.length && (
                    <tr>
                      <td
                        colSpan={sheet.columns.length || 1}
                        className="px-4 py-6 text-center text-gray-500 italic"
                      >
                        No rows available in cleaned data preview.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )
      })}
    </div>
  )
}

const formatPreviewValue = (value: unknown) => {
  if (value === null || value === undefined) {
    return '–'
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}
