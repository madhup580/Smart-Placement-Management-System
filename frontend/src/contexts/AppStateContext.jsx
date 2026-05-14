/**
 * AppStateContext - Centralized State Management using React Context API
 * Single source of truth for application state
 * Replaces fragile state_manager.js with React's built-in state management
 */
import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react'

// Initial state
const initialState = {
  // Authentication
  auth: {
    isAuthenticated: false,
    user: null,
    token: null,
    loading: false,
    error: null,
  },
  
  // Navigation
  navigation: {
    currentPage: 'dashboard',
    previousPage: null,
    params: {},
  },
  
  // UI State
  ui: {
    loading: false,
    error: null,
    modals: {
      active: null,
      data: null,
    },
  },
  
  // Page Data
  pages: {
    dashboard: { loaded: false, data: null },
    coding: { loaded: false, data: null, currentQuestion: null },
    quizzes: { loaded: false, data: null },
    'non-technical': { loaded: false, data: null },
    companies: { loaded: false, data: null },
    resources: { loaded: false, data: null },
    leaderboard: { loaded: false, data: null },
    chatbot: { loaded: false, data: null },
  },
  
  // Application Data
  data: {
    companies: [],
    questions: [],
    codingQuestions: [],
    currentQuestion: null,
    currentQuiz: null,
    currentInterview: {
      sessionId: null,
      state: null,
      lastUpdated: null,
    },
  },
}

// Action types
const ActionTypes = {
  // Auth actions
  AUTH_LOGIN_START: 'AUTH_LOGIN_START',
  AUTH_LOGIN_SUCCESS: 'AUTH_LOGIN_SUCCESS',
  AUTH_LOGIN_FAILURE: 'AUTH_LOGIN_FAILURE',
  AUTH_LOGOUT: 'AUTH_LOGOUT',
  AUTH_UPDATE_USER: 'AUTH_UPDATE_USER',
  
  // Navigation actions
  NAVIGATE: 'NAVIGATE',
  NAVIGATE_BACK: 'NAVIGATE_BACK',
  
  // UI actions
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  CLEAR_ERROR: 'CLEAR_ERROR',
  SHOW_MODAL: 'SHOW_MODAL',
  HIDE_MODAL: 'HIDE_MODAL',
  
  // Data actions
  SET_PAGE_DATA: 'SET_PAGE_DATA',
  UPDATE_DATA: 'UPDATE_DATA',
  SET_INTERVIEW_STATE: 'SET_INTERVIEW_STATE',
}

// Reducer function
function appStateReducer(state, action) {
  switch (action.type) {
    // Auth reducers
    case ActionTypes.AUTH_LOGIN_START:
      return {
        ...state,
        auth: {
          ...state.auth,
          loading: true,
          error: null,
        },
      }
    
    case ActionTypes.AUTH_LOGIN_SUCCESS:
      return {
        ...state,
        auth: {
          isAuthenticated: true,
          user: action.payload.user,
          token: action.payload.token,
          loading: false,
          error: null,
        },
      }
    
    case ActionTypes.AUTH_LOGIN_FAILURE:
      return {
        ...state,
        auth: {
          ...state.auth,
          loading: false,
          error: action.payload,
        },
      }
    
    case ActionTypes.AUTH_LOGOUT:
      return {
        ...state,
        auth: {
          isAuthenticated: false,
          user: null,
          token: null,
          loading: false,
          error: null,
        },
      }
    
    case ActionTypes.AUTH_UPDATE_USER:
      return {
        ...state,
        auth: {
          ...state.auth,
          user: { ...state.auth.user, ...action.payload },
        },
      }
    
    // Navigation reducers
    case ActionTypes.NAVIGATE:
      return {
        ...state,
        navigation: {
          previousPage: state.navigation.currentPage,
          currentPage: action.payload.page,
          params: action.payload.params || {},
        },
      }
    
    case ActionTypes.NAVIGATE_BACK:
      return {
        ...state,
        navigation: {
          ...state.navigation,
          currentPage: state.navigation.previousPage || 'dashboard',
          previousPage: state.navigation.currentPage,
        },
      }
    
    // UI reducers
    case ActionTypes.SET_LOADING:
      return {
        ...state,
        ui: {
          ...state.ui,
          loading: action.payload,
        },
      }
    
    case ActionTypes.SET_ERROR:
      return {
        ...state,
        ui: {
          ...state.ui,
          error: action.payload,
          loading: false,
        },
      }
    
    case ActionTypes.CLEAR_ERROR:
      return {
        ...state,
        ui: {
          ...state.ui,
          error: null,
        },
      }
    
    case ActionTypes.SHOW_MODAL:
      return {
        ...state,
        ui: {
          ...state.ui,
          modals: {
            active: action.payload.type,
            data: action.payload.data,
          },
        },
      }
    
    case ActionTypes.HIDE_MODAL:
      return {
        ...state,
        ui: {
          ...state.ui,
          modals: {
            active: null,
            data: null,
          },
        },
      }
    
    // Data reducers
    case ActionTypes.SET_PAGE_DATA:
      return {
        ...state,
        pages: {
          ...state.pages,
          [action.payload.page]: {
            loaded: true,
            data: action.payload.data,
            ...action.payload.extra,
          },
        },
      }
    
    case ActionTypes.UPDATE_DATA:
      return {
        ...state,
        data: {
          ...state.data,
          ...action.payload,
        },
      }
    
    case ActionTypes.SET_INTERVIEW_STATE:
      return {
        ...state,
        data: {
          ...state.data,
          currentInterview: {
            sessionId: action.payload.sessionId,
            state: action.payload.state,
            lastUpdated: new Date().toISOString(),
          },
        },
      }
    
    default:
      return state
  }
}

