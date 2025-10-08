import { useParams, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { datasetsApi } from '@/services/api'
import { Mapping, Dataset, CustomFieldDefinition } from '@/types/mapping'
import CustomFieldModal from '@/components/CustomFieldModal'
import TransformModal from '@/components/TransformModal'
import OdooConnectionModal from '@/components/OdooConnectionModal'

export default function Mappings() {
  const { id } = useParams()
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [mappings, setMappings] = useState<Mapping[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [expandedMapping, setExpandedMapping] = useState<number | null>(null)
  const [customFieldModal, setCustomFieldModal] = useState<{ mapping: Mapping; profileId?: number } | null>(null)
  const [transformModal, setTransformModal] = useState<number | null>(null)
  const [generatingAddon, setGeneratingAddon] = useState(false)
  const [showInstructions, setShowInstructions] = useState(false)
  const [instructions, setInstructions] = useState('')
  const [odooConnections, setOdooConnections] = useState<any[]>([])
  const [odooConnectionModal, setOdooConnectionModal] = useState(false)
  const [creatingFields, setCreatingFields] = useState(false)
  const [fieldCreationResult, setFieldCreationResult] = useState<any>(null)

  useEffect(() => {
    loadData()
    loadOdooConnections()
  }, [id])

  const loadData = async () => {
    try {
      const datasetData = await datasetsApi.get(Number(id))
      setDataset(datasetData)

      // Try to load existing mappings
      const response = await fetch(`/api/v1/datasets/${id}/mappings`)
      const data = await response.json()
      setMappings(data.mappings || [])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const generateMappings = async () => {
    setGenerating(true)
    try {
      const response = await fetch(`/api/v1/datasets/${id}/mappings/generate`, {
        method: 'POST'
      })
      const data = await response.json()
      setMappings(data.mappings || [])
    } catch (error) {
      console.error('Failed to generate mappings:', error)
    } finally {
      setGenerating(false)
    }
  }

  const updateMapping = async (mappingId: number, update: {
    target_model?: string
    target_field?: string
    status?: string
    chosen?: boolean
  }) => {
    try {
      const response = await fetch(`/api/v1/mappings/${mappingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(update)
      })
      const updated = await response.json()

      // Update local state
      setMappings(prev => prev.map(m => m.id === mappingId ? updated : m))
    } catch (error) {
      console.error('Failed to update mapping:', error)
    }
  }

  const selectCandidate = (mappingId: number, candidate: Candidate) => {
    updateMapping(mappingId, {
      target_model: candidate.model,
      target_field: candidate.field,
      status: 'confirmed',
      chosen: true
    })
  }

  const ignoreMapping = (mappingId: number) => {
    updateMapping(mappingId, {
      status: 'ignored',
      chosen: false
    })
  }

  const createCustomField = async (mappingId: number, customFieldDef: CustomFieldDefinition) => {
    try {
      const response = await fetch(`/api/v1/mappings/${mappingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: 'create_field',
          custom_field_definition: customFieldDef
        })
      })
      const updated = await response.json()

      // Update local state
      setMappings(prev => prev.map(m => m.id === mappingId ? updated : m))
    } catch (error) {
      console.error('Failed to create custom field:', error)
    }
  }

  const generateAddon = async () => {
    setGeneratingAddon(true)
    try {
      const response = await fetch(`/api/v1/datasets/${id}/addon/generate`, {
        method: 'POST'
      })

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'custom_fields_migration.zip'
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)

        // Fetch installation instructions
        await fetchInstructions()
      }
    } catch (error) {
      console.error('Failed to generate addon:', error)
    } finally {
      setGeneratingAddon(false)
    }
  }

  const fetchInstructions = async () => {
    try {
      const response = await fetch(`/api/v1/datasets/${id}/addon/instructions`)
      const data = await response.json()
      setInstructions(data.instructions)
      setShowInstructions(true)
    } catch (error) {
      console.error('Failed to fetch instructions:', error)
    }
  }

  const acceptAllHighConfidence = async () => {
    const highConfMappings = mappings.filter(m =>
      m.status === 'pending' && m.confidence !== null && m.confidence >= 0.9
    )

    for (const mapping of highConfMappings) {
      await updateMapping(mapping.id, { status: 'confirmed', chosen: true })
    }
  }

  const resetAllToPending = async () => {
    const nonPendingMappings = mappings.filter(m => m.status !== 'pending')

    for (const mapping of nonPendingMappings) {
      await updateMapping(mapping.id, { status: 'pending' })
    }
  }

  const exportMappings = () => {
    const exportData = mappings.map(m => ({
      header_name: m.header_name,
      target_model: m.target_model,
      target_field: m.target_field,
      status: m.status,
      custom_field_definition: m.custom_field_definition
    }))

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `mappings_${dataset?.name || 'export'}.json`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  const loadOdooConnections = async () => {
    try {
      const response = await fetch('/api/v1/odoo/connections')
      const data = await response.json()
      setOdooConnections(data)
    } catch (error) {
      console.error('Failed to load Odoo connections:', error)
    }
  }

  const hasDefaultConnection = () => {
    return odooConnections.some(conn => conn.is_default)
  }

  const createFieldsInOdoo = async () => {
    setCreatingFields(true)
    setFieldCreationResult(null)

    try {
      const response = await fetch(`/api/v1/datasets/${id}/create-custom-fields`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      const result = await response.json()
      setFieldCreationResult(result)

      if (result.success) {
        // Reload mappings to update statuses
        await loadData()
      }
    } catch (error) {
      setFieldCreationResult({
        success: false,
        message: `Failed to create fields: ${error}`,
        created: 0,
        failed: 0,
        total: 0,
        results: []
      })
    } finally {
      setCreatingFields(false)
    }
  }

  const getConfidenceColor = (confidence: number | null) => {
    if (!confidence) return 'bg-gray-100 text-gray-800'
    if (confidence >= 0.9) return 'bg-green-100 text-green-800'
    if (confidence >= 0.75) return 'bg-yellow-100 text-yellow-800'
    return 'bg-red-100 text-red-800'
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      pending: 'bg-gray-100 text-gray-800',
      confirmed: 'bg-green-100 text-green-800',
      ignored: 'bg-red-100 text-red-800',
      create_field: 'bg-blue-100 text-blue-800'
    }
    return colors[status as keyof typeof colors] || colors.pending
  }

  if (loading) {
    return <div className="p-6">Loading...</div>
  }

  if (!dataset) {
    return <div className="p-6">Dataset not found</div>
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link to="/" className="text-blue-600 hover:underline text-sm mb-2 block">
            ← Back to Datasets
          </Link>
          <h1 className="text-3xl font-bold">Configure Mappings: {dataset.name}</h1>
        </div>
        {mappings.length === 0 && (
          <button
            onClick={generateMappings}
            disabled={generating}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {generating ? 'Generating...' : 'Generate Mappings'}
          </button>
        )}
      </div>

      {mappings.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-600 mb-4">No mappings generated yet.</p>
          <button
            onClick={generateMappings}
            disabled={generating}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {generating ? 'Generating...' : 'Generate Mappings'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Stats Dashboard */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="text-2xl font-bold text-gray-900">{mappings.length}</div>
              <div className="text-xs text-gray-600">Total Mappings</div>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="text-2xl font-bold text-green-900">
                {mappings.filter(m => m.status === 'confirmed').length}
              </div>
              <div className="text-xs text-green-700">Confirmed</div>
            </div>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="text-2xl font-bold text-yellow-900">
                {mappings.filter(m => m.status === 'pending').length}
              </div>
              <div className="text-xs text-yellow-700">Pending</div>
            </div>
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <div className="text-2xl font-bold text-purple-900">
                {mappings.filter(m => m.status === 'create_field').length}
              </div>
              <div className="text-xs text-purple-700">Custom Fields</div>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <div className="text-2xl font-bold text-gray-900">
                {mappings.filter(m => m.status === 'ignored').length}
              </div>
              <div className="text-xs text-gray-600">Ignored</div>
            </div>
          </div>

          {/* Bulk Actions Toolbar */}
          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-700">Bulk Actions</h3>
              <div className="flex gap-2">
                <button
                  onClick={acceptAllHighConfidence}
                  disabled={mappings.filter(m => m.status === 'pending' && m.confidence !== null && m.confidence >= 0.9).length === 0}
                  className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  Accept All High Confidence ({mappings.filter(m => m.status === 'pending' && m.confidence !== null && m.confidence >= 0.9).length})
                </button>
                <button
                  onClick={resetAllToPending}
                  disabled={mappings.filter(m => m.status !== 'pending').length === 0}
                  className="bg-yellow-600 text-white px-3 py-1 rounded text-sm hover:bg-yellow-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  Reset All
                </button>
                <button
                  onClick={exportMappings}
                  className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                >
                  Export JSON
                </button>
              </div>
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <p className="text-sm text-blue-900">
              <strong>Review mappings:</strong> Each column has been mapped to an Odoo field.
              Confirm suggestions with high confidence (green), review medium confidence (yellow),
              and manually select for low confidence (red).
            </p>
          </div>

          {mappings.map((mapping) => (
            <div key={mapping.id} className="bg-white rounded-lg shadow border border-gray-200">
              <div className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {mapping.header_name}
                      </h3>
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadge(mapping.status)}`}>
                        {mapping.status}
                      </span>
                      {mapping.confidence !== null && (
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getConfidenceColor(mapping.confidence)}`}>
                          {Math.round(mapping.confidence * 100)}% confidence
                        </span>
                      )}
                    </div>

                    {mapping.target_model && mapping.target_field && (
                      <div className="mb-2">
                        <p className="text-sm text-gray-700">
                          <strong>Suggested:</strong> {mapping.target_model}.{mapping.target_field}
                        </p>
                        {mapping.rationale && (
                          <p className="text-xs text-gray-500 italic mt-1">{mapping.rationale}</p>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => setTransformModal(mapping.id)}
                      className="bg-orange-600 text-white px-4 py-1 rounded text-sm hover:bg-orange-700"
                    >
                      Transforms
                    </button>
                    {mapping.status === 'pending' && (
                      <>
                        {mapping.target_model && mapping.target_field && (
                          <button
                            onClick={() => updateMapping(mapping.id, { status: 'confirmed', chosen: true })}
                            className="bg-green-600 text-white px-4 py-1 rounded text-sm hover:bg-green-700"
                          >
                            Accept
                          </button>
                        )}
                        {mapping.suggestions.length > 0 && (
                          <button
                            onClick={() => setExpandedMapping(expandedMapping === mapping.id ? null : mapping.id)}
                            className="bg-blue-600 text-white px-4 py-1 rounded text-sm hover:bg-blue-700"
                          >
                            {expandedMapping === mapping.id ? 'Hide' : 'Alternatives'}
                          </button>
                        )}
                        <button
                          onClick={() => setCustomFieldModal({ mapping })}
                          className="bg-purple-600 text-white px-4 py-1 rounded text-sm hover:bg-purple-700"
                        >
                          Custom Field
                        </button>
                        <button
                          onClick={() => ignoreMapping(mapping.id)}
                          className="bg-gray-600 text-white px-4 py-1 rounded text-sm hover:bg-gray-700"
                        >
                          Ignore
                        </button>
                      </>
                    )}
                    {mapping.status === 'confirmed' && (
                      <button
                        onClick={() => updateMapping(mapping.id, { status: 'pending' })}
                        className="bg-gray-600 text-white px-4 py-1 rounded text-sm hover:bg-gray-700"
                      >
                        Change
                      </button>
                    )}
                    {mapping.status === 'ignored' && (
                      <button
                        onClick={() => updateMapping(mapping.id, { status: 'pending' })}
                        className="bg-gray-600 text-white px-4 py-1 rounded text-sm hover:bg-gray-700"
                      >
                        Reconsider
                      </button>
                    )}
                  </div>
                </div>

                {/* Show alternatives */}
                {expandedMapping === mapping.id && mapping.suggestions.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <h4 className="text-sm font-semibold text-gray-700 mb-3">Alternative Suggestions:</h4>
                    <div className="space-y-2">
                      {mapping.suggestions[0].candidates.map((candidate, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded hover:bg-gray-100 cursor-pointer"
                          onClick={() => selectCandidate(mapping.id, candidate)}
                        >
                          <div className="flex-1">
                            <p className="text-sm font-medium text-gray-900">
                              {candidate.model}.{candidate.field}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                              {candidate.rationale}
                            </p>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getConfidenceColor(candidate.confidence)}`}>
                              {Math.round(candidate.confidence * 100)}%
                            </span>
                            <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full">
                              {candidate.method}
                            </span>
                            <button
                              className="bg-blue-600 text-white px-3 py-1 rounded text-xs hover:bg-blue-700"
                              onClick={(e) => {
                                e.stopPropagation()
                                selectCandidate(mapping.id, candidate)
                              }}
                            >
                              Select
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Custom Fields Odoo Panel */}
          {mappings.filter(m => m.status === 'create_field').length > 0 && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-6 mt-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold text-purple-900">
                  Create Custom Fields in Odoo
                </h3>
                {hasDefaultConnection() ? (
                  <div className="flex items-center gap-2">
                    <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                      ✓ Odoo Connected
                    </span>
                    <button
                      onClick={() => setOdooConnectionModal(true)}
                      className="text-xs text-purple-700 hover:underline"
                    >
                      Change Connection
                    </button>
                  </div>
                ) : (
                  <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded-full">
                    ✗ No Connection
                  </span>
                )}
              </div>

              <p className="text-sm text-purple-700 mb-4">
                {mappings.filter(m => m.status === 'create_field').length} custom field(s) ready to be created.
                These fields will be created directly in your Odoo instance via XML-RPC.
              </p>

              <div className="bg-white rounded p-3 mb-4">
                <h4 className="text-xs font-semibold text-gray-700 mb-2">Custom Fields:</h4>
                <ul className="space-y-1">
                  {mappings.filter(m => m.status === 'create_field').map(mapping => (
                    <li key={mapping.id} className="text-sm text-gray-600">
                      • {mapping.custom_field_definition?.field_label || mapping.header_name}
                      <span className="text-xs text-gray-500 ml-2">
                        ({mapping.custom_field_definition?.field_type || 'Char'})
                      </span>
                      {mapping.custom_field_definition?.target_model && (
                        <span className="text-xs text-purple-600 ml-2">
                          on {mapping.custom_field_definition.target_model}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="flex gap-3">
                {hasDefaultConnection() ? (
                  <button
                    onClick={createFieldsInOdoo}
                    disabled={creatingFields}
                    className="bg-purple-600 text-white px-6 py-2 rounded hover:bg-purple-700 disabled:bg-gray-400"
                  >
                    {creatingFields ? 'Creating Fields...' : 'Create Fields in Odoo'}
                  </button>
                ) : (
                  <button
                    onClick={() => setOdooConnectionModal(true)}
                    className="bg-purple-600 text-white px-6 py-2 rounded hover:bg-purple-700"
                  >
                    Configure Odoo Connection
                  </button>
                )}
              </div>

              {/* Success/Error Messages */}
              {fieldCreationResult && (
                <div className={`mt-4 p-4 rounded border ${
                  fieldCreationResult.success
                    ? 'bg-green-50 border-green-200'
                    : 'bg-red-50 border-red-200'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className={`text-sm font-semibold ${
                      fieldCreationResult.success ? 'text-green-900' : 'text-red-900'
                    }`}>
                      {fieldCreationResult.success ? '✅ Fields Created Successfully' : '❌ Field Creation Failed'}
                    </h4>
                    <button
                      onClick={() => setFieldCreationResult(null)}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      ✕
                    </button>
                  </div>
                  <p className={`text-xs ${
                    fieldCreationResult.success ? 'text-green-700' : 'text-red-700'
                  }`}>
                    Created: {fieldCreationResult.created} | Failed: {fieldCreationResult.failed} | Total: {fieldCreationResult.total}
                  </p>

                  {fieldCreationResult.results && fieldCreationResult.results.length > 0 && (
                    <div className="mt-3 space-y-1">
                      {fieldCreationResult.results.map((result: any, idx: number) => (
                        <div key={idx} className="text-xs">
                          {result.status === 'created' ? (
                            <span className="text-green-700">
                              ✓ {result.field_label || result.field_name} (ID: {result.field_id})
                            </span>
                          ) : (
                            <span className="text-red-700">
                              ✗ {result.field_label || result.field_name}: {result.message}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="mt-6 flex justify-end gap-3">
            <button
              onClick={() => window.location.href = '/'}
              className="bg-gray-600 text-white px-6 py-2 rounded hover:bg-gray-700"
            >
              Save & Exit
            </button>
            <button
              onClick={generateMappings}
              className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
            >
              Regenerate
            </button>
          </div>
        </div>
      )}

      {/* Custom Field Modal */}
      {customFieldModal && (
        <CustomFieldModal
          mapping={customFieldModal.mapping}
          columnProfileId={customFieldModal.profileId}
          isOpen={!!customFieldModal}
          onClose={() => setCustomFieldModal(null)}
          onSave={(customFieldDef) => {
            createCustomField(customFieldModal.mapping.id, customFieldDef)
            setCustomFieldModal(null)
          }}
        />
      )}

      {/* Transform Modal */}
      {transformModal !== null && (
        <TransformModal
          mappingId={transformModal}
          isOpen={transformModal !== null}
          onClose={() => setTransformModal(null)}
          onUpdate={loadData}
        />
      )}

      {/* Odoo Connection Modal */}
      <OdooConnectionModal
        isOpen={odooConnectionModal}
        onClose={() => setOdooConnectionModal(false)}
        onSaved={() => {
          setOdooConnectionModal(false)
          loadOdooConnections()
        }}
      />
    </div>
  )
}
