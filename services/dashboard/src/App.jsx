import { Routes, Route, Navigate } from 'react-router-dom'
import Connect from './Connect'
import Dashboard from './Dashboard'
import { getConfig } from './api'

function RequireConfig({ children }) {
  return getConfig() ? children : <Navigate to="/" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Connect />} />
      <Route
        path="/dashboard"
        element={
          <RequireConfig>
            <Dashboard />
          </RequireConfig>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
