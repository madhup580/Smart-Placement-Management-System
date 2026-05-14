import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { studentAPI } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'

function NonTechnicalPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['non-technical-questions'],
    queryFn: () => studentAPI.getQuestions({
      type: 'mcq',
      module_type: 'Non-Technical',
      exclude_quiz_questions: 'true',
      per_page: 100,
    }),
    retry: 1,
  })

  if (isLoading) return <LoadingSpinner />

  if (error) {
    return <div className="error">Error loading non-technical questions: {error?.response?.data?.error || error.message}</div>
  }

  const questions = data?.questions || []

  return (
    <div className="non-technical-page">
      <h1>Non-Technical Practice</h1>
      {questions.length > 0 ? (
        <div className="questions-grid">
          {questions.map((question) => (
            <article key={question.id} className="question-card">
              <h3>{question.title}</h3>
              <p>{question.description}</p>
              {question.options?.length > 0 && (
                <ol type="A">
                  {question.options.map((option) => (
                    <li key={option}>{option}</li>
                  ))}
                </ol>
              )}
              <span className={`difficulty difficulty-${question.difficulty?.toLowerCase() || 'easy'}`}>
                {question.difficulty || 'Easy'}
              </span>
            </article>
          ))}
        </div>
      ) : (
        <div className="no-questions">
          <p>No non-technical questions available at the moment.</p>
        </div>
      )}
    </div>
  )
}

export default NonTechnicalPage
