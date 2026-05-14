import React from 'react'
import './LoadingSpinner.css'

function LoadingSpinner() {
  return (
    <div className="loading-overlay">
      <div className="loading-spinner"></div>
      <div className="loading-message">Loading...</div>
    </div>
  )
}

export default LoadingSpinner
