import { useState } from 'react'

interface Props {
  isOpen: boolean
  onClose: () => void
  onSaved: () => void
}

export default function OdooConnectionModal({ isOpen, onClose, onSaved }: Props) {
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [database, setDatabase] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isDefault, setIsDefault] = useState(true)
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null)

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)

    try {
      const response = await fetch('/api/v1/odoo/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          database,
          username,
          password
        })
      })

      const result = await response.json()
      setTestResult(result)
    } catch (error) {
      setTestResult({
        status: 'error',
        message: `Failed to connect: ${error}`
      })
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)

    try {
      const response = await fetch('/api/v1/odoo/connections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          url,
          database,
          username,
          password,
          is_default: isDefault
        })
      })

      if (response.ok) {
        onSaved()
        handleClose()
      }
    } catch (error) {
      console.error('Failed to save connection:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleClose = () => {
    setName('')
    setUrl('')
    setDatabase('')
    setUsername('')
    setPassword('')
    setIsDefault(true)
    setTestResult(null)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold">Configure Odoo Connection</h2>
            <button onClick={handleClose} className="text-gray-500 hover:text-gray-700">✕</button>
          </div>

          <div className="space-y-4">
            {/* Connection Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Connection Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2"
                placeholder="Production Odoo"
              />
            </div>

            {/* URL */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Odoo URL *
              </label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2"
                placeholder="https://mycompany.odoo.com"
              />
              <p className="text-xs text-gray-500 mt-1">Full URL to your Odoo instance</p>
            </div>

            {/* Database */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Database Name *
              </label>
              <input
                type="text"
                value={database}
                onChange={(e) => setDatabase(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2"
                placeholder="my_database"
              />
            </div>

            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username *
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2"
                placeholder="admin"
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password *
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2"
              />
            </div>

            {/* Is Default */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="is_default"
                checked={isDefault}
                onChange={(e) => setIsDefault(e.target.checked)}
                className="mr-2"
              />
              <label htmlFor="is_default" className="text-sm font-medium text-gray-700">
                Set as default connection
              </label>
            </div>

            {/* Test Result */}
            {testResult && (
              <div className={`p-3 rounded ${
                testResult.status === 'success'
                  ? 'bg-green-50 border border-green-200'
                  : 'bg-red-50 border border-red-200'
              }`}>
                <p className={`text-sm font-medium ${
                  testResult.status === 'success' ? 'text-green-900' : 'text-red-900'
                }`}>
                  {testResult.status === 'success' ? '✓' : '✗'} {testResult.message}
                </p>
              </div>
            )}
          </div>

          <div className="mt-6 flex gap-3 justify-end">
            <button
              onClick={handleClose}
              className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleTest}
              disabled={!url || !database || !username || !password || testing}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
            <button
              onClick={handleSave}
              disabled={!name || !url || !database || !username || !password || saving || testResult?.status !== 'success'}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400"
            >
              {saving ? 'Saving...' : 'Save Connection'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
