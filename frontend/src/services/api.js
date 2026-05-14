/**
 * API Service - Centralized API client for React
 * Handles authentication, token refresh, and error handling
 */
import axios from 'axios'

// Create axios instance
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json',
  },
})

const refreshClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

async function requestNewAccessToken(refreshToken) {
  const response = await refreshClient.post(
    '/auth/refresh',
    {},
    {
      headers: {
        Authorization: `Bearer ${refreshToken}`,
      },
    }
  )

  const { access_token } = response.data
  if (!access_token) {
    throw new Error('Refresh response did not include an access token')
  }

  localStorage.setItem('authToken', access_token)
  return access_token
}

// Request interceptor - Add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - Handle token refresh and errors
apiClient.interceptors.response.use(
  (response) => {
    // Return data directly for consistency
    return response.data || response
  },
  async (error) => {
    const originalRequest = error.config
    
    // Handle 401 Unauthorized - Try token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      try {
        const refreshToken = localStorage.getItem('refreshToken')
        if (refreshToken) {
          const access_token = await requestNewAccessToken(refreshToken)
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed - logout user
        localStorage.removeItem('authToken')
        localStorage.removeItem('refreshToken')
        localStorage.removeItem('currentUser')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }
    
    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  login: async (username, password) => {
    const response = await apiClient.post('/auth/login', {
      username,
      password,
    })
    
    // Store tokens
    if (response.access_token) {
      localStorage.setItem('authToken', response.access_token)
      if (response.refresh_token) {
        localStorage.setItem('refreshToken', response.refresh_token)
      }
      if (response.user) {
        localStorage.setItem('currentUser', JSON.stringify(response.user))
      }
    }
    
    return response
  },
  
  register: async (userData) => {
    const response = await apiClient.post('/auth/register', userData)
    
    // Store tokens
    if (response.access_token) {
      localStorage.setItem('authToken', response.access_token)
      if (response.refresh_token) {
        localStorage.setItem('refreshToken', response.refresh_token)
      }
      if (response.user) {
        localStorage.setItem('currentUser', JSON.stringify(response.user))
      }
    }
    
    return response
  },
  
  logout: async () => {
    try {
      await apiClient.post('/auth/logout')
    } finally {
      localStorage.removeItem('authToken')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('currentUser')
    }
  },
  
  getCurrentUser: async () => {
    return apiClient.get('/auth/me')
  },
  
  refreshToken: async () => {
    const refreshToken = localStorage.getItem('refreshToken')
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }
    
    const accessToken = await requestNewAccessToken(refreshToken)
    return { access_token: accessToken }
  },
}

// Student API
export const studentAPI = {
  getDashboard: async () => apiClient.get('/student/dashboard'),
  getQuestions: async (filters = {}) => {
    const params = new URLSearchParams(filters)
    return apiClient.get(`/student/questions?${params}`)
  },
  getCodingQuestions: async () => {
    try {
      return apiClient.get('/coding/questions')
    } catch (error) {
      // Fallback: try alternative endpoint
      try {
        return apiClient.get('/student/coding-questions')
      } catch (e) {
        return { questions: [] }
      }
    }
  },
  getQuizzes: async () => apiClient.get('/quiz/list'),
  getResources: async () => apiClient.get('/resources'),
  getAssessments: async () => apiClient.get('/student/assessments'),
  getLeaderboard: async () => apiClient.get('/leaderboard'),
}

// Faculty API
export const facultyAPI = {
  getDashboard: async () => apiClient.get('/faculty/dashboard'),
  getAssessments: async () => apiClient.get('/faculty/assessments'),
}

// Admin API
export const adminAPI = {
  getDashboard: async () => apiClient.get('/admin/dashboard'),
}

// Coding API
export const codingAPI = {
  getQuestion: async (questionId) => apiClient.get(`/coding/questions/${questionId}`),
  execute: async (code, language, stdin, questionId) =>
    apiClient.post('/coding/execute', {
      question_id: questionId,
      code,
      language,
      stdin,
    }),
  submit: async (questionId, code, language) =>
    apiClient.post('/coding/submit', {
      question_id: questionId,
      code,
      language,
    }),
}

// Interview API
export const interviewAPI = {
  startInterview: async (interviewType, resumeData, jdData) =>
    apiClient.post('/interview/start-interview', {
      interview_type: interviewType,
      resume_data: resumeData,
      jd_data: jdData,
    }),
  
  submitAnswer: async (sessionId, answer, timeTaken) =>
    apiClient.post('/interview/submit-answer', {
      session_id: sessionId,
      answer,
      time_taken_seconds: timeTaken,
    }),
  
  completeInterview: async (sessionId) =>
    apiClient.post('/interview/complete', {
      session_id: sessionId,
    }),
  
  getSessionState: async (sessionId) => {
    try {
      return apiClient.get(`/interview/session/${sessionId}`)
    } catch (error) {
      console.error('[Interview API] Error getting session state:', error)
      throw error
    }
  },
}

// Quiz API
export const quizAPI = {
  listQuizzes: async () => apiClient.get('/quiz/list'),
  getQuiz: async (quizId) => apiClient.get(`/quiz/${quizId}`),
  submitQuiz: async (quizId, answers) =>
    apiClient.post(`/quiz/${quizId}/attempt`, { answers }),
}

// Resources API
export const resourcesAPI = {
  getResources: async () => apiClient.get('/resources'),
  downloadResource: async (resourceId) =>
    apiClient.get(`/resources/${resourceId}/download`, { responseType: 'blob' }),
  uploadResource: async (formData) =>
    apiClient.post('/resources/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}

// Leaderboard API
export const leaderboardAPI = {
  getLeaderboard: async () => apiClient.get('/leaderboard'),
}

export default apiClient
