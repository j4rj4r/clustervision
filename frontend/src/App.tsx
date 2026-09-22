import { lazy } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import RequireAuth from './components/auth/RequireAuth'
import LoginPage from './pages/LoginPage'

const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const UsersPage = lazy(() => import('./pages/UsersPage'))
const RbacPage = lazy(() => import('./pages/RbacPage'))
const KubeconfigPage = lazy(() => import('./pages/KubeconfigPage'))
const ClustersPage = lazy(() => import('./pages/ClustersPage'))
const TokensPage = lazy(() => import('./pages/TokensPage'))
const AccessRequestsPage = lazy(() => import('./pages/AccessRequestsPage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))
const AuditLogPage = lazy(() => import('./pages/AuditLogPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireAuth />}>
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="rbac" element={<RbacPage />} />
            <Route path="kubeconfig" element={<KubeconfigPage />} />
            <Route path="tokens" element={<TokensPage />} />
            <Route path="access-requests" element={<AccessRequestsPage />} />
            <Route path="clusters" element={<ClustersPage />} />
            <Route path="settings" element={<AdminPage />} />
            <Route path="audit-log" element={<AuditLogPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
