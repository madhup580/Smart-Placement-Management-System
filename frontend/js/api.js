// ================= API Configuration =================

// Get API URL from index.html script tag, or fallback to 127.0.0.1
const getApiBaseUrl = () => {
    // Check for config script tag
    const configScript = document.getElementById('api-config');
    if (configScript && configScript.dataset.apiUrl) {
        const url = configScript.dataset.apiUrl;
        console.log('[API Config] Using URL from script tag:', url);
        return url;
    }
    
    // Fallback to localhost for local development
    const localhostUrl = 'http://localhost:5000/api';
    console.log('[API Config] Using localhost backend URL:', localhostUrl);
    return localhostUrl;
};

// Make function globally accessible for use in other JS files
window.getApiBaseUrl = getApiBaseUrl;

const API_BASE_URL = getApiBaseUrl();
// Make API_BASE_URL globally accessible for use in other JS files
window.API_BASE_URL = API_BASE_URL;

// Log the API base URL for debugging
console.log('[API Config] API_BASE_URL initialized:', API_BASE_URL);

// ================= Auth State =================

let authToken = localStorage.getItem('authToken') || '';
let currentUser = null;
try {
    const userStr = localStorage.getItem('currentUser');
    if (userStr && userStr !== 'null') {
        currentUser = JSON.parse(userStr);
    }
} catch (e) {
    console.warn('[API] Failed to parse currentUser from localStorage:', e);
    localStorage.removeItem('currentUser'); // Remove invalid data
}

// ================= API Helper =================

function clearAuthState() {
    authToken = '';
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('token');
    localStorage.removeItem('user');

    if (window.tokenManager) {
        window.tokenManager.clearTokens();
        if (typeof window.tokenManager.stopAutoRefresh === 'function') {
            window.tokenManager.stopAutoRefresh();
        }
    }

    window.authToken = '';
    window.currentUser = null;

    if (typeof updateState === 'function') {
        updateState('auth', {
            isAuthenticated: false,
            user: null,
            token: ''
        }, true);
    }
}

function getStoredAccessToken() {
    if (window.tokenManager) {
        const managedToken = window.tokenManager.getAccessToken();
        if (managedToken) {
            authToken = managedToken;
            return managedToken;
        }
    }

    const storedToken = localStorage.getItem('authToken') || localStorage.getItem('token') || '';
    authToken = storedToken;
    return storedToken;
}

