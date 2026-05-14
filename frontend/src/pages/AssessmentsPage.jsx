import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../contexts/AppStateContext'
import { facultyAPI, studentAPI } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'

function AssessmentsPage() {
  const { auth } = useAuth()
  const isFacultyView = auth.user?.role === 'faculty' || auth.user?.role === 'admin'

  const { data, isLoading, error } = useQuery({
    queryKey: ['assessments', auth.user?.role],
    queryFn: () => isFacultyView ? facultyAPI.getAssessments() : studentAPI.getAssessments(),
    enabled: !!auth.user,
    retry: 1,
  })

  if (isLoading) return <LoadingSpinner />

  if (error) {
    return <div className="error">Error loading assessments: {error?.response?.data?.error || error.message}</div>
  }

  const assessments = data?.assessments || []

  return (
    <div className="assessments-page">
      <h1>Assessments</h1>
      {assessments.length > 0 ? (
        <div className="questions-grid">
          {assessments.map((assessment) => (
            <article key={assessment.id} className="question-card">
              <h3>{assessment.title}</h3>
              <p>{assessment.description}</p>
              <p><strong>Mode:</strong> {assessment.assessment_mode}</p>
              <p><strong>Questions:</strong> {assessment.question_count}</p>
              <p><strong>Marks:</strong> {assessment.total_marks}</p>
              <span className={`difficulty difficulty-${assessment.difficulty?.toLowerCase() || 'medium'}`}>
                {assessment.status || assessment.difficulty}
              </span>
            </article>
          ))}
        </div>
      ) : (
        <div className="no-questions">
          <p>No assessments available at the moment.</p>
        </div>
      )}
    </div>
  )
}

export default AssessmentsPage
