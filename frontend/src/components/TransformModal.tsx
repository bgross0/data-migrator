import { useState, useEffect } from 'react'

interface Transform {
  id: number
  mapping_id: number
  order: number
  fn: string
  params: Record<string, any> | null
}

interface TransformMetadata {
  name: string
  description: string
  params: Array<{
    name: string
    type: string
    required: boolean
    default?: any
  }>
}

interface Props {
  mappingId: number
  isOpen: boolean
  onClose: () => void
  onUpdate: () => void
}

export default function TransformModal({ mappingId, isOpen, onClose, onUpdate }: Props) {
  const [transforms, setTransforms] = useState<Transform[]>([])
  const [availableTransforms, setAvailableTransforms] = useState<Record<string, TransformMetadata>>({})
  const [loading, setLoading] = useState(false)
  const [addingNew, setAddingNew] = useState(false)
  const [selectedFn, setSelectedFn] = useState('')
  const [params, setParams] = useState<Record<string, any>>({})
  const [testValue, setTestValue] = useState('')
  const [testResult, setTestResult] = useState<any>(null)

  useEffect(() => {
    if (isOpen) {
      loadTransforms()
      loadAvailableTransforms()
    }
  }, [isOpen, mappingId])

  const loadTransforms = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/v1/mappings/${mappingId}/transforms`)
      const data = await response.json()
      setTransforms(data)
    } catch (error) {
      console.error('Failed to load transforms:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadAvailableTransforms = async () => {
    try {
      const response = await fetch(`/api/v1/transforms/available`)
      const data = await response.json()
      setAvailableTransforms(data)
    } catch (error) {
      console.error('Failed to load available transforms:', error)
    }
  }

  const addTransform = async () => {
    try {
      await fetch(`/api/v1/mappings/${mappingId}/transforms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fn: selectedFn,
          params: Object.keys(params).length > 0 ? params : null
        })
      })
      await loadTransforms()
      setAddingNew(false)
      setSelectedFn('')
      setParams({})
      onUpdate()
    } catch (error) {
      console.error('Failed to add transform:', error)
    }
  }

  const deleteTransform = async (transformId: number) => {
    try {
      await fetch(`/api/v1/transforms/${transformId}`, {
        method: 'DELETE'
      })
      await loadTransforms()
      onUpdate()
    } catch (error) {
      console.error('Failed to delete transform:', error)
    }
  }

  const moveTransform = async (transformId: number, direction: 'up' | 'down') => {
    const currentIndex = transforms.findIndex(t => t.id === transformId)
    const newOrder = direction === 'up' ? currentIndex - 1 : currentIndex + 1

    if (newOrder < 0 || newOrder >= transforms.length) return

    try {
      await fetch(`/api/v1/transforms/${transformId}/reorder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_order: newOrder })
      })
      await loadTransforms()
      onUpdate()
    } catch (error) {
      console.error('Failed to reorder transform:', error)
    }
  }

  const testTransform = async () => {
    if (!selectedFn || !testValue) return

    try {
      const response = await fetch(`/api/v1/transforms/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fn: selectedFn,
          params: Object.keys(params).length > 0 ? params : null,
          sample_value: testValue
        })
      })
      const data = await response.json()
      setTestResult(data.output)
    } catch (error) {
      console.error('Failed to test transform:', error)
    }
  }

  const handleParamChange = (paramName: string, value: any) => {
    setParams(prev => ({ ...prev, [paramName]: value }))
  }

  if (!isOpen) return null

  const selectedTransformMeta = selectedFn ? availableTransforms[selectedFn] : null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold">Data Transforms</h2>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
          </div>

          <p className="text-sm text-gray-600 mb-4">
            Apply data cleaning and transformation functions to this column. Transforms execute in order from top to bottom.
          </p>

          {/* Existing transforms */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Transform Chain</h3>
            {transforms.length === 0 ? (
              <div className="bg-gray-50 rounded p-4 text-center text-gray-500 text-sm">
                No transforms applied yet
              </div>
            ) : (
              <div className="space-y-2">
                {transforms.map((transform, idx) => (
                  <div key={transform.id} className="flex items-center gap-2 bg-gray-50 rounded p-3">
                    <div className="flex flex-col gap-1">
                      <button
                        onClick={() => moveTransform(transform.id, 'up')}
                        disabled={idx === 0}
                        className="text-xs text-gray-500 hover:text-gray-700 disabled:text-gray-300"
                      >
                        ▲
                      </button>
                      <button
                        onClick={() => moveTransform(transform.id, 'down')}
                        disabled={idx === transforms.length - 1}
                        className="text-xs text-gray-500 hover:text-gray-700 disabled:text-gray-300"
                      >
                        ▼
                      </button>
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-sm">
                        {idx + 1}. {availableTransforms[transform.fn]?.name || transform.fn}
                      </div>
                      {transform.params && (
                        <div className="text-xs text-gray-500">
                          {JSON.stringify(transform.params)}
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => deleteTransform(transform.id)}
                      className="px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Add new transform */}
          {!addingNew ? (
            <button
              onClick={() => setAddingNew(true)}
              className="w-full px-3 py-2 border border-dashed border-gray-400 rounded text-gray-600 hover:bg-gray-50"
            >
              + Add Transform
            </button>
          ) : (
            <div className="border border-gray-300 rounded p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Transform Function
                </label>
                <select
                  value={selectedFn}
                  onChange={(e) => {
                    setSelectedFn(e.target.value)
                    setParams({})
                    setTestResult(null)
                  }}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                >
                  <option value="">Select a function...</option>
                  {Object.entries(availableTransforms).map(([fn, meta]) => (
                    <option key={fn} value={fn}>{meta.name}</option>
                  ))}
                </select>
                {selectedTransformMeta && (
                  <p className="text-xs text-gray-500 mt-1">{selectedTransformMeta.description}</p>
                )}
              </div>

              {/* Param inputs */}
              {selectedTransformMeta?.params.map((param) => (
                <div key={param.name}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {param.name} {param.required && '*'}
                  </label>
                  <input
                    type={param.type === 'integer' ? 'number' : 'text'}
                    value={params[param.name] || param.default || ''}
                    onChange={(e) => handleParamChange(param.name, e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    placeholder={param.default?.toString()}
                  />
                </div>
              ))}

              {/* Test transform */}
              {selectedFn && (
                <div className="bg-blue-50 border border-blue-200 rounded p-3">
                  <label className="block text-sm font-medium text-blue-900 mb-1">
                    Test Transform
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={testValue}
                      onChange={(e) => setTestValue(e.target.value)}
                      placeholder="Enter test value..."
                      className="flex-1 border border-blue-300 rounded px-3 py-2"
                    />
                    <button
                      onClick={testTransform}
                      className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                    >
                      Test
                    </button>
                  </div>
                  {testResult !== null && (
                    <div className="mt-2 text-sm">
                      <span className="text-blue-700">Result: </span>
                      <span className="font-mono bg-white px-2 py-1 rounded">{String(testResult)}</span>
                    </div>
                  )}
                </div>
              )}

              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => {
                    setAddingNew(false)
                    setSelectedFn('')
                    setParams({})
                    setTestResult(null)
                  }}
                  className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={addTransform}
                  disabled={!selectedFn}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
                >
                  Add
                </button>
              </div>
            </div>
          )}

          <div className="mt-6 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