async function apiRequest(endpoint, options = {}) {
    // Use API base URL from configuration
    let baseUrl = API_BASE_URL || getApiBaseUrl();
    
    // Ensure baseUrl is set
    if (!baseUrl) {
        baseUrl = 'http://localhost:5000/api';
        console.warn('[API Config] No base URL found, using localhost:', baseUrl);
    }
    
    const url = `${baseUrl}${endpoint}`;
    
    // Log for debugging
    console.log('[API Request]', options.method || 'GET', url);

    // Add timeout to prevent hanging requests (30 seconds default)
    const timeout = options.timeout || 30000;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const shouldRetryAuth = options._retryAuth !== false;
    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        signal: controller.signal,
        ...options
    };

    // Remove timeout from options to avoid passing it to fetch
    delete config.timeout;
    delete config._retryAuth;

    const token = getStoredAccessToken();
    if (token) {
        config.headers['Authorization'] = `Bearer ${authToken}`;
    }

    try {
        const response = await fetch(url, config);
        clearTimeout(timeoutId);
        
        console.log('[API Response]', response.status, response.statusText, url);
        
        // Check if response is JSON
        let data;
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            const text = await response.text();
            throw new Error(text || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        if (response.status === 401 && shouldRetryAuth && window.tokenManager && window.tokenManager.getRefreshToken()) {
            try {
                const refreshed = await window.tokenManager.refreshAccessToken();
                const newToken = refreshed ? window.tokenManager.getAccessToken() : '';
                if (newToken) {
                    authToken = newToken;
                    localStorage.setItem('authToken', newToken);
                    return apiRequest(endpoint, {
                        ...options,
                        headers: {
                            ...options.headers,
                            Authorization: `Bearer ${newToken}`
                        },
                        _retryAuth: false
                    });
                }
            } catch (refreshError) {
                console.warn('[API Auth] Token refresh failed after 401:', refreshError);
            }

            clearAuthState();
        } else if (response.status === 401) {
            clearAuthState();
        }

        // Update UI state on error (fixes loading forever issue)
        if (!response.ok) {
            // Update state to clear loading
            if (typeof updateState === 'function') {
                updateState('ui', { 
                    loading: false, 
                    error: data.error || `HTTP ${response.status}: ${response.statusText}` 
                });
            }
            
            // Show error toast if available
            if (window.toastManager) {
                window.toastManager.error(
                    data.error || `Request failed: ${response.statusText}`,
                    'API Error'
                );
            }
            
            // Throw error for caller to handle
            const error = new Error(data.error || data.message || 'Request failed');
            error.status = response.status;
            error.data = data;
            throw error;
        } else {
            // Clear error on success
            if (typeof updateState === 'function') {
                updateState('ui', { error: null, loading: false }, true);
            }
        }

        return data;
    } catch (error) {
        clearTimeout(timeoutId);
        
        // Update UI state on error (fixes loading forever issue)
        if (typeof updateState === 'function') {
            updateState('ui', { 
                loading: false, 
                error: error.message || 'Request failed' 
            });
        }
        
        // Show error toast if available
        if (window.toastManager) {
            window.toastManager.error(
                error.message || 'Request failed. Please try again.',
                'API Error'
            );
        }
        
        // Handle timeout/abort errors
        if (error.name === 'AbortError') {
            const timeoutError = new Error(`Request timeout: The server did not respond within ${timeout/1000} seconds. Please check your connection and try again.`);
            timeoutError.originalError = error;
            console.error('[API Error] Request timeout:', url);
            throw timeoutError;
        }
        
        console.error('[API Error]', {
            url: url,
            method: options.method || 'GET',
            error: error.message,
            name: error.name,
            stack: error.stack
        });
        
        // Provide better error messages
        if (error.message === 'Failed to fetch' || error.name === 'TypeError') {
            const detailedError = new Error(`Cannot connect to backend server at ${url}. Please check:\n1. Backend is running on localhost:5000\n2. CORS is configured correctly\n3. Network connection is active`);
            detailedError.originalError = error;
            throw detailedError;
        }
        throw error;
    }
}

// ================= Auth API =================

const authAPI = {
    login: async (username, password, options = {}) => {
        const data = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
            timeout: options.timeout || 300000 // 30 seconds for login (increased for slow connections)
        });

        authToken = data.access_token;
        const refreshToken = data.refresh_token;
        currentUser = data.user;
        
        // Store tokens
        localStorage.setItem('authToken', authToken);
        if (refreshToken) {
            localStorage.setItem('refreshToken', refreshToken);
        }
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        
        // Expose to global scope for app.js to access
        window.authToken = authToken;
        window.currentUser = currentUser;
        
        // Initialize token manager if available
        if (window.tokenManager) {
            window.tokenManager.saveTokens(authToken, refreshToken);
        }

        console.log('[Auth] Login successful, tokens stored and exposed to global scope');
        return data;
    },

    register: async (username, first_name, last_name, reg_no, college_email, password, role, batch_id = null) => {
        const data = await apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ 
                username, 
                first_name, 
                last_name, 
                reg_no, 
                college_email, 
                password, 
                role,
                batch_id: batch_id ? parseInt(batch_id) : null
            })
        });

        authToken = data.access_token;
        const refreshToken = data.refresh_token;
        currentUser = data.user;
        
        // Store tokens
        localStorage.setItem('authToken', authToken);
        if (refreshToken) {
            localStorage.setItem('refreshToken', refreshToken);
        }
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        
        // Initialize token manager if available
        if (window.tokenManager) {
            window.tokenManager.saveTokens(authToken, refreshToken);
        }

        return data;
    },

    logout: () => {
        authToken = '';
        currentUser = null;
        localStorage.removeItem('authToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('currentUser');
        
        // Clear token manager
        if (window.tokenManager) {
            window.tokenManager.clearTokens();
            window.tokenManager.stopAutoRefresh();
        }
    },

    getCurrentUser: async () => {
        return await apiRequest('/auth/me');
    },

    getBatches: async () => {
        // This endpoint doesn't require authentication, so we need to make a direct fetch
        const baseUrl = API_BASE_URL || getApiBaseUrl();
        const url = `${baseUrl}/auth/batches`;
        
        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to fetch batches');
            }
            
            return await response.json();
        } catch (error) {
            console.error('[API Error] Failed to fetch batches:', error);
            throw error;
        }
    }
};

