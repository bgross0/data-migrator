import { useState, useEffect } from 'react'
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

const COMMON_MODELS = [
  'res.partner', 'res.users', 'product.product', 'product.template',
  'sale.order', 'purchase.order', 'account.move', 'project.project'
]

export default function CustomFieldModal({ mapping, columnProfileId, isOpen, onClose, onSave }: Props) {
  const [suggestion, setSuggestion] = useState<FieldTypeSuggestion | null>(null)
  const [loading, setLoading] = useState(false)

  const [technicalName, setTechnicalName] = useState('')
  const [fieldLabel, setFieldLabel] = useState('')
  const [fieldType, setFieldType] = useState('Char')
  const [required, setRequired] = useState(false)
  const [size, setSize] = useState(255)
  const [helpText, setHelpText] = useState('')
  const [selectionOptions, setSelectionOptions] = useState<SelectionOption[]>([])
  const [relatedModel, setRelatedModel] = useState('')

  useEffect(() => {
    if (isOpen) {
      // Auto-generate technical name from header
      const autoTechName = `x_bt_${mapping.header_name.toLowerCase().replace(/[^\w]+/g, '_')}`
      setTechnicalName(autoTechName)
      setFieldLabel(mapping.header_name)

      // Fetch suggestion if profile ID provided
      if (columnProfileId) {
        fetchSuggestion()
      }
    }
  }, [isOpen, mapping, columnProfileId])

  const fetchSuggestion = async () => {
    if (!columnProfileId) return

    setLoading(true)
    try {
      const response = await fetch(
        `/api/v1/mappings/${mapping.id}/suggest-field-type?column_profile_id=${columnProfileId}`
      )
      const data: FieldTypeSuggestion = await response.json()
      setSuggestion(data)

      // Apply suggestion
      setFieldType(data.field_type)
      setRequired(data.required)
      if (data.suggested_size) setSize(data.suggested_size)
      if (data.selection_options) {
        setSelectionOptions(data.selection_options.map(opt => ({
          value: opt.value,
          label: opt.label
        })))
      }
    } catch (error) {
      console.error('Failed to fetch suggestion:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = () => {
    const customFieldDef: CustomFieldDefinition = {
      technical_name: technicalName,
      field_label: fieldLabel,
      field_type: fieldType,
      required,
      help_text: helpText || undefined,
    }

    if (fieldType === 'Char') {
      customFieldDef.size = size
    }

    if (fieldType === 'Selection') {
      customFieldDef.selection_options = selectionOptions
    }

    if (fieldType === 'Many2one') {
      customFieldDef.related_model = relatedModel
    }

    onSave(customFieldDef)
    onClose()
  }

  const addSelectionOption = () => {
    setSelectionOptions([...selectionOptions, { value: '', label: '' }])
  }

  const updateSelectionOption = (index: number, field: 'value' | 'label', value: string) => {
    const updated = [...selectionOptions]
    updated[index][field] = value
    setSelectionOptions(updated)
  }

  const removeSelectionOption = (index: number) => {
    setSelectionOptions(selectionOptions.filter((_, i) => i !== index))
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
            {suggestion && (
              <p className="text-sm text-green-600 mt-1">
                <strong>💡 Suggestion:</strong> {suggestion.rationale}
              </p>
            )}
          </div>

          <div className="space-y-4">
            {/* Technical Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Technical Name *
              </label>
              <input
                type="text"
                value={technicalName}
                onChange={(e) => setTechnicalName(e.target.value)}
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
                onChange={(e) => setFieldLabel(e.target.value)}
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
                onChange={(e) => setFieldType(e.target.value)}
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
                  onChange={(e) => setSize(Number(e.target.value))}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  min="1"
                  max="500"
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
                  onChange={(e) => setRelatedModel(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                >
                  <option value="">Select model...</option>
                  {COMMON_MODELS.map(model => (
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
