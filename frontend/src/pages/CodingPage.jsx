import React from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { studentAPI } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import './CodingPage.css'

function CodingPage() {
  const { data: questions, isLoading, error } = useQuery({
    queryKey: ['coding-questions'],
    queryFn: async () => {
      try {
        // Try to get coding questions from student API
        const response = await studentAPI.getCodingQuestions()
        return response?.questions || response || []
      } catch (err) {
        console.error('Error fetching coding questions:', err)
        return []
      }
    },
    retry: 1,
  })

  if (isLoading) {
    return <LoadingSpinner />
  }

  if (error) {
    return <div className="error">Error loading questions: {error?.response?.data?.error || error.message}</div>
  }

  return (
    <div className="coding-page">
      <h1>Coding Practice</h1>
      {questions && questions.length > 0 ? (
        <div className="questions-grid">
          {questions.map((question) => (
            <Link
              key={question.id}
              to={`/coding/${question.id}`}
              className="question-card"
            >
              <h3>{question.title || question.question || 'Untitled'}</h3>
              <p>{question.description?.substring(0, 100) || question.content?.substring(0, 100) || 'No description'}...</p>
              <span className={`difficulty difficulty-${question.difficulty?.toLowerCase() || 'medium'}`}>
                {question.difficulty || 'Medium'}
              </span>
            </Link>
          ))}
        </div>
      ) : (
        <div className="no-questions">
          <p>No coding questions available at the moment.</p>
        </div>
      )}
    </div>
  )
}

export default CodingPage