// ================= Student API =================

const studentAPI = {
    getDashboard: async () => apiRequest('/student/dashboard'),
    
    getPerformance: async () => apiRequest('/student/performance'),

    getQuestions: async (filters = {}) => {
        const params = new URLSearchParams(filters);
        return apiRequest(`/student/questions?${params}`);
    },

    getResources: async (filters = {}) => {
        const params = new URLSearchParams(filters);
        return apiRequest(`/student/resources?${params}`);
    },

    getPlacementReadiness: async (userId = null) => {
        const url = userId ? `/student/placement-readiness?user_id=${userId}` : '/student/placement-readiness';
        return apiRequest(url);
    },

    getProgressTrends: async (userId = null) => {
        const url = userId ? `/student/progress-trends?user_id=${userId}` : '/student/progress-trends';
        return apiRequest(url);
    },

    getDailyStreaks: async (userId = null) => {
        const url = userId ? `/student/daily-streaks?user_id=${userId}` : '/student/daily-streaks';
        return apiRequest(url);
    },
    
    chatWithAI: async (message) => {
        return apiRequest('/student/ai-chat', {
            method: 'POST',
            body: JSON.stringify({ message })
        });
    },
    
    // Assessment Management (Student)
    getAssessments: async () => {
        return apiRequest('/student/assessments');
    },
    
    getAssessment: async (assessmentId) => {
        return apiRequest(`/student/assessments/${assessmentId}`);
    },
    
    startAssessment: async (assessmentId) => {
        return apiRequest(`/student/assessments/${assessmentId}/start`, {
            method: 'POST'
        });
    },
    
    submitAssessment: async (assessmentId, answers) => {
        return apiRequest(`/student/assessments/${assessmentId}/submit`, {
            method: 'POST',
            body: JSON.stringify({ answers })
        });
    },
    
    getMyAttempts: async () => {
        return apiRequest('/student/assessments/attempts');
    },
    
    getMyAttempt: async (assessmentId) => {
        return apiRequest(`/student/assessments/${assessmentId}/attempt`);
    },
    
    getServerTime: async () => {
        return apiRequest('/student/server-time');
    }
};

// ================= Coding API =================

const codingAPI = {
    getQuestion: async (questionId) =>
        apiRequest(`/coding/questions/${questionId}`),

    executeCode: async (code, language, stdin = '', questionId = null) => {
        const body = { code, language, stdin };
        if (questionId) {
            body.question_id = questionId;
        }
        return apiRequest('/coding/execute', {
            method: 'POST',
            body: JSON.stringify(body)
        });
    },

    submitCode: async (questionId, code, language) =>
        apiRequest('/coding/submit', {
            method: 'POST',
            body: JSON.stringify({ question_id: questionId, code, language })
        }),

    getSubmissions: async (questionId = null) => {
        const params = questionId ? `?question_id=${questionId}` : '';
        return apiRequest(`/coding/submissions${params}`);
    },

    getLastSubmission: async (questionId, language = null) => {
        const params = new URLSearchParams({ question_id: questionId });
        if (language) {
            params.append('language', language);
        }
        return apiRequest(`/coding/submissions/last?${params}`);
    }
};

// ================= Quiz API =================

const quizAPI = {
    listQuizzes: async (filters = {}) => {
        const params = new URLSearchParams(filters);
        return apiRequest(`/quiz/list?${params}`);
    },

    getQuiz: async (quizId) => apiRequest(`/quiz/${quizId}`),

    attemptQuiz: async (quizId, answers) =>
        apiRequest(`/quiz/${quizId}/attempt`, {
            method: 'POST',
            body: JSON.stringify({ answers })
        }),

    getAttempts: async (quizId = null) => {
        const params = quizId ? `?quiz_id=${quizId}` : '';
        return apiRequest(`/quiz/attempts${params}`);
    }
};

