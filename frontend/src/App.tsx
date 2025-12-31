import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import { ErrorBoundary } from './components/ErrorBoundary'

// Pages
import Dashboard from './pages/Dashboard'
import Devices from './pages/Devices'
import Users from './pages/Users'
import Groups from './pages/Groups'
import NetworkFlows from './pages/NetworkFlows'
import Clusters from './pages/Clusters'
import SGTMatrix from './pages/SGTMatrix'

// Policy pages
import Policy from './pages/Policy'
import PolicyBuilder from './pages/PolicyBuilder'
import SGTMappings from './pages/policy/SGTMappings'
import AccessRules from './pages/policy/AccessRules'
import ImpactAnalysis from './pages/policy/ImpactAnalysis'

// Topology
import Topology from './pages/Topology'

// Data Sources
import DataSources from './pages/DataSources'
import DataSourcesOverview from './pages/data-sources/Overview'
import EdgeAgents from './pages/data-sources/Agents'
import NetFlowCollectors from './pages/data-sources/Collectors'

// Connectors
import Connectors from './pages/Connectors'
import ISEConnector from './pages/connectors/ISE'
import ADConnector from './pages/connectors/AD'
import IoTConnectors from './pages/connectors/IoT'

// Settings
import Settings from './pages/Settings'
import GlobalSettings from './pages/settings/Global'
import ClusteringSettings from './pages/settings/Clustering'
import PolicySettings from './pages/settings/Policy'
import CertificateSettings from './pages/settings/Certificates'
import SystemSettings from './pages/settings/System'

// Monitoring & Reports
import Monitoring from './pages/Monitoring'
import Audit from './pages/Audit'
import Reports from './pages/Reports'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/devices" element={<Devices />} />
              <Route path="/users" element={<Users />} />
              <Route path="/groups" element={<Groups />} />
              <Route path="/flows" element={<NetworkFlows />} />
              <Route path="/clusters" element={<Clusters />} />
              <Route path="/matrix" element={<SGTMatrix />} />
              
              {/* Policy routes */}
              <Route path="/policy" element={<Policy />}>
                <Route path="sgts" element={<SGTMappings />} />
                <Route path="rules" element={<AccessRules />} />
                <Route path="matrix" element={<SGTMatrix />} />
                <Route path="builder" element={<PolicyBuilder />} />
                <Route path="impact" element={<ImpactAnalysis />} />
              </Route>
              
              {/* Topology */}
              <Route path="/topology" element={<Topology />} />
              
              {/* Data Sources routes */}
              <Route path="/data-sources" element={<DataSources />}>
                <Route path="overview" element={<DataSourcesOverview />} />
                <Route path="agents" element={<EdgeAgents />} />
                <Route path="collectors" element={<NetFlowCollectors />} />
              </Route>
              
              {/* Connectors routes */}
              <Route path="/connectors" element={<Connectors />}>
                <Route path="ise" element={<ISEConnector />} />
                <Route path="ad" element={<ADConnector />} />
                <Route path="iot" element={<IoTConnectors />} />
              </Route>
              
              {/* Settings routes */}
              <Route path="/settings" element={<Settings />}>
                <Route path="global" element={<GlobalSettings />} />
                <Route path="clustering" element={<ClusteringSettings />} />
                <Route path="policy" element={<PolicySettings />} />
                <Route path="certificates" element={<CertificateSettings />} />
                <Route path="system" element={<SystemSettings />} />
              </Route>
              
              {/* Monitoring & Reports */}
              <Route path="/monitoring" element={<Monitoring />} />
              <Route path="/audit" element={<Audit />} />
              <Route path="/reports" element={<Reports />} />
            </Routes>
          </Layout>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
