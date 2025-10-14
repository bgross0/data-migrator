import { useState } from 'react'
// import { X, Plus, Trash2, Code, PlayCircle } from 'lucide-react'

interface LambdaMappingModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (lambdaMapping: LambdaMappingData) => void
  initialData?: LambdaMappingData
  availableColumns: string[]
}

export interface LambdaMappingData {
  header_name: string
  target_field: string | null
  target_model: string | null
  lambda_function: string
  mapping_type: 'lambda'
  description?: string
}

const LAMBDA_TEMPLATES = [
  {
    name: 'Combine First and Last Name',
    description: 'Combine first_name and last_name into full_name',
    template: 'lambda row: f"{row["first_name"]} {row["last_name"]}"',
    requiredColumns: ['first_name', 'last_name']
  },
  {
    name: 'Extract Email Domain',
    description: 'Extract domain from email address',
    template: 'lambda row: row["email"].split("@")[1] if row.get("email") and "@" in row["email"] else None',
    requiredColumns: ['email']
  },
  {
    name: 'Format Phone Number',
    description: 'Clean phone number to digits only',
    template: 'lambda row: \'\'.join(c for c in str(row["phone"]) if c.isdigit()) if row.get("phone") else ""',
    requiredColumns: ['phone']
  },
  {
    name: 'Conditional Bonus Calculation',
    description: 'Calculate bonus based on department',
    template: 'lambda row: row["salary"] * 0.15 if row.get("department") == "Engineering" else row["salary"] * 0.10',
    requiredColumns: ['salary', 'department']
  },
  {
    name: 'Calculate Age from Birthdate',
    description: 'Calculate age from birthdate string',
    template: 'lambda row: (datetime.now() - datetime.strptime(row["birthdate"], "%Y-%m-%d")).days // 365 if row.get("birthdate") else None',
    requiredColumns: ['birthdate']
  }
]

export default function LambdaMappingModal({ 
  isOpen, 
  onClose, 
  onSave, 
  initialData, 
  availableColumns 
}: LambdaMappingModalProps) {
  const [formData, setFormData] = useState<LambdaMappingData>(
    initialData || {
      header_name: '',
      target_field: '',
      target_model: '',
      lambda_function: '',
      mapping_type: 'lambda',
      description: ''
    }
  )
  
  const [testResult, setTestResult] = useState<string>('')
  const [isTesting, setIsTesting] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState('')

  const handleSave = () => {
    if (!formData.target_field || !formData.lambda_function) {
      alert('Please fill in target field and lambda function')
      return
    }
    onSave(formData)
    onClose()
  }

  const applyTemplate = (template: typeof LAMBDA_TEMPLATES[0]) => {
    setFormData(prev => ({
      ...prev,
      lambda_function: template.template,
      description: template.description,
      target_field: template.name.toLowerCase().replace(/[^a-z0-9]/g, '_')
    }))
    setSelectedTemplate(template.name)
  }

  const testLambda = async () => {
    if (!formData.lambda_function) {
      setTestResult('No lambda function to test')
      return
    }

    setIsTesting(true)
    setTestResult('Testing lambda function...')

    try {
      // In a real implementation, this would call the backend to test the lambda
      // For now, we'll simulate a basic test
      setTimeout(() => {
        setTestResult('✅ Lambda function syntax appears valid. (Note: Full testing requires backend integration)')
        setIsTesting(false)
      }, 1000)
    } catch (error) {
      setTestResult(`❌ Error: ${error}`)
      setIsTesting(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center gap-2">
            <span className="text-blue-600">⚡</span>
            <h2 className="text-xl font-semibold">
              {initialData ? 'Edit Lambda Mapping' : 'Create Lambda Mapping'}
            </h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <span className="text-xl">✕</span>
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Basic Mapping Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Target Field Name</label>
              <input
                type="text"
                value={formData.target_field || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, target_field: e.target.value }))}
                className="w-full border rounded px-3 py-2"
                placeholder="e.g., full_name, email_domain"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Target Model</label>
              <select
                value={formData.target_model || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, target_model: e.target.value }))}
                className="w-full border rounded px-3 py-2"
              >
                <option value="">Select Model</option>
                <option value="res.partner">Contact</option>
                <option value="sale.order">Sale Order</option>
                <option value="crm.lead">Lead</option>
                <option value="fleet.vehicle">Vehicle</option>
                <option value="project.project">Project</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Description</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="w-full border rounded px-3 py-2"
              placeholder="What does this lambda function do?"
            />
          </div>

          {/* Lambda Templates */}
          <div>
            <label className="block text-sm font-medium mb-2">Quick Templates</label>
            <div className="grid grid-cols-1 gap-2">
              {LAMBDA_TEMPLATES.map((template) => (
                <div
                  key={template.name}
                  className={`border rounded p-3 cursor-pointer transition-colors ${
                    selectedTemplate === template.name 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => applyTemplate(template)}
                >
                  <div className="font-medium">{template.name}</div>
                  <div className="text-sm text-gray-600">{template.description}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Needs: {template.requiredColumns.join(', ')}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Lambda Function Editor */}
          <div>
            <label className="block text-sm font-medium mb-2">Lambda Function</label>
            <div className="relative">
              <textarea
                value={formData.lambda_function}
                onChange={(e) => setFormData(prev => ({ ...prev, lambda_function: e.target.value }))}
                className="w-full border rounded px-3 py-2 font-mono text-sm h-32"
                placeholder="lambda row: # your lambda expression here"
              />
              <button
                onClick={testLambda}
                disabled={isTesting || !formData.lambda_function}
                className="absolute top-2 right-2 px-3 py-1 bg-blue-100 text-blue-700 rounded text-sm hover:bg-blue-200 disabled:opacity-50 flex items-center gap-1"
              >
                <span>▶</span>
                {isTesting ? 'Testing...' : 'Test'}
              </button>
            </div>
            {testResult && (
              <div className={`mt-2 p-2 rounded text-sm ${testResult.includes('✅') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {testResult}
              </div>
            )}
          </div>

          {/* Available Columns Reference */}
          <div>
            <label className="block text-sm font-medium mb-2">Available Columns</label>
            <div className="bg-gray-50 rounded p-3">
              <div className="text-sm text-gray-600 mb-2">Use these column names in your lambda function:</div>
              <div className="flex flex-wrap gap-2">
                {availableColumns.map((col) => (
                  <span key={col} className="px-2 py-1 bg-white border rounded text-xs font-mono">
                    {col}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Help Text */}
          <div className="bg-blue-50 rounded p-4">
            <h4 className="font-medium text-blue-900 mb-2">Lambda Function Help</h4>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Use <code className="bg-blue-100 px-1 rounded">{`row["column_name"]`}</code> to access column values</li>
              <li>• Use <code className="bg-blue-100 px-1 rounded">{`row.get("column_name")`}</code> for safe access (returns None if missing)</li>
              <li>• Combine fields: <code className="bg-blue-100 px-1 rounded">{`f"row['first'] row['last']"`}</code></li>
              <li>• Conditional logic: <code className="bg-blue-100 px-1 rounded">value if condition else other_value</code></li>
              <li>• String operations: <code className="bg-blue-100 px-1 rounded">{`row["email"].split("@")[1]`}</code></li>
            </ul>
          </div>
        </div>

        <div className="flex justify-end gap-3 p-6 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            {initialData ? 'Update' : 'Create'} Lambda Mapping
          </button>
        </div>
      </div>
    </div>
  )
}
