import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { quizAPI } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'

function QuizzesPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['quizzes'],
    queryFn: () => quizAPI.listQuizzes(),
    retry: 1,
  })

  if (isLoading) return <LoadingSpinner />

  if (error) {
    return <div className="error">Error loading quizzes: {error?.response?.data?.error || error.message}</div>
  }

  const quizzes = data?.quizzes || []

  return (
    <div className="quizzes-page">
      <h1>Quizzes</h1>
      {quizzes.length > 0 ? (
        <div className="questions-grid">
          {quizzes.map((quiz) => (
            <article key={quiz.id} className="question-card">
              <h3>{quiz.title}</h3>
              <p>{quiz.description}</p>
              <p><strong>Duration:</strong> {quiz.duration_minutes} minutes</p>
              <p><strong>Marks:</strong> {quiz.total_marks}</p>
              <span className="difficulty difficulty-easy">
                {quiz.is_locked ? 'Locked' : 'Available'}
              </span>
            </article>
          ))}
        </div>
      ) : (
        <div className="no-questions">
          <p>No quizzes available at the moment.</p>
        </div>
      )}
    </div>
  )
}

export default QuizzesPage