// Create context
const AppStateContext = createContext(null)

// Provider component
export function AppStateProvider({ children }) {
  const [state, dispatch] = useReducer(appStateReducer, initialState)
  
  // Initialize from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('authToken')
    const storedUser = localStorage.getItem('currentUser')
    
    if (storedToken && storedUser) {
      try {
        const user = JSON.parse(storedUser)
        fetch('/api/v1/auth/me', {
          headers: {
            Authorization: `Bearer ${storedToken}`,
          },
        })
          .then(async (response) => {
            if (!response.ok) {
              throw new Error('Stored login is no longer valid')
            }
            return response.json()
          })
          .then((data) => {
            const currentUser = data.user || user
            localStorage.setItem('currentUser', JSON.stringify(currentUser))
            dispatch({
              type: ActionTypes.AUTH_LOGIN_SUCCESS,
              payload: {
                user: currentUser,
                token: storedToken,
              },
            })
          })
          .catch((e) => {
            console.warn('[AppState] Clearing stale auth from localStorage:', e.message)
            localStorage.removeItem('authToken')
            localStorage.removeItem('refreshToken')
            localStorage.removeItem('currentUser')
            dispatch({ type: ActionTypes.AUTH_LOGOUT })
          })
      } catch (e) {
        console.error('[AppState] Failed to restore auth from localStorage:', e)
        localStorage.removeItem('authToken')
        localStorage.removeItem('refreshToken')
        localStorage.removeItem('currentUser')
      }
    }
  }, [])
  
  // Action creators
  const actions = {
    // Auth actions
    loginStart: useCallback(() => {
      dispatch({ type: ActionTypes.AUTH_LOGIN_START })
    }, []),
    
    loginSuccess: useCallback((user, token) => {
      localStorage.setItem('authToken', token)
      localStorage.setItem('currentUser', JSON.stringify(user))
      dispatch({
        type: ActionTypes.AUTH_LOGIN_SUCCESS,
        payload: { user, token },
      })
    }, []),
    
    loginFailure: useCallback((error) => {
      dispatch({
        type: ActionTypes.AUTH_LOGIN_FAILURE,
        payload: error,
      })
    }, []),
    
    logout: useCallback(() => {
      localStorage.removeItem('authToken')
      localStorage.removeItem('currentUser')
      localStorage.removeItem('refreshToken')
      dispatch({ type: ActionTypes.AUTH_LOGOUT })
    }, []),
    
    updateUser: useCallback((userData) => {
      dispatch({
        type: ActionTypes.AUTH_UPDATE_USER,
        payload: userData,
      })
    }, []),
    
    // Navigation actions
    navigate: useCallback((page, params = {}) => {
      dispatch({
        type: ActionTypes.NAVIGATE,
        payload: { page, params },
      })
    }, []),
    
    navigateBack: useCallback(() => {
      dispatch({ type: ActionTypes.NAVIGATE_BACK })
    }, []),
    
    // UI actions
    setLoading: useCallback((loading) => {
      dispatch({
        type: ActionTypes.SET_LOADING,
        payload: loading,
      })
    }, []),
    
    setError: useCallback((error) => {
      dispatch({
        type: ActionTypes.SET_ERROR,
        payload: error,
      })
    }, []),
    
    clearError: useCallback(() => {
      dispatch({ type: ActionTypes.CLEAR_ERROR })
    }, []),
    
    showModal: useCallback((type, data = null) => {
      dispatch({
        type: ActionTypes.SHOW_MODAL,
        payload: { type, data },
      })
    }, []),
    
    hideModal: useCallback(() => {
      dispatch({ type: ActionTypes.HIDE_MODAL })
    }, []),
    
    // Data actions
    setPageData: useCallback((page, data, extra = {}) => {
      dispatch({
        type: ActionTypes.SET_PAGE_DATA,
        payload: { page, data, extra },
      })
    }, []),
    
    updateData: useCallback((data) => {
      dispatch({
        type: ActionTypes.UPDATE_DATA,
        payload: data,
      })
    }, []),
    
    setInterviewState: useCallback((sessionId, state) => {
      dispatch({
        type: ActionTypes.SET_INTERVIEW_STATE,
        payload: { sessionId, state },
      })
    }, []),
  }
  
  const value = {
    state,
    actions,
  }
  
  return (
    <AppStateContext.Provider value={value}>
      {children}
    </AppStateContext.Provider>
  )
}

// Custom hook to use app state
export function useAppState() {
  const context = useContext(AppStateContext)
  if (!context) {
    throw new Error('useAppState must be used within AppStateProvider')
  }
  return context
}

// Selector hooks for specific state slices
export function useAuth() {
  const { state, actions } = useAppState()
  return {
    auth: state.auth,
    ...actions,
  }
}

export function useNavigation() {
  const { state, actions } = useAppState()
  return {
    navigation: state.navigation,
    navigate: actions.navigate,
    navigateBack: actions.navigateBack,
  }
}

export function useUI() {
  const { state, actions } = useAppState()
  return {
    ui: state.ui,
    setLoading: actions.setLoading,
    setError: actions.setError,
    clearError: actions.clearError,
    showModal: actions.showModal,
    hideModal: actions.hideModal,
  }
}

export function useInterviewState() {
  const { state, actions } = useAppState()
  return {
    interview: state.data.currentInterview,
    setInterviewState: actions.setInterviewState,
  }
}
