import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { resourcesAPI } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'

function saveBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(link)
}

function ResourcesPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['resources'],
    queryFn: () => resourcesAPI.getResources(),
    retry: 1,
  })

  const handleDownload = async (resource) => {
    const blob = await resourcesAPI.downloadResource(resource.id)
    const filename = `${resource.title || 'resource'}.txt`
    saveBlob(blob, filename)
  }

  if (isLoading) return <LoadingSpinner />

  if (error) {
    return <div className="error">Error loading resources: {error?.response?.data?.error || error.message}</div>
  }

  const resources = data?.resources || []

  return (
    <div className="resources-page">
      <h1>Resources</h1>
      {resources.length > 0 ? (
        <div className="questions-grid">
          {resources.map((resource) => (
            <article key={resource.id} className="question-card">
              <h3>{resource.title}</h3>
              <p>{resource.description}</p>
              {resource.tags?.length > 0 && <p><strong>Tags:</strong> {resource.tags.join(', ')}</p>}
              {resource.content && <p>{resource.content.substring(0, 180)}...</p>}
              <button type="button" className="btn-primary" onClick={() => handleDownload(resource)}>
                Download Notes
              </button>
            </article>
          ))}
        </div>
      ) : (
        <div className="no-questions">
          <p>No resources available at the moment.</p>
        </div>
      )}
    </div>
  )
}

export default ResourcesPage
