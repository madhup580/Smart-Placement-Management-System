/**
 * Centralized State Management System
 * Single source of truth for application state
 * All UI rendering is driven by state changes
 */

// Application State - Single Source of Truth
const AppState = {
    // Authentication
    auth: {
        isAuthenticated: false,
        user: null,
        token: null
    },
    
    // Navigation & Routing
    navigation: {
        currentPage: 'dashboard',
        previousPage: null,
        route: null,
        questionId: null,
        hash: ''
    },
    
    // UI Visibility
    ui: {
        authPageVisible: false,
        mainAppVisible: false,
        currentPageVisible: null,
        codingQuestionViewVisible: false,
        aiChatbotVisible: false,
        loading: false,
        error: null
    },
    
    // Page-specific data
    pages: {
        dashboard: { loaded: false, data: null },
        coding: { loaded: false, data: null, currentQuestion: null },
        quizzes: { loaded: false, data: null },
        'non-technical': { loaded: false, data: null },
        companies: { loaded: false, data: null },
        resources: { loaded: false, data: null },
        leaderboard: { loaded: false, data: null },
        chatbot: { loaded: false, data: null },
        'student-assessments': { loaded: false, data: null },
        'available-assessments': { loaded: false, data: null }
    },
    
    // Application data
    data: {
        companies: [],
        questions: [],
        codingQuestions: [],
        currentQuestion: null,
        currentQuiz: null
    }
};

// State change listeners
const stateListeners = {
    navigation: [],
    ui: [],
    auth: [],
    pages: [],
    data: []
};

/**
 * Subscribe to state changes
 * @param {string} category - State category to listen to
 * @param {Function} callback - Callback function
 */
function subscribeToState(category, callback) {
    if (!stateListeners[category]) {
        stateListeners[category] = [];
    }
    stateListeners[category].push(callback);
    
    // Return unsubscribe function
    return () => {
        const index = stateListeners[category].indexOf(callback);
        if (index > -1) {
            stateListeners[category].splice(index, 1);
        }
    };
}

/**
 * Notify listeners of state changes
 * @param {string} category - State category that changed
 * @param {object} changes - Changed properties
 */
function notifyStateChange(category, changes) {
    if (stateListeners[category]) {
        stateListeners[category].forEach(callback => {
            try {
                callback(changes, AppState);
            } catch (error) {
                console.error(`[State] Error in state listener:`, error);
            }
        });
    }
}

// State mutation lock to prevent race conditions
let _stateLock = false;
let _pendingUpdates = [];

/**
 * Update state and notify listeners (IMMUTABLE - prevents race conditions)
 * @param {string} category - State category
 * @param {object} updates - Updates to apply
 * @param {boolean} silent - If true, don't notify listeners
 */
function updateState(category, updates, silent = false) {
    if (!AppState[category]) {
        console.warn(`[State] Unknown state category: ${category}`);
        return;
    }
    
    // Queue update if state is locked (prevents race conditions)
    if (_stateLock) {
        _pendingUpdates.push({ category, updates, silent });
        console.log(`[State] Update queued (state locked): ${category}`);
        return;
    }
    
    // Lock state during update
    _stateLock = true;
    
    try {
        // Create immutable copy of old state
        const oldState = JSON.parse(JSON.stringify(AppState[category]));
        
        // Deep merge updates (immutable update)
        const newState = deepMerge(AppState[category], updates);
        
        // Replace state (immutable assignment)
        AppState[category] = newState;
        
        if (!silent) {
            notifyStateChange(category, { old: oldState, new: newState, updates });
        }
        
        // Process pending updates
        if (_pendingUpdates.length > 0) {
            const pending = _pendingUpdates.shift();
            _stateLock = false; // Release lock temporarily
            updateState(pending.category, pending.updates, pending.silent);
            return;
        }
    } catch (error) {
        console.error(`[State] Error updating state ${category}:`, error);
    } finally {
        _stateLock = false;
    }
}

/**
 * Deep merge helper (immutable)
 */
function deepMerge(target, source) {
    const output = { ...target };
    
    if (isObject(target) && isObject(source)) {
        Object.keys(source).forEach(key => {
            if (isObject(source[key]) && isObject(target[key])) {
                output[key] = deepMerge(target[key], source[key]);
            } else {
                output[key] = source[key];
            }
        });
    }
    
    return output;
}

function isObject(item) {
    return item && typeof item === 'object' && !Array.isArray(item);
}

/**
 * Get current state (read-only)
 * @param {string} category - Optional category to get
 * @returns {object} State object
 */