// ================= Company API =================

const companyAPI = {
    listCompanies: async () => apiRequest('/admin/companies'),
    
    deleteCompany: async (companyId) => {
        return apiRequest(`/admin/companies/${companyId}`, {
            method: 'DELETE'
        });
    }
};

// ================= Resources API =================

const resourcesAPI = {
    uploadResource: async (formData) => {
        const url = `${API_BASE_URL}/resources/upload`;

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to upload resource');
        }

        return await response.json();
    },

    getResources: async (filters = {}) => {
        const params = new URLSearchParams(filters);
        return apiRequest(`/student/resources?${params}`);
    },

    deleteResource: async (resourceId) =>
        apiRequest(`/resources/${resourceId}`, { method: 'DELETE' })
};

// ================= Leaderboard API =================

const leaderboardAPI = {
    getTopUsers: async (limit = 100) =>
        apiRequest(`/leaderboard/top?limit=${limit}`),

    getMyRank: async () => apiRequest('/leaderboard/my-rank')
};

// ================= Notifications API =================

const notificationsAPI = {
    getNotifications: async (isRead = null) => {
        const params = isRead !== null ? `?is_read=${isRead}` : '';
        return apiRequest(`/notifications${params}`);
    },

    markAsRead: async (notificationId) =>
        apiRequest(`/notifications/${notificationId}/read`, { method: 'PUT' }),

    markAllAsRead: async () =>
        apiRequest('/notifications/read-all', { method: 'PUT' }),

    getUnreadCount: async () =>
        apiRequest('/notifications/unread-count')
};

// ================= Interview API =================

const interviewAPI = {
    selectInterviewType: async (interviewType) => {
        return apiRequest('/interview/select-interview-type', {
            method: 'POST',
            body: JSON.stringify({ interview_type: interviewType })
        });
    },
    
    getSessionState: async (sessionId) => {
        // Get interview session state for rehydration
        try {
            const session = await apiRequest(`/interview/session/${sessionId}`);
            return {
                session_id: sessionId,
                interview_state: session.interview_state || session.interview_memory,
                conversation: session.conversation,
                question_number: session.question_number,
                total_questions: session.total_questions
            };
        } catch (error) {
            console.error('[InterviewAPI] Error getting session state:', error);
            return null;
        }
    },

    uploadResume: async (file) => {
        const url = `${API_BASE_URL}/interview/upload-resume`;
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to upload resume');
        }
        
        return await response.json();
    },

    uploadJD: async (file, resumeSkills = null) => {
        const url = `${API_BASE_URL}/interview/upload-jd`;
        const formData = new FormData();
        formData.append('file', file);
        if (resumeSkills) {
            formData.append('resume_skills', JSON.stringify(resumeSkills));
        }
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to upload job description');
        }
        
        return await response.json();
    },

    startInterview: async (data) => {
        return apiRequest('/interview/start-interview', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    getSessionState: async (sessionId) => {
        // Get interview session state for rehydration
        try {
            const session = await apiRequest(`/interview/session/${sessionId}`);
            return {
                session_id: sessionId,
                interview_state: session.interview_state || session.interview_memory,
                conversation: session.conversation,
                question_number: session.question_number,
                total_questions: session.total_questions
            };
        } catch (error) {
            console.error('[InterviewAPI] Error getting session state:', error);
            // Try alternative endpoint
            try {
                const session = await apiRequest(`/interview/sessions/${sessionId}`);
                return {
                    session_id: sessionId,
                    interview_state: session.interview_state || session.interview_memory,
                    conversation: session.conversation,
                    question_number: session.question_number,
                    total_questions: session.total_questions
                };
            } catch (e) {
                console.error('[InterviewAPI] Alternative endpoint also failed:', e);
                return null;
            }
        }
    },

    submitAnswer: async (sessionId, answer, timeTakenSeconds = 0) => {
        return apiRequest('/interview/submit-answer', {
            method: 'POST',
            body: JSON.stringify({ 
                session_id: sessionId, 
                answer: answer,
                time_taken_seconds: timeTakenSeconds
            })
        });
    },

    endInterview: async (sessionId) => {
        return apiRequest(`/interview/end-interview/${sessionId}`, {
            method: 'POST'
        });
    },

    getInterviewResult: async (sessionId) => {
        return apiRequest(`/interview/interview-result/${sessionId}`);
    },

    getSession: async (sessionId) => {
        return apiRequest(`/interview/session/${sessionId}`);
    },

    getPracticeRecommendations: async (sessionId) => {
        return apiRequest(`/interview/practice-recommendations/${sessionId}`);
    }
};

// ================= Chatbot API (Legacy) =================

const chatbotAPI = {
    startInterview: async (resumeText, jobDescription, interviewType = 'technical', experienceLevel = 'fresher', totalQuestions = 5) => {
        return apiRequest('/chatbot/start-interview', {
            method: 'POST',
            body: JSON.stringify({ 
                resume_text: resumeText, 
                job_description: jobDescription,
                interview_type: interviewType,
                experience_level: experienceLevel,
                total_questions: totalQuestions
            })
        });
    },

    submitAnswer: async (sessionId, answer) =>
        apiRequest('/chatbot/answer', {
            method: 'POST',
            body: JSON.stringify({ session_id: sessionId, answer })
        }),

    getSession: async (sessionId) =>
        apiRequest(`/chatbot/session/${sessionId}`),

    endInterview: async (sessionId) =>
        apiRequest(`/chatbot/end-interview/${sessionId}`, { method: 'POST' }),

    extractText: async (file) => {
        const url = `${API_BASE_URL}/chatbot/extract-text`;
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to extract text');
        }
        
        return await response.json();
    }
};

