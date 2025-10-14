import { useState, useEffect, useCallback, useMemo } from 'react'
import { Mapping, FieldTypeSuggestion, SelectionOption, CustomFieldDefinition } from '@/types/mapping'

interface Props {
  mapping: Mapping
  columnProfileId?: number
  isOpen: boolean
  onClose: () => void
  onSave: (customFieldDef: CustomFieldDefinition) => void
}

const FIELD_TYPES = [
  'Char', 'Integer', 'Float', 'Boolean', 'Date', 'Datetime',
  'Text', 'Html', 'Selection', 'Many2one', 'Monetary'
]

const BASE_COMMON_MODELS = [
  'res.partner', 'res.users', 'product.product', 'product.template',
  'sale.order', 'purchase.order', 'account.move', 'project.project'
]

export default function CustomFieldModal({ mapping, columnProfileId, isOpen, onClose, onSave }: Props) {
  const [suggestion, setSuggestion] = useState<FieldTypeSuggestion | null>(null)
  const [suggestionLoading, setSuggestionLoading] = useState(false)
  const [suggestionError, setSuggestionError] = useState<string | null>(null)

  const [technicalName, setTechnicalName] = useState('')
  const [fieldLabel, setFieldLabel] = useState('')
  const [fieldType, setFieldType] = useState('Char')
  const [required, setRequired] = useState(false)
  const [size, setSize] = useState<number>(255)
  const [helpText, setHelpText] = useState('')
  const [selectionOptions, setSelectionOptions] = useState<SelectionOption[]>([])
  const [relatedModel, setRelatedModel] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)

  const availableModels = useMemo(() => {
    const models = new Set<string>(BASE_COMMON_MODELS)
    if (mapping.target_model) {
      models.add(mapping.target_model)
    }
    return Array.from(models).sort()
  }, [mapping.target_model])

  const resetForm = useCallback(() => {
    const autoTechName = generateDefaultTechnicalName(mapping.header_name)
    setTechnicalName(autoTechName)
    setFieldLabel(mapping.header_name)
    setFieldType('Char')
    setRequired(false)
    setSize(255)
    setHelpText('')
    setSelectionOptions([])
    setRelatedModel(mapping.target_model || '')
    setValidationError(null)
    setSuggestion(null)
    setSuggestionError(null)
  }, [mapping.header_name, mapping.target_model])

  const applySuggestion = useCallback((data: FieldTypeSuggestion) => {
    setFieldType(data.field_type || 'Char')
    setRequired(Boolean(data.required))
    if (data.field_type === 'Char' && data.suggested_size) {
      setSize(data.suggested_size)
    }
    if (data.field_type === 'Selection' && data.selection_options) {
      setSelectionOptions(
        data.selection_options.map(opt => ({
          value: opt.value,
          label: opt.label,
        }))
      )
    }
  }, [])

  const fetchSuggestion = useCallback(async () => {
    if (!columnProfileId) {
      return
    }

    try {
      setSuggestionLoading(true)
      setSuggestionError(null)
      const response = await fetch(
        `/api/v1/mappings/${mapping.id}/suggest-field-type?column_profile_id=${columnProfileId}`
      )
      if (!response.ok) {
        const detail = await safeExtractDetail(response)
        throw new Error(detail || 'Failed to fetch field type suggestion')
      }
      const data: FieldTypeSuggestion = await response.json()
      setSuggestion(data)
      applySuggestion(data)
    } catch (error) {
      console.error('Failed to fetch suggestion:', error)
      setSuggestionError(extractErrorMessage(error, 'Unable to load field type suggestion'))
    } finally {
      setSuggestionLoading(false)
    }
  }, [applySuggestion, columnProfileId, mapping.id])

  useEffect(() => {
    if (isOpen) {
      resetForm()
      if (columnProfileId) {
        fetchSuggestion()
      }
    }
  }, [isOpen, resetForm, fetchSuggestion, columnProfileId])

  useEffect(() => {
    if (isOpen && fieldType === 'Selection' && selectionOptions.length === 0) {
      setSelectionOptions([{ value: '', label: '' }])
    }
  }, [fieldType, isOpen, selectionOptions.length])

  const handleSave = () => {
    setValidationError(null)

    const sanitizedName = ensureTechnicalName(technicalName)
    if (!sanitizedName) {
      setValidationError('Technical name is required (must begin with x_).')
      return
    }

    const trimmedLabel = fieldLabel.trim()
    if (!trimmedLabel) {
      setValidationError('Field label is required.')
      return
    }

    if (fieldType === 'Char') {
      if (!Number.isFinite(size) || size <= 0) {
        setValidationError('Max size must be a positive number.')
        return
      }
    }

    let cleanedSelectionOptions: SelectionOption[] | undefined
    if (fieldType === 'Selection') {
      cleanedSelectionOptions = selectionOptions
        .map(opt => ({
          value: opt.value.trim(),
          label: opt.label.trim(),
        }))
        .filter(opt => opt.value && opt.label)

      if (!cleanedSelectionOptions.length) {
        setValidationError('Add at least one selection option with both value and label.')
        return
      }
    }

    if (fieldType === 'Many2one' && !relatedModel) {
      setValidationError('Select a related model for Many2one fields.')
      return
    }

    const customFieldDef: CustomFieldDefinition = {
      technical_name: sanitizedName,
      field_label: trimmedLabel,
      field_type: fieldType,
      required,
      help_text: helpText.trim() || undefined,
    }

    if (fieldType === 'Char') {
      customFieldDef.size = size
    }

    if (cleanedSelectionOptions && cleanedSelectionOptions.length > 0) {
      customFieldDef.selection_options = cleanedSelectionOptions
    }

    if (fieldType === 'Many2one') {
      customFieldDef.related_model = relatedModel
    }

    onSave(customFieldDef)
    onClose()
  }

  const addSelectionOption = () => {
    setSelectionOptions(prev => [...prev, { value: '', label: '' }])
  }

  const updateSelectionOption = (index: number, field: 'value' | 'label', value: string) => {
    setSelectionOptions(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], [field]: value }
      return updated
    })
    setValidationError(null)
  }

  const removeSelectionOption = (index: number) => {
    setSelectionOptions(prev => prev.filter((_, i) => i !== index))
  }

  const handleFieldTypeChange = (value: string) => {
    setFieldType(value)
    setValidationError(null)

    if (value !== 'Selection') {
      setSelectionOptions([])
    }

    if (value !== 'Many2one') {
      setRelatedModel('')
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold">Create Custom Field</h2>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
          </div>

          <div className="mb-4 bg-gray-50 p-3 rounded">
            <p className="text-sm text-gray-600">
              <strong>Column:</strong> {mapping.header_name}
            </p>
            {suggestionLoading && (
              <p className="text-sm text-gray-500 mt-1">Analyzing column profile...</p>
            )}
            {suggestion && (
              <p className="text-sm text-green-600 mt-1">
                <strong>💡 Suggestion:</strong> {suggestion.rationale}
              </p>
            )}
            {suggestionError && (
              <div className="mt-2 flex flex-col md:flex-row md:items-center md:justify-between gap-3 border border-yellow-300 bg-yellow-50 text-yellow-800 rounded px-3 py-2 text-sm">
                <span>{suggestionError}</span>
                <button
                  onClick={fetchSuggestion}
                  className="px-3 py-1 text-sm border border-yellow-400 rounded hover:bg-yellow-100"
                >
                  Retry
                </button>
              </div>
            )}
          </div>

          {validationError && (
            <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
              {validationError}
            </div>
          )}

          <div className="space-y-4">
            {/* Technical Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Technical Name *
              </label>
              <input
                type="text"
                value={technicalName}
                onChange={(e) => {
                  setTechnicalName(e.target.value)
                  setValidationError(null)
                }}
                className="w-full border border-gray-300 rounded px-3 py-2"
                placeholder="x_bt_field_name"
              />
              <p className="text-xs text-gray-500 mt-1">Must start with x_ (Odoo custom field convention)</p>
            </div>

            {/* Field Label */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Field Label *
              </label>
              <input
                type="text"
                value={fieldLabel}
                onChange={(e) => {
                  setFieldLabel(e.target.value)
                  setValidationError(null)
                }}
                className="w-full border border-gray-300 rounded px-3 py-2"
                placeholder="Field Label"
              />
            </div>

            {/* Field Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Field Type *
              </label>
              <select
                value={fieldType}
                onChange={(e) => handleFieldTypeChange(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2"
              >
                {FIELD_TYPES.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>

            {/* Char Size */}
            {fieldType === 'Char' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Size
                </label>
                <input
                  type="number"
                  value={size}
                  min={1}
                  max={500}
                  onChange={(e) => {
                    const value = Number(e.target.value)
                    setSize(value)
                    setValidationError(null)
                  }}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>
            )}

            {/* Selection Options */}
            {fieldType === 'Selection' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Selection Options
                </label>
                <div className="space-y-2">
                  {selectionOptions.map((opt, idx) => (
                    <div key={idx} className="flex gap-2">
                      <input
                        type="text"
                        value={opt.value}
                        onChange={(e) => updateSelectionOption(idx, 'value', e.target.value)}
                        placeholder="Value"
                        className="flex-1 border border-gray-300 rounded px-3 py-2"
                      />
                      <input
                        type="text"
                        value={opt.label}
                        onChange={(e) => updateSelectionOption(idx, 'label', e.target.value)}
                        placeholder="Label"
                        className="flex-1 border border-gray-300 rounded px-3 py-2"
                      />
                      <button
                        onClick={() => removeSelectionOption(idx)}
                        className="px-3 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={addSelectionOption}
                    className="w-full px-3 py-2 border border-dashed border-gray-400 rounded text-gray-600 hover:bg-gray-50"
                  >
                    + Add Option
                  </button>
                </div>
              </div>
            )}

            {/* Many2one Model */}
            {fieldType === 'Many2one' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Related Model *
                </label>
                <select
                  value={relatedModel}
                  onChange={(e) => {
                    setRelatedModel(e.target.value)
                    setValidationError(null)
                  }}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                >
                  <option value="">Select model...</option>
                  {availableModels.map(model => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Required */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="required"
                checked={required}
                onChange={(e) => setRequired(e.target.checked)}
                className="mr-2"
              />
              <label htmlFor="required" className="text-sm font-medium text-gray-700">
                Required Field
              </label>
            </div>

            {/* Help Text */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Help Text (Optional)
              </label>
              <textarea
                value={helpText}
                onChange={(e) => setHelpText(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2"
                rows={3}
                placeholder="Description shown to users"
              />
            </div>
          </div>

          <div className="mt-6 flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!technicalName || !fieldLabel}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
            >
              Create Field
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

const generateDefaultTechnicalName = (header: string) => {
  const base = header.toLowerCase().replace(/[^\w]+/g, '_')
  return ensureTechnicalName(`x_bt_${base}`)
}

const ensureTechnicalName = (value: string) => {
  const cleaned = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '')

  if (!cleaned) {
    return ''
  }

  let withPrefix = cleaned.startsWith('x_') ? cleaned : `x_${cleaned}`
  if (!withPrefix.startsWith('x_')) {
    withPrefix = `x_${withPrefix}`
  }
  return withPrefix.slice(0, 64)
}

const extractErrorMessage = (error: unknown, fallback: string) => {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

const safeExtractDetail = async (response: Response) => {
  try {
    const data = await response.json()
    if (data?.detail && typeof data.detail === 'string') {
      return data.detail
    }
  } catch (_error) {
    // ignore - we only care about graceful fallback
  }
  return null
}
