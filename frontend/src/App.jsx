/**
 * Main App Component
 * React Router setup with protected routes
 */
import React, { useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAuth, useAppState } from './contexts/AppStateContext'
import { useWebSocket } from './contexts/WebSocketContext'

// Pages
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import CodingPage from './pages/CodingPage'
import CodingQuestionPage from './pages/CodingQuestionPage'
import InterviewPage from './pages/InterviewPage'
import NonTechnicalPage from './pages/NonTechnicalPage'
import QuizzesPage from './pages/QuizzesPage'
import ResourcesPage from './pages/ResourcesPage'
import AssessmentsPage from './pages/AssessmentsPage'
import LeaderboardPage from './pages/LeaderboardPage'
import ChatbotPage from './pages/ChatbotPage'

// Components
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import LoadingSpinner from './components/LoadingSpinner'
import ErrorBoundary from './components/ErrorBoundary'

function App() {
  const { auth } = useAuth()
  const { state } = useAppState()
  const location = useLocation()
  
  // Sync navigation state with React Router
  useEffect(() => {
    const path = location.pathname.substring(1) || 'dashboard'
    const page = path.split('/')[0]
    const params = {}
    
    // Extract params from path (e.g., /coding/123 -> { questionId: 123 })
    if (path.startsWith('coding/')) {
      const questionId = parseInt(path.split('/')[1])
      if (!isNaN(questionId)) {
        params.questionId = questionId
      }
    }
    
    // Update app state navigation
    // Note: This is handled by React Router, but we sync for consistency
  }, [location])
  
  return (
    <ErrorBoundary>
      <div className="app">
        {state.ui.loading && <LoadingSpinner />}
        
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          
          {/* Dashboard is public so users can choose Login/Register from there */}
          <Route
            path="/dashboard"
            element={
              <Layout>
                <DashboardPage />
              </Layout>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          {/* Protected routes */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Layout>
                  <Routes>
                    <Route path="/coding" element={<CodingPage />} />
                    <Route path="/coding/:questionId" element={<CodingQuestionPage />} />
                    <Route path="/interview" element={<InterviewPage />} />
                    <Route path="/non-technical" element={<NonTechnicalPage />} />
                    <Route path="/quizzes" element={<QuizzesPage />} />
                    <Route path="/assessments" element={<AssessmentsPage />} />
                    <Route path="/resources" element={<ResourcesPage />} />
                    <Route path="/leaderboard" element={<LeaderboardPage />} />
                    <Route path="/chatbot" element={<ChatbotPage />} />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </Layout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </div>
    </ErrorBoundary>
  )
}

export default App
