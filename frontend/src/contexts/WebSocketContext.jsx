/**
 * WebSocketContext - WebSocket connection with state rehydration
 * Handles reconnection and state restoration from backend
 */
import React, { createContext, useContext, useEffect, useRef, useCallback, useState } from 'react'
import { io } from 'socket.io-client'
import { useAppState } from './AppStateContext'
import { interviewAPI } from '../services/api'

const WebSocketContext = createContext(null)

export function WebSocketProvider({ children }) {
  const { setInterviewState } = useAppState()
  const socketRef = useRef(null)
  const [isConnected, setIsConnected] = useState(false)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const sessionIdRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  
  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_DELAY = 3000
  
  /**
   * Rehydrate interview state from backend
   */
  const rehydrateInterviewState = useCallback(async (sessionId) => {
    if (!sessionId) return
    
    try {
      console.log('[WebSocket] Rehydrating interview state for session:', sessionId)
      
      // Call backend API to get interview state
      const state = await interviewAPI.getSessionState(sessionId)
      
      if (state && state.interview_state) {
        const interviewState = typeof state.interview_state === 'string'
          ? JSON.parse(state.interview_state)
          : state.interview_state
        
        // Update app state with rehydrated interview state
        setInterviewState(sessionId, interviewState)
        
        console.log('[WebSocket] ✅ Interview state rehydrated from backend')
        return interviewState
      }
    } catch (error) {
      console.error('[WebSocket] Error rehydrating interview state:', error)
      
      // Fallback: Try localStorage
      try {
        const savedState = localStorage.getItem(`interview_state_${sessionId}`)
        if (savedState) {
          const interviewState = JSON.parse(savedState)
          setInterviewState(sessionId, interviewState)
          console.log('[WebSocket] ✅ Interview state rehydrated from localStorage')
          return interviewState
        }
      } catch (e) {
        console.error('[WebSocket] Error loading from localStorage:', e)
      }
    }
    
    return null
  }, [setInterviewState])
  
  /**
   * Save interview state to localStorage before disconnect
   */
  const saveInterviewState = useCallback((sessionId, state) => {
    if (sessionId && state) {
      try {
        localStorage.setItem(
          `interview_state_${sessionId}`,
          JSON.stringify(state)
        )
        console.log('[WebSocket] Interview state saved to localStorage')
      } catch (error) {
        console.error('[WebSocket] Error saving to localStorage:', error)
      }
    }
  }, [])
  
  /**
   * Initialize WebSocket connection
   */
  const connect = useCallback((sessionId) => {
    if (socketRef.current && socketRef.current.connected) {
      console.log('[WebSocket] Already connected')
      return
    }
    
    if (socketRef.current) {
      socketRef.current.disconnect()
    }
    
    sessionIdRef.current = sessionId
    
    try {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsHost = window.location.hostname
      const wsPort = window.location.port || (wsProtocol === 'wss:' ? '443' : '5000')
      const wsUrl = `${wsProtocol}//${wsHost}:${wsPort}`
      
      console.log('[WebSocket] Connecting to:', wsUrl)
      
      socketRef.current = io(wsUrl, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
        timeout: 200000,
      })
      
      // Connection events
      socketRef.current.on('connect', async () => {
        console.log('[WebSocket] ✅ Connected')
        setIsConnected(true)
        setReconnectAttempts(0)
        
        // Join session room
        if (sessionId) {
          socketRef.current.emit('join_session', { session_id: sessionId })
          
          // Rehydrate interview state on connect
          await rehydrateInterviewState(sessionId)
        }
      })
      
      socketRef.current.on('disconnect', (reason) => {
        console.log('[WebSocket] ❌ Disconnected:', reason)
        setIsConnected(false)
        
        // Save current interview state before disconnect
        if (sessionIdRef.current) {
          const currentState = JSON.parse(
            localStorage.getItem(`interview_state_${sessionIdRef.current}`) || 'null'
          )
          if (currentState) {
            saveInterviewState(sessionIdRef.current, currentState)
          }
        }
        
        // Attempt reconnection if not intentional
        if (reason === 'io server disconnect') {
          // Server disconnected, try to reconnect
          if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectTimeoutRef.current = setTimeout(() => {
              setReconnectAttempts(prev => prev + 1)
              connect(sessionIdRef.current)
            }, RECONNECT_DELAY)
          }
        }
      })
      
      socketRef.current.on('reconnect', async (attemptNumber) => {
        console.log('[WebSocket] 🔄 Reconnected after', attemptNumber, 'attempts')
        setIsConnected(true)
        setReconnectAttempts(0)
        
        // Rejoin session and rehydrate state
        if (sessionIdRef.current) {
          socketRef.current.emit('join_session', { session_id: sessionIdRef.current })
          await rehydrateInterviewState(sessionIdRef.current)
        }
      })
      
      socketRef.current.on('connect_error', (error) => {
        console.error('[WebSocket] Connection error:', error)
        setIsConnected(false)
      })
      
      // Interview state events
      socketRef.current.on('interview_status', async (data) => {
        console.log('[WebSocket] Interview status update:', data)
        
        if (data.session_id && data.interview_state) {
          const interviewState = typeof data.interview_state === 'string'
            ? JSON.parse(data.interview_state)
            : data.interview_state
          
          // Update app state
          setInterviewState(data.session_id, interviewState)
          
          // Save to localStorage
          saveInterviewState(data.session_id, interviewState)
        }
      })
      
      socketRef.current.on('proctoring_status', (data) => {
        console.log('[WebSocket] Proctoring status:', data)
        // Handle proctoring status updates
      })
      
      socketRef.current.on('proctoring_warning', (data) => {
        console.log('[WebSocket] Proctoring warning:', data)
        // Handle proctoring warnings
      })
      
    } catch (error) {
      console.error('[WebSocket] Initialization error:', error)
      setIsConnected(false)
    }
  }, [rehydrateInterviewState, saveInterviewState, reconnectAttempts])
  
  /**
   * Disconnect WebSocket
   */
  const disconnect = useCallback(() => {
    if (socketRef.current) {
      // Save state before disconnect
      if (sessionIdRef.current) {
        const currentState = JSON.parse(
          localStorage.getItem(`interview_state_${sessionIdRef.current}`) || 'null'
        )
        if (currentState) {
          saveInterviewState(sessionIdRef.current, currentState)
        }
      }
      
      socketRef.current.disconnect()
      socketRef.current = null
      setIsConnected(false)
      sessionIdRef.current = null
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
  }, [saveInterviewState])
  
  /**
   * Emit event to server
   */
  const emit = useCallback((event, data) => {
    if (socketRef.current && socketRef.current.connected) {
      socketRef.current.emit(event, data)
    } else {
      console.warn('[WebSocket] Cannot emit - not connected')
    }
  }, [])
  
  /**
   * Listen to event from server
   */
  const on = useCallback((event, callback) => {
    if (socketRef.current) {
      socketRef.current.on(event, callback)
      
      // Return cleanup function
      return () => {
        if (socketRef.current) {
          socketRef.current.off(event, callback)
        }
      }
    }
  }, [])
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])
  
  const value = {
    isConnected,
    connect,
    disconnect,
    emit,
    on,
    rehydrateInterviewState,
  }
  
  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  )
}

// Custom hook to use WebSocket
export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider')
  }
  return context
}