// ================= Faculty API =================

const facultyAPI = {
    getDashboard: async () => apiRequest('/faculty/dashboard'),
    
    getStudentPerformance: async (studentId = null) => {
        const url = studentId ? `/faculty/students/performance?student_id=${studentId}` : '/faculty/students/performance';
        return apiRequest(url);
    },

    getStudentDetails: async (studentId) => {
        return apiRequest(`/faculty/students/${studentId}/details`);
    },

    provideFeedback: async (feedbackData) => {
        return apiRequest('/faculty/feedback', {
            method: 'POST',
            body: JSON.stringify(feedbackData)
        });
    },

    exportStudentPerformancePDF: async () => {
        const token = localStorage.getItem('authToken');
        const response = await fetch(`${API_BASE_URL}/faculty/export/student-performance/pdf`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to export PDF');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `student_performance_report_${new Date().toISOString().slice(0, 10)}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    },

    exportBatchAnalyticsCSV: async () => {
        const token = localStorage.getItem('authToken');
        const response = await fetch(`${API_BASE_URL}/faculty/export/batch-analytics/csv`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to export CSV');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `batch_analytics_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    },

    createQuestion: async (question) => {
        return apiRequest('/faculty/questions', {
            method: 'POST',
            body: JSON.stringify(question)
        });
    },

    createQuiz: async (quiz) => {
        return apiRequest('/quiz/quizzes', {
            method: 'POST',
            body: JSON.stringify(quiz)
        });
    },

    deleteQuiz: async (quizId) => {
        return apiRequest(`/quiz/quizzes/${quizId}`, {
            method: 'DELETE'
        });
    },


    // Assessment Management
    createQuestion: async (questionData) => {
        return apiRequest('/faculty/questions', {
            method: 'POST',
            body: JSON.stringify(questionData)
        });
    },
    
    // Assessment Management (Faculty/Admin Only)
    getAssessments: async () => {
        return apiRequest('/faculty/assessments');
    },
    
    createAssessment: async (assessmentData) => {
        return apiRequest('/faculty/assessments', {
            method: 'POST',
            body: JSON.stringify(assessmentData)
        });
    },
    
    getAssessment: async (assessmentId) => {
        return apiRequest(`/faculty/assessments/${assessmentId}`);
    },
    
    updateAssessment: async (assessmentId, assessmentData) => {
        return apiRequest(`/faculty/assessments/${assessmentId}`, {
            method: 'PUT',
            body: JSON.stringify(assessmentData)
        });
    },
    
    deleteAssessment: async (assessmentId) => {
        return apiRequest(`/faculty/assessments/${assessmentId}`, {
            method: 'DELETE'
        });
    },
    
    getAssessmentAttempts: async (assessmentId) => {
        return apiRequest(`/faculty/assessments/${assessmentId}/attempts`);
    },
    
    addQuestionToAssessment: async (assessmentId, questionData) => {
        return apiRequest(`/faculty/assessments/${assessmentId}/questions`, {
            method: 'POST',
            body: JSON.stringify(questionData)
        });
    },
    
    removeQuestionFromAssessment: async (assessmentId, questionId) => {
        return apiRequest(`/faculty/assessments/${assessmentId}/questions/${questionId}`, {
            method: 'DELETE'
        });
    },
    
    reorderAssessmentQuestions: async (assessmentId, questionOrders) => {
        return apiRequest(`/faculty/assessments/${assessmentId}/questions/reorder`, {
            method: 'POST',
            body: JSON.stringify({ question_orders: questionOrders })
        });
    },
    
    publishAssessment: async (assessmentId) => {
        return apiRequest(`/faculty/assessments/${assessmentId}/publish`, {
            method: 'POST'
        });
    },
    
    getQuestion: async (questionId) => {
        return apiRequest(`/student/questions?question_id=${questionId}`);
    },
    
    updateQuestion: async (questionId, questionData) => {
        return apiRequest(`/faculty/questions/${questionId}`, {
            method: 'PUT',
            body: JSON.stringify(questionData)
        });
    },


    // Code Evaluation
    evaluateSubmission: async (submissionId, comment) => {
        return apiRequest(`/faculty/submissions/${submissionId}/evaluate`, {
            method: 'POST',
            body: JSON.stringify({ comment })
        });
    },

    // Delete Question
    deleteQuestion: async (questionId) => {
        return apiRequest(`/faculty/questions/${questionId}`, {
            method: 'DELETE'
        });
    }
};

// ================= Admin API =================

const adminAPI = {
    getDashboard: async () => apiRequest('/admin/dashboard'),
    
    getUsers: async (role = null, isActive = null) => {
        const params = new URLSearchParams();
        if (role) params.append('role', role);
        if (isActive !== null) params.append('is_active', isActive);
        const url = params.toString() ? `/admin/users?${params}` : '/admin/users';
        return apiRequest(url);
    },

    updateUser: async (userId, data) => {
        return apiRequest(`/admin/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    deleteUser: async (userId) => {
        return apiRequest(`/admin/users/${userId}`, {
            method: 'DELETE'
        });
    },

    // Faculty Management
    getFaculty: async () => {
        return apiRequest('/admin/faculty');
    },

    updateFaculty: async (facultyId, data) => {
        return apiRequest(`/admin/faculty/${facultyId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    // Activity Logs (Admin has full access)
    getActivityLogs: async (filters = {}) => {
        const params = new URLSearchParams();
        if (filters.activity_type) params.append('activity_type', filters.activity_type);
        if (filters.entity_type) params.append('entity_type', filters.entity_type);
        if (filters.page) params.append('page', filters.page);
        if (filters.per_page) params.append('per_page', filters.per_page);
        const url = params.toString() ? `/admin/activity-logs?${params}` : '/admin/activity-logs';
        return apiRequest(url);
    }
};

// ================= Posts API =================

const postsAPI = {
    createPost: async (formData) => {
        const url = `${API_BASE_URL}/posts`;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to create post');
        }
        
        return await response.json();
    },

    getPosts: async (filters = {}) => {
        const params = new URLSearchParams(filters);
        const url = params.toString() ? `/posts?${params}` : '/posts';
        return apiRequest(url);
    },

    getPost: async (postId) => apiRequest(`/posts/${postId}`),

    deletePost: async (postId) => {
        return apiRequest(`/posts/${postId}`, {
            method: 'DELETE'
        });
    }
};
