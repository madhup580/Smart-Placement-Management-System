import React from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AppStateContext'
import './Layout.css'

function Layout({ children }) {
  const { auth, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  
  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }
  
  const isActive = (path) => location.pathname === path
  
  return (
    <div className="layout">
      <nav className="navbar">
        <div className="navbar-brand">
          <h1>AI Interview Platform</h1>
        </div>
        
        <div className="navbar-menu">
          <Link
            to="/dashboard"
            className={`nav-link ${isActive('/dashboard') ? 'active' : ''}`}
          >
            Dashboard
          </Link>
          <Link
            to="/coding"
            className={`nav-link ${isActive('/coding') ? 'active' : ''}`}
          >
            Coding
          </Link>
          <Link
            to="/interview"
            className={`nav-link ${isActive('/interview') ? 'active' : ''}`}
          >
            Interview
          </Link>
          <Link
            to="/non-technical"
            className={`nav-link ${isActive('/non-technical') ? 'active' : ''}`}
          >
            Non-Technical
          </Link>
          <Link
            to="/quizzes"
            className={`nav-link ${isActive('/quizzes') ? 'active' : ''}`}
          >
            Quizzes
          </Link>
          <Link
            to="/assessments"
            className={`nav-link ${isActive('/assessments') ? 'active' : ''}`}
          >
            Assessments
          </Link>
          <Link
            to="/resources"
            className={`nav-link ${isActive('/resources') ? 'active' : ''}`}
          >
            Resources
          </Link>
          <Link
            to="/leaderboard"
            className={`nav-link ${isActive('/leaderboard') ? 'active' : ''}`}
          >
            Leaderboard
          </Link>
          {auth.user?.role === 'student' && (
            <Link
              to="/chatbot"
              className={`nav-link ${isActive('/chatbot') ? 'active' : ''}`}
            >
              Chatbot
            </Link>
          )}
        </div>
        
        <div className="navbar-user">
          {auth.isAuthenticated ? (
            <>
              <span className="user-name">
                {auth.user?.username || 'User'}
              </span>
              <button onClick={handleLogout} className="btn-logout">
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-logout">
                Login
              </Link>
              <Link to="/register" className="btn-logout">
                Register
              </Link>
            </>
          )}
        </div>
      </nav>
      
      <main className="main-content">
        {children}
      </main>
    </div>
  )
}

export default Layout
