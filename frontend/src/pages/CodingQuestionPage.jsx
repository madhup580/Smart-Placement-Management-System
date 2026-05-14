import React, { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { codingAPI } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import './CodingQuestionPage.css'

function CodingQuestionPage() {
  const { questionId } = useParams()
  const [code, setCode] = useState('')
  const [language, setLanguage] = useState('python')
  const [output, setOutput] = useState('')

  const { data: question, isLoading, error } = useQuery({
    queryKey: ['coding-question', questionId],
    queryFn: () => codingAPI.getQuestion(parseInt(questionId)),
    enabled: !!questionId,
    retry: 1,
  })

  const executeMutation = useMutation({
    mutationFn: () => codingAPI.execute(code, language, '', questionId),
    onSuccess: (data) => {
      setOutput(data.output || '(no output)')
    },
    onError: (err) => {
      const message = err.response?.status === 401
        ? 'Your login session expired. Please login again from the dashboard.'
        : err.response?.data?.error || err.message || 'Failed to run code'
      setOutput(message)
    },
  })

  const submitMutation = useMutation({
    mutationFn: () => codingAPI.submit(questionId, code, language),
    onSuccess: (data) => {
      console.log('Submission result:', data)
      // Handle submission result
    },
    onError: (err) => {
      const message = err.response?.status === 401
        ? 'Your login session expired. Please login again from the dashboard.'
        : err.response?.data?.error || err.message || 'Failed to submit code'
      setOutput(message)
    },
  })

  if (isLoading) {
    return <LoadingSpinner />
  }

  if (error) {
    return <div className="error">Error loading question: {error?.response?.data?.error || error.message}</div>
  }

  if (!question) {
    return <div className="error">Question not found</div>
  }

  return (
    <div className="coding-question-page">
      <div className="question-section">
        <h1>{question.title}</h1>
        <div className="question-description">
          {question.description}
        </div>
      </div>

      <div className="code-section">
        <div className="code-header">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="language-select"
          >
            <option value="python">Python</option>
            <option value="cpp">C++</option>
            <option value="c">C</option>
            <option value="java">Java</option>
          </select>
          <div className="code-actions">
            <button
              onClick={() => executeMutation.mutate()}
              disabled={executeMutation.isPending}
              className="btn-run"
            >
              Run
            </button>
            <button
              onClick={() => submitMutation.mutate()}
              disabled={submitMutation.isPending}
              className="btn-submit"
            >
              Submit
            </button>
          </div>
        </div>

        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="code-editor"
          placeholder="Write your code here..."
        />

        {output && (
          <div className="output-section">
            <h3>Output</h3>
            <pre className="output">{output}</pre>
          </div>
        )}

        {submitMutation.data && (
          <div className="submission-result">
            <h3>Submission Result</h3>
            <div className="result-content">
              <p>Status: {submitMutation.data.verdict}</p>
              <p>Passed: {submitMutation.data.passed}/{submitMutation.data.total}</p>
              {submitMutation.data.final_report && (
                <div className="comprehensive-report">
                  <h4>Industry Analysis Report</h4>
                  <p>Time Complexity: {submitMutation.data.final_report.time_complexity}</p>
                  <p>Memory Usage: {submitMutation.data.final_report.memory_usage}</p>
                  <p>Code Quality: {submitMutation.data.final_report.code_quality}</p>
                  <p>Edge Cases: {submitMutation.data.final_report.edge_case_status}</p>
                  {submitMutation.data.final_report.suggestions?.length > 0 && (
                    <div>
                      <h5>Suggestions:</h5>
                      <ul>
                        {submitMutation.data.final_report.suggestions.map((suggestion, idx) => (
                          <li key={idx}>{suggestion}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default CodingQuestionPage
