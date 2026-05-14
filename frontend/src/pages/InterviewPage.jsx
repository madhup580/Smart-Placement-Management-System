import React, { useEffect, useState } from 'react'
import { useWebSocket } from '../contexts/WebSocketContext'
import { useInterviewState } from '../contexts/AppStateContext'
import { interviewAPI } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import './InterviewPage.css'

function InterviewPage() {
  const { connect, isConnected, emit } = useWebSocket()
  const { interview, setInterviewState } = useInterviewState()
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // Connect WebSocket when component mounts
    if (sessionId) {
      connect(sessionId)
    }

    return () => {
      // Cleanup on unmount
    }
  }, [sessionId, connect])

  const handleStartInterview = async (interviewType) => {
    setLoading(true)
    try {
      const response = await interviewAPI.startInterview(interviewType, {}, {})
      if (response.session_id) {
        setSessionId(response.session_id)
        setInterviewState(response.session_id, response.interview_state || {})
      }
    } catch (error) {
      console.error('Error starting interview:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <LoadingSpinner />
  }

  return (
    <div className="interview-page">
      <h1>AI Virtual Interview</h1>
      <div className="interview-status">
        <p>WebSocket: {isConnected ? '✅ Connected' : '❌ Disconnected'}</p>
        {interview.sessionId && (
          <p>Session: {interview.sessionId}</p>
        )}
      </div>
      
      {!sessionId && (
        <div className="interview-type-selection">
          <h2>Select Interview Type</h2>
          <div className="interview-type-buttons">
            <button
              onClick={() => handleStartInterview('technical')}
              className="btn-interview-type"
            >
              Technical Interview
            </button>
            <button
              onClick={() => handleStartInterview('hr')}
              className="btn-interview-type"
            >
              HR Interview
            </button>
          </div>
        </div>
      )}
      
      {sessionId && (
        <div className="interview-container">
          <p>Interview in progress...</p>
          {/* Add interview chat UI here */}
        </div>
      )}
    </div>
  )
}

export default InterviewPage
