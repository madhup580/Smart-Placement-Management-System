import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AppStateContext'
import { authAPI } from '../services/api'
import './RegisterPage.css'

function RegisterPage() {
  const [formData, setFormData] = useState({
    username: '',
    first_name: '',
    last_name: '',
    reg_no: '',
    college_email: '',
    password: '',
    role: 'student',
    batch_id: null,
  })
  const [error, setError] = useState(null)
  const { loginStart, loginSuccess, loginFailure } = useAuth()
  const navigate = useNavigate()

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    loginStart()

    try {
      const response = await authAPI.register(formData)
      loginSuccess(response.user, response.access_token)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'Registration failed'
      setError(errorMessage)
      loginFailure(errorMessage)
    }
  }

  return (
    <div className="register-page">
      <div className="register-container">
        <h1>Register</h1>
        <form onSubmit={handleSubmit} className="register-form">
          {error && <div className="error-message">{error}</div>}
          
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                name="username"
                type="text"
                value={formData.username}
                onChange={handleChange}
                required
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="role">Role</label>
              <select
                id="role"
                name="role"
                value={formData.role}
                onChange={handleChange}
                required
              >
                <option value="student">Student</option>
                <option value="faculty">Faculty</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="first_name">First Name</label>
              <input
                id="first_name"
                name="first_name"
                type="text"
                value={formData.first_name}
                onChange={handleChange}
                required
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="last_name">Last Name</label>
              <input
                id="last_name"
                name="last_name"
                type="text"
                value={formData.last_name}
                onChange={handleChange}
                required
              />
            </div>
          </div>
          
          <div className="form-group">
            <label htmlFor="reg_no">Registration Number</label>
            <input
              id="reg_no"
              name="reg_no"
              type="text"
              value={formData.reg_no}
              onChange={handleChange}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="college_email">College Email</label>
            <input
              id="college_email"
              name="college_email"
              type="email"
              value={formData.college_email}
              onChange={handleChange}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              required
              minLength={6}
            />
          </div>
          
          <button type="submit" className="btn-primary">
            Register
          </button>
        </form>
        
        <p className="login-link">
          Already have an account? <a href="/login">Login</a>
        </p>
      </div>
    </div>
  )
}

export default RegisterPage
