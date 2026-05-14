/**
 * WebSocket Client for Live Proctoring Status
 * Connects to backend WebSocket server for real-time updates
 */

let socket = null;
let isConnected = false;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000; // 3 seconds

// WebSocket event handlers
const eventHandlers = {
    proctoring_status: [],
    proctoring_warning: [],
    interview_status: []
};

/**
 * Initialize WebSocket connection
 */
function initWebSocket(sessionId) {
    if (socket && isConnected) {
        console.log('[WebSocket] Already connected');
        return;
    }
    
    try {
        // Get WebSocket URL from config
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsHost = window.location.hostname;
        const wsPort = window.location.port || (wsProtocol === 'wss:' ? '443' : '5000');
        const wsUrl = `${wsProtocol}//${wsHost}:${wsPort}`;
        
        console.log('[WebSocket] Connecting to:', wsUrl);
        
        // Try to use Socket.IO if available, otherwise fallback to native WebSocket
        if (typeof io !== 'undefined') {
            socket = io(wsUrl, {
                transports: ['websocket', 'polling'],
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionAttempts: MAX_RECONNECT_ATTEMPTS
            });
            
            socket.on('connect', () => {
                console.log('[WebSocket] ✅ Connected');
                isConnected = true;
                reconnectAttempts = 0;
                
                // Join session room
                if (sessionId) {
                    socket.emit('join_session', { session_id: sessionId });
                    
                    // Rehydrate interview state from backend on reconnect
                    rehydrateInterviewState(sessionId);
                }
            });
            
            socket.on('disconnect', () => {
                console.log('[WebSocket] ❌ Disconnected');
                isConnected = false;
                
                // Save current interview state before disconnect
                if (sessionId) {
                    saveInterviewStateToLocalStorage(sessionId);
                }
            });
            
            socket.on('reconnect', () => {
                console.log('[WebSocket] 🔄 Reconnected');
                isConnected = true;
                
                // Rejoin session and rehydrate state
                if (sessionId) {
                    socket.emit('join_session', { session_id: sessionId });
                    rehydrateInterviewState(sessionId);
                }
            });
            
            socket.on('proctoring_status', (data) => {
                console.log('[WebSocket] Proctoring status:', data);
                eventHandlers.proctoring_status.forEach(handler => {
                    try {
                        handler(data);
                    } catch (e) {
                        console.error('[WebSocket] Error in status handler:', e);
                    }
                });
            });
            
            socket.on('proctoring_warning', (data) => {
                console.log('[WebSocket] Proctoring warning:', data);
                eventHandlers.proctoring_warning.forEach(handler => {
                    try {
                        handler(data);
                    } catch (e) {
                        console.error('[WebSocket] Error in warning handler:', e);
                    }
                });
            });
            
            socket.on('interview_status', (data) => {
                console.log('[WebSocket] Interview status:', data);
                
                // Update interview state from backend (rehydration)
                if (data.session_id && data.interview_state) {
                    try {
                        const interviewState = typeof data.interview_state === 'string' 
                            ? JSON.parse(data.interview_state) 
                            : data.interview_state;
                        
                        // Update state manager if available
                        if (typeof updateState === 'function') {
                            updateState('data', {
                                currentInterview: {
                                    sessionId: data.session_id,
                                    state: interviewState,
                                    lastUpdated: new Date().toISOString()
                                }
                            }, true);
                        }
                        
                        // Save to localStorage for persistence
                        localStorage.setItem(`interview_state_${data.session_id}`, JSON.stringify(interviewState));
                        
                        console.log('[WebSocket] Interview state rehydrated from backend');
                    } catch (e) {
                        console.error('[WebSocket] Error parsing interview state:', e);
                    }
                }
                
                eventHandlers.interview_status.forEach(handler => {
                    try {
                        handler(data);
                    } catch (e) {
                        console.error('[WebSocket] Error in interview status handler:', e);
                    }
                });
            });
            
            socket.on('connect_error', (error) => {
                console.error('[WebSocket] Connection error:', error);
                isConnected = false;
            });
        } else {
            console.warn('[WebSocket] Socket.IO not available. Install: npm install socket.io-client');
            // Fallback: Use polling via API instead
            startStatusPolling(sessionId);
        }
    } catch (error) {
        console.error('[WebSocket] Initialization error:', error);
        // Fallback: Use polling via API instead
        startStatusPolling(sessionId);
    }
}

/**
 * Fallback: Poll status via REST API
 */
let pollingInterval = null;

