import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import DatasetDetail from './pages/DatasetDetail'
import Mappings from './pages/Mappings'
import Import from './pages/Import'
import Runs from './pages/Runs'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="upload" element={<Upload />} />
        <Route path="datasets/:id" element={<DatasetDetail />} />
        <Route path="datasets/:id/mappings" element={<Mappings />} />
        <Route path="datasets/:id/import" element={<Import />} />
        <Route path="runs" element={<Runs />} />
      </Route>
    </Routes>
  )
}

export default App
