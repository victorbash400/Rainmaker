import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import DashboardLayout from '@/layouts/DashboardLayout'
import AuthLayout from '@/layouts/AuthLayout'
import Dashboard from '@/pages/Dashboard'
import Workflows from '@/pages/Workflows'
import Prospects from '@/pages/Prospects'
import Conversations from '@/pages/Conversations'
import Proposals from '@/pages/Proposals'
import Meetings from '@/pages/Meetings'
import Login from '@/pages/Login'

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/auth" element={<AuthLayout />}>
        <Route path="login" element={<Login />} />
      </Route>

      {/* Protected routes */}
      <Route
        path="/"
        element={
          isAuthenticated ? <DashboardLayout /> : <Navigate to="/auth/login" replace />
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="workflows" element={<Workflows />} />
        <Route path="prospects" element={<Prospects />} />
        <Route path="conversations" element={<Conversations />} />
        <Route path="proposals" element={<Proposals />} />
        <Route path="meetings" element={<Meetings />} />
      </Route>

      {/* Redirect unknown routes */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App