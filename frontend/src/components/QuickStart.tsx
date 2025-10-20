import { useEffect, useState } from 'react'
import { templatesApi } from '@/services/api'

interface Template {
  id: string
  name: string
  description: string
  category: string
  icon?: string
  estimatedTime: string
  difficulty: string
  modelCount: number
  completed: boolean
}

interface Category {
  id: string
  name: string
  description: string
}

export default function QuickStart() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [templatesData, categoriesData] = await Promise.all([
        templatesApi.list(),
        templatesApi.getCategories()
      ])
      setTemplates(templatesData)
      setCategories(categoriesData)
    } catch (error) {
      console.error('Failed to load templates:', error)
      setErrorMessage('Failed to load templates. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleTemplateClick = async (templateId: string) => {
    try {
      setSuccessMessage(null)
      setErrorMessage(null)
      const result = await templatesApi.instantiate(templateId)
      setSuccessMessage(`Graph created from template. Graph ID: ${result.graphId}`)
    } catch (error) {
      console.error('Failed to instantiate template:', error)
      setErrorMessage('Failed to create graph from template.')
    }
  }

  const filteredTemplates = selectedCategory
    ? templates.filter(t => t.category === selectedCategory)
    : templates

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner': return 'text-green-600 bg-green-50'
      case 'intermediate': return 'text-yellow-600 bg-yellow-50'
      case 'advanced': return 'text-red-600 bg-red-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  if (loading) {
    return <div className="text-gray-500">Loading quick start guides...</div>
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-2xl font-bold">Quick Start: Odoo 18 Setup</h2>
          <p className="text-gray-600">Choose a guided template to import your data</p>
        </div>
      </div>
      {(successMessage || errorMessage) && (
        <div className="mb-4 space-y-2 text-sm">
          {successMessage && (
            <div className="space-y-1 rounded border border-green-200 bg-green-50 px-4 py-2 text-green-700">
              <p>{successMessage}</p>
              <p className="text-sm">
                Head to the{' '}
                <a href={`/runs`} className="underline">
                  Runs dashboard
                </a>{' '}
                to track progress.
              </p>
            </div>
          )}
          {errorMessage && (
            <div className="rounded border border-red-200 bg-red-50 px-4 py-2 text-red-700">
              {errorMessage}
            </div>
          )}
        </div>
      )}

      {/* Category filters */}
      <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`px-4 py-2 rounded-lg whitespace-nowrap ${
            selectedCategory === null
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          All Templates
        </button>
        {categories.map((category) => (
          <button
            key={category.id}
            onClick={() => setSelectedCategory(category.id)}
            className={`px-4 py-2 rounded-lg whitespace-nowrap ${
              selectedCategory === category.id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {category.name}
          </button>
        ))}
      </div>

      {/* Templates grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredTemplates.map((template) => (
          <div
            key={template.id}
            className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => handleTemplateClick(template.id)}
          >
            <div className="flex items-start gap-3 mb-3">
              {template.icon && (
                <span className="text-3xl">{template.icon}</span>
              )}
              <div className="flex-1">
                <h3 className="font-semibold text-lg">{template.name}</h3>
                <p className="text-sm text-gray-600">{template.description}</p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mb-3">
              <span className={`text-xs px-2 py-1 rounded ${getDifficultyColor(template.difficulty)}`}>
                {template.difficulty}
              </span>
              <span className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-600">
                {template.modelCount} models
              </span>
              <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600">
                {template.estimatedTime}
              </span>
            </div>

            <button
              className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
              onClick={(e) => {
                e.stopPropagation()
                handleTemplateClick(template.id)
              }}
            >
              Start Import
            </button>
          </div>
        ))}
      </div>

      {filteredTemplates.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          No templates found for this category
        </div>
      )}
    </div>
  )
}