function getState(category = null) {
    if (category) {
        return JSON.parse(JSON.stringify(AppState[category]));
    }
    return JSON.parse(JSON.stringify(AppState));
}

/**
 * Initialize state from existing app state
 */
function initializeState() {
    // Initialize from existing global variables if they exist
    if (typeof authToken !== 'undefined' && authToken && typeof currentUser !== 'undefined' && currentUser) {
        updateState('auth', {
            isAuthenticated: true,
            token: authToken,
            user: currentUser
        }, true);
        
        updateUIVisibility({
            authPageVisible: false,
            mainAppVisible: true,
            aiChatbotVisible: currentUser.role === 'student'
        }, true);
    } else {
        updateState('auth', {
            isAuthenticated: false,
            token: null,
            user: null
        }, true);
        
        updateUIVisibility({
            authPageVisible: true,
            mainAppVisible: false
        }, true);
    }
    
    // Initialize navigation from hash
    const hash = window.location.hash.substring(1);
    if (hash) {
        const route = parseRouteFromHash(hash);
        updateState('navigation', {
            hash: hash,
            route: route.page,
            currentPage: route.page,
            questionId: route.questionId
        }, true);
    } else {
        updateState('navigation', {
            currentPage: 'dashboard',
            hash: '',
            route: 'dashboard',
            questionId: null
        }, true);
    }
}

/**
 * Parse route from hash
 * @param {string} hash - Hash string
 * @returns {object} Parsed route
 */
function parseRouteFromHash(hash) {
    if (!hash) return { page: 'dashboard', questionId: null };
    
    const parts = hash.split('/');
    if (parts.length === 2 && parts[0] === 'coding' && parts[1]) {
        const questionId = parseInt(parts[1]);
        if (!isNaN(questionId) && questionId > 0) {
            return { page: 'coding', questionId: questionId };
        }
    }
    return { page: hash, questionId: null };
}

/**
 * Safe navigation with History API (replaces unsafe hash routing)
 * @param {string} page - Page name
 * @param {number|null} questionId - Optional question ID
 * @param {boolean} updateHistory - Whether to update browser history
 */
function navigateToPage(page, questionId = null, updateHistory = true) {
    const currentState = getState('navigation');
    
    // Build route
    const route = questionId ? `${page}/${questionId}` : page;
    const hash = `#${route}`;
    
    // Update state first (immutable)
    updateState('navigation', {
        previousPage: currentState.currentPage,
        currentPage: page,
        questionId: questionId,
        route: route,
        hash: hash
    });
    
    // Update browser history safely (replaces unsafe hash manipulation)
    if (updateHistory) {
        try {
            // Use History API for safe navigation
            if (window.history && window.history.pushState) {
                const state = { page, questionId, route };
                const url = window.location.pathname + hash;
                
                // Push state without page reload
                window.history.pushState(state, '', url);
                
                // Also update hash for backward compatibility
                window.location.hash = hash;
            } else {
                // Fallback to hash only
                window.location.hash = hash;
            }
        } catch (error) {
            console.error('[State] Error updating history:', error);
            // Fallback to hash only
            window.location.hash = hash;
        }
    }
}

/**
 * Handle browser back/forward buttons safely
 */
function handlePopState(event) {
    try {
        if (event.state) {
            // Restore state from history
            updateState('navigation', {
                currentPage: event.state.page || 'dashboard',
                questionId: event.state.questionId || null,
                route: event.state.route || 'dashboard',
                hash: window.location.hash
            }, false); // Notify listeners to trigger render
        } else {
            // Parse from hash
            const hash = window.location.hash.substring(1);
            const route = parseRouteFromHash(hash);
            updateState('navigation', {
                currentPage: route.page,
                questionId: route.questionId,
                route: route.questionId ? `${route.page}/${route.questionId}` : route.page,
                hash: window.location.hash
            }, false);
        }
    } catch (error) {
        console.error('[State] Error handling popstate:', error);
    }
}

// Listen for browser back/forward buttons
if (typeof window !== 'undefined') {
    window.addEventListener('popstate', handlePopState);
}

/**
 * Update UI visibility state
 * @param {object} visibility - Visibility updates
 */
function updateUIVisibility(visibility) {
    updateState('ui', visibility);
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.AppState = AppState;
    window.updateState = updateState;
    window.getState = getState;
    window.subscribeToState = subscribeToState;
    window.navigateToPage = navigateToPage;
    window.updateUIVisibility = updateUIVisibility;
    window.parseRouteFromHash = parseRouteFromHash;
}
