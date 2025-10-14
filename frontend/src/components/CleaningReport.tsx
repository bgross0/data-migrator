import { useMemo } from 'react'

interface CleaningReportProps {
  status: string
  report: Record<string, unknown>
}

const isPlainObject = (value: unknown): value is Record<string, unknown> =>
  !!value && typeof value === 'object' && !Array.isArray(value)

const formatValue = (value: unknown) => {
  if (Array.isArray(value) || isPlainObject(value)) {
    return (
      <pre className="bg-gray-50 border border-gray-200 rounded p-3 text-xs overflow-x-auto whitespace-pre-wrap">
        {JSON.stringify(value, null, 2)}
      </pre>
    )
  }
  if (typeof value === 'number' || typeof value === 'string' || typeof value === 'boolean') {
    return <span className="font-mono text-sm text-gray-700">{String(value)}</span>
  }
  return <span className="text-sm text-gray-500">N/A</span>
}

export default function CleaningReport({ status, report }: CleaningReportProps) {
  const keys = useMemo(() => Object.keys(report || {}), [report])

  if (!report || keys.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 text-sm text-gray-500">
        No cleaning report is available for this dataset.
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-800">Cleaning Report</h3>
        <p className="text-sm text-gray-500 mt-1">
          Profiling status: <span className="font-medium text-gray-700 uppercase">{status}</span>
        </p>
      </div>
      <div className="space-y-4">
        {keys.map((key) => (
          <div key={key} className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">{key}</h4>
            {formatValue((report as Record<string, unknown>)[key])}
          </div>
        ))}
      </div>
    </div>
  )
}
