import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/layout/Layout'
import Login from './pages/Login'
import Overview from './pages/Overview'
import Trends from './pages/Trends'
import Sites from './pages/Sites'
import Factors from './pages/Factors'
import DataManagement from './pages/DataManagement'
import Flags from './pages/Flags'
import Reports from './pages/Reports'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Overview />} />
            <Route path="trends" element={<Trends />} />
            <Route path="sites" element={<Sites />} />
            <Route path="factors" element={<Factors />} />
            <Route path="data" element={<DataManagement />} />
            <Route path="flags" element={<Flags />} />
            <Route path="reports" element={<Reports />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
