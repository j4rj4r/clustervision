import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import UsersPage from './pages/UsersPage'
import RbacPage from './pages/RbacPage'
import KubeconfigPage from './pages/KubeconfigPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/users" replace />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="rbac" element={<RbacPage />} />
          <Route path="kubeconfig" element={<KubeconfigPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
