import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ErrorBoundary } from './components/ErrorBoundary'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import NetworkFlows from './pages/NetworkFlows'
import Clusters from './pages/Clusters'
import SGTMatrix from './pages/SGTMatrix'
import PolicyBuilder from './pages/PolicyBuilder'

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/flows" element={<NetworkFlows />} />
            <Route path="/clusters" element={<Clusters />} />
            <Route path="/matrix" element={<SGTMatrix />} />
            <Route path="/policies" element={<PolicyBuilder />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App

