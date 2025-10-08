import { Outlet, Link, useLocation } from 'react-router-dom'

export default function Layout() {
  const location = useLocation()

  const isActive = (path: string) => {
    return location.pathname === path
      ? 'bg-blue-700 text-white'
      : 'text-gray-300 hover:bg-blue-700 hover:text-white'
  }

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <div className="w-64 bg-gray-800 text-white">
        <div className="p-4">
          <h1 className="text-2xl font-bold">Data Migrator</h1>
          <p className="text-sm text-gray-400">Odoo Import Platform</p>
        </div>

        <nav className="mt-8">
          <Link
            to="/"
            className={`block px-4 py-2 ${isActive('/')}`}
          >
            Dashboard
          </Link>
          <Link
            to="/upload"
            className={`block px-4 py-2 ${isActive('/upload')}`}
          >
            Upload File
          </Link>
          <Link
            to="/runs"
            className={`block px-4 py-2 ${isActive('/runs')}`}
          >
            Import Runs
          </Link>
        </nav>
      </div>

      {/* Main content */}
      <div className="flex-1 bg-gray-100">
        <div className="p-8">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
