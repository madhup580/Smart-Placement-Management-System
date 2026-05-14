import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AppStateContext'
import { authAPI } from '../services/api'
import './LoginPage.css'

function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const { loginStart, loginSuccess, loginFailure } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    loginStart()

    try {
      const response = await authAPI.login(username, password)
      loginSuccess(response.user, response.access_token)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Login failed'
      setError(errorMessage)
      loginFailure(errorMessage)
    }
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <h1>AI Interview Platform</h1>
        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="error-message">{error}</div>}
          
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          
          <button type="submit" className="btn-primary">
            Login
          </button>
        </form>
        
        <p className="register-link">
          Don't have an account? <a href="/register">Register</a>
        </p>
      </div>
    </div>
  )
}

export default LoginPage
