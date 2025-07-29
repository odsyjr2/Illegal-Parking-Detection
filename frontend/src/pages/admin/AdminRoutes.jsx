import { Routes, Route, Navigate } from 'react-router-dom'
import AdminPage from './AdminPage'
import UserManagement from './UserManagement'
import CctvManagement from './CctvManagement'
import ReportsPage from './ReportsPage'
import ZonesManagement from './ZonesManagement'

function AdminRoutes() {
  return (
    <Routes>
    <Route path="/" element={<AdminPage />}>
        <Route index element={<UserManagement />} />
        <Route path="users" element={<UserManagement />} />
        <Route path="cctv" element={<CctvManagement />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="zones" element={<ZonesManagement />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>

  )
}
export default AdminRoutes
