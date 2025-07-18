// src/components/layout/Layout.jsx
import NavBar from './NavBar'
import './Layout.css' // 스타일 따로 분리

function Layout({ children }) {
  return (
    <div className="layout">
      <NavBar />
      <main className="content">{children}</main>
    </div>
  )
}

export default Layout
