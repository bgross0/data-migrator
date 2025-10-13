import { useState, useEffect } from 'react'
import { Check, Grid, Users, ShoppingCart, Truck, Settings, HelpCircle, Zap } from 'lucide-react'

interface Module {
  name: string
  display_name: string
  description: string
  icon: string
  model_count: number
  priority: number
}

interface ModuleSelectorProps {
  selectedModules: string[]
  onModulesChange: (modules: string[]) => void
  suggestedModules?: string[]
  loading?: boolean
}

const MODULE_ICONS: Record<string, any> = {
  'contacts_partners': Users,
  'sales_crm': ShoppingCart,
  'fleet': Truck,
  'projects': Grid,
  'inventory': Settings,
  'accounting': Zap,
  'hr': Users,
  'website': Grid,
  'manufacturing': Settings,
  'default': HelpCircle
}

export default function ModuleSelector({ 
  selectedModules, 
  onModulesChange, 
  suggestedModules,
  loading = false 
}: ModuleSelectorProps) {
  const [availableModules, setAvailableModules] = useState<Module[]>([])
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    fetchAvailableModules()
  }, [])

  const fetchAvailableModules = async () => {
    try {
      const response = await fetch('/api/v1/modules')
      const data = await response.json()
      setAvailableModules(data.modules || [])
    } catch (error) {
      console.error('Failed to fetch modules:', error)
    }
  }

  const toggleModule = (moduleName: string) => {
    if (selectedModules.includes(moduleName)) {
      onModulesChange(selectedModules.filter(m => m !== moduleName))
    } else {
      onModulesChange([...selectedModules, moduleName])
    }
  }

  const selectSuggested = () => {
    if (suggestedModules) {
      onModulesChange(suggestedModules)
    }
  }

  const clearSelection = () => {
    onModulesChange([])
  }

  const filteredModules = availableModules.filter(module =>
    module.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    module.description.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getModuleIcon = (iconName: string) => {
    return MODULE_ICONS[iconName] || MODULE_ICONS.default
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded mb-4 w-1/3"></div>
          <div className="grid grid-cols-2 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Grid className="w-5 h-5 text-blue-600" />
            Select Odoo Modules
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Choose modules to improve field mapping accuracy
          </p>
        </div>
        <div className="flex gap-2">
          {suggestedModules && suggestedModules.length > 0 && (
            <button
              onClick={selectSuggested}
              className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
            >
              Use Suggested ({suggestedModules.length})
            </button>
          )}
          <button
            onClick={clearSelection}
            className="px-3 py-1 text-sm text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
          >
            Clear All
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search modules..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full border rounded px-3 py-2"
        />
      </div>

      {/* Selection Stats */}
      <div className="mb-4 p-3 bg-gray-50 rounded">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">
            {selectedModules.length} module{selectedModules.length !== 1 ? 's' : ''} selected
          </span>
          <span className="text-sm text-gray-600">
            {availableModules.reduce((sum, m) => sum + m.model_count, 0)} total models available
          </span>
        </div>
      </div>

      {/* Modules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredModules.map((module) => {
          const Icon = getModuleIcon(module.icon)
          const isSelected = selectedModules.includes(module.name)
          const isSuggested = suggestedModules?.includes(module.name)

          return (
            <div
              key={module.name}
              onClick={() => toggleModule(module.name)}
              className={`border rounded-lg p-4 cursor-pointer transition-all ${
                isSelected 
                  ? 'border-blue-500 bg-blue-50 shadow-sm' 
                  : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded ${isSelected ? 'bg-blue-100' : 'bg-gray-100'}`}>
                    <Icon className={`w-5 h-5 ${isSelected ? 'text-blue-600' : 'text-gray-600'}`} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium">{module.display_name}</h4>
                      {isSuggested && (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">
                          Suggested
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{module.description}</p>
                    <div className="text-xs text-gray-500 mt-2">
                      {module.model_count} models • Priority: {module.priority}
                    </div>
                  </div>
                </div>
                <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                  isSelected ? 'border-blue-500 bg-blue-500' : 'border-gray-300'
                }`}>
                  {isSelected && <Check className="w-3 h-3 text-white" />}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Empty State */}
      {filteredModules.length === 0 && (
        <div className="text-center py-8">
          <HelpCircle className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600">No modules found matching "{searchTerm}"</p>
        </div>
      )}

      {/* Selected Modules Summary */}
      {selectedModules.length > 0 && (
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <h4 className="font-medium text-blue-900 mb-2">Selected Modules:</h4>
          <div className="flex flex-wrap gap-2">
            {selectedModules.map((moduleName) => {
              const module = availableModules.find(m => m.name === moduleName)
              return (
                <span key={moduleName} className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                  {module?.display_name || moduleName}
                </span>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
