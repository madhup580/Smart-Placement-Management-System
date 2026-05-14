import React from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../contexts/AppStateContext'
import { studentAPI, facultyAPI, adminAPI } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import './DashboardPage.css'

function DashboardPage() {
  const { auth } = useAuth()
  const user = auth.user
  const isAuthenticated = auth.isAuthenticated && user

  // Fetch dashboard data based on role
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', user?.role, user?.id],
    queryFn: async () => {
      if (user?.role === 'student') {
        return await studentAPI.getDashboard()
      } else if (user?.role === 'faculty') {
        return await facultyAPI.getDashboard()
      } else if (user?.role === 'admin') {
        return await adminAPI.getDashboard()
      }
      return null
    },
    enabled: !!isAuthenticated,
    retry: 1,
  })

  if (!isAuthenticated) {
    return <PublicDashboard />
  }

  if (isLoading) {
    return <LoadingSpinner />
  }

  if (error) {
    return (
      <div className="error">
        Error loading dashboard: {error?.response?.data?.error || error.message || 'Unknown error'}
      </div>
    )
  }

  return (
    <div className="dashboard-page">
      <h1>Dashboard</h1>
      <div className="dashboard-content">
        {user?.role === 'student' && (
          <StudentDashboard data={data} user={user} />
        )}
        {(user?.role === 'faculty' || user?.role === 'admin') && (
          <FacultyAdminDashboard data={data} user={user} />
        )}
      </div>
    </div>
  )
}

function PublicDashboard() {
  return (
    <div className="dashboard-page">
      <h1>Dashboard</h1>
      <div className="dashboard-content">
        <div className="student-dashboard">
          <h2>Welcome to AI Interview Platform</h2>
          <p>Practice coding questions, non-technical MCQs, quizzes, assessments, and access Python, Java, and SQL notes after login.</p>
          <div className="dashboard-cards">
            <div className="dashboard-card">
              <h3>Coding Practice</h3>
              <p>Python, Java, arrays, strings, and interview problems.</p>
            </div>
            <div className="dashboard-card">
              <h3>Non-Technical</h3>
              <p>OOP, DBMS, SQL, aptitude, and HR communication.</p>
            </div>
            <div className="dashboard-card">
              <h3>Resources</h3>
              <p>Download notes for Python, Java, and Database SQL.</p>
            </div>
          </div>
          <div className="dashboard-actions">
            <Link to="/login" className="btn-primary">Login</Link>
            <Link to="/register" className="btn-secondary">Register</Link>
          </div>
        </div>
      </div>
    </div>
  )
}

function StudentDashboard({ data, user }) {
  return (
    <div className="student-dashboard">
      <h2>Welcome, {user?.username || 'Student'}!</h2>
      <div className="dashboard-cards">
        <div className="dashboard-card">
          <h3>Placement Readiness</h3>
          <p className="score">{data?.placement_readiness_score || 'N/A'}</p>
        </div>
        <div className="dashboard-card">
          <h3>Total Questions Solved</h3>
          <p className="score">{data?.total_questions_solved || 0}</p>
        </div>
        <div className="dashboard-card">
          <h3>Interviews Completed</h3>
          <p className="score">{data?.interviews_completed || 0}</p>
        </div>
      </div>
    </div>
  )
}

function FacultyAdminDashboard({ data, user }) {
  return (
    <div className="faculty-admin-dashboard">
      <h2>Welcome, {user?.username || 'User'}!</h2>
      <div className="dashboard-cards">
        <div className="dashboard-card">
          <h3>Total Students</h3>
          <p className="score">{data?.total_students || 0}</p>
        </div>
        <div className="dashboard-card">
          <h3>Active Interviews</h3>
          <p className="score">{data?.active_interviews || 0}</p>
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
