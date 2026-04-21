import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import RequireAuth from './components/auth/RequireAuth'
import LoginPage from './pages/LoginPage'
import UsersPage from './pages/UsersPage'
import RbacPage from './pages/RbacPage'
import KubeconfigPage from './pages/KubeconfigPage'
import ClustersPage from './pages/ClustersPage'
import TokensPage from './pages/TokensPage'
import AdminPage from './pages/AdminPage'
import NotFoundPage from './pages/NotFoundPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireAuth />}>
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/users" replace />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="rbac" element={<RbacPage />} />
            <Route path="kubeconfig" element={<KubeconfigPage />} />
            <Route path="tokens" element={<TokensPage />} />
            <Route path="clusters" element={<ClustersPage />} />
            <Route path="settings" element={<AdminPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
