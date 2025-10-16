import { useState, useEffect, useCallback, useMemo } from 'react'
import { transformsApi } from '@/services/api'

interface Transform {
  id: number
  mapping_id: number
  order: number
  fn: string
  params: Record<string, unknown> | null
}

interface TransformParamMeta {
  name: string
  type: string
  required: boolean
  default?: unknown
  description?: string
}

interface TransformMetadata {
  name: string
  description: string
  params: TransformParamMeta[]
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
  const [loadingTransforms, setLoadingTransforms] = useState(false)
  const [transformsError, setTransformsError] = useState<string | null>(null)
  const [availableError, setAvailableError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [addingNew, setAddingNew] = useState(false)
  const [selectedFn, setSelectedFn] = useState('')
  const [params, setParams] = useState<Record<string, unknown>>({})
  const [testValue, setTestValue] = useState('')
  const [testResult, setTestResult] = useState<unknown>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [testError, setTestError] = useState<string | null>(null)
  const [testLoading, setTestLoading] = useState(false)

  const selectedTransformMeta = useMemo(
    () => (selectedFn ? availableTransforms[selectedFn] : null),
    [availableTransforms, selectedFn]
  )

  const resetForm = useCallback(() => {
    setAddingNew(false)
    setSelectedFn('')
    setParams({})
    setTestValue('')
    setTestResult(null)
    setFormError(null)
    setTestError(null)
  }, [])

  const loadTransforms = useCallback(async () => {
    if (!isOpen) {
      return
    }

    try {
      setLoadingTransforms(true)
      setTransformsError(null)
      const data = await transformsApi.list(mappingId)
      setTransforms(data)
    } catch (error) {
      console.error('Failed to load transforms:', error)
      setTransformsError(extractErrorMessage(error, 'Failed to load transforms'))
    } finally {
      setLoadingTransforms(false)
    }
  }, [isOpen, mappingId])

  const loadAvailableTransforms = useCallback(async () => {
    if (!isOpen) {
      return
    }

    try {
      setAvailableError(null)
      const data = await transformsApi.available()
      setAvailableTransforms(data)
    } catch (error) {
      console.error('Failed to load available transforms:', error)
      setAvailableError(extractErrorMessage(error, 'Failed to load transform catalog'))
    }
  }, [isOpen])

  useEffect(() => {
    if (isOpen) {
      loadTransforms()
      loadAvailableTransforms()
    } else {
      resetForm()
      setTransforms([])
      setTransformsError(null)
      setAvailableError(null)
    }
  }, [isOpen, loadTransforms, loadAvailableTransforms, resetForm])

  const refreshChain = useCallback(async () => {
    await loadTransforms()
    onUpdate()
  }, [loadTransforms, onUpdate])

  const prepareParams = (): { payload: Record<string, unknown> | null; error?: string } => {
    if (!selectedTransformMeta || !selectedTransformMeta.params.length) {
      return {
        payload: Object.keys(params).length ? params : null,
      }
    }

    const prepared: Record<string, unknown> = {}

    for (const param of selectedTransformMeta.params) {
      const rawValue = params[param.name]
      const hasValue = rawValue !== undefined && rawValue !== ''

      if (!hasValue) {
        if (param.required) {
          return { payload: null, error: `Parameter "${param.name}" is required.` }
        }
        continue
      }

      if (param.type === 'integer') {
        const parsed = Number(rawValue)
        if (!Number.isFinite(parsed)) {
          return { payload: null, error: `Parameter "${param.name}" must be a number.` }
        }
        prepared[param.name] = parsed
      } else {
        prepared[param.name] = rawValue
      }
    }

    return {
      payload: Object.keys(prepared).length ? prepared : null,
    }
  }

  const addTransform = async () => {
    if (!selectedFn) {
      setFormError('Select a transform to add.')
      return
    }

    const { payload, error } = prepareParams()
    if (error) {
      setFormError(error)
      return
    }

    try {
      setSaving(true)
      setFormError(null)
      await transformsApi.create(mappingId, {
        fn: selectedFn,
        params: payload,
      })
      await refreshChain()
      resetForm()
    } catch (error) {
      console.error('Failed to add transform:', error)
      setFormError(extractErrorMessage(error, 'Failed to add transform'))
    } finally {
      setSaving(false)
    }
  }

  const deleteTransform = async (transformId: number) => {
    try {
      setSaving(true)
      await transformsApi.remove(transformId)
      await refreshChain()
    } catch (error) {
      console.error('Failed to delete transform:', error)
      setTransformsError(extractErrorMessage(error, 'Failed to delete transform'))
    } finally {
      setSaving(false)
    }
  }

  const moveTransform = async (transformId: number, direction: 'up' | 'down') => {
    const currentIndex = transforms.findIndex(t => t.id === transformId)
    const newOrder = direction === 'up' ? currentIndex - 1 : currentIndex + 1

    if (newOrder < 0 || newOrder >= transforms.length) return

    try {
      setSaving(true)
      await transformsApi.reorder(transformId, newOrder)
      await refreshChain()
    } catch (error) {
      console.error('Failed to reorder transform:', error)
      setTransformsError(extractErrorMessage(error, 'Failed to reorder transform'))
    } finally {
      setSaving(false)
    }
  }

  const testTransform = async () => {
    if (!selectedFn) {
      setTestError('Select a transform to test.')
      return
    }

    const { payload, error } = prepareParams()
    if (error) {
      setTestError(error)
      return
    }

    try {
      setTestLoading(true)
      setTestError(null)
      const data = await transformsApi.test({
        fn: selectedFn,
        params: payload,
        sample_value: testValue,
      })
      setTestResult(data.output)
    } catch (error) {
      console.error('Failed to test transform:', error)
      setTestError(extractErrorMessage(error, 'Transform test failed'))
      setTestResult(null)
    } finally {
      setTestLoading(false)
    }
  }

  const handleParamChange = (paramName: string, value: unknown) => {
    setParams(prev => ({ ...prev, [paramName]: value }))
    setFormError(null)
    setTestError(null)
  }

  const handleSelectTransform = (fn: string) => {
    setSelectedFn(fn)
    setFormError(null)
    setTestError(null)
    setTestResult(null)

    if (!fn) {
      setParams({})
      return
    }

    const meta = availableTransforms[fn]
    if (!meta) {
      setParams({})
      return
    }

    if (!meta.params || meta.params.length === 0) {
      setParams({})
      return
    }

    const initialParams: Record<string, unknown> = {}
    meta.params.forEach((param) => {
      if (param.default !== undefined && param.default !== null) {
        initialParams[param.name] = param.type === 'integer'
          ? String(param.default)
          : param.default
      } else {
        initialParams[param.name] = ''
      }
    })

    setParams(initialParams)
  }

  if (!isOpen) return null

  const hasTransformCatalog = Object.keys(availableTransforms).length > 0

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold">Data Transforms</h2>
            <button onClick={() => { resetForm(); onClose() }} className="text-gray-500 hover:text-gray-700">✕</button>
          </div>

          <p className="text-sm text-gray-600 mb-4">
            Apply data cleaning and transformation functions to this column. Transforms execute in order from top to bottom.
          </p>

          {/* Existing transforms */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Transform Chain</h3>
            {transformsError && (
              <div className="mb-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3 border border-red-200 bg-red-50 text-red-700 rounded px-3 py-2 text-sm">
                <span>{transformsError}</span>
                <button
                  onClick={loadTransforms}
                  className="px-3 py-1 text-sm border border-red-300 rounded hover:bg-red-100"
                >
                  Retry
                </button>
              </div>
            )}
            {loadingTransforms && (
              <div className="bg-gray-50 rounded p-4 text-center text-gray-500 text-sm">
                Loading transforms...
              </div>
            )}
            {transforms.length === 0 ? (
              !loadingTransforms && !transformsError && (
                <div className="bg-gray-50 rounded p-4 text-center text-gray-500 text-sm">
                  No transforms applied yet
                </div>
              )
            ) : (
              <div className="space-y-2">
                {transforms.map((transform, idx) => (
                  <div key={transform.id} className="flex items-center gap-2 bg-gray-50 rounded p-3">
                    <div className="flex flex-col gap-1">
                      <button
                        onClick={() => moveTransform(transform.id, 'up')}
                        disabled={idx === 0 || saving}
                        className="text-xs text-gray-500 hover:text-gray-700 disabled:text-gray-300 disabled:cursor-not-allowed"
                      >
                        ▲
                      </button>
                      <button
                        onClick={() => moveTransform(transform.id, 'down')}
                        disabled={idx === transforms.length - 1 || saving}
                        className="text-xs text-gray-500 hover:text-gray-700 disabled:text-gray-300 disabled:cursor-not-allowed"
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
                      disabled={saving}
                      className="px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm disabled:opacity-60 disabled:cursor-not-allowed"
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
                  onChange={(e) => handleSelectTransform(e.target.value)}
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
                {availableError && (
                  <p className="text-xs text-red-600 mt-2">{availableError}</p>
                )}
                {!hasTransformCatalog && !availableError && (
                  <p className="text-xs text-gray-500 mt-2">
                    No transforms are available yet. Check with the backend service.
                  </p>
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
                    value={String(params[param.name] ?? '')}
                    onChange={(e) => handleParamChange(param.name, e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2"
                    
                  />
                  {param.description && (
                    <p className="text-xs text-gray-500 mt-1">{param.description}</p>
                  )}
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
                      disabled={testLoading}
                      className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed"
                    >
                      {testLoading ? 'Testing...' : 'Test'}
                    </button>
                  </div>
                  {testResult !== null && (
                    <div className="mt-2 text-sm">
                      <span className="text-blue-700">Result: </span>
                      <span className="font-mono bg-white px-2 py-1 rounded">{String(testResult)}</span>
                    </div>
                  )}
                  {testError && (
                    <p className="mt-2 text-sm text-red-600">{testError}</p>
                  )}
                </div>
              )}

              {formError && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                  {formError}
                </div>
              )}

              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => {
                    resetForm()
                  }}
                  className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={addTransform}
                  disabled={!selectedFn || saving}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {saving ? 'Saving...' : 'Add'}
                </button>
              </div>
            </div>
          )}

          <div className="mt-6 flex justify-end">
            <button
              onClick={() => {
                resetForm()
                onClose()
              }}
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

const extractErrorMessage = (error: unknown, fallback: string) => {
  if (typeof error === 'object' && error && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response
    if (response?.data?.detail) {
      return response.data.detail
    }
  }

  if (error instanceof Error) {
    return error.message
  }

  return fallback
}