function startStatusPolling(sessionId) {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    
    console.log('[WebSocket] Using polling fallback for session:', sessionId);
    
    // Poll every 2 seconds
    pollingInterval = setInterval(() => {
        // Status polling would be handled by individual detection modules
        // This is just a placeholder
    }, 2000);
}

function stopStatusPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

/**
 * Disconnect WebSocket
 */
function disconnectWebSocket() {
    if (socket) {
        if (socket.disconnect) {
            socket.disconnect();
        } else if (socket.close) {
            socket.close();
        }
        socket = null;
        isConnected = false;
    }
    stopStatusPolling();
}

/**
 * Register event handler
 */
function onProctoringStatus(handler) {
    eventHandlers.proctoring_status.push(handler);
}

function onProctoringWarning(handler) {
    eventHandlers.proctoring_warning.push(handler);
}

function onInterviewStatus(handler) {
    eventHandlers.interview_status.push(handler);
}

/**
 * Remove event handler
 */
function offProctoringStatus(handler) {
    const index = eventHandlers.proctoring_status.indexOf(handler);
    if (index > -1) {
        eventHandlers.proctoring_status.splice(index, 1);
    }
}

function offProctoringWarning(handler) {
    const index = eventHandlers.proctoring_warning.indexOf(handler);
    if (index > -1) {
        eventHandlers.proctoring_warning.splice(index, 1);
    }
}

function offInterviewStatus(handler) {
    const index = eventHandlers.interview_status.indexOf(handler);
    if (index > -1) {
        eventHandlers.interview_status.splice(index, 1);
    }
}

/**
 * Rehydrate interview state from backend on reconnect
 */
async function rehydrateInterviewState(sessionId) {
    try {
        // Try to load from backend API first
        if (window.interviewAPI && typeof window.interviewAPI.getSessionState === 'function') {
            const state = await window.interviewAPI.getSessionState(sessionId);
            if (state && state.interview_state) {
                const interviewState = typeof state.interview_state === 'string' 
                    ? JSON.parse(state.interview_state) 
                    : state.interview_state;
                
                // Update state manager
                if (typeof updateState === 'function') {
                    updateState('data', {
                        currentInterview: {
                            sessionId: sessionId,
                            state: interviewState,
                            lastUpdated: new Date().toISOString()
                        }
                    }, true);
                }
                
                // Save to localStorage
                localStorage.setItem(`interview_state_${sessionId}`, JSON.stringify(interviewState));
                console.log('[WebSocket] Interview state rehydrated from backend API');
                return;
            }
        }
        
        // Fallback: Load from localStorage
        const savedState = localStorage.getItem(`interview_state_${sessionId}`);
        if (savedState) {
            try {
                const interviewState = JSON.parse(savedState);
                
                // Update state manager
                if (typeof updateState === 'function') {
                    updateState('data', {
                        currentInterview: {
                            sessionId: sessionId,
                            state: interviewState,
                            lastUpdated: new Date().toISOString()
                        }
                    }, true);
                }
                
                console.log('[WebSocket] Interview state rehydrated from localStorage');
            } catch (e) {
                console.error('[WebSocket] Error parsing saved state:', e);
            }
        }
    } catch (error) {
        console.error('[WebSocket] Error rehydrating interview state:', error);
    }
}

/**
 * Save interview state to localStorage before disconnect
 */
function saveInterviewStateToLocalStorage(sessionId) {
    try {
        // Get current interview state from state manager
        if (typeof getState === 'function') {
            const state = getState('data');
            if (state.currentInterview && state.currentInterview.sessionId === sessionId) {
                localStorage.setItem(
                    `interview_state_${sessionId}`, 
                    JSON.stringify(state.currentInterview.state)
                );
                console.log('[WebSocket] Interview state saved to localStorage');
            }
        }
    } catch (error) {
        console.error('[WebSocket] Error saving interview state:', error);
    }
}

// Export functions
if (typeof window !== 'undefined') {
    window.initWebSocket = initWebSocket;
    window.disconnectWebSocket = disconnectWebSocket;
    window.onProctoringStatus = onProctoringStatus;
    window.onProctoringWarning = onProctoringWarning;
    window.onInterviewStatus = onInterviewStatus;
    window.offProctoringStatus = offProctoringStatus;
    window.offProctoringWarning = offProctoringWarning;
    window.offInterviewStatus = offInterviewStatus;
    window.rehydrateInterviewState = rehydrateInterviewState;
    window.saveInterviewStateToLocalStorage = saveInterviewStateToLocalStorage;
}

