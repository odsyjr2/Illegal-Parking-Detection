// src/App.jsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import LoginPage from './pages/auth/LoginPage'
import SignupPage from './pages/auth/SignupPage'
// 필요한 페이지들 import

function App() {
  return (
    <Router>
      <Layout>
        <div style={{ marginLeft: '220px', padding: '1rem' }}>
          <Routes>
            <Route path="/" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            {/* 나중에 다른 페이지 추가 */}
          </Routes>
        </div>
      </Layout>
    </Router>
  )
}

export default App
