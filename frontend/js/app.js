// Application State
let currentQuestion = null;
let currentQuiz = null;
// Note: currentSessionId and interview-related variables are now in interview_enhanced.js
// Access them via window.currentSessionId if needed for backward compatibility
let companies = [];
let companySearchTerm = '';
let questions = [];
let codingQuestions = [];
let codingFilter = 'all';
let codingSearch = '';
let cpTopicTags = [];
const cpErrors = {
    question: null,
    testcases: null,
    topics: null,
    title: null
};

// Interview state variables moved to interview_enhanced.js to avoid conflicts
// If you need to access them, use the variables from interview_enhanced.js or window object

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

// Hash-based Routing System
// NOTE: Now uses state management system - see state_manager.js
// These functions are kept for backward compatibility but delegate to state system

function updateRoute(pageName, questionId = null) {
    // Use state-driven navigation
    navigateToPage(pageName, questionId, true);
}

function parseRoute() {
    // Use state manager's parse function
    const hash = window.location.hash.substring(1);
    return parseRouteFromHash(hash);
}

function handleRoute() {
    // Check authentication state
    const authState = getState('auth');
    if (!authState.isAuthenticated || !authState.user) {
        // Not logged in, show auth page
        updateState('auth', { isAuthenticated: false });
        updateUIVisibility({ authPageVisible: true, mainAppVisible: false });
        debouncedRender();
        return;
    }
    
    // Parse route from hash
    const hash = window.location.hash.substring(1);
    const route = parseRouteFromHash(hash);
    
    // Update navigation state (this will trigger render)
    navigateToPage(route.page || 'dashboard', route.questionId, false);
    
    // Render UI based on new state
    debouncedRender();
}

// Initialize App
// Test backend connection on page load
async function testBackendConnection() {
    try {
        const baseUrl = window.API_BASE_URL || getApiBaseUrl() || 'http://localhost:5000/api';
        // Test the /api endpoint (which should return API info)
        const apiUrl = baseUrl;
        
        // Use AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout for connection test
        
        const response = await fetch(apiUrl, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const data = await response.json();
            console.log('[Connection] âœ… Backend API connected:', data.message || 'OK');
            return true;
        } else {
            console.warn('[Connection] âš ï¸ Backend API returned status:', response.status);
            return false;
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            console.error('[Connection] âŒ Backend connection test timed out (5s)');
        } else {
            console.error('[Connection] âŒ Cannot connect to backend API:', error.message);
        }
        console.error('[Connection] ðŸ’¡ Make sure backend server is running:');
        console.error('[Connection]   1. Open terminal in backend folder');
        console.error('[Connection]   2. Run: python app.py');
        console.error('[Connection]   3. Wait for "Running on http://0.0.0.0:5000" message');
        return false;
    }
}

// Initialize App
function initializeApp() {
    // Test backend connection after a short delay to ensure API_BASE_URL is set
    setTimeout(async () => {
        const connected = await testBackendConnection();
        if (!connected) {
            // Show warning but don't block the app
            console.warn('[Connection] Frontend will continue, but API calls may fail.');
        }
    }, 500);
    
    // Register application flows for better maintainability
    if (window.flowManager) {
        // Register login flow
        window.flowManager.register('login', {
            steps: [
                { action: () => checkAuth(), wait: 100 },
                { action: () => loadCompanies(), wait: 0 },
                { action: () => setupCodingUI(), wait: 0 }
            ],
            onStart: () => console.log('[Flow] Login flow started'),
            onEnd: () => console.log('[Flow] Login flow completed')
        });
        
        // Register dashboard flow
        window.flowManager.register('dashboard', {
            steps: [
                { action: () => loadDashboard(), wait: 0 }
            ],
            onStart: () => console.log('[Flow] Dashboard flow started'),
            onError: (error) => {
                console.error('[Flow] Dashboard error:', error);
                if (window.errorHandler) {
                    window.errorHandler.handle(error, 'Dashboard Flow');
                }
            }
        });
    }
    
    checkAuth();
    loadCompanies();
    setupCodingUI();
    
    // Set up safe routing (History API + hash fallback)
    // Use popstate for browser back/forward (handled by state_manager.js)
    // Use hashchange as fallback for direct hash navigation
    window.addEventListener('hashchange', () => {
        // Only handle if not already handled by popstate
        const hash = window.location.hash.substring(1);
        const currentState = typeof getState === 'function' ? getState('navigation') : null;
        
        if (!currentState || currentState.hash !== `#${hash}`) {
            handleRoute();
        }
    });
    
    // Handle initial route
    if (window.location.hash) {
        handleRoute();
    } else if (authToken && currentUser) {
        // Default to dashboard if logged in and no hash
        updateRoute('dashboard');
    }
    
    // Aggressive layout recalculation after initialization
    function forceLayoutRecalc() {
        // Multiple reflow triggers
        if (document.body) {
            void document.body.offsetHeight;
            void document.body.scrollHeight;
            void document.documentElement.offsetHeight;
        }
        
        // Trigger resize for viewport calculations
        window.dispatchEvent(new Event('resize'));
        
        // Force all flexbox/grid recalculations
        const allElements = document.querySelectorAll('*');
        allElements.forEach(function(el) {
            void el.offsetHeight;
        });
    }
    
    // Run multiple times to ensure layout is calculated
    requestAnimationFrame(function() {
        forceLayoutRecalc();
        setTimeout(forceLayoutRecalc, 10);
        setTimeout(forceLayoutRecalc, 50);
        setTimeout(forceLayoutRecalc, 100);
    });
}

// Aggressive initialization to force layout rendering
function forceInitialLayout() {
    // Force reflow on all critical elements
    const mainApp = document.getElementById('main-app');
    const codingPage = document.getElementById('coding-page');
    const questionView = document.getElementById('coding-question-view');
    
    if (mainApp) {
        void mainApp.offsetHeight;
        // Ensure main-app is visible
        if (window.getComputedStyle(mainApp).display === 'none') {
            mainApp.style.display = 'block';
        }
    }
    
    if (codingPage) {
        void codingPage.offsetHeight;
    }
    
    if (questionView) {
        // Only show if it should be visible (has display: flex in style)
        const currentDisplay = questionView.style.display;
        if (currentDisplay === 'flex') {
            // Force it to stay visible
            questionView.style.display = 'none';
            void questionView.offsetHeight;
            questionView.style.display = 'flex';
            void questionView.offsetHeight;
        }
    }
    
    // Trigger resize for viewport recalculation
    window.dispatchEvent(new Event('resize'));
    
    // Force another reflow after a delay
    setTimeout(function() {
        if (document.body) {
            void document.body.offsetHeight;
            window.dispatchEvent(new Event('resize'));
        }
        }, 50);
}

// Initialize when DOM is ready - simplified approach
document.addEventListener('DOMContentLoaded', function() {
    // Force layout immediately
    forceInitialLayout();
    
    // Small delay to ensure CSS is applied
    requestAnimationFrame(function() {
        initializeApp();
        // Force layout again after initialization
        setTimeout(forceInitialLayout, 10);
    });
});

// Also initialize on window load as backup
window.addEventListener('load', function() {
    // Force layout on window load
    if (typeof forceInitialLayout === 'function') {
        forceInitialLayout();
    }
    
    if (!window.appInitialized) {
        window.appInitialized = true;
        requestAnimationFrame(function() {
            // Force one more layout recalculation
            if (typeof forceInitialLayout === 'function') {
                forceInitialLayout();
            } else if (document.body) {
                void document.body.offsetHeight;
                window.dispatchEvent(new Event('resize'));
            }
        });
    }
});

// Also force layout when CSS loads (if using dynamic CSS loading)
if (window.addEventListener) {
    window.addEventListener('cssLoaded', function() {
        if (typeof forceInitialLayout === 'function') {
            setTimeout(forceInitialLayout, 10);
        }
    });
}

// Also initialize on window load as backup
window.addEventListener('load', function() {
    // Force layout on window load
    forceInitialLayout();
    
    if (!window.appInitialized) {
        window.appInitialized = true;
        requestAnimationFrame(function() {
            // Force one more layout recalculation
            forceInitialLayout();
        });
    }
});

// Also force layout when CSS loads (if using dynamic CSS loading)
if (window.addEventListener) {
    window.addEventListener('cssLoaded', function() {
        setTimeout(forceInitialLayout, 10);
    });
}

// Authentication Functions
function checkAuth() {
    // Ensure only one page is visible at a time
    const authPage = document.getElementById('auth-page');
    const mainApp = document.getElementById('main-app');
    
    // Force hide both first, then show the correct one
    if (authPage) {
        authPage.classList.remove('active');
        authPage.style.display = 'none';
    }
    if (mainApp) {
        mainApp.classList.remove('active');
        mainApp.style.display = 'none';
    }
    
    if (authToken && currentUser) {
        showMainApp();
        // Handle route after showing main app
        if (window.location.hash) {
            handleRoute();
        } else {
            // Default to dashboard if no hash
            updateRoute('dashboard');
            loadDashboard();
            // Load notification badge count (only if logged in)
            if (authToken && currentUser) {
                loadNotificationBadge();
            }
        }
    } else {
        showPublicDashboard();
    }
}

function showPublicDashboard() {
    const authPage = document.getElementById('auth-page');
    const mainApp = document.getElementById('main-app');
    const publicDashboard = document.getElementById('public-demo-dashboard');
    const studentDashboard = document.getElementById('student-dashboard');
    const facultyDashboard = document.getElementById('faculty-admin-dashboard');
    const navCenter = document.getElementById('nav-center');
    const userInfoEl = document.getElementById('user-info');
    const authActionBtn = document.getElementById('auth-action-btn');

    if (authPage) {
        authPage.classList.remove('active');
        authPage.style.display = 'none';
    }
    if (mainApp) {
        mainApp.classList.add('active');
        mainApp.style.display = 'block';
    }
    document.querySelectorAll('.page-content').forEach(page => {
        page.style.display = 'none';
    });
    const dashboardPage = document.getElementById('dashboard-page');
    if (dashboardPage) dashboardPage.style.display = 'block';
    if (publicDashboard) publicDashboard.style.display = 'block';
    if (studentDashboard) studentDashboard.style.display = 'none';
    if (facultyDashboard) facultyDashboard.style.display = 'none';
    if (navCenter) navCenter.style.display = 'none';
    if (userInfoEl) userInfoEl.textContent = 'Presentation Demo';
    if (authActionBtn) {
        authActionBtn.textContent = 'Login';
        authActionBtn.onclick = () => {
            showAuthPage();
            if (typeof showAuthTab === 'function') showAuthTab('login');
        };
    }
}

function showAuthPage() {
    // Update state instead of directly manipulating DOM
    updateState('auth', { isAuthenticated: false });
    updateUIVisibility({ authPageVisible: true, mainAppVisible: false });
    
    // Render based on new state
    debouncedRender();
}

function showMainApp() {
    // Get current auth state from state manager or global variables
    const authState = getState('auth');
    const currentUser = authState.currentUser || window.currentUser || (() => {
        try {
            const userStr = localStorage.getItem('currentUser');
            return userStr ? JSON.parse(userStr) : null;
        } catch (e) {
            return null;
        }
    })();
    const authToken = authState.authToken || window.authToken || localStorage.getItem('authToken') || '';
    
    if (!currentUser || !authToken) {
        console.error('[showMainApp] Missing currentUser or authToken');
        return;
    }
    
    // Update state instead of directly manipulating DOM
    // Note: state manager uses 'user' and 'token', not 'currentUser' and 'authToken'
    updateState('auth', {
        isAuthenticated: true,
        user: currentUser,
        token: authToken
    });
    updateUIVisibility({ 
        authPageVisible: false, 
        mainAppVisible: true,
        aiChatbotVisible: currentUser && currentUser.role === 'student'
    });

    const publicDashboard = document.getElementById('public-demo-dashboard');
    const navCenter = document.getElementById('nav-center');
    const authActionBtn = document.getElementById('auth-action-btn');
    if (publicDashboard) publicDashboard.style.display = 'none';
    if (navCenter) navCenter.style.display = '';
    if (authActionBtn) {
        authActionBtn.textContent = 'Logout';
        authActionBtn.onclick = logout;
    }
    
    // Update user info in DOM (this is data, not visibility)
    const userInfoEl = document.getElementById('user-info');
    if (userInfoEl) {
        userInfoEl.textContent = `Welcome, ${currentUser?.username || 'User'}`;
    }
    
    // Show dashboard by default after login
    updateActiveNav('Dashboard');
    navigateToPage('dashboard', null, true);
    
    // Ensure dashboard page is visible and load data immediately
    setTimeout(() => {
        const dashboardPage = document.getElementById('dashboard-page');
        if (dashboardPage) {
            dashboardPage.style.display = 'block';
        }
        // Load dashboard data
        loadDashboard().catch(err => {
            console.error('[showMainApp] Error loading dashboard:', err);
        });
    }, 100); // Small delay to ensure DOM is ready
    
    // Force immediate DOM update FIRST (before renderer)
    // Must update both display style AND active class (CSS uses .active with !important)
    const authPage = document.getElementById('auth-page');
    const mainApp = document.getElementById('main-app');
    if (authPage) {
        authPage.classList.remove('active');
        authPage.style.display = 'none';
        console.log('[showMainApp] âœ… Hiding auth page (removed active class)');
    }
    if (mainApp) {
        mainApp.classList.add('active');
        mainApp.style.display = 'block';
        console.log('[showMainApp] âœ… Showing main app (added active class)');
    }
    
    // Then trigger renderer to sync state
    if (typeof render === 'function') {
        render();
        console.log('[showMainApp] âœ… Renderer called');
    }
    if (typeof debouncedRender === 'function') {
        debouncedRender();
    }
    
    // Update +Add button visibility
    if (typeof updateAddButtonVisibility === 'function') {
        updateAddButtonVisibility();
    }
}

function updateAddButtonVisibility() {
    if (!currentUser) {
        // Hide buttons if no user
        const addNonTechBtn = document.getElementById('add-nontech-btn');
        const addQuizBtn = document.getElementById('add-quiz-btn');
        const usersNavLink = document.getElementById('users-nav-link');
        if (addNonTechBtn) addNonTechBtn.style.display = 'none';
        if (addQuizBtn) addQuizBtn.style.display = 'none';
        if (usersNavLink) usersNavLink.style.display = 'none';
        return;
    }
    
    // Show add buttons based on user role
    const addNonTechBtn = document.getElementById('add-nontech-btn');
    const addQuizBtn = document.getElementById('add-quiz-btn');
    const usersNavLink = document.getElementById('users-nav-link');
    
    // Non-technical questions - all users can add
    if (addNonTechBtn) {
        addNonTechBtn.style.display = 'block';
    }
    
    // Quiz - only faculty and admin can add (students can only attempt)
    if (addQuizBtn) {
        if (currentUser && currentUser.role === 'student') {
            addQuizBtn.style.display = 'none';
        } else {
            addQuizBtn.style.display = 'block';
        }
    }
    
    // Users management - only admin can see
    if (usersNavLink) {
        if (currentUser && currentUser.role === 'admin') {
            usersNavLink.style.display = 'block';
        } else {
            usersNavLink.style.display = 'none';
        }
    }
    
    // Assessment menu link - only faculty/admin can see (in dropdown)
    const assessmentMenuLink = document.getElementById('assessment-menu-link');
    if (assessmentMenuLink) {
        if (currentUser && (currentUser.role === 'faculty' || currentUser.role === 'admin')) {
            assessmentMenuLink.style.display = 'block';
        } else {
            assessmentMenuLink.style.display = 'none';
        }
    }
    
    // Student Assessment menu link - only students can see (in dropdown)
    // Student Assessment menu link - only students can see (in dropdown)
    const studentAssessmentMenuLink = document.getElementById('student-assessment-menu-link');
    if (studentAssessmentMenuLink) {
        if (currentUser && currentUser.role === 'student') {
            studentAssessmentMenuLink.style.display = 'block';
        } else {
            studentAssessmentMenuLink.style.display = 'none';
        }
    }
}

async function login() {
    const usernameEl = document.getElementById('login-username');
    const passwordEl = document.getElementById('login-password');
    const errorDiv = document.getElementById('login-error');
    const loginButton = document.querySelector('#login-form .btn-login');
    
    // Check if required elements exist
    if (!usernameEl || !passwordEl) {
        console.error('Login form elements not found');
        return;
    }
    
    const username = usernameEl.value.trim();
    const password = passwordEl.value;
    
    // Clear previous errors
    if (errorDiv) {
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
    }
    
    // Validation
    if (!username || !password) {
        errorDiv.textContent = 'Please enter both username and password';
        errorDiv.style.display = 'block';
        return;
    }
    
    // Disable button and show loading state
    if (loginButton) {
        loginButton.disabled = true;
        loginButton.textContent = 'Logging in...';
    }
    
    try {
        // Use a shorter timeout for login (10 seconds) to fail faster if backend is down
        const loginResponse = await authAPI.login(username, password, { timeout: 300000 });
        
        // Ensure we have the latest authToken and currentUser from the response
        // They should be set by authAPI.login, but let's be explicit
        if (loginResponse && loginResponse.access_token) {
            // Update global variables for backward compatibility
            window.authToken = loginResponse.access_token;
            window.currentUser = loginResponse.user;
            
            // Also update from localStorage (authAPI.login already stored them)
            const storedToken = localStorage.getItem('authToken');
            const storedUser = localStorage.getItem('currentUser');
            if (storedToken) window.authToken = storedToken;
            if (storedUser) {
                try {
                    window.currentUser = JSON.parse(storedUser);
                } catch (e) {
                    console.warn('[Login] Failed to parse stored user:', e);
                }
            }
        }
        
        // Reset button immediately after successful login
        if (loginButton) {
            loginButton.disabled = false;
            loginButton.textContent = 'Login';
        }
        
        // Get the latest authToken and currentUser from global scope or localStorage
        const authToken = window.authToken || localStorage.getItem('authToken') || '';
        const currentUser = window.currentUser || (() => {
            try {
                const userStr = localStorage.getItem('currentUser');
                return userStr ? JSON.parse(userStr) : null;
            } catch (e) {
                return null;
            }
        })();
        
        // Verify we have valid auth data
        if (!authToken || !currentUser) {
            console.error('[Login] Missing authToken or currentUser after login');
            throw new Error('Login succeeded but authentication data is missing');
        }
        
        // Update state with the correct values
        // Note: state manager uses 'user' and 'token', not 'currentUser' and 'authToken'
        updateState('auth', {
            isAuthenticated: true,
            user: currentUser,
            token: authToken
        }, true); // Silent update to avoid triggering render twice
        
        console.log('[Login] Authentication successful, showing main app');
        showMainApp();
        
        // Clear form on success
        const usernameEl = document.getElementById('login-username');
        const passwordEl = document.getElementById('login-password');
        if (usernameEl) usernameEl.value = '';
        if (passwordEl) passwordEl.value = '';
        if (errorDiv) errorDiv.textContent = '';
        errorDiv.style.display = 'none';
        
        // Handle routing after login
        if (window.location.hash) {
            handleRoute();
        } else {
            updateRoute('dashboard');
            loadDashboard().catch(err => {
                console.error('Error loading dashboard:', err);
            });
        }
        
        // Load notification badge count (only if logged in)
        if (authToken && currentUser) {
            loadNotificationBadge().catch(err => {
                console.error('Error loading notification badge:', err);
            });
        }
    } catch (error) {
        // Always reset button on error
        if (loginButton) {
            loginButton.disabled = false;
            loginButton.textContent = 'Login';
        }
        
        // Show user-friendly error message
        let errorMessage = 'Login failed';
        if (error.message) {
            if (error.message.includes('timeout') || error.message.includes('Request timeout')) {
                errorMessage = 'Connection timeout: The server did not respond within 30 seconds.\n\nPlease ensure:\n1. Backend server is running (python app.py in backend folder)\n2. Server is listening on localhost:5000\n3. No firewall is blocking the connection\n4. Try refreshing the page';
            } else if (error.message.includes('Cannot connect') || error.message.includes('Failed to fetch')) {
                errorMessage = 'Cannot connect to server.\n\nPlease ensure:\n1. Backend server is running (python app.py in backend folder)\n2. Server is listening on localhost:5000\n3. CORS is configured correctly\n4. Network connection is active';
            } else if (error.message.includes('Invalid credentials') || error.message.includes('401')) {
                errorMessage = 'Invalid username or password';
            } else {
                errorMessage = error.message;
            }
        }
        
        errorDiv.textContent = errorMessage;
        errorDiv.style.display = 'block';
        console.error('Login error:', error);
    }
}

// Make login function globally accessible
window.login = login;

async function loadBatches() {
    const batchSelect = document.getElementById('reg-batch');
    if (!batchSelect) return;
    
    try {
        // Clear existing options except the first one
        batchSelect.innerHTML = '<option value="">Select Batch</option>';
        
        const data = await authAPI.getBatches();
        const batches = data.batches || [];
        
        // Populate batch options
        batches.forEach(batch => {
            const option = document.createElement('option');
            option.value = batch.id;
            option.textContent = batch.name;
            batchSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load batches:', error);
        // Keep default options if API call fails
    }
}

async function handleRoleChange() {
    const roleEl = document.getElementById('reg-role');
    if (!roleEl) {
        console.error('Registration role element not found');
        return;
    }
    const role = roleEl.value;
    const batchGroup = document.getElementById('reg-batch-group');
    if (batchGroup) {
        if (role === 'student') {
            batchGroup.style.display = 'block';
            const batchSelect = document.getElementById('reg-batch');
            if (batchSelect) {
                batchSelect.required = true;
                // Load batches if dropdown is empty (only has "Select Batch" option)
                if (batchSelect.options.length <= 1) {
                    await loadBatches();
                }
            }
        } else {
            batchGroup.style.display = 'none';
            const batchSelect = document.getElementById('reg-batch');
            if (batchSelect) {
                batchSelect.required = false;
                batchSelect.value = '';
            }
        }
    }
}

// Make handleRoleChange globally accessible
window.handleRoleChange = handleRoleChange;

async function register() {
    const usernameEl = document.getElementById('reg-username');
    const firstNameEl = document.getElementById('reg-firstname');
    const lastNameEl = document.getElementById('reg-lastname');
    const regNoEl = document.getElementById('reg-regno');
    const collegeEmailEl = document.getElementById('reg-college-email');
    const passwordEl = document.getElementById('reg-password');
    const confirmPasswordEl = document.getElementById('reg-confirm-password');
    const roleEl = document.getElementById('reg-role');
    const batchIdEl = document.getElementById('reg-batch');
    const errorDiv = document.getElementById('register-error');
    
    // Check if required elements exist
    if (!usernameEl || !firstNameEl || !lastNameEl || !regNoEl || !collegeEmailEl || 
        !passwordEl || !confirmPasswordEl || !roleEl) {
        console.error('Registration form elements not found');
        if (errorDiv) {
            errorDiv.textContent = 'Registration form error. Please refresh the page.';
            errorDiv.style.display = 'block';
        }
        return;
    }
    
    const username = usernameEl.value.trim();
    const firstName = firstNameEl.value.trim();
    const lastName = lastNameEl.value.trim();
    const regNo = regNoEl.value.trim();
    const collegeEmail = collegeEmailEl.value.trim();
    const password = passwordEl.value;
    const confirmPassword = confirmPasswordEl.value;
    const role = roleEl.value;
    const batchId = batchIdEl ? batchIdEl.value : null;
    
    // Clear previous errors
    if (errorDiv) {
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
    }
    
    // Validation
    if (!username || !firstName || !lastName || !regNo || !collegeEmail || !password || !confirmPassword || !role) {
        errorDiv.textContent = 'All fields are required';
        errorDiv.style.display = 'block';
        return;
    }
    
    // Validate batch selection for students
    if (role === 'student' && !batchId) {
        errorDiv.textContent = 'Please select a batch';
        errorDiv.style.display = 'block';
        return;
    }
    
    // Validate first name (alphabets only)
    if (!/^[A-Za-z\s]+$/.test(firstName)) {
        errorDiv.textContent = 'First name must contain only alphabets';
        errorDiv.style.display = 'block';
        return;
    }
    
    // Validate last name (alphabets only)
    if (!/^[A-Za-z\s]+$/.test(lastName)) {
        errorDiv.textContent = 'Last name must contain only alphabets';
        errorDiv.style.display = 'block';
        return;
    }
    
    // Validate registration number (alphanumeric)
    if (!/^[A-Za-z0-9]+$/.test(regNo)) {
        errorDiv.textContent = 'Registration number must be alphanumeric';
        errorDiv.style.display = 'block';
        return;
    }
    
    // Validate college email (must end with @audisankara.ac.in)
    if (!collegeEmail.endsWith('@audisankara.ac.in')) {
        errorDiv.textContent = 'College email must end with @audisankara.ac.in';
        errorDiv.style.display = 'block';
        return;
    }
    
    // Validate password match
    if (password !== confirmPassword) {
        errorDiv.textContent = 'Passwords do not match';
        errorDiv.style.display = 'block';
        return;
    }
    
    // Validate password strength
    const passwordStrength = checkPasswordStrengthValue(password);
    if (passwordStrength < 3) {
        errorDiv.textContent = 'Password is too weak. Please use a stronger password.';
        errorDiv.style.display = 'block';
        return;
    }
    
    // Check password match
    if (password !== confirmPassword) {
        errorDiv.textContent = 'Passwords do not match';
        errorDiv.style.display = 'block';
        return;
    }
    
    const registerButton = document.querySelector('#register-form .btn-login');
    
    // Disable button and show loading state
    if (registerButton) {
        registerButton.disabled = true;
        registerButton.textContent = 'Registering...';
    }
    
    try {
        const batchId = role === 'student' ? document.getElementById('reg-batch').value : null;
        await authAPI.register(username, firstName, lastName, regNo, collegeEmail, password, role, batchId);
        showMainApp();
        loadDashboard();
        // Load notification badge count (only if logged in)
        if (authToken && currentUser) {
            loadNotificationBadge();
        }
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
        
        // Clear form on success
        clearAuthForms();
    } catch (error) {
        errorDiv.textContent = error.message || 'Registration failed';
        errorDiv.style.display = 'block';
    } finally {
        // Re-enable button
        if (registerButton) {
            registerButton.disabled = false;
            registerButton.textContent = 'Register';
        }
    }
}

function checkPasswordStrengthValue(password) {
    if (!password) return 0;
    
    let strength = 0;
    if (password.length >= 8) strength += 1;
    if (/[a-z]/.test(password)) strength += 1;
    if (/[A-Z]/.test(password)) strength += 1;
    if (/[0-9]/.test(password)) strength += 1;
    if (/[^A-Za-z0-9]/.test(password)) strength += 1;
    
    return strength;
}

// Make register function globally accessible
window.register = register;

function logout() {
    authAPI.logout();
    
    // Clear all form fields
    clearAuthForms();
    
    showAuthPage();
}

function clearAuthForms() {
    // Clear login form
    const loginUsername = document.getElementById('login-username');
    const loginPassword = document.getElementById('login-password');
    const loginError = document.getElementById('login-error');
    if (loginUsername) loginUsername.value = '';
    if (loginPassword) loginPassword.value = '';
    if (loginError) {
        loginError.textContent = '';
        loginError.style.display = 'none';
    }
    
    // Clear register form
    const regFields = [
        'reg-username', 'reg-firstname', 'reg-lastname', 'reg-regno',
        'reg-college-email', 'reg-password', 'reg-confirm-password', 'reg-role'
    ];
    regFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) field.value = '';
    });
    
    // Reset batch field and hide batch group
    const batchSelect = document.getElementById('reg-batch');
    const batchGroup = document.getElementById('reg-batch-group');
    if (batchSelect) {
        batchSelect.value = '';
        batchSelect.required = false;
    }
    if (batchGroup) {
        batchGroup.style.display = 'none';
    }
    
    const registerError = document.getElementById('register-error');
    if (registerError) {
        registerError.textContent = '';
        registerError.style.display = 'none';
    }
    
    // Clear password strength indicator
    const passwordStrength = document.getElementById('password-strength');
    if (passwordStrength) {
        passwordStrength.style.display = 'none';
    }
    
    // Reset password visibility
    const passwordInputs = ['reg-password', 'reg-confirm-password', 'login-password'];
    passwordInputs.forEach(inputId => {
        const input = document.getElementById(inputId);
        if (input) {
            input.type = 'password';
            const icon = input.nextElementSibling;
            if (icon && icon.classList.contains('password-toggle')) {
                icon.textContent = 'ðŸ‘ï¸';
            }
        }
    });
}

// Toggle password visibility
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    const icon = input.nextElementSibling;
    if (input.type === 'password') {
        input.type = 'text';
        icon.textContent = 'ðŸ™ˆ';
        icon.setAttribute('aria-label', 'Hide password');
    } else {
        input.type = 'password';
        icon.textContent = 'ðŸ‘ï¸';
        icon.setAttribute('aria-label', 'Show password');
    }
}

// Password strength checker
function checkPasswordStrength(password) {
    const strengthDiv = document.getElementById('password-strength');
    const strengthFill = document.getElementById('strength-fill');
    const strengthText = document.getElementById('strength-text');
    const strengthRequirements = document.getElementById('strength-requirements');
    
    if (!strengthDiv || !strengthFill || !strengthText || !strengthRequirements) return;
    
    if (!password) {
        strengthDiv.style.display = 'none';
        return;
    }
    
    strengthDiv.style.display = 'block';
    
    let strength = 0;
    let feedback = [];
    let requirements = [];
    
    // Length check
    if (password.length >= 8) {
        strength += 1;
        requirements.push('âœ“ At least 8 characters');
    } else {
        requirements.push('âœ— At least 8 characters');
    }
    
    // Lowercase check
    if (/[a-z]/.test(password)) {
        strength += 1;
        requirements.push('âœ“ Contains lowercase letter');
    } else {
        requirements.push('âœ— Contains lowercase letter');
    }
    
    // Uppercase check
    if (/[A-Z]/.test(password)) {
        strength += 1;
        requirements.push('âœ“ Contains uppercase letter');
    } else {
        requirements.push('âœ— Contains uppercase letter');
    }
    
    // Number check
    if (/[0-9]/.test(password)) {
        strength += 1;
        requirements.push('âœ“ Contains number');
    } else {
        requirements.push('âœ— Contains number');
    }
    
    // Special character check
    if (/[^A-Za-z0-9]/.test(password)) {
        strength += 1;
        requirements.push('âœ“ Contains special character');
    } else {
        requirements.push('âœ— Contains special character');
    }
    
    // Calculate strength percentage and color
    const strengthPercent = (strength / 5) * 100;
    let strengthLabel = '';
    let strengthColor = '';
    
    if (strength <= 1) {
        strengthLabel = 'Very Weak';
        strengthColor = '#e74c3c'; // Red
    } else if (strength === 2) {
        strengthLabel = 'Weak';
        strengthColor = '#f39c12'; // Orange
    } else if (strength === 3) {
        strengthLabel = 'Fair';
        strengthColor = '#f1c40f'; // Yellow
    } else if (strength === 4) {
        strengthLabel = 'Good';
        strengthColor = '#2ecc71'; // Light Green
    } else {
        strengthLabel = 'Strong';
        strengthColor = '#27ae60'; // Dark Green
    }
    
    strengthFill.style.width = strengthPercent + '%';
    strengthFill.style.backgroundColor = strengthColor;
    strengthText.textContent = strengthLabel;
    strengthText.style.color = strengthColor;
    strengthRequirements.innerHTML = requirements.map(req => {
        const isMet = req.startsWith('âœ“');
        return `<div style="color: ${isMet ? '#2ecc71' : '#95a5a6'}; font-size: 12px; margin: 2px 0;">${req}</div>`;
    }).join('');
}

function showPasswordStrength() {
    const passwordInput = document.getElementById('reg-password');
    const strengthDiv = document.getElementById('password-strength');
    if (passwordInput && passwordInput.value && strengthDiv) {
        strengthDiv.style.display = 'block';
    }
}

function hidePasswordStrengthIfEmpty() {
    const passwordInput = document.getElementById('reg-password');
    const strengthDiv = document.getElementById('password-strength');
    if (passwordInput && !passwordInput.value && strengthDiv) {
        // Hide after a short delay to allow clicking on requirements
        setTimeout(() => {
            if (!passwordInput.value) {
                strengthDiv.style.display = 'none';
            }
        }, 200);
    }
}

function checkPasswordMatch() {
    const password = document.getElementById('reg-password')?.value;
    const confirmPassword = document.getElementById('reg-confirm-password')?.value;
    const matchIndicator = document.getElementById('password-match-indicator');
    
    if (!matchIndicator) return;
    
    if (!confirmPassword) {
        matchIndicator.style.display = 'none';
        return;
    }
    
    matchIndicator.style.display = 'block';
    
    if (password === confirmPassword) {
        matchIndicator.innerHTML = '<span style="color: #2ecc71;">âœ“ Passwords match</span>';
        matchIndicator.style.color = '#2ecc71';
    } else {
        matchIndicator.innerHTML = '<span style="color: #e74c3c;">âœ— Passwords do not match</span>';
        matchIndicator.style.color = '#e74c3c';
    }
}

// Toggle between login and register forms
function toggleAuthForm() {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const switchText = document.getElementById('auth-switch-text');
    const switchLink = document.getElementById('auth-switch-link');
    const authTitle = document.querySelector('.auth-title');
    
    // Clear forms when switching
    clearAuthForms();
    
    if (loginForm.classList.contains('active')) {
        // Switch to register
        loginForm.classList.remove('active');
        registerForm.classList.add('active');
        authTitle.textContent = 'Register';
        switchText.textContent = 'Already have an account? ';
        switchLink.textContent = 'Login';
    } else {
        // Switch to login
        registerForm.classList.remove('active');
        loginForm.classList.add('active');
        authTitle.textContent = 'Login';
        switchText.textContent = "Don't have account? ";
        switchLink.textContent = "Signup";
    }
}

// Show forgot password (placeholder)
function showForgotPassword() {
    alert('Forgot password feature coming soon!');
}

function showAuthTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.auth-form').forEach(form => form.classList.remove('active'));
    
    if (tab === 'login') {
        const loginTab = document.querySelector('.tab-btn');
        const loginForm = document.getElementById('login-form');
        if (loginTab) loginTab.classList.add('active');
        if (loginForm) loginForm.classList.add('active');
    } else {
        const registerTabs = document.querySelectorAll('.tab-btn');
        const registerForm = document.getElementById('register-form');
        if (registerTabs.length > 1) registerTabs[1].classList.add('active');
        if (registerForm) registerForm.classList.add('active');
    }
}

// Navigation
function showPage(pageName, updateHash = true) {
    // Get current state
    const navState = getState('navigation');
    const currentPage = navState.currentPage;
    
    // Check if we're leaving the interview page
    const isLeavingInterview = currentPage === 'chatbot' || currentPage === 'ai-interview';
    
    // If leaving interview page, cleanup camera and mic
    if (isLeavingInterview && pageName !== 'chatbot' && pageName !== 'ai-interview') {
        if (typeof cleanupInterviewMedia === 'function') {
            cleanupInterviewMedia();
        }
    }
    
    // If leaving coding question view, close it
    if (currentPage === 'coding' && pageName !== 'coding') {
        if (typeof closeCodingQuestionView === 'function') {
            closeCodingQuestionView();
        }
        // Update state to hide coding question view
        updateUIVisibility({ codingQuestionViewVisible: false });
    }
    
    // Update navigation state (state-driven approach)
    navigateToPage(pageName, null, updateHash);
    
    // Close all dropdown menus when navigating
    if (typeof closeNonTechnicalMenu === 'function') {
        closeNonTechnicalMenu();
    }
    if (typeof closeInterviewMenu === 'function') {
        closeInterviewMenu();
    }
    
    // Render UI based on new state (this will handle all DOM updates)
    debouncedRender();
    
    // Update +Add button visibility based on role
    if (typeof updateAddButtonVisibility === 'function') {
        updateAddButtonVisibility();
    }
}

function hideAllPages() {
    // Use state-driven approach instead of direct DOM manipulation
    // This function is kept for backward compatibility but should use state
    updateUIVisibility({ currentPageVisible: null });
    debouncedRender();
}

function showOnlyDashboard() {
    // Use state-driven navigation
    navigateToPage('dashboard', null, true);
    debouncedRender();
}

function showDashboard() {
    updateActiveNav('Dashboard');
    showOnlyDashboard();
}
function showNonTechnical() { 
    // Close dropdown menu
    closeNonTechnicalMenu();
    closeInterviewMenu();
    updateActiveNav('Non-Technical');
    updateRoute('non-technical');
    showPage('non-technical', false); 
}

function showQuizPage() {
    // Close dropdown menu
    closeNonTechnicalMenu();
    closeInterviewMenu();
    updateActiveNav('Non-Technical');
    updateRoute('quizzes');
    showPage('quizzes', false);
}

// Assessment Builder State
let currentAssessment = null;
let assessmentQuestions = [];

// Flatpickr instances for datetime pickers
let startDateTimePicker = null;
let endDateTimePicker = null;

function initializeAssessmentDateTimePickers() {
    // Destroy existing instances if they exist
    if (startDateTimePicker) {
        startDateTimePicker.destroy();
    }
    if (endDateTimePicker) {
        endDateTimePicker.destroy();
    }
    
    const startInput = document.getElementById('assessment-start-datetime');
    const endInput = document.getElementById('assessment-end-datetime');
    
    if (!startInput || !endInput) return;
    
    // Initialize start datetime picker
    startDateTimePicker = flatpickr(startInput, {
        enableTime: true,
        dateFormat: "Y-m-d h:i K", // Format: 2026-01-03 6:20 PM
        time_24hr: false, // Use 12-hour format with AM/PM
        minuteIncrement: 1,
        minDate: "today",
        onChange: function(selectedDates, dateStr, instance) {
            // Update hidden inputs
            if (selectedDates.length > 0) {
                const date = selectedDates[0];
                // Get date in YYYY-MM-DD format
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                const dateStr = `${year}-${month}-${day}`;
                
                // Get time in HH:MM format (24-hour)
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                const timeStr = `${hours}:${minutes}`;
                
                document.getElementById('assessment-start-date').value = dateStr;
                document.getElementById('assessment-start-time').value = timeStr;
                
                // Update end picker min date to be after start
                if (endDateTimePicker) {
                    endDateTimePicker.set('minDate', date);
                }
            }
        }
    });
    
    // Initialize end datetime picker
    endDateTimePicker = flatpickr(endInput, {
        enableTime: true,
        dateFormat: "Y-m-d h:i K", // Format: 2026-01-03 6:30 PM
        time_24hr: false, // Use 12-hour format with AM/PM
        minuteIncrement: 1,
        minDate: "today",
        onChange: function(selectedDates, dateStr, instance) {
            // Update hidden inputs
            if (selectedDates.length > 0) {
                const date = selectedDates[0];
                // Get date in YYYY-MM-DD format
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                const dateStr = `${year}-${month}-${day}`;
                
                // Get time in HH:MM format (24-hour)
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                const timeStr = `${hours}:${minutes}`;
                
                document.getElementById('assessment-end-date').value = dateStr;
                document.getElementById('assessment-end-time').value = timeStr;
            }
        }
    });
}

function showAssessmentPage() {
    // Close dropdown menu
    closeNonTechnicalMenu();
    updateActiveNav('Non-Technical');
    showPage('assessment');
    
    // Only show for faculty/admin
    if (!currentUser || (currentUser.role !== 'faculty' && currentUser.role !== 'admin')) {
        showSuccessNotification('Access denied. Only faculty and administrators can create assessments.', 'error');
        showDashboard();
        return;
    }
    
    // Reset to step 1
    goToAssessmentStep(1);
    currentAssessment = null;
    assessmentQuestions = [];
    
    // Initialize datetime pickers after a short delay to ensure DOM is ready
    setTimeout(() => {
        initializeAssessmentDateTimePickers();
    }, 100);
}

function goToAssessmentStep(step) {
    // Hide all steps
    document.querySelectorAll('.assessment-step').forEach(s => {
        s.style.display = 'none';
    });
    
    // Update step indicators
    for (let i = 1; i <= 3; i++) {
        const indicator = document.getElementById(`step-${i}-indicator`);
        const label = indicator?.parentElement.querySelector('.step-label');
        if (i <= step) {
            if (indicator) {
                indicator.style.background = '#667eea';
                indicator.style.color = 'white';
            }
            if (label) label.style.color = '#667eea';
        } else {
            if (indicator) {
                indicator.style.background = '#e0e0e0';
                indicator.style.color = '#999';
            }
            if (label) label.style.color = '#999';
        }
    }
    
    // Show current step
    const stepElement = document.getElementById(`assessment-step-${step}`);
    if (stepElement) {
        stepElement.style.display = 'block';
    }
    
    // Load data for step 2 and 3
    if (step === 2) {
        loadAssessmentQuestions();
    } else if (step === 3) {
        loadAssessmentReview();
    }
}

// Batch checkbox handlers
function handleBatchBothCheckbox(checkbox) {
    // Legacy helper: when "all batches" is checked, check every visible batch.
    if (checkbox.checked) {
        document.querySelectorAll('input[name="assigned-batches"]').forEach(batch => {
            batch.checked = true;
        });
    }
}

function handleBatchCheckboxChange() {
    // Keep legacy "all batches" checkbox in sync if present.
    const batchCheckboxes = Array.from(document.querySelectorAll('input[name="assigned-batches"]'));
    const bothCheckbox = document.getElementById('batch-both-checkbox');
    
    if (batchCheckboxes.length && bothCheckbox) {
        bothCheckbox.checked = batchCheckboxes.every(batch => batch.checked);
    }
}

// Make functions globally accessible
window.handleBatchBothCheckbox = handleBatchBothCheckbox;
window.handleBatchCheckboxChange = handleBatchCheckboxChange;

// Helper function to format assessment date/time range
function formatAssessmentDateTimeRange(assessment) {
    if (!assessment.start_date || !assessment.end_date || !assessment.start_time || !assessment.end_time) {
        return 'Not set';
    }
    
    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    };
    
    const formatTime = (timeStr) => {
        if (!timeStr) return '';
        // timeStr is in format "HH:MM:SS" or "HH:MM"
        const parts = timeStr.split(':');
        const hours = parseInt(parts[0]);
        const minutes = parts[1];
        const ampm = hours >= 12 ? 'PM' : 'AM';
        const hours12 = hours % 12 || 12;
        return `${hours12}:${minutes} ${ampm}`;
    };
    
    const startDate = formatDate(assessment.start_date);
    const endDate = formatDate(assessment.end_date);
    const startTime = formatTime(assessment.start_time);
    const endTime = formatTime(assessment.end_time);
    
    if (assessment.start_date === assessment.end_date) {
        return `${startDate} ${startTime} - ${endTime}`;
    } else {
        return `${startDate} ${startTime} to ${endDate} ${endTime}`;
    }
}

async function submitAssessmentStep1(event) {
    event.preventDefault();
    
    // Check user role
    if (!currentUser || (currentUser.role !== 'faculty' && currentUser.role !== 'admin')) {
        showSuccessNotification('Access denied. Only faculty and administrators can create assessments.', 'error');
        return;
    }
    
    try {
        const titleEl = document.getElementById('assessment-title');
        const descriptionEl = document.getElementById('assessment-description');
        const difficultyEl = document.getElementById('assessment-difficulty');
        const startDateEl = document.getElementById('assessment-start-date');
        const endDateEl = document.getElementById('assessment-end-date');
        const startTimeEl = document.getElementById('assessment-start-time');
        const endTimeEl = document.getElementById('assessment-end-time');
        const tagsInputEl = document.getElementById('assessment-tags');
        
        // Check if required elements exist
        if (!titleEl || !descriptionEl || !difficultyEl || !startDateEl || !endDateEl || 
            !startTimeEl || !endTimeEl) {
            showSuccessNotification('Assessment form elements not found. Please refresh the page.', 'error');
            return;
        }
        
        const title = titleEl.value.trim();
        const description = descriptionEl.value.trim();
        const assessmentMode = document.querySelector('input[name="assessment-mode"]:checked')?.value;
        const difficulty = difficultyEl.value;
        const startDate = startDateEl.value;
        const endDate = endDateEl.value;
        const startTime = startTimeEl.value;
        const endTime = endTimeEl.value;
        const tagsInput = tagsInputEl ? tagsInputEl.value.trim() : '';
        
        // Validate
        if (!title || !assessmentMode || !difficulty || !startDate || !endDate || !startTime || !endTime) {
            showSuccessNotification('Please fill in all required fields.', 'error');
            return;
        }
        
        // Validate that end date/time is after start date/time
        const startDateTime = new Date(`${startDate}T${startTime}`);
        const endDateTime = new Date(`${endDate}T${endTime}`);
        if (endDateTime <= startDateTime) {
            showSuccessNotification('End date and time must be after start date and time.', 'error');
            return;
        }
        
        // Parse tags
        const topicTags = tagsInput ? tagsInput.split(',').map(tag => tag.trim()).filter(tag => tag) : [];
        
        // Get batch assignments
        const batchCheckboxes = document.querySelectorAll('input[name="assigned-batches"]:checked');
        const assignedBatches = [];
        batchCheckboxes.forEach(checkbox => {
            const batchId = parseInt(checkbox.value);
            if (batchId && !assignedBatches.includes(batchId)) {
                assignedBatches.push(batchId);
            }
        });
        // Sort batch IDs for consistency
        assignedBatches.sort();
        
        const assessmentData = {
            title,
            description,
            assessment_mode: assessmentMode,
            difficulty,
            start_date: startDate,
            end_date: endDate,
            start_time: startTime,
            end_time: endTime,
            topic_tags: topicTags,
            assigned_batches: assignedBatches.length > 0 ? assignedBatches : null  // null means all batches
        };
        
        // Show loading
        const submitBtn = event.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Saving...';
        
        if (currentAssessment && currentAssessment.id) {
            // Update existing assessment
            await facultyAPI.updateAssessment(currentAssessment.id, assessmentData);
            showSuccessNotification('Assessment updated successfully!');
        } else {
            // Create new assessment
            const response = await facultyAPI.createAssessment(assessmentData);
            currentAssessment = response.assessment;
            showSuccessNotification('Basic information saved! Now add questions.');
        }
        
        // Go to step 2
        goToAssessmentStep(2);
        
        // Reset button
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
        
    } catch (error) {
        console.error('Error saving assessment:', error);
        showSuccessNotification(error.message || 'Failed to save assessment. Please try again.', 'error');
        
        // Reset button
        const submitBtn = event.target.querySelector('button[type="submit"]');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Save & Continue to Step 2 â†’';
    }
}

function loadAssessmentQuestions() {
    if (!currentAssessment || !currentAssessment.id) return;
    
    // Load questions from API
    facultyAPI.getAssessment(currentAssessment.id)
        .then(response => {
            assessmentQuestions = response.assessment.questions || [];
            renderAssessmentQuestions();
            updateQuestionButtons();
        })
        .catch(error => {
            console.error('Error loading questions:', error);
        });
}

function renderAssessmentQuestions() {
    const container = document.getElementById('assessment-questions-list');
    if (!container) return;
    
    if (assessmentQuestions.length === 0) {
        container.innerHTML = '<p style="color: #999; text-align: center; margin: 0;">No questions added yet. Click the buttons above to add questions.</p>';
        return;
    }
    
    container.innerHTML = assessmentQuestions.map((aq, index) => {
        const q = aq.question || {};
        const typeLabel = q.type === 'coding' ? 'Technical' : (q.type === 'mcq' ? 'MCQ' : 'Fill-in-the-blank');
        return `
            <div class="question-item" style="display: flex; justify-content: space-between; align-items: center; padding: 15px; background: white; border-radius: 8px; margin-bottom: 10px; border: 1px solid #e0e0e0;">
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span style="font-weight: bold; color: #667eea;">Q${index + 1}</span>
                        <span style="padding: 4px 12px; background: #e0e0e0; border-radius: 4px; font-size: 12px;">${typeLabel}</span>
                        <span style="color: #666;">${q.title || 'Untitled Question'}</span>
                    </div>
                    <div style="margin-top: 8px; color: #999; font-size: 14px;">
                        Marks: ${aq.marks} | Difficulty: ${q.difficulty || 'N/A'}
                    </div>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button onclick="editAssessmentQuestion(${aq.id}, ${aq.question_id})" class="btn btn-sm" style="padding: 6px 12px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer;">Edit</button>
                    <button onclick="removeAssessmentQuestion(${aq.question_id})" class="btn btn-sm" style="padding: 6px 12px; background: #ff6b6b; color: white; border: none; border-radius: 4px; cursor: pointer;">Delete</button>
                </div>
            </div>
        `;
    }).join('');
}

function updateQuestionButtons() {
    if (!currentAssessment) return;
    
    const mode = currentAssessment.assessment_mode;
    const addTechnicalBtn = document.getElementById('add-technical-btn');
    const addNonTechnicalBtn = document.getElementById('add-non-technical-btn');
    
    if (mode === 'technical_only') {
        if (addNonTechnicalBtn) addNonTechnicalBtn.style.display = 'none';
        if (addTechnicalBtn) addTechnicalBtn.style.display = 'flex';
    } else if (mode === 'non_technical_only') {
        if (addTechnicalBtn) addTechnicalBtn.style.display = 'none';
        if (addNonTechnicalBtn) addNonTechnicalBtn.style.display = 'flex';
    } else {
        if (addTechnicalBtn) addTechnicalBtn.style.display = 'flex';
        if (addNonTechnicalBtn) addNonTechnicalBtn.style.display = 'flex';
    }
}

function openTechnicalQuestionBuilder() {
    const modal = document.getElementById('technical-question-modal');
    if (modal) {
        modal.classList.remove('hidden');
        // Reset form
        document.getElementById('tech-question-title').value = '';
        document.getElementById('tech-question-description').value = '';
        document.getElementById('tech-constraints').value = '';
        document.getElementById('tech-question-marks').value = '10';
        document.getElementById('tech-question-difficulty').value = 'medium';
    }
}

function closeTechnicalQuestionBuilder() {
    const modal = document.getElementById('technical-question-modal');
    if (modal) modal.classList.add('hidden');
}

function openNonTechnicalQuestionBuilder() {
    const modal = document.getElementById('non-technical-question-modal');
    if (modal) {
        modal.classList.remove('hidden');
        // Reset form
        document.getElementById('nt-question-type').value = '';
        document.getElementById('nt-assessment-question').value = '';
        document.getElementById('nt-assessment-marks').value = '1';
        handleNonTechQuestionTypeChange();
        
        // Reset button
        const submitBtn = document.querySelector('#non-technical-question-modal .btn-primary');
        if (submitBtn) {
            submitBtn.textContent = 'Add Question to Assessment';
            submitBtn.onclick = submitNonTechnicalQuestion;
        }
        
        // Clear editing state
        window.editingQuestionId = null;
        window.editingAssessmentQuestionId = null;
    }
}

function closeNonTechnicalQuestionBuilder() {
    const modal = document.getElementById('non-technical-question-modal');
    if (modal) modal.classList.add('hidden');
}

function handleNonTechQuestionTypeChange() {
    const type = document.getElementById('nt-question-type').value;
    const mcqFields = document.getElementById('nt-mcq-fields');
    const fillBlankFields = document.getElementById('nt-fill-blank-fields');
    
    if (type === 'mcq') {
        if (mcqFields) mcqFields.style.display = 'block';
        if (fillBlankFields) fillBlankFields.style.display = 'none';
    } else if (type === 'fill_blank') {
        if (mcqFields) mcqFields.style.display = 'none';
        if (fillBlankFields) fillBlankFields.style.display = 'block';
    } else {
        if (mcqFields) mcqFields.style.display = 'none';
        if (fillBlankFields) fillBlankFields.style.display = 'none';
    }
}

async function submitTechnicalQuestion() {
    if (!currentAssessment || !currentAssessment.id) {
        showSuccessNotification('Please complete Step 1 first.', 'error');
        return;
    }
    
    try {
        const title = document.getElementById('tech-question-title').value.trim();
        const description = document.getElementById('tech-question-description').value.trim();
        const constraints = document.getElementById('tech-constraints').value.trim();
        const marks = parseInt(document.getElementById('tech-question-marks').value);
        const difficulty = document.getElementById('tech-question-difficulty').value;
        
        if (!title || !description) {
            showSuccessNotification('Please fill in title and description.', 'error');
            return;
        }
        
        // Collect test cases
        const testCases = [];
        const testCaseItems = document.querySelectorAll('.test-case-item');
        testCaseItems.forEach(item => {
            const input = item.querySelector('.test-case-input')?.value.trim();
            const output = item.querySelector('.test-case-output')?.value.trim();
            const hidden = item.querySelector('.test-case-hidden')?.checked || false;
            
            if (input && output) {
                testCases.push({ input, output, hidden });
            }
        });
        
        if (testCases.length === 0) {
            showSuccessNotification('Please add at least one test case.', 'error');
            return;
        }
        
        // Build description with constraints if provided
        let fullDescription = description;
        if (constraints) {
            fullDescription += `\n\nConstraints:\n${constraints}`;
        }
        
        const questionData = {
            create_new: true,
            question_data: {
                title,
                description: fullDescription,
                type: 'coding',
                difficulty,
                test_cases: testCases,
                starter_code: '',  // Empty starter code
                tags: []
            },
            marks
        };
        
        await facultyAPI.addQuestionToAssessment(currentAssessment.id, questionData);
        
        showSuccessNotification('Technical question added successfully!');
        closeTechnicalQuestionBuilder();
        loadAssessmentQuestions();
        
    } catch (error) {
        console.error('Error adding technical question:', error);
        showSuccessNotification(error.message || 'Failed to add question. Please try again.', 'error');
    }
}

async function submitNonTechnicalQuestion() {
    if (!currentAssessment || !currentAssessment.id) {
        showSuccessNotification('Please complete Step 1 first.', 'error');
        return;
    }
    
    try {
        const type = document.getElementById('nt-question-type').value;
        const questionText = document.getElementById('nt-assessment-question').value.trim();
        const marks = parseInt(document.getElementById('nt-assessment-marks').value);
        
        if (!type || !questionText) {
            showSuccessNotification('Please fill in all required fields.', 'error');
            return;
        }
        
        let questionData = {
            create_new: true,
            question_data: {
                title: questionText.substring(0, 100),
                description: questionText,
                type,
                difficulty: currentAssessment.difficulty || 'medium',
                tags: []
            },
            marks
        };
        
        if (type === 'mcq') {
            const options = [];
            document.querySelectorAll('.nt-option-input').forEach((input, index) => {
                const value = input.value.trim();
                if (value) {
                    options.push(value);
                }
            });
            
            const correctAnswer = document.getElementById('nt-assessment-correct-answer').value;
            
            if (options.length < 2) {
                showSuccessNotification('Please add at least 2 options.', 'error');
                return;
            }
            
            if (!correctAnswer) {
                showSuccessNotification('Please select the correct answer.', 'error');
                return;
            }
            
            questionData.question_data.options = options;
            questionData.question_data.correct_answer = correctAnswer;
        } else if (type === 'fill_blank') {
            const answer = document.getElementById('nt-fill-blank-answer').value.trim();
            const caseSensitive = document.getElementById('nt-case-sensitive')?.checked || false;
            
            if (!answer) {
                showSuccessNotification('Please enter the correct answer.', 'error');
                return;
            }
            
            questionData.question_data.blanks = answer.split('\n').filter(a => a.trim());
            questionData.question_data.case_sensitive = caseSensitive;
        }
        
        await facultyAPI.addQuestionToAssessment(currentAssessment.id, questionData);
        
        showSuccessNotification('Non-technical question added successfully!');
        closeNonTechnicalQuestionBuilder();
        loadAssessmentQuestions();
        
    } catch (error) {
        console.error('Error adding non-technical question:', error);
        showSuccessNotification(error.message || 'Failed to add question. Please try again.', 'error');
    }
}

function removeAssessmentQuestion(questionId) {
    if (!currentAssessment || !currentAssessment.id) return;
    
    if (!confirm('Are you sure you want to remove this question from the assessment?')) {
        return;
    }
    
    facultyAPI.removeQuestionFromAssessment(currentAssessment.id, questionId)
        .then(() => {
            showSuccessNotification('Question removed successfully!');
            loadAssessmentQuestions();
        })
        .catch(error => {
            console.error('Error removing question:', error);
            showSuccessNotification(error.message || 'Failed to remove question.', 'error');
        });
}

function editAssessmentQuestion(assessmentQuestionId, questionId) {
    if (!currentAssessment || !currentAssessment.id) return;
    
    // Load the question details using coding API for coding questions, or student API for others
    const loadQuestion = questionId => {
        // Try coding API first (for coding questions)
        return codingAPI.getQuestion(questionId)
            .catch(() => {
                // Fallback to student API
                return studentAPI.getQuestions({ question_id: questionId })
                    .then(response => {
                        const questions = response.questions || [];
                        if (questions.length === 0) {
                            throw new Error('Question not found');
                        }
                        return { question: questions[0] };
                    });
            });
    };
    
    loadQuestion(questionId)
        .then(response => {
            const question = response.question;
            
            if (question.type === 'coding') {
                // Open technical question builder with existing data
                openTechnicalQuestionBuilder();
                
                // Populate form with existing question data
                document.getElementById('tech-question-title').value = question.title || '';
                document.getElementById('tech-question-description').value = question.description || '';
                document.getElementById('tech-constraints').value = '';
                document.getElementById('tech-question-marks').value = question.marks || 10;
                document.getElementById('tech-question-difficulty').value = question.difficulty || 'medium';
                
                // Parse test cases if they exist
                let testCases = [];
                if (question.test_cases) {
                    try {
                        testCases = typeof question.test_cases === 'string' ? JSON.parse(question.test_cases) : question.test_cases;
                    } catch (e) {
                        console.error('Error parsing test cases:', e);
                    }
                }
                
                // Clear existing test cases and add the ones from the question
                const container = document.getElementById('tech-test-cases-container');
                if (container) {
                    container.innerHTML = '';
                    
                    if (testCases.length > 0) {
                        testCases.forEach((tc, index) => {
                            const testCaseHtml = `
                                <div class="test-case-item" style="margin-bottom: 15px; padding: 15px; background: white; border-radius: 8px; border: 1px solid #e0e0e0;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                        <strong>Test Case ${index + 1}</strong>
                                        <label style="display: flex; align-items: center; gap: 5px; font-size: 14px;">
                                            <input type="checkbox" class="test-case-hidden" ${tc.hidden ? 'checked' : ''}> Hidden
                                        </label>
                                    </div>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                                        <div>
                                            <label style="font-size: 12px; color: #666;">Input</label>
                                            <textarea class="test-case-input" rows="3" placeholder="Test input...">${tc.input || ''}</textarea>
                                        </div>
                                        <div>
                                            <label style="font-size: 12px; color: #666;">Expected Output</label>
                                            <textarea class="test-case-output" rows="3" placeholder="Expected output...">${tc.output || ''}</textarea>
                                        </div>
                                    </div>
                                    <button onclick="removeAssessmentTestCase(this)" class="btn btn-sm" style="background: #ff6b6b; color: white; padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Remove</button>
                                </div>
                            `;
                            container.insertAdjacentHTML('beforeend', testCaseHtml);
                        });
                    } else {
                        // Add one empty test case if none exist
                        addAssessmentTestCase();
                    }
                }
                
                // Store the question ID for update
                window.editingQuestionId = questionId;
                window.editingAssessmentQuestionId = assessmentQuestionId;
                
                // Change button text and onclick
                const submitBtn = document.querySelector('#technical-question-modal .btn-primary');
                if (submitBtn) {
                    submitBtn.textContent = 'Update Question';
                    submitBtn.onclick = updateTechnicalQuestion;
                }
            } else {
                // Handle non-technical questions
                openNonTechnicalQuestionBuilder();
                
                document.getElementById('nt-question-type').value = question.type || '';
                document.getElementById('nt-assessment-question').value = question.description || '';
                document.getElementById('nt-assessment-marks').value = question.marks || 1;
                
                if (question.type === 'mcq') {
                    handleNonTechQuestionTypeChange();
                    if (question.options) {
                        const options = typeof question.options === 'string' ? JSON.parse(question.options) : question.options;
                        const optionInputs = document.querySelectorAll('.nt-option-input');
                        options.forEach((opt, idx) => {
                            if (optionInputs[idx]) {
                                optionInputs[idx].value = opt;
                            }
                        });
                    }
                    if (question.correct_answer) {
                        document.getElementById('nt-assessment-correct-answer').value = question.correct_answer;
                    }
                } else if (question.type === 'fill_blank') {
                    handleNonTechQuestionTypeChange();
                    if (question.blanks) {
                        const blanks = typeof question.blanks === 'string' ? JSON.parse(question.blanks) : question.blanks;
                        document.getElementById('nt-fill-blank-answer').value = Array.isArray(blanks) ? blanks.join('\n') : blanks;
                    }
                }
                
                window.editingQuestionId = questionId;
                window.editingAssessmentQuestionId = assessmentQuestionId;
                
                const submitBtn = document.querySelector('#non-technical-question-modal .btn-primary');
                if (submitBtn) {
                    submitBtn.textContent = 'Update Question';
                    submitBtn.onclick = updateNonTechnicalQuestion;
                }
            }
        })
        .catch(error => {
            console.error('Error loading question:', error);
            showSuccessNotification('Failed to load question for editing.', 'error');
        });
}

async function updateTechnicalQuestion() {
    if (!currentAssessment || !currentAssessment.id || !window.editingQuestionId) {
        showSuccessNotification('Cannot update question.', 'error');
        return;
    }
    
    try {
        const title = document.getElementById('tech-question-title').value.trim();
        const description = document.getElementById('tech-question-description').value.trim();
        const constraints = document.getElementById('tech-constraints').value.trim();
        const marks = parseInt(document.getElementById('tech-question-marks').value);
        const difficulty = document.getElementById('tech-question-difficulty').value;
        
        if (!title || !description) {
            showSuccessNotification('Please fill in title and description.', 'error');
            return;
        }
        
        // Collect test cases
        const testCases = [];
        const testCaseItems = document.querySelectorAll('#tech-test-cases-container .test-case-item');
        testCaseItems.forEach(item => {
            const input = item.querySelector('.test-case-input')?.value.trim();
            const output = item.querySelector('.test-case-output')?.value.trim();
            const hidden = item.querySelector('.test-case-hidden')?.checked || false;
            
            if (input && output) {
                testCases.push({ input, output, hidden });
            }
        });
        
        if (testCases.length === 0) {
            showSuccessNotification('Please add at least one test case.', 'error');
            return;
        }
        
        let fullDescription = description;
        if (constraints) {
            fullDescription += `\n\nConstraints:\n${constraints}`;
        }
        
        // Update the question using faculty API
        await facultyAPI.updateQuestion(window.editingQuestionId, {
            title,
            description: fullDescription,
            difficulty,
            test_cases: testCases,
            starter_code: ''
        });
        
        showSuccessNotification('Question updated successfully!');
        closeTechnicalQuestionBuilder();
        
        // Reset editing state
        window.editingQuestionId = null;
        window.editingAssessmentQuestionId = null;
        
        // Reset button
        const submitBtn = document.querySelector('#technical-question-modal .btn-primary');
        if (submitBtn) {
            submitBtn.textContent = 'Add Question to Assessment';
            submitBtn.onclick = submitTechnicalQuestion;
        }
        
        loadAssessmentQuestions();
        
    } catch (error) {
        console.error('Error updating technical question:', error);
        showSuccessNotification(error.message || 'Failed to update question. Please try again.', 'error');
    }
}

async function updateNonTechnicalQuestion() {
    if (!currentAssessment || !currentAssessment.id || !window.editingQuestionId) {
        showSuccessNotification('Cannot update question.', 'error');
        return;
    }
    
    try {
        const type = document.getElementById('nt-question-type').value;
        const questionText = document.getElementById('nt-assessment-question').value.trim();
        const marks = parseInt(document.getElementById('nt-assessment-marks').value);
        
        if (!type || !questionText) {
            showSuccessNotification('Please fill in all required fields.', 'error');
            return;
        }
        
        let questionData = {
            title: questionText.substring(0, 100),
            description: questionText,
            type,
            difficulty: currentAssessment.difficulty || 'medium',
            tags: []
        };
        
        if (type === 'mcq') {
            const options = [];
            document.querySelectorAll('.nt-option-input').forEach((input) => {
                const value = input.value.trim();
                if (value) {
                    options.push(value);
                }
            });
            
            const correctAnswer = document.getElementById('nt-assessment-correct-answer').value;
            
            if (options.length < 2) {
                showSuccessNotification('Please add at least 2 options.', 'error');
                return;
            }
            
            if (!correctAnswer) {
                showSuccessNotification('Please select the correct answer.', 'error');
                return;
            }
            
            questionData.options = options;
            questionData.correct_answer = correctAnswer;
            questionData.marks = marks;
        } else if (type === 'fill_blank') {
            const answer = document.getElementById('nt-fill-blank-answer').value.trim();
            const caseSensitive = document.getElementById('nt-case-sensitive')?.checked || false;
            
            if (!answer) {
                showSuccessNotification('Please enter the correct answer.', 'error');
                return;
            }
            
            questionData.blanks = answer.split('\n').filter(a => a.trim());
            questionData.case_sensitive = caseSensitive;
        }
        
        // Update the question
        await facultyAPI.updateQuestion(window.editingQuestionId, questionData);
        
        showSuccessNotification('Question updated successfully!');
        closeNonTechnicalQuestionBuilder();
        
        // Reset editing state
        window.editingQuestionId = null;
        window.editingAssessmentQuestionId = null;
        
        // Reset button
        const submitBtn = document.querySelector('#non-technical-question-modal .btn-primary');
        if (submitBtn) {
            submitBtn.textContent = 'Add Question to Assessment';
            submitBtn.onclick = submitNonTechnicalQuestion;
        }
        
        loadAssessmentQuestions();
        
    } catch (error) {
        console.error('Error updating non-technical question:', error);
        showSuccessNotification(error.message || 'Failed to update question. Please try again.', 'error');
    }
}

function loadAssessmentReview() {
    if (!currentAssessment || !currentAssessment.id) return;
    
    facultyAPI.getAssessment(currentAssessment.id)
        .then(response => {
            const assessment = response.assessment;
            const summary = document.getElementById('assessment-review-summary');
            
            if (summary) {
                const technicalCount = assessment.technical_count || 0;
                const nonTechnicalCount = assessment.non_technical_count || 0;
                
                summary.innerHTML = `
                    <h4 style="margin-top: 0; color: #667eea;">Assessment Summary</h4>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-top: 20px; color: white;">
                        <div>
                            <strong style="color: white;">Title:</strong> <span style="color: #ccc;">${assessment.title}</span>
                        </div>
                        <div>
                            <strong style="color: white;">Mode:</strong> <span style="color: #ccc;">${assessment.assessment_mode === 'technical_only' ? 'Technical Only' : (assessment.assessment_mode === 'non_technical_only' ? 'Non-Technical Only' : 'Mixed')}</span>
                        </div>
                        <div>
                            <strong style="color: white;">Total Questions:</strong> <span style="color: #ccc;">${assessment.question_count || 0}</span>
                        </div>
                        <div>
                            <strong style="color: white;">Total Marks:</strong> <span style="color: #ccc;">${assessment.total_marks || 0}</span>
                        </div>
                        <div>
                            <strong style="color: white;">Technical Questions:</strong> <span style="color: #ccc;">${technicalCount}</span>
                        </div>
                        <div>
                            <strong style="color: white;">Non-Technical Questions:</strong> <span style="color: #ccc;">${nonTechnicalCount}</span>
                        </div>
                        <div>
                            <strong style="color: white;">Duration:</strong> <span style="color: #ccc;">${formatAssessmentDateTimeRange(assessment)}</span>
                        </div>
                        <div>
                            <strong style="color: white;">Difficulty:</strong> <span style="color: #ccc;">${assessment.difficulty.charAt(0).toUpperCase() + assessment.difficulty.slice(1)}</span>
                        </div>
                    </div>
                    ${assessment.topic_tags && assessment.topic_tags.length > 0 ? `
                        <div style="margin-top: 20px; color: white;">
                            <strong style="color: white;">Topic Tags:</strong> <span style="color: #ccc;">${assessment.topic_tags.join(', ')}</span>
                        </div>
                    ` : ''}
                `;
            }
        })
        .catch(error => {
            console.error('Error loading review:', error);
        });
}

async function saveAssessmentAsDraft() {
    if (!currentAssessment || !currentAssessment.id) {
        showSuccessNotification('No assessment to save.', 'error');
        return;
    }
    
    try {
        await facultyAPI.updateAssessment(currentAssessment.id, { status: 'draft' });
        showSuccessNotification('Assessment saved as draft successfully!');
    } catch (error) {
        console.error('Error saving draft:', error);
        showSuccessNotification(error.message || 'Failed to save draft.', 'error');
    }
}

async function publishAssessment() {
    if (!currentAssessment || !currentAssessment.id) {
        showSuccessNotification('No assessment to publish.', 'error');
        return;
    }
    
    if (assessmentQuestions.length === 0) {
        showSuccessNotification('Cannot publish assessment without questions. Please add at least one question.', 'error');
        goToAssessmentStep(2);
        return;
    }
    
    try {
        await facultyAPI.publishAssessment(currentAssessment.id);
        showSuccessNotification('Assessment published successfully!');
        
        // Reload assessment to get updated status
        const response = await facultyAPI.getAssessment(currentAssessment.id);
        currentAssessment = response.assessment;
        
        // Optionally redirect or show success message
        setTimeout(() => {
            showDashboard();
        }, 2000);
    } catch (error) {
        console.error('Error publishing assessment:', error);
        showSuccessNotification(error.message || 'Failed to publish assessment.', 'error');
    }
}

function addAssessmentTestCase() {
    const container = document.getElementById('tech-test-cases-container');
    if (!container) {
        console.error('Test cases container not found');
        return;
    }
    
    const count = container.querySelectorAll('.test-case-item').length + 1;
    const testCaseHtml = `
        <div class="test-case-item" style="margin-bottom: 15px; padding: 15px; background: white; border-radius: 8px; border: 1px solid #e0e0e0;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <strong>Test Case ${count}</strong>
                <label style="display: flex; align-items: center; gap: 5px; font-size: 14px;">
                    <input type="checkbox" class="test-case-hidden" checked> Hidden
                </label>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                <div>
                    <label style="font-size: 12px; color: #666;">Input</label>
                    <textarea class="test-case-input" rows="3" placeholder="Test input..."></textarea>
                </div>
                <div>
                    <label style="font-size: 12px; color: #666;">Expected Output</label>
                    <textarea class="test-case-output" rows="3" placeholder="Expected output..."></textarea>
                </div>
            </div>
            <button onclick="removeAssessmentTestCase(this)" class="btn btn-sm" style="background: #ff6b6b; color: white; padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Remove</button>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', testCaseHtml);
}

function removeAssessmentTestCase(button) {
    if (button && button.closest) {
        button.closest('.test-case-item').remove();
    }
}

function removeTestCase(button) {
    button.closest('.test-case-item').remove();
}

function toggleNonTechnicalMenu(event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    
    const menu = document.getElementById('non-technical-menu');
    if (!menu) return;
    
    // Try both parentElement and closest
    const dropdown = menu.parentElement || menu.closest('.nav-dropdown');
    if (!dropdown) return;
    
    const isOpen = dropdown.classList.contains('open');
    
    // Close other dropdowns first
    closeInterviewMenu();
    
    // Toggle this dropdown
    if (isOpen) {
        dropdown.classList.remove('open');
    } else {
        dropdown.classList.add('open');
    }
}

function closeNonTechnicalMenu() {
    const menu = document.getElementById('non-technical-menu');
    if (menu) {
        const dropdown = menu.parentElement || menu.closest('.nav-dropdown');
        if (dropdown) {
            dropdown.classList.remove('open');
        }
    }
}
function showResources() { 
    updateActiveNav('Resources');
    updateRoute('resources');
    showPage('resources', false);
    loadResourcesPage();
    // Hide upload form by default
    closeResourceUploadForm();
}
function showInterview() {
    // Close dropdown menu
    closeInterviewMenu();
    closeNonTechnicalMenu();
    updateActiveNav('Interview');
    
    // Cleanup any existing media before showing interview page
    if (typeof cleanupInterviewMedia === 'function') {
        cleanupInterviewMedia();
    }
    
    // Stop any existing proctoring
    if (typeof stopProctoring === 'function') {
        stopProctoring();
    }
    
    showPage('chatbot');
    
    // Initialize proctoring immediately when AI Virtual Interview screen opens
    // This ensures the screen is proctored from the start
    function initProctoringWithRetry(maxRetries = 10, delay = 200) {
        let retries = 0;
        
        function checkAndInit() {
            retries++;
            
            if (typeof initializeProctoring === 'function') {
                console.log('[Interview] âœ… Proctoring available. Initializing...');
                try {
                    initializeProctoring();
                    console.log('[Interview] âœ… Proctoring initialized successfully');
                } catch (error) {
                    console.error('[Interview] âŒ Error initializing proctoring:', error);
                }
                return true;
            }
            
            if (retries < maxRetries) {
                if (retries % 3 === 0) {
                    console.log(`[Interview] Waiting for proctoring.js to load... (attempt ${retries}/${maxRetries})`);
                }
                setTimeout(checkAndInit, delay);
                return false;
            } else {
                console.error('[Interview] âŒ Proctoring script not loaded after', maxRetries, 'attempts');
                console.error('[Interview] Make sure proctoring.js is included in index.html');
                return false;
            }
        }
        
        // Start checking
        checkAndInit();
    }
    
    // Start proctoring initialization
    initProctoringWithRetry();
    
    // Reset interview flow - show selfie capture first
    const selfieSection = document.getElementById('selfie-capture-section');
    const typeSelection = document.getElementById('interview-type-selection');
    const uploadSection = document.getElementById('interview-upload');
    const chatSection = document.getElementById('interview-chat');
    const resultsSection = document.getElementById('interview-results');
    
    // Hide all sections
    if (typeSelection) typeSelection.style.display = 'none';
    if (uploadSection) uploadSection.style.display = 'none';
    if (chatSection) chatSection.style.display = 'none';
    if (resultsSection) resultsSection.style.display = 'none';
    
    // Show selfie capture section (FIRST STEP)
    if (selfieSection) {
        selfieSection.style.display = 'block';
        // Reset selfie state
        if (typeof retakeSelfie === 'function') {
            retakeSelfie();
        }
    }
    
    // Clear any stored selfie session (start fresh)
    localStorage.removeItem('selfieSessionId');
    
    // Reset interview state
    if (typeof startNewInterview === 'function') {
        startNewInterview();
    }
}
function showCompanies() { 
    // Close dropdown menu
    closeInterviewMenu();
    closeNonTechnicalMenu();
    updateActiveNav('Interview');
    updateRoute('companies');
    showPage('companies', false);
    loadCompanies();
    loadPosts(); // Load posts when showing companies page
    
    // Clear company context when returning to companies list
    window.currentCompanyId = null;
    window.currentCompanyName = null;
    
    // Clear search when showing companies page
    companySearchTerm = '';
    const searchInput = document.getElementById('company-search-input');
    if (searchInput) {
        searchInput.value = '';
    }
    clearCompanySearch();
}

function filterCompanies() {
    const searchInput = document.getElementById('company-search-input');
    if (searchInput) {
        companySearchTerm = searchInput.value;
        renderCompanies();
        
        // Show/hide clear button
        const clearBtn = document.getElementById('clear-search-btn');
        if (clearBtn) {
            clearBtn.style.display = companySearchTerm.trim() ? 'block' : 'none';
        }
    }
}

function clearCompanySearch() {
    companySearchTerm = '';
    const searchInput = document.getElementById('company-search-input');
    if (searchInput) {
        searchInput.value = '';
    }
    const clearBtn = document.getElementById('clear-search-btn');
    if (clearBtn) {
        clearBtn.style.display = 'none';
    }
    const searchResultsDiv = document.getElementById('company-search-results');
    if (searchResultsDiv) {
        searchResultsDiv.style.display = 'none';
    }
    renderCompanies();
}
function showLeaderboard() { 
    updateActiveNav('Leaderboard');
    updateRoute('leaderboard');
    showPage('leaderboard', false); 
}

function showUsers() {
    // Only allow admin to access users page
    if (!currentUser || currentUser.role !== 'admin') {
        alert('Access denied. Only administrators can view users.');
        return;
    }
    updateActiveNav('Users');
    showPage('users');
    loadUsers();
}

// ==================== Assessment Management (Faculty/Admin) ====================

function showCodePractice() {
    updateActiveNav('Coding Practice');
    updateRoute('coding');
    showPage('coding', false); 
}

// Navigation functions for Placement Readiness Score links
function navigateToCodePractice() {
    showCodePractice();
}

function navigateToNonTechnical() {
    showNonTechnical();
}

function navigateToInterview() {
    showInterview();
}

function updateActiveNav(activeName) {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        const linkText = link.textContent.trim();
        // Handle dropdown toggle button separately
        if (link.classList.contains('dropdown-toggle')) {
            return;
        }
        if (linkText === activeName) {
            link.classList.add('active');
        }
    });
}

function toggleInterviewMenu(event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    
    const menu = document.getElementById('interview-menu');
    if (!menu) return;
    
    // Try both parentElement and closest
    const dropdown = menu.parentElement || menu.closest('.nav-dropdown');
    if (!dropdown) return;
    
    const isOpen = dropdown.classList.contains('open');
    
    // Close other dropdowns first
    closeNonTechnicalMenu();
    
    // Toggle this dropdown
    if (isOpen) {
        dropdown.classList.remove('open');
    } else {
        dropdown.classList.add('open');
    }
}

function closeInterviewMenu() {
    const menu = document.getElementById('interview-menu');
    if (menu) {
        const dropdown = menu.parentElement || menu.closest('.nav-dropdown');
        if (dropdown) {
            dropdown.classList.remove('open');
        }
    }
}

// Dashboard
async function loadDashboard() {
    try {
        // Get current user from state or global scope
        const authState = getState('auth');
        const user = authState.user || window.currentUser || currentUser;
        
        if (!user) {
            console.error('[Dashboard] No user found, cannot load dashboard');
            return;
        }
        
        console.log(`[Dashboard] Loading dashboard for role: ${user.role}`);
        
        // Show loading state immediately
        const studentDashboard = document.getElementById('student-dashboard');
        const facultyDashboard = document.getElementById('faculty-admin-dashboard');
        const publicDashboard = document.getElementById('public-demo-dashboard');
        if (publicDashboard) publicDashboard.style.display = 'none';
        
        // Check user role and load appropriate dashboard
        if (user.role === 'faculty' || user.role === 'admin') {
            // Show faculty/admin dashboard immediately
            if (studentDashboard) studentDashboard.style.display = 'none';
            if (facultyDashboard) {
                facultyDashboard.style.display = 'block';
                console.log('[Dashboard] âœ… Faculty/Admin dashboard shown');
            } else {
                console.error('[Dashboard] âŒ Faculty/Admin dashboard element not found');
            }
            
            // Load data asynchronously
            loadFacultyAdminDashboard().catch(err => {
                console.error('[Dashboard] Error loading faculty/admin dashboard:', err);
            });
            return;
        }
        
        // Student dashboard - show immediately
        if (studentDashboard) {
            studentDashboard.style.display = 'grid';
            console.log('[Dashboard] âœ… Student dashboard shown');
        } else {
            console.error('[Dashboard] âŒ Student dashboard element not found');
        }
        if (facultyDashboard) facultyDashboard.style.display = 'none';
        
        // Load all student dashboard data in parallel for faster loading
        console.log('[Dashboard] Loading student dashboard data...');
        const [dashboardData, readinessData, trendsData, streaksData] = await Promise.allSettled([
            studentAPI.getDashboard().catch(err => {
                console.warn('[Dashboard] Error loading dashboard data:', err);
                return null;
            }),
            loadPlacementReadinessScore().catch(err => {
                console.warn('[Dashboard] Error loading readiness score:', err);
            }),
            loadProgressTrends().catch(err => {
                console.warn('[Dashboard] Error loading progress trends:', err);
            }),
            loadDailyStreaks().catch(err => {
                console.warn('[Dashboard] Error loading daily streaks:', err);
            })
        ]);
        
        console.log('[Dashboard] âœ… Student dashboard data loaded');
    } catch (error) {
        console.error('[Dashboard] Error loading dashboard:', error);
    }
}

// Faculty/Admin Dashboard
async function loadFacultyAdminDashboard() {
    try {
        // Get current user from state or global scope
        const authState = getState('auth');
        const user = authState.user || window.currentUser || currentUser;
        
        if (!user) {
            console.error('[Faculty/Admin Dashboard] No user found');
            return;
        }
        
        console.log(`[Faculty/Admin Dashboard] Loading dashboard for role: ${user.role}`);
        
        // Ensure dashboard is visible
        const studentDashboard = document.getElementById('student-dashboard');
        const facultyDashboard = document.getElementById('faculty-admin-dashboard');
        
        if (studentDashboard) studentDashboard.style.display = 'none';
        if (facultyDashboard) {
            facultyDashboard.style.display = 'block';
        } else {
            console.error('[Faculty/Admin Dashboard] âŒ Dashboard element not found');
            return;
        }
        
        // Load dashboard data based on role
        let dashboardData;
        try {
            if (user.role === 'admin') {
                console.log('[Faculty/Admin Dashboard] Loading admin dashboard data...');
                dashboardData = await adminAPI.getDashboard();
            } else {
                console.log('[Faculty/Admin Dashboard] Loading faculty dashboard data...');
                dashboardData = await facultyAPI.getDashboard();
            }
            console.log('[Faculty/Admin Dashboard] âœ… Dashboard data loaded:', dashboardData);
        } catch (apiError) {
            console.error('[Faculty/Admin Dashboard] Error fetching dashboard data:', apiError);
            throw apiError;
        }
        
        // Update batch overview
        if (dashboardData && dashboardData.batch_analytics) {
            const analytics = dashboardData.batch_analytics;
            const totalStudentsEl = document.getElementById('batch-total-students');
            const totalSubmissionsEl = document.getElementById('batch-total-submissions');
            const totalQuizzesEl = document.getElementById('batch-total-quizzes');
            const avgAccuracyEl = document.getElementById('batch-avg-accuracy');
            const avgQuizScoreEl = document.getElementById('batch-avg-quiz-score');
            
            if (totalStudentsEl) {
                totalStudentsEl.textContent = analytics.total_students || 0;
                console.log('[Faculty/Admin Dashboard] Updated total students:', analytics.total_students);
            }
            if (totalSubmissionsEl) {
                totalSubmissionsEl.textContent = analytics.total_submissions || 0;
                console.log('[Faculty/Admin Dashboard] Updated total submissions:', analytics.total_submissions);
            }
            if (totalQuizzesEl) {
                totalQuizzesEl.textContent = analytics.total_quiz_attempts || 0;
                console.log('[Faculty/Admin Dashboard] Updated total quizzes:', analytics.total_quiz_attempts);
            }
            if (avgAccuracyEl) {
                avgAccuracyEl.textContent = `${analytics.batch_avg_accuracy || 0}%`;
                console.log('[Faculty/Admin Dashboard] Updated avg accuracy:', analytics.batch_avg_accuracy);
            }
            if (avgQuizScoreEl) {
                avgQuizScoreEl.textContent = analytics.batch_avg_quiz_score || 0;
                console.log('[Faculty/Admin Dashboard] Updated avg quiz score:', analytics.batch_avg_quiz_score);
            }
        } else {
            console.warn('[Faculty/Admin Dashboard] No batch analytics data in response');
        }
        
        // Load student performance and readiness in parallel
        await Promise.allSettled([
            loadStudentPerformanceTable().catch(err => {
                console.warn('[Faculty/Admin Dashboard] Error loading student performance:', err);
            }),
            loadPlacementReadinessScore().catch(err => {
                console.warn('[Faculty/Admin Dashboard] Error loading readiness score:', err);
            })
        ]);
        
        console.log('[Faculty/Admin Dashboard] âœ… Dashboard fully loaded');
    } catch (error) {
        console.error('[Faculty/Admin Dashboard] Error loading dashboard:', error);
        // Show error message to user
        const facultyDashboard = document.getElementById('faculty-admin-dashboard');
        if (facultyDashboard) {
            const errorMsg = document.createElement('div');
            errorMsg.className = 'error-message';
            errorMsg.style.cssText = 'padding: 20px; background: #ffebee; color: #c62828; border-radius: 8px; margin: 20px;';
            errorMsg.textContent = `Error loading dashboard: ${error.message || 'Unknown error'}`;
            facultyDashboard.insertBefore(errorMsg, facultyDashboard.firstChild);
        }
    }
}

// Load Placement Readiness Score
async function loadPlacementReadinessScore(userId = null) {
    try {
        const data = await studentAPI.getPlacementReadiness(userId);
        
        console.log('Placement Readiness Data:', data); // Debug log
        
        // Determine which elements to update based on dashboard type
        const isFacultyDashboard = document.getElementById('faculty-admin-dashboard')?.style.display !== 'none';
        const scoreValueId = isFacultyDashboard ? 'faculty-placement-score-value' : 'placement-score-value';
        const codePracticeId = isFacultyDashboard ? 'faculty-code-practice-score' : 'code-practice-score';
        const nonTechnicalId = isFacultyDashboard ? 'faculty-non-technical-score' : 'non-technical-score';
        const interviewId = isFacultyDashboard ? 'faculty-interview-score' : 'interview-score';
        const contentId = isFacultyDashboard ? 'faculty-placement-readiness-content' : 'placement-readiness-content';
        
        // Update main score
        const scoreValueEl = document.getElementById(scoreValueId);
        if (scoreValueEl) {
            const score = Math.round(data.placement_readiness_score || 0);
            scoreValueEl.textContent = score;
            console.log(`Updated ${scoreValueId} to ${score}`); // Debug log
            
            // Add color class based on score
            scoreValueEl.className = '';
            if (score >= 80) {
                scoreValueEl.classList.add('score-excellent');
            } else if (score >= 60) {
                scoreValueEl.classList.add('score-good');
            } else if (score >= 40) {
                scoreValueEl.classList.add('score-medium');
            } else {
                scoreValueEl.classList.add('score-poor');
            }
        }
        
        // Update breakdown scores
        const breakdown = data.breakdown || {};
        const codePracticeEl = document.getElementById(codePracticeId);
        const nonTechnicalEl = document.getElementById(nonTechnicalId);
        const interviewEl = document.getElementById(interviewId);
        
        if (codePracticeEl) {
            const codePracticeScore = Math.round(breakdown.code_practice || 0);
            codePracticeEl.textContent = `${codePracticeScore}%`;
            codePracticeEl.className = 'breakdown-value ' + getScoreClass(breakdown.code_practice || 0);
        }
        if (nonTechnicalEl) {
            const nonTechnicalScore = Math.round(breakdown.non_technical || 0);
            nonTechnicalEl.textContent = `${nonTechnicalScore}%`;
            nonTechnicalEl.className = 'breakdown-value ' + getScoreClass(breakdown.non_technical || 0);
        }
        if (interviewEl) {
            const interviewScore = Math.round(breakdown.interview || 0);
            interviewEl.textContent = `${interviewScore}%`;
            interviewEl.className = 'breakdown-value ' + getScoreClass(breakdown.interview || 0);
        }
        
        // Show/hide message based on data availability
        // Note: Don't clear innerHTML as it contains the score display elements
        const contentEl = document.getElementById(contentId);
        if (contentEl) {
            // Check if there's a "no data" message element
            let noDataMsg = contentEl.querySelector('.no-data-message');
            
            // Check if any data is available
            const hasData = data.data_available && (
                data.data_available.code_practice || 
                data.data_available.non_technical || 
                data.data_available.interview
            );
            
            if (!hasData) {
                // Show no data message (only if it doesn't exist and score elements don't exist)
                const hasScoreElements = contentEl.querySelector('#placement-score-value') || 
                                       contentEl.querySelector('#faculty-placement-score-value');
                
                if (!hasScoreElements) {
                    // If score elements don't exist, show full message
                    if (!noDataMsg) {
                        contentEl.innerHTML = '<p class="no-data-message" style="text-align: center; color: rgba(232,236,243,0.6); padding: 20px;">Complete Code Practice challenges, Non-Technical quizzes, and AI Virtual Interviews to see your Placement Readiness Score</p>';
                    }
                } else {
                    // Score elements exist, just add message below
                    if (!noDataMsg) {
                        const msgEl = document.createElement('p');
                        msgEl.className = 'no-data-message';
                        msgEl.style.cssText = 'text-align: center; color: rgba(232,236,243,0.6); padding: 20px; margin-top: 20px;';
                        msgEl.textContent = 'Complete more Code Practice, Non-Technical quizzes, or AI Virtual Interviews to improve your score';
                        contentEl.appendChild(msgEl);
                    }
                }
            } else {
                // Data is available - remove no data message if it exists
                if (noDataMsg) {
                    noDataMsg.remove();
                }
            }
        }
    } catch (error) {
        console.error('Error loading placement readiness score:', error);
        const isFacultyDashboard = document.getElementById('faculty-admin-dashboard')?.style.display !== 'none';
        const contentId = isFacultyDashboard ? 'faculty-placement-readiness-content' : 'placement-readiness-content';
        const contentEl = document.getElementById(contentId);
        if (contentEl) {
            let errorMsg = 'Error loading Placement Readiness Score';
            if (error.message) {
                if (error.message.includes('Cannot connect to server')) {
                    errorMsg = 'Cannot connect to server. Please ensure the backend is running.';
                } else if (error.message.includes('401') || error.message.includes('Unauthorized')) {
                    errorMsg = 'Please log in again to view your Placement Readiness Score.';
                } else {
                    errorMsg = error.message;
                }
            }
            contentEl.innerHTML = `<p style="text-align: center; color: #ff6b6b; padding: 20px;">${errorMsg}</p>`;
        }
    }
}

// Progress Trend Graph
let progressChart = null;

async function loadProgressTrends() {
    try {
        const data = await studentAPI.getProgressTrends();
        
        const ctx = document.getElementById('progress-trend-chart');
        if (!ctx) return;
        
        // Destroy existing chart if it exists
        if (progressChart) {
            progressChart.destroy();
        }
        
        // Format dates for display (show day name)
        const formattedDates = data.dates.map(dateStr => {
            const date = new Date(dateStr);
            const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
            return days[date.getDay()];
        });
        
        progressChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: formattedDates,
                datasets: [
                    {
                        label: 'Placement Score',
                        data: data.placement_scores,
                        borderColor: '#6c5ce7',
                        backgroundColor: 'rgba(108, 92, 231, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Coding Accuracy',
                        data: data.coding_accuracy,
                        borderColor: '#00b894',
                        backgroundColor: 'rgba(0, 184, 148, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Interview Score',
                        data: data.interview_scores,
                        borderColor: '#fdcb6e',
                        backgroundColor: 'rgba(253, 203, 110, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#f2f4ff'
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            color: '#f2f4ff',
                            callback: function(value) {
                                return value + '%';
                            }
                        },
                        grid: {
                            color: 'rgba(242, 244, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#f2f4ff'
                        },
                        grid: {
                            color: 'rgba(242, 244, 255, 0.1)'
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading progress trends:', error);
    }
}

// Daily Streaks
async function loadDailyStreaks() {
    try {
        const data = await studentAPI.getDailyStreaks();
        
        const codingStreakEl = document.getElementById('coding-streak');
        const quizStreakEl = document.getElementById('quiz-streak');
        const interviewStreakEl = document.getElementById('interview-streak');
        
        if (codingStreakEl) codingStreakEl.textContent = data.coding_streak || 0;
        if (quizStreakEl) quizStreakEl.textContent = data.quiz_streak || 0;
        if (interviewStreakEl) interviewStreakEl.textContent = data.interview_streak || 0;
        
        // Add fire emoji for streaks >= 7 days
        if (codingStreakEl && data.coding_streak >= 7) {
            codingStreakEl.textContent = `ðŸ”¥ ${data.coding_streak}`;
        }
        if (quizStreakEl && data.quiz_streak >= 7) {
            quizStreakEl.textContent = `ðŸ”¥ ${data.quiz_streak}`;
        }
        if (interviewStreakEl && data.interview_streak >= 7) {
            interviewStreakEl.textContent = `ðŸ”¥ ${data.interview_streak}`;
        }
    } catch (error) {
        console.error('Error loading daily streaks:', error);
    }
}

// Helper function to format question description with LeetCode-style formatting
function formatQuestionDescription(description) {
    if (!description) return '';
    
    // Escape HTML to prevent XSS, but preserve some formatting
    const escapeHtml = (text) => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };
    
    // Process inline code patterns (like nums[i], nums[j], etc.)
    const processInlineCode = (text) => {
        // Match patterns like nums[i], nums[j], nums[k], array[i], etc.
        // Also match code-like patterns: `code`, variable names in backticks
        return text
            // Match backtick-wrapped code
            .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
            // Match array indexing patterns: nums[i], arr[j], etc.
            .replace(/(\w+)\[(\w+)\]/g, '<code class="inline-code">$1[$2]</code>')
            // Match function calls: func(), method(), etc.
            .replace(/(\w+)\(/g, '<code class="inline-code">$1</code>(')
            // Match common variable patterns in problem descriptions
            .replace(/\b(nums|arr|array|list|str|string|target|result|output|input)\b/g, '<code class="inline-code">$1</code>');
    };
    
    const lines = description.split('\n');
    let html = '';
    let inCodeBlock = false;
    let codeBlockContent = [];
    let currentParagraph = [];
    let inExample = false;
    let exampleContent = [];
    
    const flushParagraph = () => {
        if (currentParagraph.length > 0) {
            const paraText = currentParagraph.join(' ').trim();
            if (paraText) {
                html += `<p>${processInlineCode(escapeHtml(paraText))}</p>`;
            }
            currentParagraph = [];
        }
    };
    
    const flushCodeBlock = () => {
        if (codeBlockContent.length > 0) {
            const code = codeBlockContent.join('\n');
            html += `<pre class="leetcode-code-block"><code>${escapeHtml(code)}</code></pre>`;
            codeBlockContent = [];
        }
        inCodeBlock = false;
    };
    
    const flushExample = () => {
        if (exampleContent.length > 0) {
            html += '<div class="leetcode-example">';
            html += exampleContent.join('');
            html += '</div>';
            exampleContent = [];
        }
        inExample = false;
    };
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();
        const nextLine = i < lines.length - 1 ? lines[i + 1].trim() : '';
        
        // Detect code blocks (indented lines, code-like patterns)
        const isCodeLine = (trimmed.startsWith('    ') || trimmed.startsWith('\t')) && 
                          (trimmed.includes('=') || trimmed.includes(':') || 
                           trimmed.includes('(') || trimmed.includes('[') ||
                           /^\s*(if|for|while|def|class|import|print|return|function|const|let|var)\s/.test(trimmed));
        
        // Detect example sections
        const isExampleHeader = /^Example\s+\d+:/i.test(trimmed);
        const isInputLine = /^Input:/i.test(trimmed);
        const isOutputLine = /^Output:/i.test(trimmed);
        const isExplanationLine = /^Explanation:/i.test(trimmed);
        
        if (isExampleHeader) {
            flushCodeBlock();
            flushParagraph();
            flushExample();
            inExample = true;
            exampleContent.push(`<div class="leetcode-example-header">${processInlineCode(escapeHtml(trimmed))}</div>`);
        } else if (inExample) {
            if (isInputLine) {
                const content = trimmed.replace(/^Input:\s*/i, '').trim();
                exampleContent.push(`<div class="leetcode-example-item"><strong>Input:</strong> <code class="leetcode-example-code">${escapeHtml(content)}</code></div>`);
            } else if (isOutputLine) {
                const content = trimmed.replace(/^Output:\s*/i, '').trim();
                exampleContent.push(`<div class="leetcode-example-item"><strong>Output:</strong> <code class="leetcode-example-code">${escapeHtml(content)}</code></div>`);
            } else if (isExplanationLine) {
                const explanation = trimmed.replace(/^Explanation:\s*/i, '').trim();
                if (explanation) {
                    exampleContent.push(`<div class="leetcode-example-item"><strong>Explanation:</strong> <span class="leetcode-example-text">${processInlineCode(escapeHtml(explanation))}</span></div>`);
                }
            } else if (trimmed && !isCodeLine) {
                // Continuation of explanation
                if (exampleContent.length > 0) {
                    const lastItem = exampleContent[exampleContent.length - 1];
                    if (lastItem.includes('Explanation:')) {
                        exampleContent[exampleContent.length - 1] = lastItem.replace(
                            /<\/span>$/,
                            ` ${processInlineCode(escapeHtml(trimmed))}</span>`
                        );
                    } else {
                        exampleContent.push(`<div class="leetcode-example-item"><span class="leetcode-example-text">${processInlineCode(escapeHtml(trimmed))}</span></div>`);
                    }
                }
            } else if (trimmed === '') {
                // Empty line in example - might be end of example
                if (nextLine && !isExampleHeader && !isInputLine && !isOutputLine && !isExplanationLine) {
                    flushExample();
                }
            }
        } else if (isCodeLine || (trimmed && /^[\s\t]+/.test(line) && trimmed.length > 0)) {
            // Code block line
            if (!inCodeBlock) {
                flushParagraph();
                inCodeBlock = true;
            }
            // Remove leading indentation but preserve relative indentation
            const codeLine = line.replace(/^[\s\t]{4}/, '').replace(/^[\s\t]{1,3}/, '  ');
            codeBlockContent.push(codeLine);
        } else if (trimmed === '') {
            // Empty line
            flushCodeBlock();
            flushParagraph();
            if (!inExample) {
                html += '<br>';
            }
        } else {
            // Regular text line
            flushCodeBlock();
            currentParagraph.push(trimmed);
        }
    }
    
    // Flush any remaining content
    flushCodeBlock();
    flushParagraph();
    flushExample();
    
    return html || '<p>No description available.</p>';
}

// Helper function to get score class for styling
function getScoreClass(score) {
    if (score >= 80) return 'score-excellent';
    if (score >= 60) return 'score-good';
    if (score >= 40) return 'score-medium';
    return 'score-poor';
}

// Load Student Performance Table
async function loadStudentPerformanceTable() {
    try {
        // Double-check user role - only faculty/admin should access this
        if (!currentUser || (currentUser.role !== 'faculty' && currentUser.role !== 'admin')) {
            console.warn('Student Performance table access denied - students cannot view this');
            return;
        }
        
        const performanceData = await facultyAPI.getStudentPerformance();
        const tableBody = document.getElementById('student-performance-table');
        
        if (!tableBody) return;
        
        if (performanceData.performance && performanceData.performance.length > 0) {
            tableBody.innerHTML = performanceData.performance.map(perf => {
                const student = perf.student;
                return `
                    <tr>
                        <td>
                            <a href="#" class="student-name-link" data-student-id="${student.id}" data-student-name="${student.full_name || student.username}">
                                ${student.full_name || 'N/A'}
                            </a>
                        </td>
                        <td>${student.username}</td>
                        <td>${perf.total_submissions || 0}</td>
                        <td>
                            <span class="accuracy-badge ${perf.accuracy >= 70 ? 'good' : perf.accuracy >= 50 ? 'medium' : 'poor'}">
                                ${perf.accuracy || 0}%
                            </span>
                        </td>
                        <td>${perf.total_quizzes || 0}</td>
                        <td>${perf.avg_quiz_score || 0}</td>
                    </tr>
                `;
            }).join('');
            
            // Add click event listeners to student name links
            document.querySelectorAll('.student-name-link').forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const studentId = parseInt(link.getAttribute('data-student-id'));
                    const studentName = link.getAttribute('data-student-name');
                    showStudentDetailsModal(studentId, studentName);
                });
            });
        } else {
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px;">No student data available</td></tr>';
        }
    } catch (error) {
        console.error('Error loading student performance:', error);
        const tableBody = document.getElementById('student-performance-table');
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px; color: #ff6b6b;">Error loading student data</td></tr>';
        }
    }
}

// Show student details modal
async function showStudentDetailsModal(studentId, studentName) {
    try {
        // Show loading state
        const modal = document.getElementById('student-details-modal');
        if (!modal) {
            console.error('Student details modal not found');
            return;
        }
        
        modal.style.display = 'flex';
        document.getElementById('student-details-content').innerHTML = '<div style="text-align: center; padding: 40px;"><div class="spinner"></div><p>Loading student details...</p></div>';
        
        // Fetch student details
        const details = await facultyAPI.getStudentDetails(studentId);
        
        // Render student details
        renderStudentDetails(details, studentName);
        
    } catch (error) {
        console.error('Error loading student details:', error);
        const content = document.getElementById('student-details-content');
        if (content) {
            content.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #ff6b6b;">
                    <p>Error loading student details. Please try again.</p>
                    <button class="btn-secondary" onclick="closeStudentDetailsModal()">Close</button>
                </div>
            `;
        }
    }
}

// Render student details in modal
function renderStudentDetails(details, studentName) {
    const content = document.getElementById('student-details-content');
    const student = details.student;
    const summary = details.summary;
    
    // Format date helper
    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    };
    
    // Status badge helper
    const getStatusBadge = (status) => {
        const statusClass = status === 'accepted' ? 'good' : status === 'wrong_answer' ? 'poor' : 'medium';
        return `<span class="accuracy-badge ${statusClass}">${status || 'N/A'}</span>`;
    };
    
    content.innerHTML = `
        <div class="student-details-header">
            <h2>ðŸ“Š ${studentName}'s Performance Details</h2>
            <button class="close-modal-btn" onclick="closeStudentDetailsModal()">Ã—</button>
        </div>
        
        <div class="student-details-summary">
            <div class="summary-card">
                <h3>ðŸ“ Code Practice</h3>
                <p>Total: ${summary.total_code_submissions}</p>
                <p>Accepted: ${summary.accepted_submissions}</p>
            </div>
            <div class="summary-card">
                <h3>ðŸ“‹ Quizzes</h3>
                <p>Attempts: ${summary.total_quiz_attempts}</p>
            </div>
            <div class="summary-card">
                <h3>ðŸŽ¤ Interviews</h3>
                <p>Total: ${summary.total_interview_attempts}</p>
                <p>Completed: ${summary.completed_interviews}</p>
            </div>
        </div>
        
        <div class="student-details-tabs">
            <button class="tab-btn active" onclick="switchStudentDetailTab('code-practice')">Code Practice</button>
            <button class="tab-btn" onclick="switchStudentDetailTab('quizzes')">Quiz Attempts</button>
            <button class="tab-btn" onclick="switchStudentDetailTab('interviews')">Interview Attempts</button>
            <button class="tab-btn" onclick="switchStudentDetailTab('feedback')">Give Feedback</button>
        </div>
        
        <div class="student-details-body">
            <!-- Code Practice Tab -->
            <div id="tab-code-practice" class="detail-tab active">
                <h3>Code Practice History</h3>
                ${details.code_practice && details.code_practice.length > 0 ? `
                    <div class="details-table-container">
                        <table class="details-table">
                            <thead>
                                <tr>
                                    <th>Question</th>
                                    <th>Language</th>
                                    <th>Status</th>
                                    <th>Submitted At</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${details.code_practice.map(sub => `
                                    <tr>
                                        <td>${sub.question ? (sub.question.title || 'N/A') : 'N/A'}</td>
                                        <td>${sub.language || 'N/A'}</td>
                                        <td>${getStatusBadge(sub.status)}</td>
                                        <td>${formatDate(sub.submitted_at)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                ` : '<p style="text-align: center; padding: 20px; color: rgba(232,236,243,0.6);">No code practice submissions yet.</p>'}
            </div>
            
            <!-- Quiz Attempts Tab -->
            <div id="tab-quizzes" class="detail-tab">
                <h3>Quiz Attempts</h3>
                ${details.quiz_attempts && details.quiz_attempts.length > 0 ? `
                    <div class="details-table-container">
                        <table class="details-table">
                            <thead>
                                <tr>
                                    <th>Quiz</th>
                                    <th>Score</th>
                                    <th>Submitted At</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${details.quiz_attempts.map(attempt => `
                                    <tr>
                                        <td>${attempt.quiz ? (attempt.quiz.title || 'N/A') : 'N/A'}</td>
                                        <td><span class="accuracy-badge ${attempt.score >= 70 ? 'good' : attempt.score >= 50 ? 'medium' : 'poor'}">${attempt.score || 0}</span></td>
                                        <td>${formatDate(attempt.submitted_at)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                ` : '<p style="text-align: center; padding: 20px; color: rgba(232,236,243,0.6);">No quiz attempts yet.</p>'}
            </div>
            
            <!-- Interview Attempts Tab -->
            <div id="tab-interviews" class="detail-tab">
                <h3>AI Interview Attempts</h3>
                ${details.interview_attempts && details.interview_attempts.length > 0 ? `
                    <div class="details-table-container">
                        <table class="details-table">
                            <thead>
                                <tr>
                                    <th>Type</th>
                                    <th>Score</th>
                                    <th>Status</th>
                                    <th>Started At</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${details.interview_attempts.map(interview => `
                                    <tr>
                                        <td>${interview.interview_type || 'N/A'}</td>
                                        <td><span class="accuracy-badge ${interview.final_score >= 70 ? 'good' : interview.final_score >= 50 ? 'medium' : 'poor'}">${interview.final_score || 0}%</span></td>
                                        <td>${interview.is_completed ? '<span class="accuracy-badge good">Completed</span>' : '<span class="accuracy-badge medium">In Progress</span>'}</td>
                                        <td>${formatDate(interview.started_at)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                ` : '<p style="text-align: center; padding: 20px; color: rgba(232,236,243,0.6);">No interview attempts yet.</p>'}
            </div>
            
            <!-- Feedback Tab -->
            <div id="tab-feedback" class="detail-tab">
                <h3>Give Feedback to ${studentName}</h3>
                <form id="student-feedback-form" onsubmit="submitStudentFeedback(event, ${student.id}, '${studentName}')">
                    <div class="form-group">
                        <label for="feedback-title">Title</label>
                        <input type="text" id="feedback-title" name="title" placeholder="Feedback Title" value="Feedback from Faculty" required>
                    </div>
                    <div class="form-group">
                        <label for="feedback-message">Message</label>
                        <textarea id="feedback-message" name="message" rows="6" placeholder="Enter your feedback message..." required></textarea>
                    </div>
                    <div class="form-group">
                        <label for="feedback-link">Link (Optional)</label>
                        <input type="text" id="feedback-link" name="link" placeholder="e.g., /coding/questions/123">
                    </div>
                    <button type="submit" class="btn-primary">
                        <span>ðŸ“¤</span>
                        <span>Send Feedback</span>
                    </button>
                </form>
            </div>
        </div>
    `;
}

// Switch tabs in student details modal
function switchStudentDetailTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.detail-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    const selectedTab = document.getElementById(`tab-${tabName}`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Add active class to clicked button
    event.target.classList.add('active');
}

// Close student details modal
function closeStudentDetailsModal() {
    const modal = document.getElementById('student-details-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Show success notification modal
function showSuccessNotification(message, type = 'success') {
    const modal = document.getElementById('success-notification-modal');
    const messageEl = document.getElementById('success-notification-message');
    const iconEl = modal.querySelector('.notification-icon');
    const titleEl = modal.querySelector('.notification-title');
    
    if (!modal || !messageEl) return;
    
    // Set message
    messageEl.textContent = message;
    
    // Update styling based on type
    if (type === 'error') {
        iconEl.textContent = 'âœ•';
        iconEl.style.background = 'linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%)';
        titleEl.textContent = 'Error';
        titleEl.style.color = '#ff6b6b';
    } else {
        iconEl.textContent = 'âœ“';
        iconEl.style.background = 'linear-gradient(135deg, #66e3c4 0%, #42d3b8 100%)';
        titleEl.textContent = 'Success!';
        titleEl.style.color = '#66e3c4';
    }
    
    // Show modal
    modal.style.display = 'flex';
    
    // Auto-close after 3 seconds for success, 5 seconds for error
    const autoCloseTime = type === 'error' ? 5000 : 3000;
    setTimeout(() => {
        closeSuccessNotification();
    }, autoCloseTime);
}

// Close success notification modal
function closeSuccessNotification() {
    const modal = document.getElementById('success-notification-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Toggle download dropdown
function toggleDownloadDropdown(event) {
    event.stopPropagation();
    const dropdown = document.getElementById('download-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('download-dropdown');
    const container = document.querySelector('.download-dropdown-container');
    if (dropdown && container && !container.contains(event.target)) {
        dropdown.classList.remove('show');
    }
});

// Export Student Performance as PDF (Faculty/Admin Only)
async function exportStudentPerformancePDF() {
    // Check user role - only faculty/admin can export
    if (!currentUser || (currentUser.role !== 'faculty' && currentUser.role !== 'admin')) {
        showSuccessNotification('Access denied. Only faculty and administrators can export student performance.', 'error');
        return;
    }
    
    // Close dropdown
    const dropdown = document.getElementById('download-dropdown');
    if (dropdown) {
        dropdown.classList.remove('show');
    }
    
    try {
        const option = event.target.closest('.download-option');
        if (option) {
            option.disabled = true;
            option.innerHTML = '<span>â³</span> Generating PDF...';
        }
        
        await facultyAPI.exportStudentPerformancePDF();
        
        showSuccessNotification('Student Performance PDF exported successfully!');
        
        if (option) {
            option.disabled = false;
            option.innerHTML = '<span>ðŸ“„</span> Student Performance (PDF)';
        }
    } catch (error) {
        console.error('Error exporting PDF:', error);
        showSuccessNotification('Error exporting PDF. Please try again.', 'error');
        const option = document.querySelector('.download-option');
        if (option && option.innerHTML.includes('PDF')) {
            option.disabled = false;
            option.innerHTML = '<span>ðŸ“„</span> Student Performance (PDF)';
        }
    }
}

// Export Batch Analytics as CSV (Faculty/Admin Only)
async function exportBatchAnalyticsCSV() {
    // Check user role - only faculty/admin can export
    if (!currentUser || (currentUser.role !== 'faculty' && currentUser.role !== 'admin')) {
        showSuccessNotification('Access denied. Only faculty and administrators can export batch analytics.', 'error');
        return;
    }
    
    // Close dropdown
    const dropdown = document.getElementById('download-dropdown');
    if (dropdown) {
        dropdown.classList.remove('show');
    }
    
    try {
        const option = event.target.closest('.download-option');
        if (option) {
            option.disabled = true;
            option.innerHTML = '<span>â³</span> Generating CSV...';
        }
        
        await facultyAPI.exportBatchAnalyticsCSV();
        
        showSuccessNotification('Batch Analytics CSV exported successfully!');
        
        if (option) {
            option.disabled = false;
            option.innerHTML = '<span>ðŸ“Š</span> Batch Analytics (CSV)';
        }
    } catch (error) {
        console.error('Error exporting CSV:', error);
        showSuccessNotification('Error exporting CSV. Please try again.', 'error');
        const option = document.querySelectorAll('.download-option')[1];
        if (option && option.innerHTML.includes('CSV')) {
            option.disabled = false;
            option.innerHTML = '<span>ðŸ“Š</span> Batch Analytics (CSV)';
        }
    }
}

// Submit student feedback
async function submitStudentFeedback(event, studentId, studentName) {
    event.preventDefault();
    
    const title = document.getElementById('feedback-title').value;
    const message = document.getElementById('feedback-message').value;
    const link = document.getElementById('feedback-link').value || '';
    
    if (!message.trim()) {
        showSuccessNotification('Please enter a feedback message', 'error');
        return;
    }
    
    try {
        const submitBtn = event.target.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span>â³</span><span>Sending...</span>';
        
        await facultyAPI.provideFeedback({
            student_id: studentId,
            title: title,
            message: message,
            link: link
        });
        
        // Show success message
        showSuccessNotification(`Feedback sent successfully to ${studentName}! They will receive a notification.`);
        
        // Reset form
        document.getElementById('student-feedback-form').reset();
        document.getElementById('feedback-title').value = 'Feedback from Faculty';
        
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span>ðŸ“¤</span><span>Send Feedback</span>';
        
    } catch (error) {
        console.error('Error sending feedback:', error);
        showSuccessNotification('Error sending feedback. Please try again.', 'error');
        const submitBtn = event.target.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Send Feedback';
        }
    }
}

// Coding Page (New UI)
function setupCodingUI() {
    const searchInput = document.getElementById('cp-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            codingSearch = e.target.value.toLowerCase();
            renderCodingQuestions();
        });
    }

    const topicsInput = document.getElementById('cp-topics');
    if (topicsInput) {
        topicsInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && topicsInput.value.trim()) {
                e.preventDefault();
                addTopicChip(topicsInput.value.trim());
                topicsInput.value = '';
            }
        });
    }

    // Suggested chips click handled inline; ensure focus on open
    const addBtn = document.querySelector('.add-btn');
    if (addBtn) {
        addBtn.addEventListener('click', () => {
            setTimeout(() => {
                const t = document.getElementById('cp-topics');
                if (t) t.focus();
            }, 50);
        });
    }
}

function addTopicChip(label) {
    if (cpTopicTags.includes(label)) return;
    cpTopicTags.push(label);
    const chips = document.getElementById('cp-topic-chips');
    chips.innerHTML = cpTopicTags.map(t => `<span class="tag">${t}</span>`).join('');
    clearError('topics');
}

async function loadCodingPage() {
    try {
        const [questionRes, submissionsRes] = await Promise.all([
            studentAPI.getQuestions({ type: 'coding', per_page: 200 }),
            codingAPI.getSubmissions()
        ]);

        const solvedIds = new Set(
            (submissionsRes.submissions || [])
                .filter(s => s.status === 'accepted')
                .map(s => s.question_id)
        );

        codingQuestions = questionRes.questions.map(q => ({
            ...q,
            status: solvedIds.has(q.id) ? 'solved' : 'unsolved',
            company_name: q.company_name || 'General',
            tags: q.tags || []
        }));

        renderCodingQuestions();
        
        // Force layout recalculation after rendering
        requestAnimationFrame(function() {
            const codingPage = document.getElementById('coding-page');
            if (codingPage) {
                void codingPage.offsetHeight;
                window.dispatchEvent(new Event('resize'));
                
                // Force another reflow after a delay
                setTimeout(function() {
                    void codingPage.offsetHeight;
                    window.dispatchEvent(new Event('resize'));
                }, 50);
            }
        });
    } catch (error) {
        console.error('Error loading coding page:', error);
    }
}

function renderCodingQuestions() {
    const listEl = document.getElementById('cp-question-list');
    if (!listEl) return;
    
    // Ensure codingQuestions is an array
    if (!Array.isArray(codingQuestions)) {
        codingQuestions = [];
    }

    const total = codingQuestions.length;
    const solved = codingQuestions.filter(q => q && q.status === 'solved').length;
    const unsolved = total - solved;
    const progress = total ? Math.round((solved / total) * 100) : 0;

    setText('cp-total', total);
    setText('cp-solved', solved);
    setText('cp-unsolved', unsolved);

    // Check if user is admin (can delete questions)
    const canDelete = currentUser && currentUser.role === 'admin';

    const filtered = codingQuestions.filter(q => {
        if (!q) return false;
        const matchesFilter = codingFilter === 'all' ? true : (q.status === codingFilter);
        const matchesSearch = !codingSearch || (
            (q.title || '').toLowerCase().includes(codingSearch.toLowerCase()) ||
            (q.company_name || '').toLowerCase().includes(codingSearch.toLowerCase()) ||
            (Array.isArray(q.tags) ? q.tags : []).some(t => (t || '').toLowerCase().includes(codingSearch.toLowerCase()))
        );
        return matchesFilter && matchesSearch;
    });

    if (filtered.length === 0) {
        listEl.innerHTML = `<div class="card">No questions found.</div>`;
        return;
    }

    listEl.innerHTML = filtered.map(q => `
        <div class="cp-card" onclick="openCodingQuestion(${q.id})" style="cursor: pointer;">
            <div class="cp-card-header">
                <div class="cp-title-row">
                    <span class="cp-status-dot ${q.status === 'unsolved' ? 'status-unsolved' : ''}"></span>
                    <div>
                        <div>${q.title}</div>
                        <div class="cp-company">ðŸ¢ ${q.company_name}</div>
                    </div>
                </div>
                <div class="cp-card-right" onclick="event.stopPropagation();">
                    ${q.status === 'solved' 
                        ? `<span class="btn btn-sm btn-solved" style="cursor: default;">âœ… Solved</span>` 
                        : `<span class="cp-pill pill-unsolved">Unsolved</span>
                           <button class="btn btn-sm btn-open" onclick="openCodingQuestion(${q.id})">Open</button>`
                    }
                    ${canDelete ? `
                        <button class="btn btn-sm btn-delete-question" onclick="deleteCodingQuestion(${q.id}, '${q.title.replace(/'/g, "\\'")}')" title="Delete Question" style="margin-left: 8px; background: #dc3545; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                            ðŸ—‘ï¸
                        </button>
                    ` : ''}
                </div>
            </div>
            <div class="cp-tags">
                ${(q.tags || []).map(t => `<span class="tag">${t}</span>`).join('')}
            </div>
            <div class="cp-card-footer">
                <span>Difficulty: ${q.difficulty || 'n/a'}</span>
                ${q.type ? `<span>Type: ${q.type}</span>` : ''}
                <span class="cp-star">â˜†</span>
            </div>
        </div>
    `).join('');
}

async function loadQuestion(questionId) {
    try {
        const local = codingQuestions.find(q => q.id === questionId);
        if (local) {
            currentQuestion = local;
            return;
        }
        const data = await codingAPI.getQuestion(questionId);
        currentQuestion = data.question;
    } catch (e) {
        console.error('Error loading question', e);
    }
}

async function deleteCodingQuestion(questionId, questionTitle) {
    if (!confirm(`Are you sure you want to delete the question "${questionTitle}"?\n\nThis action cannot be undone.`)) {
        return;
    }
    
    try {
        await facultyAPI.deleteQuestion(questionId);
        alert('Question deleted successfully!');
        await loadCodingPage();
    } catch (error) {
        console.error('Error deleting question:', error);
        alert(`Error deleting question: ${error.message || 'Failed to delete question'}`);
    }
}

// Store current coding question
let currentCodingQuestion = null;

// Get starter code based on language
function getStarterCodeForLanguage(language) {
    const templates = {
        'python': `# Write your solution here
def solution():
    # Your code here
    pass

# Example usage
if __name__ == "__main__":
    result = solution()
    print(result)`,
        
        'java': `import java.util.*;

public class Solution {
    public int[] twoSum(int[] arr, int target) {
        // Write your solution here
        return new int[]{-1};
    }
}`,
        
        'cpp': `#include <iostream>
#include <vector>
#include <string>
using namespace std;

int main() {
    // Your code here
    
    return 0;
}`,
        
        'c': `#include <stdio.h>
#include <stdlib.h>

int main() {
    // Your code here
    
    return 0;
}`
    };
    
    return templates[language] || templates['python'];
}

// Open Coding Question in Full Page View
async function openCodingQuestion(questionId, updateHash = true) {
    // Validate questionId
    if (!questionId || isNaN(questionId) || questionId <= 0) {
        console.error('Invalid question ID:', questionId);
        alert('Invalid question ID');
        return;
    }
    
    questionId = parseInt(questionId);
    
    try {
        // Make sure we're on coding page
        const codingPage = document.getElementById('coding-page');
        if (codingPage && codingPage.style.display === 'none') {
            showPage('coding', false);
        }
        
        // Hide question list
        const listEl = document.getElementById('cp-question-list');
        const statsEl = document.querySelector('.cp-stats');
        const toolbarEl = document.querySelector('.cp-toolbar');
        
        if (listEl) listEl.style.display = 'none';
        if (statsEl) statsEl.style.display = 'none';
        if (toolbarEl) toolbarEl.style.display = 'none';
        
        // Show full page view - SIMPLIFIED APPROACH
        const fullPageView = document.getElementById('coding-question-view');
        if (!fullPageView) {
            console.error('coding-question-view element not found');
            alert('Error: Coding question view not found');
            return;
        }
        
        // SIMPLE: Just remove the hidden class - CSS handles the rest
        fullPageView.classList.remove('coding-question-hidden');
        
        // Ensure class is applied
        if (!fullPageView.classList.contains('leetcode-platform')) {
            fullPageView.classList.add('leetcode-platform');
        }
        
        // Force a single reflow to trigger layout calculation
        requestAnimationFrame(function() {
            // Access offsetHeight to force reflow
            void fullPageView.offsetHeight;
            
            // Verify it's visible - if class removal didn't work, use inline style
            const computedStyle = window.getComputedStyle(fullPageView);
            if (computedStyle.display === 'none' || fullPageView.classList.contains('coding-question-hidden')) {
                // Force remove class and set inline style as fallback
                fullPageView.classList.remove('coding-question-hidden');
                fullPageView.style.display = 'flex';
                fullPageView.style.position = 'fixed';
                fullPageView.style.top = '64px';
                fullPageView.style.left = '0';
                fullPageView.style.right = '0';
                fullPageView.style.bottom = '0';
                fullPageView.style.zIndex = '100';
                fullPageView.style.width = '100%';
                fullPageView.style.height = 'calc(100vh - 64px)';
                void fullPageView.offsetHeight;
            }
            
            // Trigger resize for viewport calculations
            window.dispatchEvent(new Event('resize'));
        });
        
        // Update hash for direct URL access
        if (updateHash) {
            updateRoute('coding', questionId);
        }
        
        // Load question data
        const data = await codingAPI.getQuestion(questionId);
        const question = data.question;
        
        if (!question) {
            alert('Question not found');
            return;
        }
        
        // Store question globally
        currentCodingQuestion = question;
        currentQuestion = question;
        
        // Populate question details
        document.getElementById('coding-question-title').textContent = question.title || 'Coding Question';
        
        // Populate sidebar with problem list
        populateSidebarProblems();
        
        // Mark current problem as active in sidebar
        setTimeout(() => {
            const sidebarItems = document.querySelectorAll('.sidebar-problem-item');
            sidebarItems.forEach(item => {
                if (parseInt(item.dataset.questionId) === questionId) {
                    item.classList.add('active');
                }
            });
        }, 100);
        
        // Populate tags with modern styling
        const metaDiv = document.getElementById('coding-question-meta');
        const tags = question.tags ? (Array.isArray(question.tags) ? question.tags : question.tags.split(',')) : [];
        const difficulty = question.difficulty || 'medium';
        
        metaDiv.innerHTML = `
            ${tags.length > 0 ? tags.map(t => `<span class="problem-tag category">${t.trim()}</span>`).join('') : ''}
            <span class="problem-tag difficulty-${difficulty}">${difficulty.charAt(0).toUpperCase() + difficulty.slice(1)}</span>
            ${question.company_name ? `<span class="problem-tag category">${question.company_name}</span>` : ''}
        `;
        
        const contentDiv = document.getElementById('coding-question-content');
        
        if (!contentDiv) {
            console.error('coding-question-content element not found');
            alert('Error: Question content area not found');
            return;
        }
        
        // Get test cases - full visible cases are shown to every role.
        let testCases = [];
        try {
            if (question.test_cases) {
                testCases = typeof question.test_cases === 'string' ? JSON.parse(question.test_cases) : question.test_cases;
            } else if (question.sample_test_cases) {
                testCases = typeof question.sample_test_cases === 'string' ? JSON.parse(question.sample_test_cases) : question.sample_test_cases;
            }
            
            // Ensure testCases is an array
            if (!Array.isArray(testCases)) {
                testCases = [];
            }
        } catch (e) {
            console.error('Error parsing test cases:', e);
            testCases = [];
        }
        
        const testCasesLabel = 'Test Cases';
        
        // Helper function to escape HTML
        const escapeHtml = (text) => {
            if (text === null || text === undefined) return '';
            try {
                const div = document.createElement('div');
                div.textContent = String(text);
                return div.innerHTML;
            } catch (e) {
                console.error('Error escaping HTML:', e);
                return String(text).replace(/[&<>"']/g, (m) => {
                    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
                    return map[m];
                });
            }
        };
        
        // Format value for display (arrays, objects, strings)
        const formatValue = (value) => {
            if (value === null || value === undefined) {
                return '';
            }
            if (typeof value === 'string') {
                try {
                    // Try to parse as JSON to format arrays/objects nicely
                    const parsed = JSON.parse(value);
                    return JSON.stringify(parsed, null, 0);
                } catch {
                    return value;
                }
            }
            return JSON.stringify(value, null, 0);
        };
        
        // Build test cases HTML (LeetCode style - exact format)
        let testCasesHTML = '';
        if (testCases.length > 0) {
            const studentNote = '';
            const testCasesList = testCases.map((tc, idx) => {
                if (!tc) return '';
                const exampleNum = idx + 1;
                const input = formatValue(tc.input || '');
                const output = formatValue(tc.output || '');
                const explanation = (tc.explanation || '').toString();
                
                // Format explanation as paragraph if it exists
                let explanationHTML = '';
                if (explanation && typeof explanation === 'string') {
                    try {
                        // Split explanation by newlines and format as paragraphs
                        const explanationLines = explanation.split('\n').filter(line => line && line.trim());
                        explanationHTML = explanationLines.map(line => {
                            // First escape HTML to prevent XSS
                            let processedLine = escapeHtml(line);
                            // Then process inline code patterns (safe because we already escaped)
                            processedLine = processedLine
                                .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
                                .replace(/(\w+)\[(\w+)\]/g, '<code class="inline-code">$1[$2]</code>');
                            return `<p class="leetcode-explanation-text">${processedLine}</p>`;
                        }).join('');
                    } catch (e) {
                        console.error('Error processing explanation:', e);
                        explanationHTML = `<p class="leetcode-explanation-text">${escapeHtml(explanation)}</p>`;
                    }
                }
                
                return `
                    <div class="leetcode-example">
                        <div class="leetcode-example-header">Example ${exampleNum}:</div>
                        <div class="leetcode-example-item">
                            <strong>Input:</strong>
                            <code class="leetcode-example-code">${escapeHtml(input)}</code>
                        </div>
                        <div class="leetcode-example-item">
                            <strong>Output:</strong>
                            <code class="leetcode-example-code">${escapeHtml(output)}</code>
                        </div>
                        ${explanation ? `
                        <div class="leetcode-example-item">
                            <strong>Explanation:</strong>
                            <div class="leetcode-explanation">${explanationHTML}</div>
                        </div>
                        ` : ''}
                    </div>
                `;
            }).join('');
            
            testCasesHTML = `
                <div class="leetcode-test-cases-view">
                    <h4>${testCasesLabel}</h4>
                    ${studentNote}
                    ${testCasesList}
                </div>
            `;
        } else {
            testCasesHTML = `
                <div class="leetcode-test-cases-view">
                    <h4>${testCasesLabel}</h4>
                    <p class="leetcode-test-empty">No test cases available.</p>
                </div>
            `;
        }
        
        // Build description HTML
        const descriptionHTML = question.description ? formatQuestionDescription(question.description) : '<p>No description available.</p>';
        
        contentDiv.innerHTML = `
            <div class="question-description-view">
                <h4>Problem Description</h4>
                <div>${descriptionHTML}</div>
            </div>
            ${testCasesHTML}
        `;
        
        // FORCE REPAINT after content insertion - Critical for layout lifecycle
        requestAnimationFrame(function() {
            // Force layout recalculation
            void contentDiv.offsetHeight;
            void contentDiv.scrollHeight;
            
            // Force parent layouts
            const problemSection = document.querySelector('.leetcode-problem-section');
            if (problemSection) {
                void problemSection.offsetHeight;
                void problemSection.scrollHeight;
            }
            
            // Force main container layout
            const main = document.querySelector('.leetcode-main');
            if (main) {
                void main.offsetHeight;
            }
            
            // Final repaint
            requestAnimationFrame(function() {
                void fullPageView.getBoundingClientRect();
                window.dispatchEvent(new Event('resize'));
            });
        });
        
        // Set starter code in editor based on selected language
        const codeEditor = document.getElementById('code-editor');
        const languageSelect = document.getElementById('code-language');
        
        if (codeEditor && languageSelect) {
            const selectedLanguage = languageSelect.value;
            
            // Try to restore saved code from localStorage (LeetCode-like behavior)
            const savedCodeKey = `code_${questionId}_${selectedLanguage}`;
            const savedCode = localStorage.getItem(savedCodeKey);
            
            if (savedCode && savedCode.trim().length > 0) {
                // Restore saved code
                codeEditor.value = savedCode;
            } else {
                // Always use language-specific template, ignore question.starter_code
                const starterCode = getStarterCodeForLanguage(selectedLanguage);
                codeEditor.value = starterCode;
            }
            
            // Save code on input (auto-save like LeetCode)
            const saveCodeHandler = function() {
                const currentCode = this.value;
                const currentLang = document.getElementById('code-language').value;
                const currentKey = `code_${questionId}_${currentLang}`;
                localStorage.setItem(currentKey, currentCode);
            };
            
            // Add auto-save listener
            codeEditor.addEventListener('input', saveCodeHandler);
            
            // Remove any existing event listeners by cloning the select
            const newSelect = languageSelect.cloneNode(true);
            languageSelect.parentNode.replaceChild(newSelect, languageSelect);
            
            // Add event listener to language selector to update code when language changes
            newSelect.addEventListener('change', function() {
                const selectedLanguage = this.value;
                const codeEditor = document.getElementById('code-editor');
                if (codeEditor) {
                    // Save current code before switching
                    const currentCode = codeEditor.value;
                    const previousLanguage = this.dataset.previousLang || 'python';
                    const previousKey = `code_${questionId}_${previousLanguage}`;
                    localStorage.setItem(previousKey, currentCode);
                    
                    // Try to restore code for new language
                    const newKey = `code_${questionId}_${selectedLanguage}`;
                    const savedCode = localStorage.getItem(newKey);
                    
                    if (savedCode && savedCode.trim().length > 0) {
                        // Restore saved code for this language
                        codeEditor.value = savedCode;
                    } else {
                        // Check if user has written custom code
                        const currentCodeTrimmed = currentCode.trim();
                        const previousStarter = getStarterCodeForLanguage(previousLanguage);
                        
                        // Only replace if code is still the starter template or empty
                        if (!currentCodeTrimmed || currentCodeTrimmed === previousStarter || currentCodeTrimmed.length < 50) {
                            // User hasn't written much, just replace with new language template
                            const starterCode = getStarterCodeForLanguage(selectedLanguage);
                            codeEditor.value = starterCode;
                        } else {
                            // Ask user if they want to replace their code
                            if (confirm('Changing language will replace your current code with the new language template. Continue?')) {
                                const starterCode = getStarterCodeForLanguage(selectedLanguage);
                                codeEditor.value = starterCode;
                            } else {
                                // Revert to previous language
                                this.value = previousLanguage;
                                return;
                            }
                        }
                    }
                    this.dataset.previousLang = selectedLanguage;
                }
            });
            
            // Load editor settings
            loadEditorSettings();
            
            // Store initial language
            newSelect.dataset.previousLang = selectedLanguage;
        }
        
        // Clear output and switch to output tab
        const outputDiv = document.getElementById('code-output');
        if (outputDiv) {
            outputDiv.innerHTML = '<div class="output-placeholder" style="color: rgba(255,255,255,0.5); padding: 20px; text-align: center;">Output will appear here...</div>';
        }
        // Switch to output tab
        if (typeof switchOutputTab === 'function') {
            switchOutputTab('output');
        }
        
        // Hide output panel by default (clean view)
        const outputPanelWrapper = document.querySelector('.output-panel-wrapper');
        if (outputPanelWrapper) {
            outputPanelWrapper.classList.add('output-panel-hidden');
        }
        const outputContainer = document.getElementById('output-container');
        const toggleBtn = document.getElementById('output-toggle-btn');
        if (outputContainer) {
            outputContainer.classList.remove('collapsed');
        }
        if (toggleBtn) {
            toggleBtn.classList.remove('collapsed');
        }
        
        // Hide sidebar by default
        const sidebar = document.querySelector('.leetcode-sidebar');
        if (sidebar) {
            sidebar.classList.add('sidebar-hidden');
        }
        
    } catch (error) {
        console.error('Error loading coding question:', error);
        console.error('Error stack:', error.stack);
        alert(`Failed to load question: ${error.message || 'Unknown error'}`);
        // Show question list again on error
        const listEl = document.getElementById('cp-question-list');
        if (listEl) listEl.style.display = 'block';
        const statsEl = document.querySelector('.cp-stats');
        if (statsEl) statsEl.style.display = 'block';
        const toolbarEl = document.querySelector('.cp-toolbar');
        if (toolbarEl) toolbarEl.style.display = 'block';
        const fullPageView = document.getElementById('coding-question-view');
        if (fullPageView) {
            fullPageView.classList.add('coding-question-hidden');
            fullPageView.style.display = 'none';
        }
    }
}

// Populate sidebar with problems
function populateSidebarProblems() {
    const sidebarList = document.getElementById('sidebar-problems-list');
    if (!sidebarList) return;
    
    // Ensure codingQuestions is an array
    if (!Array.isArray(codingQuestions)) {
        codingQuestions = [];
    }
    
    const filtered = codingQuestions.filter(q => {
        if (!q) return false;
        const matchesFilter = codingFilter === 'all' ? true : (q.status === codingFilter);
        return matchesFilter;
    });
    
    // Helper to escape HTML
    const escapeHtml = (text) => {
        if (text === null || text === undefined) return '';
        try {
            const div = document.createElement('div');
            div.textContent = String(text);
            return div.innerHTML;
        } catch (e) {
            return String(text).replace(/[&<>"']/g, (m) => {
                const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
                return map[m] || m;
            });
        }
    };
    
    sidebarList.innerHTML = filtered.map(q => {
        if (!q || !q.id) return '';
        const difficulty = (q.difficulty || 'medium').toLowerCase();
        const difficultyClass = `difficulty-${difficulty}`;
        const title = (q.title || 'Untitled').toString();
        const difficultyText = difficulty.charAt(0).toUpperCase() + difficulty.slice(1);
        return `
            <div class="sidebar-problem-item" data-question-id="${q.id}" onclick="openCodingQuestion(${q.id}); closeProblemListOverlay();">
                <div class="problem-name">${escapeHtml(title)}</div>
                <div class="problem-difficulty ${difficultyClass}">${escapeHtml(difficultyText)}</div>
            </div>
        `;
    }).filter(html => html).join('');
}

// Filter sidebar problems
function filterSidebarProblems(searchTerm) {
    const items = document.querySelectorAll('.sidebar-problem-item');
    const term = searchTerm.toLowerCase();
    
    items.forEach(item => {
        const name = item.querySelector('.problem-name').textContent.toLowerCase();
        if (name.includes(term)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

// Show output panel (called after Run/Submit)
function showOutputPanel() {
    const outputPanelWrapper = document.querySelector('.output-panel-wrapper');
    if (outputPanelWrapper) {
        outputPanelWrapper.classList.remove('output-panel-hidden');
        // Force reflow for animation
        void outputPanelWrapper.offsetHeight;
    }
}

// Hide output panel
function hideOutputPanel() {
    const outputPanelWrapper = document.querySelector('.output-panel-wrapper');
    if (outputPanelWrapper) {
        outputPanelWrapper.classList.add('output-panel-hidden');
    }
}

// Toggle problem list overlay
function toggleProblemListOverlay() {
    const overlay = document.getElementById('problem-list-overlay');
    const expandBtn = document.getElementById('expand-panel-btn');
    
    if (!overlay) return;
    
    const isHidden = overlay.classList.contains('overlay-hidden');
    
    if (isHidden) {
        overlay.classList.remove('overlay-hidden');
        if (expandBtn) {
            expandBtn.classList.add('active');
            expandBtn.title = 'Hide Problem List';
        }
        // Prevent body scroll when overlay is open
        document.body.style.overflow = 'hidden';
    } else {
        overlay.classList.add('overlay-hidden');
        if (expandBtn) {
            expandBtn.classList.remove('active');
            expandBtn.title = 'Show Problem List';
        }
        // Restore body scroll
        document.body.style.overflow = '';
    }
}

// Close problem list overlay
function closeProblemListOverlay() {
    const overlay = document.getElementById('problem-list-overlay');
    const expandBtn = document.getElementById('expand-panel-btn');
    
    if (overlay) {
        overlay.classList.add('overlay-hidden');
    }
    if (expandBtn) {
        expandBtn.classList.remove('active');
        expandBtn.title = 'Show Problem List';
    }
    // Restore body scroll
    document.body.style.overflow = '';
}

// Switch output tabs
// Toggle output panel collapse/expand
function toggleOutputPanel() {
    const outputContainer = document.getElementById('output-container');
    const toggleBtn = document.getElementById('output-toggle-btn');
    
    if (!outputContainer || !toggleBtn) return;
    
    const isCollapsed = outputContainer.classList.contains('collapsed');
    
    if (isCollapsed) {
        // Expand
        outputContainer.classList.remove('collapsed');
        toggleBtn.classList.remove('collapsed');
    } else {
        // Collapse
        outputContainer.classList.add('collapsed');
        toggleBtn.classList.add('collapsed');
    }
}

function switchOutputTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.output-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.tab === tabName) {
            tab.classList.add('active');
        }
    });
    
    // Update content
    document.querySelectorAll('.output-content').forEach(content => {
        content.classList.remove('active');
        if (content.dataset.tab === tabName) {
            content.classList.add('active');
        }
    });
    
    // Populate test cases tab if needed
    if (tabName === 'testcases' && currentCodingQuestion) {
        const testCasesOutput = document.getElementById('testcases-output');
        if (testCasesOutput && !testCasesOutput.innerHTML.trim()) {
            // Load test cases display
            let testCases = [];
            try {
                if (currentCodingQuestion.test_cases) {
                    testCases = typeof currentCodingQuestion.test_cases === 'string' 
                        ? JSON.parse(currentCodingQuestion.test_cases) 
                        : currentCodingQuestion.test_cases;
                }
            } catch (e) {
                console.error('Error parsing test cases:', e);
            }
            
            if (testCases.length > 0) {
                testCasesOutput.innerHTML = testCases.map((tc, idx) => {
                    const input = JSON.stringify(tc.input || '');
                    const output = JSON.stringify(tc.output || '');
                    return `
                        <div style="margin-bottom: 16px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 6px;">
                            <strong style="color: #9cb2d4;">Test Case ${idx + 1}:</strong><br>
                            <span style="color: rgba(255,255,255,0.7);">Input: </span><code style="color: #d4d4d4;">${input}</code><br>
                            <span style="color: rgba(255,255,255,0.7);">Expected: </span><code style="color: #d4d4d4;">${output}</code>
                        </div>
                    `;
                }).join('');
            } else {
                testCasesOutput.innerHTML = '<div style="color: rgba(255,255,255,0.5); padding: 20px; text-align: center;">No test cases available</div>';
            }
        }
    }
}

function closeCodingQuestionView() {
    // Hide full page view - SIMPLIFIED: Just add hidden class
    const fullPageView = document.getElementById('coding-question-view');
    if (fullPageView) {
        fullPageView.classList.add('coding-question-hidden');
        // Also set inline style as backup
        fullPageView.style.display = 'none';
    }
    
    // Show question list
    const listEl = document.getElementById('cp-question-list');
    const statsEl = document.querySelector('.cp-stats');
    const toolbarEl = document.querySelector('.cp-toolbar');
    
    if (listEl) listEl.style.display = 'flex';
    if (statsEl) statsEl.style.display = 'grid';
    if (toolbarEl) toolbarEl.style.display = 'flex';
    
    currentCodingQuestion = null;
    currentQuestion = null;
    
    // Update hash to just 'coding' (question list view)
    updateRoute('coding');
}

async function runCode() {
    const codeEditor = document.getElementById('code-editor');
    const languageSelect = document.getElementById('code-language');
    const outputDiv = document.getElementById('code-output');
    
    if (!codeEditor || !languageSelect || !outputDiv) return;
    
    const code = codeEditor.value.trim();
    const language = languageSelect.value;
    
    if (!code) {
        outputDiv.innerHTML = '<div class="output-error">Please write some code first.</div>';
        // Show output panel even for error
        showOutputPanel();
        return;
    }
    
    // Show output panel
    showOutputPanel();
    
    // Show loading
    outputDiv.innerHTML = '<div class="output-loading">Running code...</div>';
    
    // Switch to Output tab
    if (typeof switchOutputTab === 'function') {
        switchOutputTab('output');
    }
    
    try {
        // If we have a current question, run test cases
        let result;
        if (currentCodingQuestion && currentCodingQuestion.id) {
            result = await codingAPI.executeCode(code, language, '', currentCodingQuestion.id);
        } else {
            result = await codingAPI.executeCode(code, language);
        }
        
        // Run mode: Just show program output (like normal compiler)
        // User program controls input/output - if no print, show "(no output)"
        if (result.output !== undefined) {
            outputDiv.innerHTML = `
                <div class="output-success">
                    <div class="output-label">Output:</div>
                    <pre>${result.output || '(no output)'}</pre>
                </div>
            `;
        } else if (result.error) {
            outputDiv.innerHTML = `
                <div class="output-error">
                    <div class="output-label">Error:</div>
                    <pre>${result.error}</pre>
                </div>
            `;
        } else {
            outputDiv.innerHTML = '<div class="output-placeholder">(no output)</div>';
        }
    } catch (error) {
        const message = error.status === 401
            ? 'Your login session expired. Please logout and login again, then run the code.'
            : error.message || 'Failed to execute code';
        outputDiv.innerHTML = `
            <div class="output-error">
                <div class="output-label">Error:</div>
                <pre>${message}</pre>
            </div>
        `;
    }
}

async function submitCode() {
    if (!currentCodingQuestion) {
        alert('No question loaded');
        return;
    }
    
    const codeEditor = document.getElementById('code-editor');
    const languageSelect = document.getElementById('code-language');
    const outputDiv = document.getElementById('code-output');
    
    if (!codeEditor || !languageSelect || !outputDiv) return;
    
    const code = codeEditor.value.trim();
    const language = languageSelect.value;
    
    if (!code) {
        outputDiv.innerHTML = '<div class="output-error">Please write some code first.</div>';
        // Show output panel even for error
        showOutputPanel();
        return;
    }
    
    // Show output panel
    showOutputPanel();
    
    // Show loading
    outputDiv.innerHTML = '<div class="output-loading">Submitting code...</div>';
    
    // Switch to Output tab
    if (typeof switchOutputTab === 'function') {
        switchOutputTab('output');
    }
    
    try {
        const result = await codingAPI.submitCode(currentCodingQuestion.id, code, language);
        
        // Refresh Placement Readiness Score after code submission
        if (typeof loadPlacementReadinessScore === 'function') {
            loadPlacementReadinessScore();
        }
        
        // Display test results - Submit mode shows test case results with âœ…/âŒ
        if (result.test_results && result.test_results.length > 0) {
            const testResultsHtml = result.test_results.map((tr, idx) => {
                const statusIcon = tr.passed ? 'âœ…' : 'âŒ';
                return `
                    <div class="test-result-display ${tr.passed ? 'test-passed' : 'test-failed'}">
                        <div class="test-result-header">
                            <span class="test-case-number">Test Case ${idx + 1}</span>
                            <span class="test-status">${statusIcon}</span>
                        </div>
                        ${!tr.passed ? `
                            <div class="test-result-details">
                                <div class="test-detail-item">
                                    <strong>Expected:</strong> <code>${tr.expected_output || 'N/A'}</code>
                                </div>
                                <div class="test-detail-item">
                                    <strong>Got:</strong> <code>${tr.actual_output || 'N/A'}</code>
                                </div>
                                ${tr.status && tr.status !== 'accepted' ? `
                                    <div class="test-detail-item">
                                        <strong>Status:</strong> <span class="test-status-badge">${tr.status}</span>
                                    </div>
                                ` : ''}
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('');
            
            const summaryHtml = `
                <div class="test-summary ${result.status === 'accepted' ? 'summary-success' : 'summary-error'}">
                    <strong>${result.status === 'accepted' ? 'âœ… Accepted!' : 'âŒ Wrong Answer'}</strong>
                    <span>Test Cases: ${result.test_cases_passed || result.passed || 0} / ${result.total_test_cases || result.total || 0} passed</span>
                    ${result.execution_time ? `<span>Execution Time: ${result.execution_time.toFixed(2)}s</span>` : ''}
                </div>
            `;
            
            outputDiv.innerHTML = `
                <div class="output-test-results">
                    ${summaryHtml}
                    <div class="test-results-list">
                        ${testResultsHtml}
                    </div>
                </div>
            `;
            
            // Reload coding page to update solved status if accepted
            if (result.status === 'accepted') {
                setTimeout(() => {
                    loadCodingPage();
                    // Refresh Placement Readiness Score after successful code submission
                    if (typeof loadPlacementReadinessScore === 'function') {
                        loadPlacementReadinessScore();
                    }
                }, 1000);
            }
        } else if (result.status === 'accepted') {
            outputDiv.innerHTML = `
                <div class="output-success">
                    <div class="output-label">âœ… Accepted!</div>
                    <div>Test Cases Passed: ${result.test_cases_passed || result.passed || 0} / ${result.total_test_cases || result.total || 0}</div>
                    ${result.execution_time ? `<div>Execution Time: ${result.execution_time.toFixed(2)}s</div>` : ''}
                </div>
            `;
            
            // Reload coding page to update solved status
            setTimeout(() => {
                loadCodingPage();
            }, 1000);
        } else {
            outputDiv.innerHTML = `
                <div class="output-error">
                    <div class="output-label">âŒ Wrong Answer</div>
                    <div>Test Cases Passed: ${result.test_cases_passed || result.passed || 0} / ${result.total_test_cases || result.total || 0}</div>
                </div>
            `;
        }
    } catch (error) {
        const message = error.status === 401
            ? 'Your login session expired. Please logout and login again, then submit the code.'
            : error.message || 'Failed to submit code';
        outputDiv.innerHTML = `
            <div class="output-error">
                <div class="output-label">Error:</div>
                <pre>${message}</pre>
            </div>
        `;
    }
}

// ==================== LeetCode-Style Features ====================

// 1. Retrieve Last Submitted Code
async function retrieveLastCode() {
    if (!currentCodingQuestion) {
        alert('No question loaded');
        return;
    }
    
    const codeEditor = document.getElementById('code-editor');
    const languageSelect = document.getElementById('code-language');
    
    if (!codeEditor || !languageSelect) return;
    
    const language = languageSelect.value;
    
    try {
        const result = await codingAPI.getLastSubmission(currentCodingQuestion.id, language);
        
        if (result.submission && result.submission.code) {
            // Confirm before replacing current code
            const currentCode = codeEditor.value.trim();
            if (currentCode && currentCode !== result.submission.code) {
                if (!confirm('This will replace your current code with the last submitted code. Continue?')) {
                    return;
                }
            }
            
            codeEditor.value = result.submission.code;
            
            // Update language if different
            if (result.submission.language && result.submission.language !== language) {
                languageSelect.value = result.submission.language;
            }
            
            // Show success message
            const outputDiv = document.getElementById('code-output');
            if (outputDiv) {
                outputDiv.innerHTML = `
                    <div class="output-success">
                        <div class="output-label">Last submitted code loaded</div>
                        <div style="font-size: 12px; color: rgba(232, 236, 243, 0.7); margin-top: 8px;">
                            Submitted: ${new Date(result.submission.submitted_at).toLocaleString()}
                        </div>
                    </div>
                `;
            }
        } else {
            alert('No previous submission found for this question');
        }
    } catch (error) {
        alert(`Failed to retrieve last code: ${error.message}`);
    }
}

// 2. Reset to Default Template
function resetToTemplate() {
    const codeEditor = document.getElementById('code-editor');
    const languageSelect = document.getElementById('code-language');
    
    if (!codeEditor || !languageSelect) return;
    
    const currentCode = codeEditor.value.trim();
    const language = languageSelect.value;
    
    // Confirm before resetting
    if (currentCode) {
        if (!confirm('This will replace your current code with the default template. Continue?')) {
            return;
        }
    }
    
    // Get default template for current language
    const template = getStarterCodeForLanguage(language);
    codeEditor.value = template;
    
    // Show message
    const outputDiv = document.getElementById('code-output');
    if (outputDiv) {
        outputDiv.innerHTML = `
            <div class="output-success">
                <div class="output-label">Reset to default template</div>
            </div>
        `;
    }
}

// 3. Editor Settings
function openEditorSettings() {
    const modal = document.getElementById('editor-settings-modal');
    if (!modal) return;
    
    // Load saved settings
    const settings = getEditorSettings();
    document.getElementById('editor-font-size').value = settings.fontSize || '14';
    document.getElementById('editor-theme').value = settings.theme || 'dark';
    document.getElementById('editor-key-bindings').value = settings.keyBindings || 'default';
    document.getElementById('editor-tab-size').value = settings.tabSize || '4';
    document.getElementById('editor-word-wrap').value = settings.wordWrap || 'on';
    
    modal.classList.remove('hidden');
}

function closeEditorSettings() {
    const modal = document.getElementById('editor-settings-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function saveEditorSettings() {
    const settings = {
        fontSize: document.getElementById('editor-font-size').value,
        theme: document.getElementById('editor-theme').value,
        keyBindings: document.getElementById('editor-key-bindings').value,
        tabSize: document.getElementById('editor-tab-size').value,
        wordWrap: document.getElementById('editor-word-wrap').value
    };
    
    // Save to localStorage
    localStorage.setItem('editorSettings', JSON.stringify(settings));
    
    // Apply settings
    applyEditorSettings(settings);
    
    closeEditorSettings();
    
    // Show success message
    const outputDiv = document.getElementById('code-output');
    if (outputDiv) {
        outputDiv.innerHTML = `
            <div class="output-success">
                <div class="output-label">Editor settings saved</div>
            </div>
        `;
    }
}

function getEditorSettings() {
    const saved = localStorage.getItem('editorSettings');
    if (saved) {
        try {
            return JSON.parse(saved);
        } catch (e) {
            return getDefaultEditorSettings();
        }
    }
    return getDefaultEditorSettings();
}

function getDefaultEditorSettings() {
    return {
        fontSize: '14',
        theme: 'dark',
        keyBindings: 'default',
        tabSize: '4',
        wordWrap: 'on'
    };
}

function applyEditorSettings(settings) {
    const codeEditor = document.getElementById('code-editor');
    if (!codeEditor) return;
    
    // Apply font size
    codeEditor.style.fontSize = `${settings.fontSize}px`;
    
    // Apply theme (affects background/colors)
    if (settings.theme === 'light') {
        codeEditor.style.backgroundColor = '#ffffff';
        codeEditor.style.color = '#000000';
    } else if (settings.theme === 'dark') {
        codeEditor.style.backgroundColor = '#0c1322';
        codeEditor.style.color = '#66e3c4';
    } else if (settings.theme === 'monokai') {
        codeEditor.style.backgroundColor = '#272822';
        codeEditor.style.color = '#f8f8f2';
    } else if (settings.theme === 'solarized') {
        codeEditor.style.backgroundColor = '#002b36';
        codeEditor.style.color = '#839496';
    }
    
    // Apply word wrap
    if (settings.wordWrap === 'on') {
        codeEditor.style.whiteSpace = 'pre-wrap';
        codeEditor.style.wordWrap = 'break-word';
    } else {
        codeEditor.style.whiteSpace = 'pre';
        codeEditor.style.wordWrap = 'normal';
    }
    
    // Tab size is handled via CSS (tab-size property)
    codeEditor.style.tabSize = settings.tabSize;
    codeEditor.style.MozTabSize = settings.tabSize;
}

// Load editor settings on page load
function loadEditorSettings() {
    const settings = getEditorSettings();
    applyEditorSettings(settings);
}

function setCodingFilter(filter) {
    codingFilter = filter;
    document.querySelectorAll('.chip').forEach(chip => {
        chip.classList.toggle('active', chip.dataset.filter === filter);
    });
    renderCodingQuestions();
}

function openQuestionModal() {
    const modal = document.getElementById('cp-modal');
    if (modal) modal.classList.remove('hidden');
}

function closeQuestionModal() {
    const modal = document.getElementById('cp-modal');
    if (modal) modal.classList.add('hidden');
    document.getElementById('cp-company').value = '';
    document.getElementById('cp-title').value = '';
    document.getElementById('cp-description').value = '';
    document.getElementById('cp-topics').value = '';
    cpTopicTags = [];
    const chips = document.getElementById('cp-topic-chips');
    if (chips) chips.innerHTML = '';
    
    // Reset test cases container
    const testCasesContainer = document.getElementById('cp-testcases-container');
    if (testCasesContainer) {
        testCasesContainer.innerHTML = `
            <div class="test-case-row">
                <div class="test-case-input-group">
                    <label class="test-case-label">Input:</label>
                    <input type="text" class="test-case-input" placeholder="e.g., 2 3" data-test-case="input">
                </div>
                <div class="test-case-input-group">
                    <label class="test-case-label">Output:</label>
                    <input type="text" class="test-case-output" placeholder="e.g., 5" data-test-case="output">
                </div>
                <button type="button" class="btn-remove-testcase" onclick="removeTestCase(this)" style="display: none;">âœ•</button>
            </div>
        `;
    }
    
    clearAllErrors();
}

// Test Case Management Functions
function addTestCase() {
    const container = document.getElementById('cp-testcases-container');
    if (!container) return;
    
    const testCaseRow = document.createElement('div');
    testCaseRow.className = 'test-case-row';
    testCaseRow.innerHTML = `
        <div class="test-case-input-group">
            <label class="test-case-label">Input:</label>
            <input type="text" class="test-case-input" placeholder="e.g., 2 3" data-test-case="input">
        </div>
        <div class="test-case-input-group">
            <label class="test-case-label">Output:</label>
            <input type="text" class="test-case-output" placeholder="e.g., 5" data-test-case="output">
        </div>
        <button type="button" class="btn-remove-testcase" onclick="removeTestCase(this)">âœ•</button>
    `;
    container.appendChild(testCaseRow);
    
    // Update remove button visibility
    updateTestCaseRemoveButtons();
}

function removeTestCase(btn) {
    const container = document.getElementById('cp-testcases-container');
    if (!container) return;
    
    const rows = container.querySelectorAll('.test-case-row');
    if (rows.length <= 1) {
        alert('At least one test case is required');
        return;
    }
    
    btn.closest('.test-case-row').remove();
    updateTestCaseRemoveButtons();
}

function updateTestCaseRemoveButtons() {
    const container = document.getElementById('cp-testcases-container');
    if (!container) return;
    
    const rows = container.querySelectorAll('.test-case-row');
    rows.forEach(row => {
        const removeBtn = row.querySelector('.btn-remove-testcase');
        if (removeBtn) {
            removeBtn.style.display = rows.length > 1 ? 'block' : 'none';
        }
    });
}

function parseTestCases() {
    const container = document.getElementById('cp-testcases-container');
    if (!container) return [];
    
    const rows = container.querySelectorAll('.test-case-row');
    const cases = [];
    
    rows.forEach(row => {
        const inputField = row.querySelector('.test-case-input');
        const outputField = row.querySelector('.test-case-output');
        
        if (inputField && outputField) {
            let input = inputField.value.trim();
            let output = outputField.value.trim();
            
            // Clean up input/output - remove labels if present
            input = input.replace(/^Input:\s*/i, '').replace(/^nums\s*=\s*/i, '').trim();
            output = output.replace(/^Output:\s*/i, '').trim();
            
            if (input && output) {
                cases.push({ input, output });
            }
        }
    });
    
    return cases;
}

function findCompanyIdByName(name) {
    if (!name) return null;
    const found = companies.find(c => c.name.toLowerCase() === name.toLowerCase());
    return found ? found.id : null;
}

async function submitNewQuestion() {
    const title = document.getElementById('cp-title').value.trim();
    const description = document.getElementById('cp-description').value.trim();
    const companyName = document.getElementById('cp-company').value.trim();

    let hasError = false;
    clearAllErrors();
    if (!title) { setError('title', 'Title is required'); hasError = true; }
    if (!description) { setError('question', 'Question is required'); hasError = true; }
    if (cpTopicTags.length === 0) { setError('topics', 'Please add at least one topic'); hasError = true; }
    
    const parsedCases = parseTestCases();
    if (!parsedCases.length) {
        setError('testcases', 'Please provide at least one valid Input/Output pair');
        hasError = true;
    }
    
    if (hasError) return;

    const payload = {
        title,
        description,
        type: 'coding',
        module_type: 'CodePractice',  // Required: Set to CodePractice when adding from CodePractice page
        difficulty: 'medium',
        company_id: findCompanyIdByName(companyName),
        tags: cpTopicTags,
        test_cases: parsedCases,
        starter_code: '',  // Optional but include it
        solution: ''  // Optional but include it
    };

    try {
        const result = await facultyAPI.createQuestion(payload);
        closeQuestionModal();
        await loadCodingPage();
        alert('Question added successfully.');
    } catch (error) {
        console.error('Error creating question:', error);
        const errorMessage = error.message || 'Failed to add question';
        setError('question', errorMessage);
        // Also show alert for visibility
        alert(`Error: ${errorMessage}`);
    }
}

function setError(field, message) {
    const el = document.getElementById(`cp-error-${field}`);
    if (el) el.textContent = message;
}

function clearError(field) {
    const el = document.getElementById(`cp-error-${field}`);
    if (el) el.textContent = '';
}

function clearAllErrors() {
    ['question', 'testcases', 'topics', 'title'].forEach(clearError);
}

// Non-Technical Questions Page
async function loadNonTechnicalPage() {
    try {
        // Check user role for +Add button visibility
        const addBtn = document.getElementById('add-nontech-btn');
        if (addBtn) {
            // All users (students, faculty, admin) can add questions
            addBtn.style.display = 'block';
        }
        
        // Load non-technical questions (MCQ type) - exclude quiz questions
        const data = await studentAPI.getQuestions({ type: 'mcq', per_page: 200, exclude_quiz_questions: 'true' });
        const questionsDiv = document.getElementById('non-technical-questions-list');
        
        // Check if user is faculty or admin (can delete questions)
        const canDelete = currentUser && (currentUser.role === 'faculty' || currentUser.role === 'admin');
        
        if (data.questions && data.questions.length > 0) {
            questionsDiv.innerHTML = data.questions.map(q => `
                <div class="question-card" onclick="openNonTechQuestion(${q.id})" style="cursor: pointer;">
                    <div class="question-card-content">
                        <div class="question-card-left">
                            <h4 class="question-title-clickable">${q.title}</h4>
                            <div>${q.description ? formatQuestionDescription(q.description) : ''}</div>
                            ${q.options ? `<div class="options-preview">Options: ${q.options.join(', ')}</div>` : ''}
                            <small>Marks: ${q.marks || 1}</small>
                        </div>
                        <div class="question-card-right" onclick="event.stopPropagation();">
                            <button class="btn btn-sm btn-open" onclick="openNonTechQuestion(${q.id})">Open</button>
                            ${canDelete ? `
                                <button class="btn btn-sm btn-delete-question" onclick="deleteNonTechQuestion(${q.id}, '${q.title.replace(/'/g, "\\'")}')" title="Delete Question">
                                    ðŸ—‘ï¸
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            questionsDiv.innerHTML = '<p>No non-technical questions available yet.</p>';
        }
    } catch (error) {
        console.error('Error loading non-technical page:', error);
    }
}

// Non-Technical Question Modal Functions
let ntOptionCount = 2; // Start with A and B

function openNonTechQuestionModal() {
    const modal = document.getElementById('nontech-modal');
    if (modal) {
        modal.classList.remove('hidden');
        
        // Reset form
        document.getElementById('nt-question').value = '';
        document.getElementById('nt-marks').value = '1';
        document.getElementById('nt-correct-answer').value = '';
        
        // Reset options container
        const container = document.getElementById('nt-options-container');
        if (container) {
            container.innerHTML = `
                <div class="option-row">
                    <input type="text" class="option-input" placeholder="Option A" data-option="A">
                    <button class="btn-remove-option" onclick="removeOption(this)" style="display: none;">âœ•</button>
                </div>
                <div class="option-row">
                    <input type="text" class="option-input" placeholder="Option B" data-option="B">
                    <button class="btn-remove-option" onclick="removeOption(this)" style="display: none;">âœ•</button>
                </div>
            `;
        }
        
        ntOptionCount = 2;
        updateOptionLabels();
        updateCorrectAnswerOptions();
        clearNonTechErrors();
        
        // Close on outside click
        modal.onclick = (e) => {
            if (e.target === modal) closeNonTechQuestionModal();
        };
    }
}

function closeNonTechQuestionModal() {
    const modal = document.getElementById('nontech-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function addOption() {
    if (ntOptionCount >= 10) {
        alert('Maximum 10 options allowed');
        return;
    }
    ntOptionCount++;
    updateOptionsContainer();
}

function removeOption(btn) {
    const container = document.getElementById('nt-options-container');
    const rows = container.querySelectorAll('.option-row');
    if (rows.length <= 2) {
        alert('Minimum 2 options required');
        return;
    }
    btn.closest('.option-row').remove();
    ntOptionCount--;
    updateOptionLabels();
}

function updateOptionsContainer() {
    const container = document.getElementById('nt-options-container');
    if (!container) return;
    
    // Get current number of rows
    let currentRowCount = container.querySelectorAll('.option-row').length;
    
    // Add new rows if needed
    while (currentRowCount < ntOptionCount) {
        const row = document.createElement('div');
        row.className = 'option-row';
        const letter = String.fromCharCode(65 + currentRowCount);
        row.innerHTML = `
            <input type="text" class="option-input" placeholder="Option ${letter}" data-option="${letter}">
            <button class="btn-remove-option" onclick="removeOption(this)">âœ•</button>
        `;
        container.appendChild(row);
        currentRowCount++;
    }
    
    updateOptionLabels();
    updateCorrectAnswerOptions();
}

function updateOptionLabels() {
    const rows = document.querySelectorAll('#nt-options-container .option-row');
    rows.forEach((row, idx) => {
        const letter = String.fromCharCode(65 + idx);
        const input = row.querySelector('.option-input');
        input.setAttribute('data-option', letter);
        input.placeholder = `Option ${letter}`;
        const removeBtn = row.querySelector('.btn-remove-option');
        removeBtn.style.display = rows.length > 2 ? 'block' : 'none';
    });
    updateCorrectAnswerOptions();
}

function updateCorrectAnswerOptions() {
    const select = document.getElementById('nt-correct-answer');
    if (!select) return;
    
    const currentValue = select.value;
    select.innerHTML = '<option value="">Select correct answer</option>';
    
    const rows = document.querySelectorAll('#nt-options-container .option-row');
    rows.forEach((row, idx) => {
        const letter = String.fromCharCode(65 + idx);
        const option = document.createElement('option');
        option.value = letter;
        option.textContent = letter;
        select.appendChild(option);
    });
    
    if (currentValue && Array.from(select.options).some(opt => opt.value === currentValue)) {
        select.value = currentValue;
    }
}

function clearNonTechErrors() {
    ['question', 'options', 'answer', 'marks'].forEach(field => {
        const el = document.getElementById(`nt-error-${field}`);
        if (el) el.textContent = '';
    });
}

async function submitNonTechQuestion() {
    const question = document.getElementById('nt-question').value.trim();
    const marks = parseInt(document.getElementById('nt-marks').value) || 1;
    const correctAnswer = document.getElementById('nt-correct-answer').value;
    
    // Get options
    const optionInputs = document.querySelectorAll('#nt-options-container .option-input');
    const options = Array.from(optionInputs)
        .map(input => input.value.trim())
        .filter(val => val.length > 0);
    
    let hasError = false;
    clearNonTechErrors();
    
    if (!question) {
        document.getElementById('nt-error-question').textContent = 'Question is required';
        hasError = true;
    }
    if (options.length < 2) {
        document.getElementById('nt-error-options').textContent = 'At least 2 options are required';
        hasError = true;
    }
    if (!correctAnswer) {
        document.getElementById('nt-error-answer').textContent = 'Please select the correct answer';
        hasError = true;
    }
    if (marks < 1) {
        document.getElementById('nt-error-marks').textContent = 'Marks must be at least 1';
        hasError = true;
    }
    
    if (hasError) return;
    
    // Create question payload
    const payload = {
        title: question.substring(0, 100), // Use first 100 chars as title
        description: question,
        type: 'mcq',
        module_type: 'Non-Technical', // Required: Set to Non-Technical for non-technical questions
        difficulty: 'medium',
        options: options,
        correct_answer: correctAnswer,
        marks: marks
    };
    
    try {
        await facultyAPI.createQuestion(payload);
        closeNonTechQuestionModal();
        await loadNonTechnicalPage();
        alert('Question added successfully!');
    } catch (error) {
        console.error('Error creating question:', error);
        let errorMessage = error.message || 'Failed to add question';
        
        // Check if it's a permission error
        if (errorMessage.includes('Insufficient permissions') || errorMessage.includes('403')) {
            errorMessage = 'You do not have permission to add questions. Only faculty and administrators can create questions.';
        }
        
        document.getElementById('nt-error-question').textContent = errorMessage;
        document.getElementById('nt-error-question').style.display = 'block';
    }
}

// Store current question for submission
let currentNonTechQuestion = null;

// Open Non-Technical Question in Modal
async function openNonTechQuestion(questionId) {
    try {
        const data = await studentAPI.getQuestions({ per_page: 1000 });
        const question = data.questions.find(q => q.id === questionId);
        
        if (!question) {
            alert('Question not found');
            return;
        }
        
        // Store question globally
        currentNonTechQuestion = question;
        
        // Create or get modal
        let modal = document.getElementById('nontech-view-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'nontech-view-modal';
            modal.className = 'cp-modal hidden';
            modal.innerHTML = `
                <div class="cp-modal-content" onclick="event.stopPropagation()" style="max-width: 600px;">
                    <div class="cp-modal-header">
                        <div><h3>Question</h3></div>
                        <button class="cp-close" onclick="closeNonTechQuestionView()">âœ•</button>
                    </div>
                    <div class="cp-modal-body" id="nontech-view-content">
                        <!-- Content will be inserted here -->
                    </div>
                    <div class="cp-modal-footer" id="nontech-view-footer">
                        <!-- Footer buttons will be inserted here -->
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            
            // Close on outside click
            modal.onclick = (e) => {
                if (e.target === modal) closeNonTechQuestionView();
            };
        }
        
        // Populate modal content
        const content = document.getElementById('nontech-view-content');
        const footer = document.getElementById('nontech-view-footer');
        
        // Check if question has been answered
        const isAnswered = currentNonTechQuestion.user_answer !== undefined;
        const showResult = isAnswered;
        
        content.innerHTML = `
            <div class="question-view" id="question-view-container">
                <h4>${question.title}</h4>
                ${question.description && question.description.trim() !== question.title.trim() && question.description.trim() !== '' ? `<div class="question-description">${formatQuestionDescription(question.description)}</div>` : ''}
                <div class="question-options-view">
                    <label>Select your answer:</label>
                    ${question.options ? question.options.map((opt, idx) => {
                        const letter = String.fromCharCode(65 + idx);
                        return `
                            <div class="option-item-view" onclick="selectNonTechOption('view-opt-${questionId}-${idx}')" style="cursor: pointer;">
                                <input type="radio" name="view-question-${questionId}" value="${letter}" id="view-opt-${questionId}-${idx}">
                                <label for="view-opt-${questionId}-${idx}" onclick="event.stopPropagation();" style="cursor: pointer;">
                                    <strong>${letter}.</strong> ${opt}
                                </label>
                            </div>
                        `;
                    }).join('') : ''}
                </div>
                <div class="question-meta">
                    <small>Marks: ${question.marks || 1}</small>
                </div>
                <div id="question-result" style="display: none; margin-top: 20px;"></div>
            </div>
        `;
        
        // Footer buttons
        footer.innerHTML = `
            <button class="btn" onclick="closeNonTechQuestionView()">Close</button>
            <button class="btn btn-primary" onclick="submitNonTechAnswer(${questionId})" id="submit-answer-btn">Submit Answer</button>
        `;
        
        // Show modal
        modal.classList.remove('hidden');
    } catch (error) {
        console.error('Error loading question:', error);
        alert('Failed to load question');
    }
}

function selectNonTechOption(radioId) {
    const radio = document.getElementById(radioId);
    if (radio) {
        radio.checked = true;
        radio.dispatchEvent(new Event('change', { bubbles: true }));
    }
}

function closeNonTechQuestionView() {
    const modal = document.getElementById('nontech-view-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
    currentNonTechQuestion = null;
}

async function deleteNonTechQuestion(questionId, questionTitle) {
    if (!confirm(`Are you sure you want to delete the question "${questionTitle}"?\n\nThis action cannot be undone.`)) {
        return;
    }
    
    try {
        await facultyAPI.deleteQuestion(questionId);
        alert('Question deleted successfully!');
        await loadNonTechnicalPage();
    } catch (error) {
        console.error('Error deleting question:', error);
        alert(`Error deleting question: ${error.message || 'Failed to delete question'}`);
    }
}

async function submitNonTechAnswer(questionId) {
    if (!currentNonTechQuestion) {
        alert('Question not loaded');
        return;
    }
    
    // Get selected answer
    const selectedRadio = document.querySelector(`input[name="view-question-${questionId}"]:checked`);
    if (!selectedRadio) {
        alert('Please select an answer before submitting');
        return;
    }
    
    const userAnswer = selectedRadio.value;
    const correctAnswer = currentNonTechQuestion.correct_answer;
    const isCorrect = userAnswer === correctAnswer;
    const marks = currentNonTechQuestion.marks || 1;
    const obtainedMarks = isCorrect ? marks : 0;
    const score = isCorrect ? 100 : 0;
    
    // Disable all radio buttons
    document.querySelectorAll(`input[name="view-question-${questionId}"]`).forEach(radio => {
        radio.disabled = true;
    });
    
    // Hide submit button
    const submitBtn = document.getElementById('submit-answer-btn');
    if (submitBtn) {
        submitBtn.style.display = 'none';
    }
    
    // Display result with score
    const resultDiv = document.getElementById('question-result');
    if (resultDiv) {
        // Safely get correct answer text
        let correctAnswerText = correctAnswer;
        if (currentNonTechQuestion.options && correctAnswer && correctAnswer.length > 0) {
            try {
                const answerIndex = correctAnswer.charCodeAt(0) - 65; // A=0, B=1, C=2, etc.
                if (answerIndex >= 0 && answerIndex < currentNonTechQuestion.options.length) {
                    correctAnswerText = currentNonTechQuestion.options[answerIndex];
                }
            } catch (e) {
                console.error('Error parsing correct answer:', e);
                correctAnswerText = correctAnswer;
            }
        }
        
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = `
            <div class="question-result-card ${isCorrect ? 'result-correct-card' : 'result-wrong-card'}" style="
                background: ${isCorrect ? 'rgba(40, 167, 69, 0.2)' : 'rgba(220, 53, 69, 0.2)'};
                border: 2px solid ${isCorrect ? '#28a745' : '#dc3545'};
                border-radius: 8px;
                padding: 20px;
                margin-top: 20px;
            ">
                <div style="text-align: center; margin-bottom: 15px;">
                    ${isCorrect 
                        ? '<div style="font-size: 48px; margin-bottom: 10px;">âœ…</div><h3 style="color: #28a745; margin: 8px 0;">Correct Answer!</h3>' 
                        : '<div style="font-size: 48px; margin-bottom: 10px;">âŒ</div><h3 style="color: #dc3545; margin: 8px 0;">Wrong Answer</h3>'}
                </div>
                
                <div style="background: rgba(0, 0, 0, 0.3); padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <span style="color: #b8b8d1;">Marks Obtained:</span>
                        <strong style="color: #f2f4ff; font-size: 18px;">${obtainedMarks}/${marks}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #b8b8d1;">Score:</span>
                        <strong style="color: ${isCorrect ? '#28a745' : '#dc3545'}; font-size: 24px;">${score}%</strong>
                    </div>
                </div>
                
                <p style="margin: 15px 0 0 0; color: rgba(242, 244, 255, 0.9); text-align: center;">
                    ${isCorrect 
                        ? 'ðŸŽ‰ Congratulations! You got it right!' 
                        : `The correct answer is: <strong style="color: #667eea;">${correctAnswer}. ${correctAnswerText}</strong>`}
                </p>
            </div>
        `;
    }
    
    // Store the answer in the question object
    currentNonTechQuestion.user_answer = userAnswer;
    currentNonTechQuestion.is_correct = isCorrect;
}

// Quiz Modal Functions
let quizQuestions = []; // Array to store quiz questions
let quizQuestionCounter = 0;

function openQuizModal() {
    const modal = document.getElementById('quiz-modal');
    if (modal) {
        modal.classList.remove('hidden');
        
        // Reset form with null checks
        const titleEl = document.getElementById('quiz-modal-title');
        const descEl = document.getElementById('quiz-modal-description');
        const durationEl = document.getElementById('quiz-modal-duration');
        const deadlineEl = document.getElementById('quiz-modal-deadline');
        const assignmentTypeEl = document.getElementById('quiz-modal-assignment-type');
        const lockDeadlineEl = document.getElementById('quiz-modal-lock-deadline');
        const studentSelectorEl = document.getElementById('quiz-student-selector');
        const selectedStudentsEl = document.getElementById('quiz-selected-students');
        
        if (titleEl) titleEl.value = '';
        if (descEl) descEl.value = '';
        if (durationEl) durationEl.value = '60';
        if (deadlineEl) deadlineEl.value = '';
        if (assignmentTypeEl) assignmentTypeEl.value = 'entire_batch';
        if (lockDeadlineEl) lockDeadlineEl.checked = true;
        if (studentSelectorEl) studentSelectorEl.style.display = 'none';
        if (selectedStudentsEl) selectedStudentsEl.innerHTML = '';
        
        quizQuestions = [];
        quizQuestionCounter = 0;
        
        // Clear questions container
        const container = document.getElementById('quiz-questions-container');
        if (container) {
            container.innerHTML = '';
        }
        
        // Add first question by default
        addQuizQuestion();
        
        clearQuizErrors();
        
        // Close on outside click
        modal.onclick = (e) => {
            if (e.target === modal) closeQuizModal();
        };
    }
}

// Handle assignment type change in quiz modal
function handleAssignmentTypeChange() {
    const assignmentTypeEl = document.getElementById('quiz-modal-assignment-type');
    const studentSelector = document.getElementById('quiz-student-selector');
    
    if (!assignmentTypeEl || !studentSelector) {
        console.error('Quiz assignment type elements not found');
        return;
    }
    
    const assignmentType = assignmentTypeEl.value;
    
    if (assignmentType === 'selected_students') {
        studentSelector.style.display = 'block';
        loadStudentsForQuiz();
    } else {
        studentSelector.style.display = 'none';
    }
}

// Load students for quiz assignment
async function loadStudentsForQuiz() {
    try {
        const studentsContainer = document.getElementById('quiz-selected-students');
        if (!studentsContainer) return;
        
        // Get all students
        const students = await facultyAPI.getStudentPerformance();
        
        if (!students.performance || students.performance.length === 0) {
            studentsContainer.innerHTML = '<p style="color: rgba(232,236,243,0.6); padding: 10px;">No students available</p>';
            return;
        }
        
        studentsContainer.innerHTML = students.performance.map(perf => {
            const student = perf.student;
            return `
                <label style="display: flex; align-items: center; gap: 10px; padding: 8px; cursor: pointer; border-radius: 4px; transition: background 0.2s;">
                    <input type="checkbox" value="${student.id}" style="cursor: pointer;">
                    <span>${student.full_name || student.username} (${student.username})</span>
                </label>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Error loading students:', error);
        const studentsContainer = document.getElementById('quiz-selected-students');
        if (studentsContainer) {
            studentsContainer.innerHTML = '<p style="color: #ff6b6b; padding: 10px;">Error loading students</p>';
        }
    }
}

function closeQuizModal() {
    const modal = document.getElementById('quiz-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function addQuizQuestion() {
    const container = document.getElementById('quiz-questions-container');
    if (!container) return;
    
    const questionId = `quiz-q-${quizQuestionCounter++}`;
    const questionData = {
        id: questionId,
        question: '',
        options: ['', ''],
        correctAnswer: '',
        marks: 1
    };
    quizQuestions.push(questionData);
    
    const questionDiv = document.createElement('div');
    questionDiv.className = 'quiz-question-builder';
    questionDiv.id = questionId;
    questionDiv.innerHTML = `
        <div style="background: rgba(255,255,255,0.05); padding: 16px; border-radius: 8px; margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h4 style="margin: 0; color: #f2f4ff;">Question ${quizQuestions.length}</h4>
                <button type="button" class="btn-remove-option" onclick="removeQuizQuestion('${questionId}')" ${quizQuestions.length <= 1 ? 'style="display: none;"' : ''}>âœ• Remove</button>
            </div>
            
            <label>Question <span class="required-star">â˜…</span></label>
            <textarea class="quiz-q-input" data-field="question" rows="2" placeholder="Enter question text"></textarea>
            <div class="cp-error quiz-q-error" data-field="question"></div>

            <label>Options <span class="required-star">â˜…</span></label>
            <div class="quiz-options-container" data-question-id="${questionId}">
                <div class="option-row">
                    <input type="text" class="option-input quiz-option-input" placeholder="Option A" data-option="A">
                    <button class="btn-remove-option" onclick="removeQuizOption(this, '${questionId}')" style="display: none;">âœ•</button>
                </div>
                <div class="option-row">
                    <input type="text" class="option-input quiz-option-input" placeholder="Option B" data-option="B">
                    <button class="btn-remove-option" onclick="removeQuizOption(this, '${questionId}')" style="display: none;">âœ•</button>
                </div>
            </div>
            <button type="button" class="btn btn-sm" onclick="addQuizOption('${questionId}')" style="margin-top: 8px;">+ Add Option</button>
            <div class="cp-error quiz-q-error" data-field="options"></div>

            <label>Correct Answer <span class="required-star">â˜…</span></label>
            <select class="quiz-q-select" data-field="correctAnswer" data-question-id="${questionId}">
                <option value="">Select correct answer</option>
                <option value="A">A</option>
                <option value="B">B</option>
            </select>
            <div class="cp-error quiz-q-error" data-field="correctAnswer"></div>

            <label>Marks <span class="required-star">â˜…</span></label>
            <input type="number" class="quiz-q-input" data-field="marks" min="1" value="1" placeholder="Marks">
            <div class="cp-error quiz-q-error" data-field="marks"></div>
        </div>
    `;
    
    container.appendChild(questionDiv);
    
    // Add event listeners
    setupQuizQuestionListeners(questionId);
    updateQuizCorrectAnswerOptions(questionId);
}

function setupQuizQuestionListeners(questionId) {
    const questionDiv = document.getElementById(questionId);
    if (!questionDiv) return;
    
    // Update question data on input change
    questionDiv.querySelectorAll('.quiz-q-input, .quiz-q-select').forEach(input => {
        input.addEventListener('input', () => updateQuizQuestionData(questionId));
        input.addEventListener('change', () => updateQuizQuestionData(questionId));
    });
    
    // Update options on input
    questionDiv.querySelectorAll('.quiz-option-input').forEach(input => {
        input.addEventListener('input', () => {
            updateQuizQuestionData(questionId);
            updateQuizCorrectAnswerOptions(questionId);
        });
    });
}

function updateQuizQuestionData(questionId) {
    const questionDiv = document.getElementById(questionId);
    if (!questionDiv) return;
    
    const questionData = quizQuestions.find(q => q.id === questionId);
    if (!questionData) return;
    
    // Update question text
    const questionInput = questionDiv.querySelector('[data-field="question"]');
    if (questionInput) questionData.question = questionInput.value.trim();
    
    // Update options
    const optionInputs = questionDiv.querySelectorAll('.quiz-option-input');
    questionData.options = Array.from(optionInputs).map(input => input.value.trim());
    
    // Update correct answer
    const correctAnswerSelect = questionDiv.querySelector('[data-field="correctAnswer"]');
    if (correctAnswerSelect) questionData.correctAnswer = correctAnswerSelect.value;
    
    // Update marks
    const marksInput = questionDiv.querySelector('[data-field="marks"]');
    if (marksInput) questionData.marks = parseInt(marksInput.value) || 1;
}

function addQuizOption(questionId) {
    const container = document.querySelector(`[data-question-id="${questionId}"]`);
    if (!container) return;
    
    const questionData = quizQuestions.find(q => q.id === questionId);
    if (!questionData) return;
    
    if (questionData.options.length >= 10) {
        alert('Maximum 10 options allowed per question');
        return;
    }
    
    const currentOptions = container.querySelectorAll('.option-row');
    const letter = String.fromCharCode(65 + currentOptions.length);
    
    const row = document.createElement('div');
    row.className = 'option-row';
    row.innerHTML = `
        <input type="text" class="option-input quiz-option-input" placeholder="Option ${letter}" data-option="${letter}">
        <button class="btn-remove-option" onclick="removeQuizOption(this, '${questionId}')">âœ•</button>
    `;
    container.appendChild(row);
    
    questionData.options.push('');
    updateQuizCorrectAnswerOptions(questionId);
    
    // Add event listener
    row.querySelector('.quiz-option-input').addEventListener('input', () => {
        updateQuizQuestionData(questionId);
        updateQuizCorrectAnswerOptions(questionId);
    });
}

function removeQuizOption(btn, questionId) {
    const container = document.querySelector(`[data-question-id="${questionId}"]`);
    if (!container) return;
    
    const rows = container.querySelectorAll('.option-row');
    if (rows.length <= 2) {
        alert('Minimum 2 options required');
        return;
    }
    
    btn.closest('.option-row').remove();
    updateQuizQuestionData(questionId);
    updateQuizOptionLabels(questionId);
    updateQuizCorrectAnswerOptions(questionId);
}

function updateQuizOptionLabels(questionId) {
    const container = document.querySelector(`[data-question-id="${questionId}"]`);
    if (!container) return;
    
    const rows = container.querySelectorAll('.option-row');
    rows.forEach((row, idx) => {
        const letter = String.fromCharCode(65 + idx);
        const input = row.querySelector('.quiz-option-input');
        if (input) {
            input.setAttribute('data-option', letter);
            input.placeholder = `Option ${letter}`;
        }
        const removeBtn = row.querySelector('.btn-remove-option');
        if (removeBtn) {
            removeBtn.style.display = rows.length > 2 ? 'block' : 'none';
        }
    });
}

function updateQuizCorrectAnswerOptions(questionId) {
    const questionDiv = document.getElementById(questionId);
    if (!questionDiv) return;
    
    const select = questionDiv.querySelector('[data-field="correctAnswer"]');
    if (!select) return;
    
    const container = document.querySelector(`[data-question-id="${questionId}"]`);
    if (!container) return;
    
    const currentValue = select.value;
    const rows = container.querySelectorAll('.option-row');
    
    select.innerHTML = '<option value="">Select correct answer</option>';
    rows.forEach((row, idx) => {
        const letter = String.fromCharCode(65 + idx);
        const option = document.createElement('option');
        option.value = letter;
        option.textContent = letter;
        select.appendChild(option);
    });
    
    if (currentValue && Array.from(select.options).some(opt => opt.value === currentValue)) {
        select.value = currentValue;
    }
}

function removeQuizQuestion(questionId) {
    if (quizQuestions.length <= 1) {
        alert('At least one question is required');
        return;
    }
    
    const questionDiv = document.getElementById(questionId);
    if (questionDiv) {
        questionDiv.remove();
    }
    
    quizQuestions = quizQuestions.filter(q => q.id !== questionId);
    
    // Renumber questions
    const container = document.getElementById('quiz-questions-container');
    if (container) {
        const questions = container.querySelectorAll('.quiz-question-builder');
        questions.forEach((q, idx) => {
            const title = q.querySelector('h4');
            if (title) title.textContent = `Question ${idx + 1}`;
        });
    }
}

function clearQuizErrors() {
    document.getElementById('quiz-error-title').textContent = '';
    document.getElementById('quiz-error-questions').textContent = '';
    document.querySelectorAll('.quiz-q-error').forEach(el => el.textContent = '');
}

async function submitQuizCreation() {
    const title = document.getElementById('quiz-modal-title').value.trim();
    const description = document.getElementById('quiz-modal-description').value.trim();
    const duration = parseInt(document.getElementById('quiz-modal-duration').value) || 60;
    
    let hasError = false;
    clearQuizErrors();
    
    if (!title) {
        document.getElementById('quiz-error-title').textContent = 'Quiz title is required';
        hasError = true;
    }
    
    // Validate all questions
    quizQuestions.forEach((qData, idx) => {
        const questionDiv = document.getElementById(qData.id);
        if (!questionDiv) return;
        
        if (!qData.question) {
            const errorEl = questionDiv.querySelector('[data-field="question"].quiz-q-error');
            if (errorEl) errorEl.textContent = 'Question is required';
            hasError = true;
        }
        
        const validOptions = qData.options.filter(opt => opt.trim().length > 0);
        if (validOptions.length < 2) {
            const errorEl = questionDiv.querySelector('[data-field="options"].quiz-q-error');
            if (errorEl) errorEl.textContent = 'At least 2 options are required';
            hasError = true;
        }
        
        if (!qData.correctAnswer) {
            const errorEl = questionDiv.querySelector('[data-field="correctAnswer"].quiz-q-error');
            if (errorEl) errorEl.textContent = 'Please select the correct answer';
            hasError = true;
        }
        
        if (qData.marks < 1) {
            const errorEl = questionDiv.querySelector('[data-field="marks"].quiz-q-error');
            if (errorEl) errorEl.textContent = 'Marks must be at least 1';
            hasError = true;
        }
    });
    
    if (quizQuestions.length === 0) {
        document.getElementById('quiz-error-questions').textContent = 'At least one question is required';
        hasError = true;
    }
    
    if (hasError) return;
    
    try {
        // First, create all questions
        const questionIds = [];
        for (let i = 0; i < quizQuestions.length; i++) {
            const qData = quizQuestions[i];
            const validOptions = qData.options.filter(opt => opt.trim().length > 0);
            
            if (validOptions.length < 2) {
                throw new Error(`Question ${i + 1} must have at least 2 options`);
            }
            
            if (!qData.correctAnswer || qData.correctAnswer.trim() === '') {
                throw new Error(`Question ${i + 1} must have a correct answer`);
            }
            
            const questionPayload = {
                title: qData.question.substring(0, 100),
                description: qData.question,
                type: 'mcq',
                module_type: 'Non-Technical',  // Required: Set to Non-Technical for quiz questions
                difficulty: 'medium',
                options: validOptions,
                correct_answer: qData.correctAnswer,
                marks: qData.marks || 1
            };
            
            console.log(`Creating question ${i + 1}:`, questionPayload);
            const result = await facultyAPI.createQuestion(questionPayload);
            console.log(`Question ${i + 1} created:`, result);
            
            if (!result || !result.question || !result.question.id) {
                throw new Error(`Failed to create question ${i + 1}: Invalid response from server`);
            }
            
            questionIds.push(result.question.id);
        }
        
        if (questionIds.length === 0) {
            throw new Error('No questions were created');
        }
        
        // Create a map of question IDs to their marks
        const questionMarksMap = {};
        quizQuestions.forEach((qData, idx) => {
            if (questionIds[idx]) {
                questionMarksMap[questionIds[idx]] = qData.marks || 1;
            }
        });
        
        // Calculate total marks
        const totalMarks = quizQuestions.reduce((sum, q) => sum + (q.marks || 1), 0);
        
        // Get deadline and assignment settings
        const deadlineInput = document.getElementById('quiz-modal-deadline');
        const deadline = deadlineInput.value ? new Date(deadlineInput.value).toISOString() : null;
        
        const assignmentType = document.getElementById('quiz-modal-assignment-type').value;
        const lockAfterDeadline = document.getElementById('quiz-modal-lock-deadline').checked;
        
        // Get selected student IDs if assignment type is 'selected_students'
        let assignedStudentIds = [];
        if (assignmentType === 'selected_students') {
            const selectedCheckboxes = document.querySelectorAll('#quiz-selected-students input[type="checkbox"]:checked');
            assignedStudentIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));
            
            if (assignedStudentIds.length === 0) {
                throw new Error('Please select at least one student when using "Selected Students" assignment');
            }
        }
        
        // Then create the quiz with these questions
        const quizPayload = {
            title: title,
            description: description,
            duration_minutes: parseInt(duration) || 15,
            question_ids: questionIds,
            question_marks: questionMarksMap,
            total_marks: totalMarks,
            marks_per_question: 1,  // Fallback default
            deadline: deadline,
            assignment_type: assignmentType,
            assigned_student_ids: assignedStudentIds,
            lock_after_deadline: lockAfterDeadline
        };
        
        console.log('Creating quiz with payload:', quizPayload);
        const quizResult = await facultyAPI.createQuiz(quizPayload);
        console.log('Quiz created:', quizResult);
        
        closeQuizModal();
        await loadQuizzesPage();
        alert('Quiz created successfully!');
    } catch (error) {
        console.error('Quiz creation error:', error);
        const errorMsg = error.message || 'Failed to create quiz';
        const errorEl = document.getElementById('quiz-error-title');
        if (errorEl) {
            errorEl.textContent = errorMsg;
        }
        alert(`Error creating quiz: ${errorMsg}\n\nPlease check:\n1. Backend server is running\n2. Database connection is working\n3. All required fields are filled`);
    }
}

// Quiz Page
let deleteMode = false;
let selectedQuizIds = new Set();

async function loadQuizzesPage() {
    try {
        // Reset delete mode
        deleteMode = false;
        selectedQuizIds.clear();
        
        // Show quiz list and hide quiz taking view
        const quizzesList = document.getElementById('quizzes-list');
        const quizTaking = document.getElementById('quiz-taking');
        if (quizzesList) quizzesList.style.display = 'block';
        if (quizTaking) quizTaking.style.display = 'none';
        
        // Check user role for +Add button visibility
        const addBtn = document.getElementById('add-quiz-btn');
        if (addBtn) {
            // Hide "Add Quiz" button for students - they can only attempt quizzes
            if (currentUser && currentUser.role === 'student') {
                addBtn.style.display = 'none';
            } else {
                // Show for faculty and admin
                addBtn.style.display = 'block';
            }
        }
        
        const data = await quizAPI.listQuizzes({ is_active: 'true' });
        const quizzesDiv = document.getElementById('quizzes-list');
        
        // Check if user is faculty or admin (can delete quizzes)
        const canDelete = currentUser && (currentUser.role === 'faculty' || currentUser.role === 'admin');
        
        // Update delete button visibility - only show in quiz list view
        const deleteBtn = document.getElementById('delete-mode-btn');
        if (deleteBtn) {
            deleteBtn.style.display = canDelete ? 'block' : 'none';
        }
        
        // Hide selection controls initially
        updateDeleteModeUI();
        
        if (data.quizzes && data.quizzes.length > 0) {
            renderQuizzesList(data.quizzes, canDelete);
        } else {
            quizzesDiv.innerHTML = '<p>No quizzes available yet.</p>';
        }
    } catch (error) {
        console.error('Error loading quizzes:', error);
    }
}

function renderQuizzesList(quizzes, canDelete) {
    const quizzesDiv = document.getElementById('quizzes-list');
    if (!quizzesDiv) return;
    
    quizzesDiv.innerHTML = quizzes.map(q => `
        <div class="quiz-item ${deleteMode ? 'delete-mode' : ''}" data-quiz-id="${q.id}">
            ${deleteMode && canDelete ? `
                <input type="checkbox" class="quiz-select-checkbox" 
                       onchange="toggleQuizSelection(${q.id})" 
                       ${selectedQuizIds.has(q.id) ? 'checked' : ''}>
            ` : ''}
            <div class="quiz-item-content" onclick="${deleteMode ? 'event.stopPropagation();' : `openQuiz(${q.id})`}">
                <h4 class="quiz-title-clickable">${q.title}</h4>
                <p>${q.description || ''}</p>
                <small>Duration: ${q.duration_minutes} minutes | Total Marks: ${q.total_marks}</small>
            </div>
            ${!deleteMode ? `
                <button class="btn-open-quiz" onclick="event.stopPropagation(); openQuiz(${q.id})" title="Open Quiz">
                    Open
                </button>
            ` : ''}
        </div>
    `).join('');
}

async function toggleDeleteMode() {
    deleteMode = !deleteMode;
    selectedQuizIds.clear();
    updateDeleteModeUI();
    
    try {
        const data = await quizAPI.listQuizzes({ is_active: 'true' });
        const canDelete = currentUser && (currentUser.role === 'faculty' || currentUser.role === 'admin');
        renderQuizzesList(data.quizzes || [], canDelete);
    } catch (err) {
        console.error('Error reloading quizzes:', err);
    }
}

function toggleQuizSelection(quizId) {
    if (selectedQuizIds.has(quizId)) {
        selectedQuizIds.delete(quizId);
    } else {
        selectedQuizIds.add(quizId);
    }
    updateDeleteButtonState();
    
    // Update checkbox state visually
    const checkbox = document.querySelector(`.quiz-select-checkbox[onchange*="${quizId}"]`);
    if (checkbox) {
        checkbox.checked = selectedQuizIds.has(quizId);
    }
}

function updateDeleteModeUI() {
    const deleteBtn = document.getElementById('delete-mode-btn');
    const cancelBtn = document.getElementById('cancel-delete-btn');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    
    if (deleteMode) {
        if (deleteBtn) deleteBtn.textContent = 'Cancel';
        if (cancelBtn) cancelBtn.style.display = 'none';
        if (confirmDeleteBtn) confirmDeleteBtn.style.display = selectedQuizIds.size > 0 ? 'block' : 'none';
    } else {
        if (deleteBtn) deleteBtn.textContent = 'Delete';
        if (cancelBtn) cancelBtn.style.display = 'none';
        if (confirmDeleteBtn) confirmDeleteBtn.style.display = 'none';
    }
}

function updateDeleteButtonState() {
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.style.display = selectedQuizIds.size > 0 ? 'block' : 'none';
        confirmDeleteBtn.textContent = `Delete Selected (${selectedQuizIds.size})`;
    }
}

function cancelDeleteMode() {
    deleteMode = false;
    selectedQuizIds.clear();
    updateDeleteModeUI();
    loadQuizzesPage();
}

async function confirmDeleteSelected() {
    if (selectedQuizIds.size === 0) {
        alert('Please select at least one quiz to delete');
        return;
    }
    
    const count = selectedQuizIds.size;
    if (!confirm(`Are you sure you want to delete ${count} quiz${count > 1 ? 'es' : ''}?\n\nThis action cannot be undone.`)) {
        return;
    }
    
    try {
        const deletePromises = Array.from(selectedQuizIds).map(quizId => 
            facultyAPI.deleteQuiz(quizId).catch(err => {
                console.error(`Error deleting quiz ${quizId}:`, err);
                return { error: true, quizId };
            })
        );
        
        const results = await Promise.all(deletePromises);
        const errors = results.filter(r => r && r.error);
        
        if (errors.length > 0) {
            alert(`Deleted ${count - errors.length} quiz${count - errors.length > 1 ? 'es' : ''}, but ${errors.length} failed.`);
        } else {
            alert(`Successfully deleted ${count} quiz${count > 1 ? 'es' : ''}!`);
        }
        
        cancelDeleteMode();
    } catch (error) {
        console.error('Error deleting quizzes:', error);
        alert(`Error deleting quizzes: ${error.message || 'Failed to delete quizzes'}`);
    }
}


function selectQuizOption(radioId) {
    const radio = document.getElementById(radioId);
    if (radio) {
        radio.checked = true;
        // Trigger change event to ensure form state is updated
        radio.dispatchEvent(new Event('change', { bubbles: true }));
    }
}

function openQuiz(quizId) {
    takeQuiz(quizId);
}

async function takeQuiz(quizId) {
    try {
        const data = await quizAPI.getQuiz(quizId);
        currentQuiz = data.quiz;
        currentQuizId = quizId;
        
        // Hide delete button when taking quiz
        const deleteBtn = document.getElementById('delete-mode-btn');
        const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
        if (deleteBtn) deleteBtn.style.display = 'none';
        if (confirmDeleteBtn) confirmDeleteBtn.style.display = 'none';
        
        document.getElementById('quizzes-list').style.display = 'none';
        document.getElementById('quiz-taking').style.display = 'block';
        document.getElementById('quiz-results').style.display = 'none';
        document.getElementById('quiz-title').textContent = currentQuiz.title;
        
        const questionsDiv = document.getElementById('quiz-questions');
        questionsDiv.innerHTML = currentQuiz.questions.map((qq, idx) => {
            const q = qq.question;
            let html = `<div class="quiz-question" data-question-id="${q.id}">
                <h4>Question ${idx + 1}: ${q.title}</h4>`;
            
            // Only show description if it's different from title and not empty
            if (q.description && q.description.trim() !== q.title.trim() && q.description.trim() !== '') {
                // Format description with proper code block rendering
                html += formatQuestionDescription(q.description);
            }
            
            if (q.type === 'mcq') {
                html += q.options.map((opt, i) => `
                    <div class="quiz-option" onclick="selectQuizOption('q${q.id}_${i}')">
                        <input type="radio" name="q${q.id}" value="${String.fromCharCode(65 + i)}" id="q${q.id}_${i}">
                        <label for="q${q.id}_${i}" onclick="event.stopPropagation();">${opt}</label>
                    </div>
                `).join('');
            } else if (q.type === 'fill_blank') {
                html += q.blanks.map(blank => `
                    <div>
                        <label>${blank.text}</label>
                        <input type="text" name="q${q.id}_${blank.id}" placeholder="Your answer">
                    </div>
                `).join('');
            }
            
            html += '</div>';
            return html;
        }).join('');
    } catch (error) {
        console.error('Error loading quiz:', error);
    }
}

async function submitQuiz() {
    if (!currentQuiz) return;
    
    const answers = {};
    const questionElements = document.querySelectorAll('.quiz-question');
    
    questionElements.forEach(qDiv => {
        const radios = qDiv.querySelectorAll('input[type="radio"]:checked');
        const textInputs = qDiv.querySelectorAll('input[type="text"]');
        
        if (radios.length > 0) {
            const qId = radios[0].name.replace('q', '');
            answers[qId] = radios[0].value;
        } else if (textInputs.length > 0) {
            const qId = textInputs[0].name.split('_')[0].replace('q', '');
            if (!answers[qId]) answers[qId] = {};
            textInputs.forEach(input => {
                const blankId = input.name.split('_')[1];
                answers[qId][blankId] = input.value;
            });
        }
    });
    
    try {
        const result = await quizAPI.attemptQuiz(currentQuiz.id, answers);
        
        // Display results with âœ…/âŒ
        displayQuizResults(result, currentQuiz);
        
        // Refresh Placement Readiness Score after quiz submission
        // Use setTimeout to ensure the backend has processed the quiz attempt
        setTimeout(() => {
            if (typeof loadPlacementReadinessScore === 'function') {
                loadPlacementReadinessScore();
            }
        }, 1000);
        
        loadDashboard();
        // Load notification badge count (only if logged in)
        if (authToken && currentUser) {
            loadNotificationBadge();
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

function displayQuizResults(result, quiz) {
    const resultsDiv = document.getElementById('quiz-results');
    const questionsDiv = document.getElementById('quiz-questions');
    
    // Hide submit button
    const submitBtn = document.querySelector('#quiz-taking button[onclick="submitQuiz()"]');
    if (submitBtn) submitBtn.style.display = 'none';
    
    // Get results from backend
    const questionResults = result.question_results || {};
    const obtainedMarks = result.obtained_marks || 0;
    const totalMarks = result.total_marks || 0;
    const score = result.score || 0;
    
    // Update each question with result indicator
    quiz.questions.forEach((qq, idx) => {
        const q = qq.question;
        const questionDiv = questionsDiv.querySelector(`[data-question-id="${q.id}"]`);
        if (!questionDiv) return;
        
        // Get result for this question
        const qResult = questionResults[q.id];
        if (!qResult) return;
        
        const isCorrect = qResult.is_correct;
        const userAnswer = qResult.user_answer || '';
        const correctAnswer = qResult.correct_answer || q.correct_answer || '';
        
        // Format correct answer for display (convert A, B, C to option text if needed)
        let correctAnswerText = correctAnswer;
        if (q.type === 'mcq' && q.options && q.options.length > 0) {
            const answerIndex = correctAnswer.charCodeAt(0) - 65; // A=0, B=1, C=2, etc.
            if (answerIndex >= 0 && answerIndex < q.options.length) {
                correctAnswerText = `${correctAnswer} - ${q.options[answerIndex]}`;
            }
        }
        
        // Add result indicator
        const indicator = document.createElement('div');
        indicator.className = 'quiz-result-indicator';
        indicator.style.marginTop = '12px';
        indicator.style.padding = '10px';
        indicator.style.borderRadius = '5px';
        indicator.style.backgroundColor = isCorrect ? 'rgba(40, 167, 69, 0.2)' : 'rgba(220, 53, 69, 0.2)';
        indicator.style.border = `1px solid ${isCorrect ? '#28a745' : '#dc3545'}`;
        
        indicator.innerHTML = isCorrect 
            ? `<span class="result-correct" style="color: #28a745; font-weight: bold;">âœ… Correct</span><br><small style="color: #b8b8d1;">Marks: ${qResult.marks_obtained}/${qResult.marks_total}</small>` 
            : `<span class="result-wrong" style="color: #dc3545; font-weight: bold;">âŒ Wrong</span><br><small style="color: #b8b8d1;">Your answer: ${userAnswer || 'Not answered'}</small><br><small style="color: #b8b8d1;">Correct answer: ${correctAnswerText}</small><br><small style="color: #b8b8d1;">Marks: ${qResult.marks_obtained}/${qResult.marks_total}</small>`;
        
        questionDiv.appendChild(indicator);
        
        // Disable inputs
        questionDiv.querySelectorAll('input').forEach(input => {
            input.disabled = true;
        });
    });
    
    // Show results summary
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = `
        <h3 style="color: #f2f4ff; margin-bottom: 15px;">Quiz Results</h3>
        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            <div style="background: rgba(102, 126, 234, 0.2); padding: 15px; border-radius: 5px; border: 1px solid #667eea;">
                <p style="color: #b8b8d1; margin: 0 0 5px 0; font-size: 14px;">Marks Obtained</p>
                <p style="color: #f2f4ff; margin: 0; font-size: 24px; font-weight: bold;">${obtainedMarks}/${totalMarks}</p>
            </div>
            <div style="background: rgba(102, 126, 234, 0.2); padding: 15px; border-radius: 5px; border: 1px solid #667eea;">
                <p style="color: #b8b8d1; margin: 0 0 5px 0; font-size: 14px;">Score</p>
                <p style="color: #f2f4ff; margin: 0; font-size: 24px; font-weight: bold;">${score.toFixed(1)}%</p>
            </div>
        </div>
    `;
}

// Companies Page
async function loadCompanies() {
    try {
        // Only load companies if user is logged in
        if (!authToken || !currentUser) {
            companies = [];
            return;
        }
        const data = await companyAPI.listCompanies();
        companies = data.companies;
        // Re-render companies to apply any active search filter
        renderCompanies();
    } catch (error) {
        console.error('Error loading companies:', error);
        companies = [];
    }
}

let companyDeleteMode = false;
let selectedCompanyIds = new Set();

async function loadCompaniesPage() {
    await loadCompanies();
    
    // Reset delete mode
    companyDeleteMode = false;
    selectedCompanyIds.clear();
    
    // Check user role and show delete button if faculty/admin
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
    const canDelete = currentUser && (currentUser.role === 'faculty' || currentUser.role === 'admin');
    const deleteBtn = document.getElementById('delete-company-btn');
    if (deleteBtn && canDelete) {
        deleteBtn.style.display = 'block';
    } else if (deleteBtn) {
        deleteBtn.style.display = 'none';
    }
    
    updateCompanyDeleteModeUI();
    renderCompanies();
}

function renderCompanies() {
    const companiesDiv = document.getElementById('companies-list');
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
    const canDelete = currentUser && (currentUser.role === 'faculty' || currentUser.role === 'admin');
    
    // Filter companies based on search term
    let filteredCompanies = companies;
    if (companySearchTerm.trim()) {
        const searchLower = companySearchTerm.toLowerCase().trim();
        filteredCompanies = companies.filter(c => 
            c.name.toLowerCase().includes(searchLower) || 
            (c.description && c.description.toLowerCase().includes(searchLower))
        );
    }
    
    // Update search results count
    const searchResultsDiv = document.getElementById('company-search-results');
    if (searchResultsDiv) {
        if (companySearchTerm.trim()) {
            searchResultsDiv.style.display = 'block';
            searchResultsDiv.textContent = `Found ${filteredCompanies.length} of ${companies.length} companies`;
        } else {
            searchResultsDiv.style.display = 'none';
        }
    }
    
    // Show message if no companies found
    if (filteredCompanies.length === 0) {
        companiesDiv.innerHTML = `
            <div style="padding: 40px; text-align: center; background: rgba(102, 126, 234, 0.1); border-radius: 8px;">
                <p style="color: #8b9aff; font-size: 16px; margin-bottom: 10px;">No companies found</p>
                <p style="color: #9cb2d4; font-size: 14px;">${companySearchTerm.trim() ? 'Try a different search term' : 'No companies available'}</p>
            </div>
        `;
        return;
    }
    
    companiesDiv.innerHTML = filteredCompanies.map(c => `
        <div class="company-card ${companyDeleteMode ? 'delete-mode' : ''}"
             data-company-id="${c.id}"
             ${!companyDeleteMode ? `onclick="openCompanyQuestions(${c.id})"` : ''}
             style="${!companyDeleteMode ? 'cursor: pointer;' : ''}">
            ${companyDeleteMode && canDelete ? `
                <input type="checkbox" class="company-select-checkbox" 
                       onchange="toggleCompanySelection(${c.id})" 
                       ${selectedCompanyIds.has(c.id) ? 'checked' : ''}
                       style="margin-right: 15px;"
                       onclick="event.stopPropagation();">
            ` : ''}
            <div class="company-card-content" style="flex: 1;">
                <h3>${c.name}</h3>
                <p>${c.description || ''}</p>
            </div>
            ${!companyDeleteMode ? `
                <button class="btn btn-sm company-open-btn" type="button" data-company-id="${c.id}"
                        style="margin-left: auto; padding: 8px 16px; background: rgba(102, 126, 234, 0.2); color: #8b9aff; border: 1px solid rgba(102, 126, 234, 0.3);">
                    Open
                </button>
            ` : ''}
        </div>
    `).join('');

    // Bind direct click handlers after rendering. This is more reliable than
    // relying only on inline onclick attributes inside generated markup.
    if (!companyDeleteMode) {
        companiesDiv.querySelectorAll('.company-card[data-company-id]').forEach(card => {
            card.addEventListener('click', () => {
                openCompanyQuestions(Number(card.dataset.companyId));
            });
        });

        companiesDiv.querySelectorAll('.company-open-btn[data-company-id]').forEach(button => {
            button.addEventListener('click', (event) => {
                event.stopPropagation();
                openCompanyQuestions(Number(button.dataset.companyId));
            });
        });
    }
}

async function openCompanyQuestions(companyId) {
    try {
        // Find the company
        const company = companies.find(c => c.id === companyId);
        if (!company) {
            alert('Company not found');
            return;
        }
        
        // Navigate to company posts page
        showCompanyPostsPage(companyId, company.name);
        
        // Load posts filtered by this company
        const data = await postsAPI.getPosts({ company_id: companyId });
        const postsDiv = document.getElementById('company-posts-list');
        
        if (!data.posts || data.posts.length === 0) {
            postsDiv.innerHTML = `
                <div style="margin-top: 20px; padding: 40px; text-align: center; background: rgba(102, 126, 234, 0.1); border-radius: 8px;">
                    <h3 style="color: #8b9aff; margin-bottom: 10px;">${company.name} - Interview Questions</h3>
                    <p style="color: rgba(242, 244, 255, 0.6); margin-bottom: 20px;">No posts yet for ${company.name}. Be the first to share your interview experience!</p>
                    <button class="btn btn-primary" onclick="openPostModal()">+ Add First Question</button>
                </div>
            `;
            return;
        }
        
        postsDiv.innerHTML = `
            <div style="margin-bottom: 20px; padding: 15px; background: rgba(102, 126, 234, 0.1); border-radius: 8px; border-left: 3px solid #667eea;">
                <h3 style="color: #8b9aff; margin: 0 0 5px 0;">${company.name} - Interview Questions</h3>
                <p style="color: #b8b8d1; margin: 0; font-size: 14px;">Total: ${data.posts.length} question${data.posts.length > 1 ? 's' : ''}</p>
            </div>
            ${data.posts.map(post => {
                // Get first MCQ question if available
                const mcq = post.mcq_questions && post.mcq_questions.length > 0 ? post.mcq_questions[0] : null;
                
                return `
                <div class="post-card">
                    <div class="post-header">
                        <h4>${post.company_name || 'Unknown Company'}</h4>
                        <span class="post-type-badge">${post.post_type || 'Question'}</span>
                    </div>
                    <div class="post-meta">
                        <span>${post.user_name || 'Anonymous'}</span>
                        <span>â€¢</span>
                        <span>${new Date(post.created_at).toLocaleDateString()}</span>
                    </div>
                    
                    ${mcq ? `
                        <div class="post-question-section" style="margin: 15px 0; padding: 15px; background: rgba(102, 126, 234, 0.1); border-radius: 8px; border-left: 3px solid #667eea;">
                            <p style="font-weight: 600; color: #f2f4ff; margin-bottom: 12px; font-size: 15px;">${mcq.question || 'Question'}</p>
                            <div style="margin-left: 10px;">
                                ${mcq.options && mcq.options.map((opt, optIdx) => {
                                    const optionLetter = String.fromCharCode(65 + optIdx);
                                    const isCorrect = optionLetter === mcq.correct_answer;
                                    return `
                                        <div style="display: flex; align-items: center; margin: 8px 0; padding: 8px; background: ${isCorrect ? 'rgba(102, 227, 196, 0.15)' : 'rgba(255,255,255,0.03)'}; border-radius: 6px; border: 1px solid ${isCorrect ? 'rgba(102, 227, 196, 0.3)' : 'rgba(255,255,255,0.08)'};">
                                            <span style="color: ${isCorrect ? '#66e3c4' : '#9cb2d4'}; font-weight: ${isCorrect ? '600' : '400'}; margin-right: 10px; min-width: 20px;">
                                                ${isCorrect ? 'âœ“' : 'â—‹'} ${optionLetter}.
                                            </span>
                                            <span style="color: ${isCorrect ? '#66e3c4' : '#b8b8d1'}; flex: 1;">${opt}</span>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${post.content ? `
                        <div class="post-description-section" style="margin: 15px 0; padding: 15px; background: rgba(255,255,255,0.03); border-radius: 8px; border-left: 3px solid rgba(102, 126, 234, 0.5);">
                            <h5 style="color: #8b9aff; margin-bottom: 10px; font-size: 14px;">ðŸ“ Description / Topics</h5>
                            <p style="color: #b8b8d1; line-height: 1.6; white-space: pre-wrap;">${post.content}</p>
                        </div>
                    ` : ''}
                    
                    ${post.file_path ? `
                        <div class="post-file-attachment" style="margin: 15px 0;">
                            <a href="${getApiBaseUrl()}/posts/${post.id}/file" target="_blank" class="file-link" style="display: inline-flex; align-items: center; padding: 8px 15px; background: rgba(102, 126, 234, 0.2); border-radius: 6px; color: #8b9aff; text-decoration: none;">
                                ðŸ“Ž View ${post.file_type ? post.file_type.toUpperCase() : 'File'}
                            </a>
                        </div>
                    ` : ''}
                </div>
            `;
            }).join('')}
        `;
        
    } catch (error) {
        console.error('Error loading company posts:', error);
        alert(`Error loading posts: ${error.message || 'Failed to load posts'}`);
    }
}

function showCompanyPostsPage(companyId, companyName) {
    // Keep the centralized renderer in sync. Without this, the next render
    // switches the visible page back to the companies list.
    if (typeof navigateToPage === 'function') {
        navigateToPage('company-posts', null, true);
    }
    if (typeof updateUIVisibility === 'function') {
        updateUIVisibility({ currentPageVisible: 'company-posts' }, true);
    }

    document.querySelectorAll('.page-content').forEach(page => {
        page.style.display = 'none';
    });
    
    const companyPostsPage = document.getElementById('company-posts-page');
    if (companyPostsPage) {
        companyPostsPage.style.display = 'block';
        
        const titleElement = document.getElementById('company-posts-title');
        if (titleElement) {
            titleElement.textContent = `${companyName} - Interview Questions`;
        }
    }
    
    window.currentCompanyId = companyId;
    window.currentCompanyName = companyName;
}

function toggleCompanyDeleteMode() {
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
    const canDelete = currentUser && (currentUser.role === 'faculty' || currentUser.role === 'admin');
    
    if (!canDelete) {
        alert('You do not have permission to delete companies');
        return;
    }
    
    companyDeleteMode = !companyDeleteMode;
    selectedCompanyIds.clear();
    updateCompanyDeleteModeUI();
    renderCompanies();
}

function updateCompanyDeleteModeUI() {
    const deleteBtn = document.getElementById('delete-company-btn');
    const confirmDeleteBtn = document.getElementById('confirm-delete-company-btn');
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
    const canDelete = currentUser && (currentUser.role === 'faculty' || currentUser.role === 'admin');
    
    if (deleteBtn) {
        if (canDelete) {
            deleteBtn.style.display = 'block';
            if (companyDeleteMode) {
                deleteBtn.textContent = 'âœ• Cancel';
                deleteBtn.classList.add('btn-secondary');
                deleteBtn.classList.remove('btn-delete-quiz');
            } else {
                deleteBtn.textContent = 'ðŸ—‘ï¸ Delete';
                deleteBtn.classList.remove('btn-secondary');
                deleteBtn.classList.add('btn-delete-quiz');
            }
        } else {
            deleteBtn.style.display = 'none';
        }
    }
    
    if (confirmDeleteBtn) {
        confirmDeleteBtn.style.display = companyDeleteMode && selectedCompanyIds.size > 0 ? 'block' : 'none';
        confirmDeleteBtn.textContent = `Delete Selected (${selectedCompanyIds.size})`;
    }
}

function toggleCompanySelection(companyId) {
    if (selectedCompanyIds.has(companyId)) {
        selectedCompanyIds.delete(companyId);
    } else {
        selectedCompanyIds.add(companyId);
    }
    updateCompanyDeleteModeUI();
}

function cancelCompanyDeleteMode() {
    companyDeleteMode = false;
    selectedCompanyIds.clear();
    updateCompanyDeleteModeUI();
    renderCompanies();
}

async function confirmDeleteSelectedCompanies() {
    if (selectedCompanyIds.size === 0) {
        alert('Please select at least one company to delete');
        return;
    }
    
    const count = selectedCompanyIds.size;
    if (!confirm(`Are you sure you want to delete ${count} compan${count > 1 ? 'ies' : 'y'}?\n\nThis will also delete all related posts, questions, and resources.\n\nThis action cannot be undone.`)) {
        return;
    }
    
    try {
        const deletePromises = Array.from(selectedCompanyIds).map(async (companyId) => {
            try {
                const result = await companyAPI.deleteCompany(companyId);
                return { success: true, companyId, result };
            } catch (err) {
                console.error(`Error deleting company ${companyId}:`, err);
                const errorMessage = err.message || (err.error || 'Unknown error');
                return { error: true, companyId, message: errorMessage };
            }
        });
        
        const results = await Promise.all(deletePromises);
        const errors = results.filter(r => r && r.error);
        const successes = results.filter(r => r && r.success);
        
        if (errors.length > 0) {
            const errorDetails = errors.map(e => `Company ID ${e.companyId}: ${e.message}`).join('\n');
            alert(`Deleted ${successes.length} compan${successes.length > 1 ? 'ies' : 'y'}, but ${errors.length} failed:\n\n${errorDetails}`);
        } else {
            alert(`Successfully deleted ${count} compan${count > 1 ? 'ies' : 'y'}!`);
        }
        
        cancelCompanyDeleteMode();
        await loadCompanies();
        renderCompanies();
    } catch (error) {
        console.error('Error deleting companies:', error);
        alert(`Error deleting companies: ${error.message || 'Failed to delete companies'}`);
    }
}

async function loadPosts() {
    try {
        const data = await postsAPI.getPosts();
        const postsDiv = document.getElementById('posts-list');
        
        if (!data.posts || data.posts.length === 0) {
            postsDiv.innerHTML = '<p style="text-align: center; color: rgba(242, 244, 255, 0.6); padding: 20px;">No posts yet. Be the first to share your interview experience!</p>';
            return;
        }
        
        postsDiv.innerHTML = `
            <h3 style="margin-bottom: 20px; color: #f2f4ff;">Recent Posts</h3>
            ${data.posts.map(post => {
                // Get first MCQ question if available
                const mcq = post.mcq_questions && post.mcq_questions.length > 0 ? post.mcq_questions[0] : null;
                
                return `
                <div class="post-card">
                    <div class="post-header">
                        <h4>${post.company_name || 'Unknown Company'}</h4>
                        <span class="post-type-badge">${post.post_type || 'Question'}</span>
                    </div>
                    <div class="post-meta">
                        <span>${post.user_name || 'Anonymous'}</span>
                        <span>â€¢</span>
                        <span>${new Date(post.created_at).toLocaleDateString()}</span>
                    </div>
                    
                    ${mcq ? `
                        <div class="post-question-section" style="margin: 15px 0; padding: 15px; background: rgba(102, 126, 234, 0.1); border-radius: 8px; border-left: 3px solid #667eea;">
                            <p style="font-weight: 600; color: #f2f4ff; margin-bottom: 12px; font-size: 15px;">${mcq.question || 'Question'}</p>
                            <div style="margin-left: 10px;">
                                ${mcq.options && mcq.options.map((opt, optIdx) => {
                                    const optionLetter = String.fromCharCode(65 + optIdx);
                                    const isCorrect = optionLetter === mcq.correct_answer;
                                    return `
                                        <div style="display: flex; align-items: center; margin: 8px 0; padding: 8px; background: ${isCorrect ? 'rgba(102, 227, 196, 0.15)' : 'rgba(255,255,255,0.03)'}; border-radius: 6px; border: 1px solid ${isCorrect ? 'rgba(102, 227, 196, 0.3)' : 'rgba(255,255,255,0.08)'};">
                                            <span style="color: ${isCorrect ? '#66e3c4' : '#9cb2d4'}; font-weight: ${isCorrect ? '600' : '400'}; margin-right: 10px; min-width: 20px;">
                                                ${isCorrect ? 'âœ“' : 'â—‹'} ${optionLetter}.
                                            </span>
                                            <span style="color: ${isCorrect ? '#66e3c4' : '#b8b8d1'}; flex: 1;">${opt}</span>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${post.content ? `
                        <div class="post-description-section" style="margin: 15px 0; padding: 15px; background: rgba(255,255,255,0.03); border-radius: 8px; border-left: 3px solid rgba(102, 126, 234, 0.5);">
                            <h5 style="color: #8b9aff; margin-bottom: 10px; font-size: 14px;">ðŸ“ Description / Topics</h5>
                            <p style="color: #b8b8d1; line-height: 1.6; white-space: pre-wrap;">${post.content}</p>
                        </div>
                    ` : ''}
                    
                    ${post.file_path ? `
                        <div class="post-file-attachment" style="margin: 15px 0;">
                            <a href="${getApiBaseUrl()}/posts/${post.id}/file" target="_blank" class="file-link" style="display: inline-flex; align-items: center; padding: 8px 15px; background: rgba(102, 126, 234, 0.2); border-radius: 6px; color: #8b9aff; text-decoration: none;">
                                ðŸ“Ž View ${post.file_type ? post.file_type.toUpperCase() : 'File'}
                            </a>
                        </div>
                    ` : ''}
                </div>
            `;
            }).join('')}
        `;
    } catch (error) {
        console.error('Error loading posts:', error);
        const postsDiv = document.getElementById('posts-list');
        postsDiv.innerHTML = '<p style="color: #ff6b6b;">Error loading posts. Please try again later.</p>';
    }
}

// Post Question Management (Company-wise Interview Preparation)
let postOptionCount = 2;

function openPostModal() {
    const modal = document.getElementById('post-modal');
    if (modal) {
        modal.classList.remove('hidden');
        // Reset form
        document.getElementById('post-form').reset();
        postOptionCount = 2;
        updatePostOptionsContainer();
        updatePostCorrectAnswerOptions();
        clearPostErrors();
    }
}

function closePostModal() {
    const modal = document.getElementById('post-modal');
    const form = document.getElementById('post-form');
    const fileDisplay = document.getElementById('file-name-display');
    
    if (modal) modal.classList.add('hidden');
    if (form) form.reset();
    
    postOptionCount = 2;
    updatePostOptionsContainer();
    updatePostCorrectAnswerOptions();
    clearPostErrors();
    
    if (fileDisplay) {
        fileDisplay.style.display = 'none';
        fileDisplay.textContent = '';
    }
}

function addPostOption() {
    if (postOptionCount >= 10) {
        alert('Maximum 10 options allowed');
        return;
    }
    postOptionCount++;
    updatePostOptionsContainer();
}

function removePostOption(btn) {
    const container = document.getElementById('post-options-container');
    const rows = container.querySelectorAll('.option-row');
    if (rows.length <= 2) {
        alert('Minimum 2 options required');
        return;
    }
    btn.closest('.option-row').remove();
    postOptionCount--;
    updatePostOptionLabels();
    updatePostCorrectAnswerOptions();
}

function updatePostOptionsContainer() {
    const container = document.getElementById('post-options-container');
    if (!container) return;
    
    let currentRowCount = container.querySelectorAll('.option-row').length;
    
    while (currentRowCount < postOptionCount) {
        const row = document.createElement('div');
        row.className = 'option-row';
        const letter = String.fromCharCode(65 + currentRowCount);
        row.innerHTML = `
            <input type="text" class="option-input" placeholder="Option ${letter}" data-option="${letter}">
            <button class="btn-remove-option" onclick="removePostOption(this)">âœ•</button>
        `;
        container.appendChild(row);
        currentRowCount++;
    }
    
    updatePostOptionLabels();
    updatePostCorrectAnswerOptions();
}

function updatePostOptionLabels() {
    const rows = document.querySelectorAll('#post-options-container .option-row');
    rows.forEach((row, idx) => {
        const letter = String.fromCharCode(65 + idx);
        const input = row.querySelector('.option-input');
        input.setAttribute('data-option', letter);
        input.placeholder = `Option ${letter}`;
        const removeBtn = row.querySelector('.btn-remove-option');
        removeBtn.style.display = rows.length > 2 ? 'block' : 'none';
    });
    updatePostCorrectAnswerOptions();
}

function updatePostCorrectAnswerOptions() {
    const select = document.getElementById('post-correct-answer');
    if (!select) return;
    
    const currentValue = select.value;
    select.innerHTML = '<option value="">Select correct answer</option>';
    
    const rows = document.querySelectorAll('#post-options-container .option-row');
    rows.forEach((row, idx) => {
        const letter = String.fromCharCode(65 + idx);
        const option = document.createElement('option');
        option.value = letter;
        option.textContent = letter;
        select.appendChild(option);
    });
    
    if (currentValue && Array.from(select.options).some(opt => opt.value === currentValue)) {
        select.value = currentValue;
    }
}

function clearPostErrors() {
    const errorIds = ['post-error-company', 'post-error-question', 'post-error-options', 'post-error-answer'];
    errorIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '';
    });
}

async function submitPostQuestion() {
    const companyName = document.getElementById('post-company').value.trim();
    const question = document.getElementById('post-question').value.trim();
    const correctAnswer = document.getElementById('post-correct-answer').value;
    const description = document.getElementById('post-description').value.trim();
    const fileInput = document.getElementById('post-file');
    
    // Get options
    const optionInputs = document.querySelectorAll('#post-options-container .option-input');
    const options = Array.from(optionInputs)
        .map(input => input.value.trim())
        .filter(val => val.length > 0);
    
    clearPostErrors();
    
    // Check file size if file is provided
    const file = fileInput.files[0];
    if (file && file.size > 16 * 1024 * 1024) {
        alert('File size exceeds 16MB limit');
        return;
    }
    
    // Validate that at least some content is provided
    if (!companyName && !question && options.length === 0 && !description && !file) {
        alert('Please fill at least one field');
        return;
    }
    
    try {
        const formData = new FormData();
        if (companyName) {
            formData.append('company_name', companyName);
        }
        if (question) {
            formData.append('question', question);
        }
        if (options.length > 0) {
            formData.append('options', JSON.stringify(options));
        }
        if (correctAnswer) {
            formData.append('correct_answer', correctAnswer);
        }
        if (description) {
            formData.append('description', description);
        }
        if (file) {
            formData.append('file', file);
        }
        
        await postsAPI.createPost(formData);
        alert('Post added successfully!');
        closePostModal();
        
        // Reload posts based on current view
        if (window.currentCompanyId) {
            // If viewing a company page, reload that company's posts
            openCompanyQuestions(window.currentCompanyId);
        } else {
            // Otherwise reload all posts
            loadPosts();
        }
    } catch (error) {
        console.error('Error creating post:', error);
        alert(`Error: ${error.message || 'Failed to create post'}`);
    }
}


// Handle file input change
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('post-file');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const fileDisplay = document.getElementById('file-name-display');
            if (e.target.files && e.target.files.length > 0) {
                const fileName = e.target.files[0].name;
                const fileSize = (e.target.files[0].size / (1024 * 1024)).toFixed(2);
                fileDisplay.textContent = `Selected: ${fileName} (${fileSize} MB)`;
                fileDisplay.style.display = 'block';
            } else {
                fileDisplay.style.display = 'none';
                fileDisplay.textContent = '';
            }
        });
    }
    
});

async function loadCompanyQuestions(companyId) {
    try {
        const data = await studentAPI.getQuestions({ company_id: companyId });
        const questionsDiv = document.getElementById('company-questions');
        
        questionsDiv.innerHTML = `
            <h3>Questions</h3>
            ${data.questions.map(q => `
                <div class="question-item" onclick="loadQuestion(${q.id})">
                    <h4>${q.title}</h4>
                    <p>${q.type} - ${q.difficulty}</p>
                </div>
            `).join('')}
        `;
    } catch (error) {
        console.error('Error loading company questions:', error);
    }
}

// Resources Page
async function loadResourcesPage() {
    try {
        const data = await resourcesAPI.getResources();
        const resourcesDiv = document.getElementById('resources-list');
        const canManageResources = currentUser && (currentUser.role === 'faculty' || currentUser.role === 'admin');

        if (!data.resources || data.resources.length === 0) {
            resourcesDiv.className = '';
            resourcesDiv.innerHTML = '<p style="text-align: center; color: rgba(242, 244, 255, 0.6); padding: 40px;">No resources uploaded yet.</p>';
            return;
        }

        resourcesDiv.className = 'resource-grid';
        resourcesDiv.innerHTML = data.resources.map(r => {
            const hasFile = r.file_path && r.file_path.trim() !== '' && r.file_path !== null && r.file_path !== 'None';
            const uploadDate = r.created_at ? new Date(r.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            }) : 'Demo Resource';

            return `
            <div class="resource-item resource-card">
                <div class="resource-content">
                    <div class="resource-header">
                        <h4>${r.title || 'Untitled'}</h4>
                        <span class="resource-type-badge">${r.type ? r.type.toUpperCase() : 'NOTES'}</span>
                    </div>
                    ${r.description ? `<p class="resource-description">${r.description}</p>` : ''}
                    <div class="resource-meta">
                        <small>Updated: ${uploadDate}</small>
                    </div>
                    ${hasFile ? `
                        <div class="resource-actions">
                            <button onclick="viewResource(${r.id})" class="btn btn-sm btn-primary">Open Notes</button>
                            <button onclick="downloadResource(${r.id})" class="btn btn-sm btn-secondary">Download</button>
                        </div>
                    ` : `<div class="resource-no-file">Notes content available in description</div>`}
                </div>
                ${canManageResources ? `<button onclick="deleteResource(${r.id})" class="btn btn-sm btn-delete">Delete</button>` : ''}
            </div>
        `;
        }).join('');
    } catch (error) {
        console.error('Error loading resources:', error);
        const resourcesDiv = document.getElementById('resources-list');
        resourcesDiv.innerHTML = '<p style="color: #e74c3c;">Error loading resources. Please try again.</p>';
    }
}
function openResourceUploadForm() {
    const form = document.getElementById('resource-upload-form');
    const addBtn = document.getElementById('add-resource-btn');
    if (form) {
        form.style.display = 'block';
        if (addBtn) addBtn.style.display = 'none';
    }
}

function closeResourceUploadForm() {
    const form = document.getElementById('resource-upload-form');
    const addBtn = document.getElementById('add-resource-btn');
    if (form) {
        form.style.display = 'none';
        // Clear form fields
        document.getElementById('resource-title').value = '';
        document.getElementById('resource-description').value = '';
        document.getElementById('resource-type').value = 'pdf';
        document.getElementById('resource-file').value = '';
    }
    if (addBtn) addBtn.style.display = 'inline-block';
}

async function uploadResource() {
    const title = document.getElementById('resource-title').value.trim();
    const description = document.getElementById('resource-description').value.trim();
    const type = document.getElementById('resource-type').value;
    const file = document.getElementById('resource-file').files[0];
    
    if (!title) {
        alert('Please enter a title');
        return;
    }
    
    if (!file && type === 'pdf') {
        alert('Please select a file to upload');
        return;
    }
    
    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description);
    formData.append('type', type);
    if (file) formData.append('file', file);
    
    try {
        await resourcesAPI.uploadResource(formData);
        alert('Resource uploaded successfully!');
        
        // Clear form and close it
        document.getElementById('resource-title').value = '';
        document.getElementById('resource-description').value = '';
        document.getElementById('resource-type').value = 'pdf';
        document.getElementById('resource-file').value = '';
        
        // Close upload form
        closeResourceUploadForm();
        
        // Reload resources list
        await loadResourcesPage();
    } catch (error) {
        alert(`Error: ${error.message || 'Failed to upload resource'}`);
    }
}

async function viewResource(resourceId) {
    // Open PDF in new tab with authentication
    const url = `${API_BASE_URL}/resources/${resourceId}/download`;
    const token = localStorage.getItem('authToken');
    
    // Create a temporary link with Authorization header
    // Since we can't set headers on direct links, we'll fetch and open as blob
    try {
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load PDF');
        }
        
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        window.open(blobUrl, '_blank');
    } catch (error) {
        alert(`Error: ${error.message || 'Failed to view PDF'}`);
    }
}

async function downloadResource(resourceId) {
    // Download PDF with authentication
    const url = `${API_BASE_URL}/resources/${resourceId}/download`;
    const token = localStorage.getItem('authToken');
    
    try {
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to download PDF');
        }
        
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = `resource_${resourceId}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
    } catch (error) {
        alert(`Error: ${error.message || 'Failed to download PDF'}`);
    }
}

async function deleteResource(resourceId) {
    if (!confirm('Are you sure you want to delete this resource?')) return;
    
    try {
        await resourcesAPI.deleteResource(resourceId);
        loadResourcesPage();
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Leaderboard
async function loadLeaderboard() {
    try {
        const data = await leaderboardAPI.getTopUsers(100);
        const tableDiv = document.getElementById('leaderboard-table');
        
        if (!data.leaderboard || data.leaderboard.length === 0) {
            tableDiv.innerHTML = `
                <div style="text-align: center; padding: 40px; color: rgba(242, 244, 255, 0.6);">
                    <p style="font-size: 16px; margin-bottom: 10px;">No students on leaderboard yet</p>
                    <p style="font-size: 14px;">Start practicing to appear on the leaderboard!</p>
                </div>
            `;
            return;
        }
        
        tableDiv.innerHTML = `
            <div class="leaderboard-row header">
                <div>Rank</div>
                <div>Full Name</div>
                <div>Registration Number</div>
                <div>Email</div>
                <div>Overall Score</div>
            </div>
            ${data.leaderboard.map(entry => `
                <div class="leaderboard-row">
                    <div class="rank-cell" data-label="Rank">${entry.rank || '-'}</div>
                    <div class="name-cell" data-label="Full Name">${entry.full_name || entry.username || 'N/A'}</div>
                    <div class="regno-cell" data-label="Reg No">${entry.reg_no || 'N/A'}</div>
                    <div class="email-cell" data-label="Email">${entry.college_email || entry.email || 'N/A'}</div>
                    <div class="score-cell" data-label="Score">${entry.total_score ? Math.min(100, entry.total_score).toFixed(1) : '0.0'}</div>
                </div>
            `).join('')}
        `;
    } catch (error) {
        console.error('Error loading leaderboard:', error);
        const tableDiv = document.getElementById('leaderboard-table');
        tableDiv.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #e74c3c;">
                <p>Error loading leaderboard. Please try again later.</p>
            </div>
        `;
    }
}

// ================= Users Management (Admin Only) =================

async function loadUsers() {
    // Only allow admin to load users
    if (!currentUser || currentUser.role !== 'admin') {
        console.warn('Access denied. Only administrators can view users.');
        return;
    }
    
    const loadingDiv = document.getElementById('users-loading');
    const errorDiv = document.getElementById('users-error');
    const tableBody = document.getElementById('users-table-body');
    const emptyDiv = document.getElementById('users-empty');
    
    // Show loading, hide error and empty
    if (loadingDiv) loadingDiv.style.display = 'block';
    if (errorDiv) errorDiv.style.display = 'none';
    if (emptyDiv) emptyDiv.style.display = 'none';
    
    try {
        // Get filter values
        const roleFilter = document.getElementById('filter-role')?.value || '';
        const statusFilter = document.getElementById('filter-status')?.value || '';
        
        // Call API with filters
        const data = await adminAPI.getUsers(
            roleFilter || null,
            statusFilter !== '' ? statusFilter : null
        );
        
        // Hide loading
        if (loadingDiv) loadingDiv.style.display = 'none';
        
        if (!data.users || data.users.length === 0) {
            if (tableBody) tableBody.innerHTML = '';
            if (emptyDiv) emptyDiv.style.display = 'block';
            return;
        }
        
        // Render users table
        if (tableBody) {
            tableBody.innerHTML = data.users.map((user, index) => {
                const rowNumber = index + 1; // Sequential row number starting from 1
                const createdDate = user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A';
                const statusBadge = user.is_active 
                    ? '<span style="color: #28a745; font-weight: bold;">Active</span>'
                    : '<span style="color: #dc3545; font-weight: bold;">Inactive</span>';
                
                // Editable role dropdown
                const roleDropdown = `
                    <select id="role-select-${user.id}" onchange="updateUserRole(${user.id}, this.value)" 
                            style="padding: 4px 8px; border-radius: 4px; border: 1px solid #ddd; 
                                   background: ${user.role === 'admin' ? '#dc3545' : user.role === 'faculty' ? '#007bff' : '#28a745'}; 
                                   color: white; font-size: 12px; font-weight: bold; cursor: pointer; min-width: 90px;">
                        <option value="student" ${user.role === 'student' ? 'selected' : ''} style="background: white; color: #333;">Student</option>
                        <option value="faculty" ${user.role === 'faculty' ? 'selected' : ''} style="background: white; color: #333;">Faculty</option>
                        <option value="admin" ${user.role === 'admin' ? 'selected' : ''} style="background: white; color: #333;">Admin</option>
                    </select>
                `;
                
                // Batch dropdown (only for students)
                const batchDropdown = user.role === 'student' ? `
                    <select id="batch-select-${user.id}" onchange="updateUserBatch(${user.id}, this.value)" 
                            style="padding: 4px 8px; border-radius: 4px; border: 1px solid #ddd; 
                                   background: #6c5ce7; color: white; font-size: 12px; font-weight: bold; cursor: pointer; min-width: 100px;">
                        <option value="" ${!user.batch_id ? 'selected' : ''} style="background: white; color: #333;">Select Batch</option>
                        <option value="1" ${user.batch_id == 1 ? 'selected' : ''} style="background: white; color: #333;">2021</option>
                        <option value="2" ${user.batch_id == 2 ? 'selected' : ''} style="background: white; color: #333;">2022</option>
                        <option value="3" ${user.batch_id == 3 ? 'selected' : ''} style="background: white; color: #333;">2023</option>
                        <option value="4" ${user.batch_id == 4 ? 'selected' : ''} style="background: white; color: #333;">2024</option>
                    </select>
                ` : '<span style="color: #999;">N/A</span>';
                
                // Don't allow deleting yourself
                const canDelete = user.id !== currentUser.id;
                const deleteButton = canDelete 
                    ? `<button onclick="confirmDeleteUser(${user.id}, '${user.username}')" class="btn btn-danger" style="padding: 6px 12px; font-size: 12px; margin-left: 5px;">Delete</button>`
                    : '<span style="color: #999; font-size: 12px;">Current User</span>';
                
                return `
                    <tr id="user-row-${user.id}" style="border-bottom: 1px solid #e0e0e0; background: #ffffff;">
                        <td style="padding: 12px; color: #000000;">${rowNumber}</td>
                        <td style="padding: 12px; color: #000000; font-weight: 500;">${user.username || 'N/A'}</td>
                        <td style="padding: 12px; color: #000000;">${user.full_name || (user.first_name && user.last_name ? `${user.first_name} ${user.last_name}` : 'N/A')}</td>
                        <td style="padding: 12px; color: #000000;">${user.first_name || 'N/A'}</td>
                        <td style="padding: 12px; color: #000000;">${user.last_name || 'N/A'}</td>
                        <td style="padding: 12px; color: #000000;">${user.reg_no || 'N/A'}</td>
                        <td style="padding: 12px; color: #000000;">${user.college_email || user.email || 'N/A'}</td>
                        <td style="padding: 12px;">${roleDropdown}</td>
                        <td style="padding: 12px;">${batchDropdown}</td>
                        <td style="padding: 12px;">${statusBadge}</td>
                        <td style="padding: 12px; color: #000000;">${createdDate}</td>
                        <td style="padding: 12px; text-align: center;">
                            <button onclick="editUser(${user.id})" class="btn btn-primary" style="padding: 6px 12px; font-size: 12px;">Edit</button>
                            ${deleteButton}
                        </td>
                    </tr>
                `;
            }).join('');
        }
        
        if (emptyDiv) emptyDiv.style.display = 'none';
        
    } catch (error) {
        console.error('Error loading users:', error);
        if (loadingDiv) loadingDiv.style.display = 'none';
        if (errorDiv) {
            errorDiv.textContent = `Error loading users: ${error.message || 'Unknown error'}`;
            errorDiv.style.display = 'block';
        }
        if (tableBody) tableBody.innerHTML = '';
        if (emptyDiv) emptyDiv.style.display = 'block';
    }
}

function confirmDeleteUser(userId, username) {
    if (!currentUser || currentUser.role !== 'admin') {
        alert('Access denied. Only administrators can delete users.');
        return;
    }
    
    // Double confirmation
    const confirmMessage = `Are you sure you want to delete user "${username}"?\n\nThis action cannot be undone and will delete all associated data.\n\nType "DELETE" to confirm:`;
    const userInput = prompt(confirmMessage);
    
    if (userInput !== 'DELETE') {
        return; // User cancelled or didn't type DELETE
    }
    
    // Final confirmation
    if (!confirm(`Final confirmation: Delete user "${username}" (ID: ${userId})?`)) {
        return;
    }
    
    deleteUser(userId);
}

async function deleteUser(userId) {
    if (!currentUser || currentUser.role !== 'admin') {
        alert('Access denied. Only administrators can delete users.');
        return;
    }
    
    try {
        await adminAPI.deleteUser(userId);
        alert('User deleted successfully!');
        // Reload users list
        await loadUsers();
    } catch (error) {
        console.error('Error deleting user:', error);
        alert(`Error deleting user: ${error.message || 'Unknown error'}`);
    }
}

async function updateUserRole(userId, newRole) {
    if (!currentUser || currentUser.role !== 'admin') {
        alert('Access denied. Only administrators can update user roles.');
        // Reload to reset dropdown
        await loadUsers();
        return;
    }
    
    // Don't allow changing your own role
    if (userId === currentUser.id) {
        alert('You cannot change your own role.');
        // Reload to reset dropdown
        await loadUsers();
        return;
    }
    
    // Confirm role change
    if (!confirm(`Are you sure you want to change this user's role to ${newRole.toUpperCase()}?`)) {
        // Reload to reset dropdown
        await loadUsers();
        return;
    }
    
    try {
        const selectElement = document.getElementById(`role-select-${userId}`);
        if (selectElement) {
            selectElement.disabled = true;
            selectElement.style.opacity = '0.6';
        }
        
        await adminAPI.updateUser(userId, { role: newRole });
        
        // Show success message
        const row = document.getElementById(`user-row-${userId}`);
        if (row) {
            const tempMsg = document.createElement('div');
            tempMsg.textContent = 'Role updated!';
            tempMsg.style.cssText = 'position: absolute; background: #28a745; color: white; padding: 5px 10px; border-radius: 4px; z-index: 1000;';
            row.style.position = 'relative';
            row.appendChild(tempMsg);
            setTimeout(() => {
                tempMsg.remove();
            }, 2000);
        }
        
        // Update dropdown background color based on new role
        if (selectElement) {
            const bgColor = newRole === 'admin' ? '#dc3545' : newRole === 'faculty' ? '#007bff' : '#28a745';
            selectElement.style.background = bgColor;
            selectElement.disabled = false;
            selectElement.style.opacity = '1';
        }
        
        // Optionally reload the entire list to ensure consistency
        // await loadUsers();
        
    } catch (error) {
        console.error('Error updating user role:', error);
        alert(`Error updating user role: ${error.message || 'Unknown error'}`);
        // Reload to reset dropdown on error
        await loadUsers();
    }
}

function editUser(userId) {
    // Open a modal or form to edit user details
    // For now, we'll show a prompt for editing role and status
    if (!currentUser || currentUser.role !== 'admin') {
        alert('Access denied. Only administrators can edit users.');
        return;
    }
    
    // Get current user data from the table
    const roleSelect = document.getElementById(`role-select-${userId}`);
    const currentRole = roleSelect ? roleSelect.value : null;
    
    // Get current status and batch from the row
    const row = document.getElementById(`user-row-${userId}`);
    const statusCells = row ? row.querySelectorAll('td') : [];
    const statusCell = statusCells[9]; // Status is now in the 10th column (0-indexed: 9)
    const currentStatus = statusCell && statusCell.textContent.trim() === 'Active';
    
    // Get current batch from batch dropdown if exists
    const batchSelect = document.getElementById(`batch-select-${userId}`);
    const currentBatchId = batchSelect ? batchSelect.value : null;
    
    // Create a simple edit modal
    const editModal = document.createElement('div');
    editModal.id = 'edit-user-modal';
    editModal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
    `;
    
    editModal.innerHTML = `
        <div style="background: #1a1a2e; padding: 30px; border-radius: 8px; max-width: 400px; width: 90%; border: 1px solid #444;">
            <h3 style="margin-top: 0; color: white;">Edit User</h3>
            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold; color: white;">Role:</label>
                <select id="edit-role-select" onchange="handleEditRoleChange()" style="width: 100%; padding: 8px; border: 1px solid #555; border-radius: 4px; background: #2a2a3e; color: white;">
                    <option value="student" ${currentRole === 'student' ? 'selected' : ''} style="background: #2a2a3e; color: white;">Student</option>
                    <option value="faculty" ${currentRole === 'faculty' ? 'selected' : ''} style="background: #2a2a3e; color: white;">Faculty</option>
                    <option value="admin" ${currentRole === 'admin' ? 'selected' : ''} style="background: #2a2a3e; color: white;">Admin</option>
                </select>
            </div>
            <div style="margin-bottom: 15px;" id="edit-batch-container" style="display: ${currentRole === 'student' ? 'block' : 'none'};">
                <label style="display: block; margin-bottom: 5px; font-weight: bold; color: white;">Batch:</label>
                <select id="edit-batch-select" style="width: 100%; padding: 8px; border: 1px solid #555; border-radius: 4px; background: #2a2a3e; color: white;">
                    <option value="" ${!currentBatchId ? 'selected' : ''} style="background: #2a2a3e; color: white;">Select Batch</option>
                    <option value="1" ${currentBatchId == 1 ? 'selected' : ''} style="background: #2a2a3e; color: white;">2021</option>
                    <option value="2" ${currentBatchId == 2 ? 'selected' : ''} style="background: #2a2a3e; color: white;">2022</option>
                    <option value="3" ${currentBatchId == 3 ? 'selected' : ''} style="background: #2a2a3e; color: white;">2023</option>
                    <option value="4" ${currentBatchId == 4 ? 'selected' : ''} style="background: #2a2a3e; color: white;">2024</option>
                </select>
            </div>
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold; color: white;">Status:</label>
                <select id="edit-status-select" style="width: 100%; padding: 8px; border: 1px solid #555; border-radius: 4px; background: #2a2a3e; color: white;">
                    <option value="true" ${currentStatus ? 'selected' : ''} style="background: #2a2a3e; color: white;">Active</option>
                    <option value="false" ${!currentStatus ? 'selected' : ''} style="background: #2a2a3e; color: white;">Inactive</option>
                </select>
            </div>
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button onclick="closeEditUserModal()" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">Cancel</button>
                <button onclick="saveUserChanges(${userId})" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">Save Changes</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(editModal);
}

function handleEditRoleChange() {
    const roleSelect = document.getElementById('edit-role-select');
    const batchContainer = document.getElementById('edit-batch-container');
    if (roleSelect && batchContainer) {
        if (roleSelect.value === 'student') {
            batchContainer.style.display = 'block';
        } else {
            batchContainer.style.display = 'none';
            const batchSelect = document.getElementById('edit-batch-select');
            if (batchSelect) batchSelect.value = '';
        }
    }
}

function closeEditUserModal() {
    const modal = document.getElementById('edit-user-modal');
    if (modal) {
        modal.remove();
    }
}

async function saveUserChanges(userId) {
    if (!currentUser || currentUser.role !== 'admin') {
        alert('Access denied. Only administrators can update users.');
        closeEditUserModal();
        return;
    }
    
    // Don't allow changing your own role
    if (userId === currentUser.id) {
        alert('You cannot change your own role or status.');
        closeEditUserModal();
        return;
    }
    
    const roleSelect = document.getElementById('edit-role-select');
    const statusSelect = document.getElementById('edit-status-select');
    const batchSelect = document.getElementById('edit-batch-select');
    
    if (!roleSelect || !statusSelect) {
        alert('Error: Could not find form fields.');
        closeEditUserModal();
        return;
    }
    
    const newRole = roleSelect.value;
    const newStatus = statusSelect.value === 'true';
    const newBatchId = batchSelect ? (batchSelect.value ? parseInt(batchSelect.value) : null) : null;
    
    // Prepare update data
    const updateData = {
        role: newRole,
        is_active: newStatus
    };
    
    // Only include batch_id if role is student
    if (newRole === 'student' && newBatchId) {
        updateData.batch_id = newBatchId;
    } else if (newRole !== 'student') {
        updateData.batch_id = null;
    }
    
    try {
        await adminAPI.updateUser(userId, updateData);
        
        alert('User updated successfully!');
        closeEditUserModal();
        // Reload users list
        await loadUsers();
        
    } catch (error) {
        console.error('Error updating user:', error);
        alert(`Error updating user: ${error.message || 'Unknown error'}`);
    }
}

async function updateUserBatch(userId, batchId) {
    if (!currentUser || currentUser.role !== 'admin') {
        alert('Access denied. Only administrators can update user batches.');
        await loadUsers();
        return;
    }
    
    // Don't allow changing your own batch if you're a student (though admins typically aren't students)
    if (userId === currentUser.id) {
        alert('You cannot change your own batch.');
        await loadUsers();
        return;
    }
    
    // Confirm batch change
    const batchNames = { '1': '2021', '2': '2022', '3': '2023', '4': '2024' };
    const batchName = batchNames[batchId] || 'No Batch';
    if (!confirm(`Are you sure you want to change this user's batch to ${batchName}?`)) {
        await loadUsers();
        return;
    }
    
    try {
        await adminAPI.updateUser(userId, { 
            batch_id: batchId ? parseInt(batchId) : null
        });
        
        alert('User batch updated successfully!');
        await loadUsers();
    } catch (error) {
        console.error('Error updating user batch:', error);
        alert(`Error updating user batch: ${error.message || 'Unknown error'}`);
        await loadUsers();
    }
}

// Make edit functions globally accessible
window.updateUserRole = updateUserRole;
window.updateUserBatch = updateUserBatch;
window.editUser = editUser;
window.closeEditUserModal = closeEditUserModal;
window.saveUserChanges = saveUserChanges;
window.handleEditRoleChange = handleEditRoleChange;

// Chatbot
function loadChatbotPage() {
    const interviewSetup = document.getElementById('interview-setup');
    const interviewChat = document.getElementById('interview-chat');
    const resumeFileName = document.getElementById('resume-file-name');
    const jobFileName = document.getElementById('job-file-name');
    
    if (interviewSetup) {
        interviewSetup.style.display = 'block';
    }
    if (interviewChat) {
        interviewChat.style.display = 'none';
    }
    currentSessionId = null;
    
    // Stop any ongoing recording and camera
    stopVoiceRecording();
    if (interviewStream) {
        interviewStream.getTracks().forEach(track => track.stop());
        interviewStream = null;
    }
    const videoElement = document.getElementById('interview-video');
    if (videoElement) {
        videoElement.srcObject = null;
    }
    
    // Clear file names
    if (resumeFileName) {
        resumeFileName.textContent = '';
    }
    if (jobFileName) {
        jobFileName.textContent = '';
    }
    
    // Reset transcript
    currentTranscript = '';
    const transcriptDiv = document.getElementById('voice-transcript');
    if (transcriptDiv) transcriptDiv.innerHTML = '';
}

async function handleResumeUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const fileNameDiv = document.getElementById('resume-file-name');
    const resumeTextarea = document.getElementById('resume-text');
    
    // Show loading
    fileNameDiv.textContent = `Uploading ${file.name}...`;
    fileNameDiv.style.color = '#66e3c4';
    
    try {
        const result = await chatbotAPI.extractText(file);
        resumeTextarea.value = result.text;
        fileNameDiv.textContent = `âœ“ ${file.name} - Text extracted successfully`;
        fileNameDiv.style.color = '#33d17a';
    } catch (error) {
        fileNameDiv.textContent = `âœ— Error: ${error.message}`;
        fileNameDiv.style.color = '#ff6b6b';
        alert(`Error extracting text from file: ${error.message}`);
    }
}

async function handleJobUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const fileNameDiv = document.getElementById('job-file-name');
    const jobTextarea = document.getElementById('job-description');
    
    // Show loading
    fileNameDiv.textContent = `Uploading ${file.name}...`;
    fileNameDiv.style.color = '#66e3c4';
    
    try {
        const result = await chatbotAPI.extractText(file);
        jobTextarea.value = result.text;
        fileNameDiv.textContent = `âœ“ ${file.name} - Text extracted successfully`;
        fileNameDiv.style.color = '#33d17a';
    } catch (error) {
        fileNameDiv.textContent = `âœ— Error: ${error.message}`;
        fileNameDiv.style.color = '#ff6b6b';
        alert(`Error extracting text from file: ${error.message}`);
    }
}

async function startInterview() {
    const resumeTextEl = document.getElementById('resume-text');
    const jobDescriptionEl = document.getElementById('job-description');
    
    if (!resumeTextEl || !jobDescriptionEl) {
        alert('Interview form elements not found');
        return;
    }
    
    const resumeText = resumeTextEl.value;
    const jobDescription = jobDescriptionEl.value;
    
    if (!resumeText || !jobDescription) {
        alert('Please provide both resume and job description');
        return;
    }
    
    try {
        // Show loading state
        const interviewSetup = document.getElementById('interview-setup');
        const interviewChat = document.getElementById('interview-chat');
        if (interviewSetup) {
            interviewSetup.style.display = 'none';
        }
        if (interviewChat) {
            interviewChat.style.display = 'block';
            // Show loading message
            const chatDiv = document.getElementById('chat-messages');
            if (chatDiv) {
                chatDiv.innerHTML = '<div class="chat-message question">Requesting camera and microphone access...</div>';
            }
        }
        
        // Request camera and microphone access
        await requestCameraAndMicrophone();
        
        // Start interview session
        const data = await chatbotAPI.startInterview(resumeText, jobDescription, 'technical', 'fresher', 5);
        currentSessionId = data.session_id;
        
        // Display first question with phase indicator
        const chatDiv = document.getElementById('chat-messages');
        if (chatDiv) {
            const phaseLabel = getPhaseLabel(data.phase || 'introduction');
            chatDiv.innerHTML = `
                <div class="interview-progress">
                    <div class="progress-info">
                        <span class="phase-badge phase-${data.phase || 'introduction'}">${phaseLabel}</span>
                    </div>
                </div>
                <div class="chat-message question">
                    <strong>Interviewer:</strong> ${data.question}
                </div>
            `;
        }
        
        // Initialize speech recognition
        initializeSpeechRecognition();
    } catch (error) {
        alert(`Error: ${error.message}`);
        
        // Show error in chat
        const chatDiv = document.getElementById('chat-messages');
        if (chatDiv) {
            chatDiv.innerHTML = `
                <div class="chat-message feedback">
                    <strong>Error:</strong> ${error.message}
                </div>
            `;
        }
        
        // Stop stream if there was an error
        if (interviewStream) {
            interviewStream.getTracks().forEach(track => track.stop());
            interviewStream = null;
        }
        
        // Show setup again on error
        const interviewSetup = document.getElementById('interview-setup');
        const interviewChat = document.getElementById('interview-chat');
        if (interviewSetup) interviewSetup.style.display = 'block';
        if (interviewChat) interviewChat.style.display = 'none';
    }
}

async function requestCameraAndMicrophone() {
    try {
        // Check if mediaDevices is available
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Camera and microphone access is not supported in this browser. Please use a modern browser like Chrome, Firefox, or Edge.');
        }
        
        // Request both video (front camera) and audio with proper echo cancellation
        interviewStream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'user', // Front camera
                width: { ideal: 1280 },
                height: { ideal: 720 }
            },
            audio: {
                echoCancellation: true,      // CRITICAL: Prevents echo feedback
                noiseSuppression: true,       // Reduces background noise
                autoGainControl: true,        // Normalizes audio levels
                sampleRate: 48000,           // High quality audio
                channelCount: 1              // Mono audio (sufficient for voice)
            }
        });
        
        const videoElement = document.getElementById('interview-video');
        if (videoElement) {
            // CRITICAL FIX: Create a video-only stream to prevent audio playback
            // This prevents the microphone audio from being played through speakers
            const videoTracks = interviewStream.getVideoTracks();
            const videoOnlyStream = new MediaStream(videoTracks);
            
            // Attach only video tracks to video element (no audio)
            videoElement.srcObject = videoOnlyStream;
            videoElement.muted = true;  // CRITICAL: Mute to prevent any audio playback
            videoElement.setAttribute('muted', 'true');  // HTML5 muted attribute
            videoElement.playsInline = true;
            
            // Wait for video to be ready
            await new Promise((resolve, reject) => {
                videoElement.onloadedmetadata = () => {
                    videoElement.play()
                        .then(() => {
                            console.log('Video started successfully');
                            resolve();
                        })
                        .catch(reject);
                };
                videoElement.onerror = reject;
                
                // Timeout after 5 seconds
                setTimeout(() => reject(new Error('Video loading timeout')), 5000);
            });
        } else {
            throw new Error('Video element not found');
        }
    } catch (error) {
        // Clean up on error
        if (interviewStream) {
            interviewStream.getTracks().forEach(track => track.stop());
            interviewStream = null;
        }
        throw new Error(`Failed to access camera/microphone: ${error.message}. Please allow camera and microphone access.`);
    }
}

function initializeSpeechRecognition() {
    // Check if browser supports Web Speech API
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.warn('Speech recognition not supported in this browser');
        // Fallback: show text input
        const voiceInputContainer = document.querySelector('.voice-input-container');
        if (voiceInputContainer) {
            voiceInputContainer.innerHTML = `
                <textarea id="chat-answer" placeholder="Type your answer... (Speech recognition not available)"></textarea>
            `;
        }
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    
    recognition.onstart = () => {
        isRecording = true;
        const indicator = document.getElementById('recording-indicator');
        if (indicator) indicator.style.display = 'flex';
    };
    
    recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript + ' ';
            } else {
                interimTranscript += transcript;
            }
        }
        
        currentTranscript = finalTranscript + interimTranscript;
        const transcriptDiv = document.getElementById('voice-transcript');
        if (transcriptDiv) {
            transcriptDiv.innerHTML = `
                <div class="transcript-text">${finalTranscript}<span class="interim">${interimTranscript}</span></div>
            `;
        }
        
        // Show submit button when there's text
        const submitBtn = document.getElementById('submit-answer-btn');
        if (submitBtn && currentTranscript.trim()) {
            submitBtn.style.display = 'block';
        }
    };
    
    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        if (event.error === 'no-speech') {
            // User stopped speaking, keep recording
            return;
        }
        stopVoiceRecording();
        alert(`Speech recognition error: ${event.error}`);
    };
    
    recognition.onend = () => {
        if (isRecording) {
            // Restart recognition if still recording
            try {
                recognition.start();
            } catch (e) {
                console.error('Failed to restart recognition:', e);
            }
        }
    };
}

function startVoiceRecording() {
    if (!recognition) {
        alert('Speech recognition not initialized. Please refresh and try again.');
        return;
    }
    
    try {
        recognition.start();
        const startBtn = document.getElementById('start-recording-btn');
        const stopBtn = document.getElementById('stop-recording-btn');
        if (startBtn) startBtn.style.display = 'none';
        if (stopBtn) stopBtn.style.display = 'block';
    } catch (error) {
        console.error('Error starting recognition:', error);
        alert('Failed to start recording. Please try again.');
    }
}

function stopVoiceRecording() {
    isRecording = false;
    if (recognition) {
        recognition.stop();
    }
    
    const startBtn = document.getElementById('start-recording-btn');
    const stopBtn = document.getElementById('stop-recording-btn');
    const indicator = document.getElementById('recording-indicator');
    
    if (startBtn) startBtn.style.display = 'block';
    if (stopBtn) stopBtn.style.display = 'none';
    if (indicator) indicator.style.display = 'none';
}

function getPhaseLabel(phase) {
    const phaseLabels = {
        'introduction': 'Introduction',
        'resume': 'Resume-Based',
        'jd': 'Job Description',
        'general': 'General'
    };
    return phaseLabels[phase] || 'General';
}

async function submitAnswer() {
    if (!currentSessionId) return;
    
    // Stop recording before submitting
    stopVoiceRecording();
    
    // Get answer from transcript or textarea
    let answer = currentTranscript.trim();
    const chatAnswerEl = document.getElementById('chat-answer');
    if (!answer && chatAnswerEl) {
        answer = chatAnswerEl.value.trim();
    }
    
    if (!answer) {
        alert('Please provide an answer');
        return;
    }
    
    try {
        const data = await chatbotAPI.submitAnswer(currentSessionId, answer);
        const chatDiv = document.getElementById('chat-messages');
        
        if (chatDiv) {
            // Check if interview is completed
            if (data.interview_completed) {
                chatDiv.innerHTML += `
                    <div class="chat-message answer">
                        <strong>You:</strong> ${answer}
                    </div>
                    <div class="chat-message feedback">
                        <strong>Feedback:</strong> ${data.feedback}
                        ${data.scores ? `
                            <div class="score-display">
                                <div class="score-item">
                                    <span>Correctness:</span>
                                    <span class="score-value">${data.scores.correctness}/10</span>
                                </div>
                                <div class="score-item">
                                    <span>Clarity:</span>
                                    <span class="score-value">${data.scores.clarity}/10</span>
                                </div>
                                <div class="score-item">
                                    <span>Confidence:</span>
                                    <span class="score-value">${data.scores.confidence}/10</span>
                                </div>
                                <div class="score-item overall">
                                    <span>Overall Score:</span>
                                    <span class="score-value">${data.scores.overall}/10</span>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                    <div class="interview-complete">
                        <div class="interview-complete-header">
                            <h2>ðŸŽ‰ Interview Completed!</h2>
                            <p style="color: rgba(242, 244, 255, 0.8); margin-top: 10px;">Great job completing the interview. Here's your performance summary:</p>
                        </div>
                        
                        <div class="interview-performance-cards">
                            <div class="performance-card-main">
                                <div class="performance-card-icon">ðŸ“Š</div>
                                <div class="performance-card-content">
                                    <p class="performance-card-label">Average Score</p>
                                    <h3 class="performance-card-value">${data.average_score || 0}/10</h3>
                                    <div class="performance-bar">
                                        <div class="performance-bar-fill" style="width: ${((data.average_score || 0) / 10) * 100}%"></div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="performance-card-secondary">
                                <div class="performance-card-content">
                                    <p class="performance-card-label">Total Questions</p>
                                    <h3 class="performance-card-value">${data.total_questions || 0}</h3>
                                </div>
                            </div>
                        </div>
                        
                        <div class="interview-summary">
                            <h4>ðŸ“ Performance Summary</h4>
                            <div class="summary-content">
                                <p>${data.summary || 'Interview completed successfully. Review your answers and continue practicing to improve your interview skills.'}</p>
                            </div>
                        </div>
                        
                        <div class="interview-actions">
                            <button onclick="location.reload()" class="btn btn-primary">Start New Interview</button>
                        </div>
                    </div>
                `;
            } else {
                // Continue interview
                const phaseLabel = getPhaseLabel(data.phase || 'general');
                chatDiv.innerHTML += `
                    <div class="chat-message answer">
                        <strong>You:</strong> ${answer}
                    </div>
                    <div class="chat-message feedback">
                        <strong>Feedback:</strong> ${data.feedback}
                        ${data.scores ? `
                            <div class="score-display">
                                <div class="score-item">
                                    <span>Correctness:</span>
                                    <span class="score-value">${data.scores.correctness}/10</span>
                                </div>
                                <div class="score-item">
                                    <span>Clarity:</span>
                                    <span class="score-value">${data.scores.clarity}/10</span>
                                </div>
                                <div class="score-item">
                                    <span>Confidence:</span>
                                    <span class="score-value">${data.scores.confidence}/10</span>
                                </div>
                                <div class="score-item overall">
                                    <span>Overall:</span>
                                    <span class="score-value">${data.scores.overall}/10</span>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                    <div class="interview-progress">
                        <div class="progress-info">
                            <span class="phase-badge phase-${data.phase || 'general'}">${phaseLabel}</span>
                        </div>
                    </div>
                    <div class="chat-message question">
                        <strong>Interviewer:</strong> ${data.next_question}
                    </div>
                `;
            }
            chatDiv.scrollTop = chatDiv.scrollHeight;
        }
        
        // Clear transcript and hide submit button
        currentTranscript = '';
        const transcriptDiv = document.getElementById('voice-transcript');
        if (transcriptDiv) transcriptDiv.innerHTML = '';
        const submitBtn = document.getElementById('submit-answer-btn');
        if (submitBtn) submitBtn.style.display = 'none';
        
        if (chatAnswerEl) chatAnswerEl.value = '';
        
        // Restart recording for next question
        setTimeout(() => {
            startVoiceRecording();
        }, 1000);
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Notifications
let notificationDropdownOpen = false;

// Load notification badge count
async function loadNotificationBadge() {
    try {
        // Check if user is logged in
        if (!authToken || !currentUser) {
            return;
        }
        
        const data = await notificationsAPI.getUnreadCount();
        const badge = document.getElementById('notification-badge');
        if (!badge) return;
        
        const count = data.count || 0;
        
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    } catch (error) {
        // Silently fail - don't show errors if notifications can't be loaded
        console.error('Error loading notification badge:', error);
        const badge = document.getElementById('notification-badge');
        if (badge) {
            badge.style.display = 'none';
        }
    }
}

// Load notifications into dropdown
async function loadNotifications(forceReload = false) {
    try {
        // Check if dropdown is open - if not, don't load
        if (!notificationDropdownOpen && !forceReload) {
            console.log('[Notification] Dropdown is closed, skipping load');
            return;
        }
        
        // Check if user is logged in
        if (!authToken || !currentUser) {
            const notificationList = document.getElementById('notification-list');
            if (notificationList) {
                notificationList.innerHTML = '<div class="notification-empty">Please log in to view notifications</div>';
            }
            return;
        }
        
        console.log('[Notification] Fetching notifications from API...');
        const data = await notificationsAPI.getNotifications();
        console.log('[Notification] API Response:', JSON.stringify(data, null, 2));
        
        const notificationList = document.getElementById('notification-list');
        if (!notificationList) {
            console.error('[Notification] Notification list element not found');
            return;
        }
        
        // Log the list element to verify it exists
        console.log('[Notification] Notification list element:', notificationList);
        console.log('[Notification] List element styles:', {
            display: window.getComputedStyle(notificationList).display,
            visibility: window.getComputedStyle(notificationList).visibility,
            height: window.getComputedStyle(notificationList).height,
            maxHeight: window.getComputedStyle(notificationList).maxHeight,
            overflow: window.getComputedStyle(notificationList).overflow
        });
        
        // Check if data structure is correct
        if (!data) {
            console.error('[Notification] No data received from API');
            notificationList.innerHTML = '<div class="notification-empty">Error: No data received</div>';
            return;
        }
        
        // Handle both possible response formats
        const notifications = data.notifications || data || [];
        console.log('[Notification] Notifications array:', notifications);
        console.log('[Notification] Notifications count:', notifications.length);
        
        if (!Array.isArray(notifications) || notifications.length === 0) {
            console.log('[Notification] No notifications found - showing empty state');
            notificationList.innerHTML = '<div class="notification-empty">No new notifications</div>';
            // Ensure empty state is visible
            const emptyDiv = notificationList.querySelector('.notification-empty');
            if (emptyDiv) {
                console.log('[Notification] Empty state element created');
            }
            return;
        }
        
        console.log('[Notification] Rendering', notifications.length, 'notifications');
        
        // Use data attributes instead of inline onclick for better reliability
        const notificationsHTML = notifications.map(n => {
            const date = n.created_at ? new Date(n.created_at).toLocaleString() : '';
            const unreadClass = !n.is_read ? 'unread' : '';
            
            // Store notification data in data attributes
            // Helper to escape HTML safely
            const escapeHtmlFunc = (text) => {
                if (!text) return '';
                const div = document.createElement('div');
                div.textContent = String(text);
                return div.innerHTML;
            };
            
            const linkData = n.link ? `data-link="${escapeHtmlFunc(n.link)}"` : '';
            const title = escapeHtmlFunc(n.title || 'Notification');
            const message = escapeHtmlFunc(n.message || '');
            
            return `
                <div class="notification-item ${unreadClass}" 
                     data-notification-id="${n.id}" 
                     ${linkData}
                     style="cursor: pointer;">
                    <div class="notification-content">
                        <div class="notification-title">${title}</div>
                        <div class="notification-message">${message}</div>
                        <div class="notification-time">${date}</div>
                    </div>
                    ${!n.is_read ? '<div class="notification-dot"></div>' : ''}
                </div>
            `;
        }).join('');
        
        console.log('[Notification] Generated HTML length:', notificationsHTML.length);
        notificationList.innerHTML = notificationsHTML;
        
        // Verify items were added
        const items = notificationList.querySelectorAll('.notification-item');
        console.log('[Notification] Notification items in DOM:', items.length);
        
        // Log first item to verify it's visible
        if (items.length > 0) {
            const firstItem = items[0];
            const computedStyle = window.getComputedStyle(firstItem);
            console.log('[Notification] First item styles:', {
                display: computedStyle.display,
                visibility: computedStyle.visibility,
                color: computedStyle.color,
                backgroundColor: computedStyle.backgroundColor,
                height: computedStyle.height,
                padding: computedStyle.padding
            });
        }
        
        // Attach event listeners using event delegation
        attachNotificationClickHandlers();
    } catch (error) {
        console.error('Error loading notifications:', error);
        const notificationList = document.getElementById('notification-list');
        if (notificationList) {
            // Show user-friendly error message
            const errorMsg = error.message && error.message.includes('connect') 
                ? 'Unable to connect to server' 
                : 'Error loading notifications';
            notificationList.innerHTML = `<div class="notification-empty">${errorMsg}</div>`;
        }
    }
}

// Attach click handlers to notification items using event delegation
function attachNotificationClickHandlers() {
    const notificationList = document.getElementById('notification-list');
    if (!notificationList) return;
    
    // Remove existing listeners to prevent duplicates
    const newNotificationList = notificationList.cloneNode(true);
    notificationList.parentNode.replaceChild(newNotificationList, notificationList);
    
    // Use event delegation for better performance and reliability
    newNotificationList.addEventListener('click', async (e) => {
        // Find the notification item that was clicked
        const notificationItem = e.target.closest('.notification-item');
        if (!notificationItem) {
            console.log('[Notification] Click was not on a notification item');
            return;
        }
        
        e.preventDefault();
        e.stopPropagation();
        
        const notificationId = parseInt(notificationItem.getAttribute('data-notification-id'));
        const link = notificationItem.getAttribute('data-link');
        
        console.log('[Notification] Clicked notification:', {
            id: notificationId,
            link: link,
            element: notificationItem
        });
        
        if (!notificationId || isNaN(notificationId)) {
            console.error('[Notification] Invalid notification ID:', notificationId);
            showSuccessNotification('Invalid notification. Please refresh and try again.', 'error');
            return;
        }
        
        try {
            // Handle different notification link types
            if (link) {
                if (link.startsWith('assessment:')) {
                    // Assessment notification
                    const assessmentId = link.split(':')[1];
                    console.log('[Notification] Opening assessment:', assessmentId);
                    await handleAssessmentNotification(notificationId, assessmentId);
                } else if (link.startsWith('/')) {
                    // Regular URL link - mark as read first, then navigate
                    console.log('[Notification] Navigating to:', link);
                    await markNotificationRead(notificationId);
                    window.location.href = link;
                } else {
                    // Other custom link formats - just mark as read
                    console.log('[Notification] Marking as read (custom link)');
                    await markNotificationRead(notificationId);
                }
            } else {
                // No link - just mark as read
                console.log('[Notification] Marking as read (no link)');
                await markNotificationRead(notificationId);
            }
        } catch (error) {
            console.error('[Notification] Error handling notification click:', error);
            showSuccessNotification('Failed to process notification. Please try again.', 'error');
        }
    });
}

// Toggle notification dropdown
function toggleNotificationDropdown(event) {
    // Prevent event bubbling
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    const dropdown = document.getElementById('notification-dropdown');
    if (!dropdown) {
        console.error('[Notification] Dropdown element not found');
        return;
    }
    
    // Toggle state
    notificationDropdownOpen = !notificationDropdownOpen;
    
    if (notificationDropdownOpen) {
        // Opening dropdown
        console.log('[Notification] Opening dropdown');
        
        // Calculate position directly below bell button
        const bellBtn = document.getElementById('notification-bell-btn');
        let rightPosition = 16; // Default right position
        let topPosition = 64; // Position directly below navbar
        
        if (bellBtn) {
            const bellRect = bellBtn.getBoundingClientRect();
            const viewportWidth = window.innerWidth;
            const dropdownWidth = 380; // Fixed width of dropdown
            
            // Position dropdown to align with right edge of bell button
            rightPosition = viewportWidth - bellRect.right;
            // Add small offset to align with bell center
            rightPosition = Math.max(16, rightPosition - 10);
            
            // Position directly below the bell button
            topPosition = bellRect.bottom + 8; // 8px gap below bell
            
            // Ensure dropdown doesn't go off-screen
            if (rightPosition + dropdownWidth > viewportWidth - 16) {
                rightPosition = viewportWidth - dropdownWidth - 16;
            }
            
            console.log('[Notification] Bell button position:', {
                bellRight: bellRect.right,
                bellBottom: bellRect.bottom,
                viewportWidth: viewportWidth,
                calculatedRight: rightPosition,
                calculatedTop: topPosition
            });
        }
        
        // Set ALL required styles explicitly with !important
        // CRITICAL: Ensure dropdown is fixed relative to VIEWPORT, not parent
        dropdown.style.setProperty('display', 'flex', 'important');
        dropdown.style.setProperty('visibility', 'visible', 'important');
        dropdown.style.setProperty('opacity', '1', 'important');
        dropdown.style.setProperty('z-index', '99999', 'important'); // Extremely high z-index
        dropdown.style.setProperty('position', 'fixed', 'important'); // Fixed to viewport
        dropdown.style.setProperty('top', `${topPosition}px`, 'important');
        dropdown.style.setProperty('right', `${rightPosition}px`, 'important');
        dropdown.style.setProperty('left', 'auto', 'important'); // Don't use left
        dropdown.style.setProperty('bottom', 'auto', 'important'); // Don't use bottom
        dropdown.style.setProperty('background', '#2b2454', 'important');
        dropdown.style.setProperty('width', '380px', 'important');
        dropdown.style.setProperty('min-width', '300px', 'important');
        dropdown.style.setProperty('max-width', '380px', 'important');
        dropdown.style.setProperty('border', '1px solid rgba(255, 255, 255, 0.2)', 'important');
        dropdown.style.setProperty('box-shadow', '0 12px 40px rgba(0, 0, 0, 0.6)', 'important');
        dropdown.style.setProperty('transform', 'translateY(0) translateZ(0)', 'important'); // Force GPU acceleration
        dropdown.style.setProperty('pointer-events', 'auto', 'important');
        dropdown.style.setProperty('overflow', 'visible', 'important');
        dropdown.style.setProperty('contain', 'none', 'important');
        dropdown.style.setProperty('clip-path', 'none', 'important');
        dropdown.style.setProperty('clip', 'auto', 'important');
        
        // Also add a class to ensure visibility
        dropdown.classList.add('notification-dropdown-open');
        
        // Verify it's actually visible and positioned correctly
        const computedStyle = window.getComputedStyle(dropdown);
        const rect = dropdown.getBoundingClientRect();
        console.log('[Notification] Dropdown opened - computed styles:', {
            display: computedStyle.display,
            visibility: computedStyle.visibility,
            opacity: computedStyle.opacity,
            zIndex: computedStyle.zIndex,
            position: computedStyle.position,
            top: computedStyle.top,
            right: computedStyle.right,
            width: computedStyle.width,
            height: computedStyle.height,
            boundingRect: {
                top: rect.top,
                right: rect.right,
                bottom: rect.bottom,
                left: rect.left,
                width: rect.width,
                height: rect.height
            },
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            isVisible: rect.width > 0 && rect.height > 0 && 
                      rect.top >= 0 && rect.left >= 0 && 
                      rect.right <= window.innerWidth &&
                      rect.bottom <= window.innerHeight,
            isOnScreen: rect.top < window.innerHeight && rect.bottom > 0 && 
                       rect.left < window.innerWidth && rect.right > 0
        });
        
        // If not visible, try to fix it
        if (rect.width === 0 || rect.height === 0) {
            console.warn('[Notification] Dropdown has zero dimensions! Attempting to fix...');
            // Force re-render
            dropdown.style.display = 'none';
            void dropdown.offsetHeight; // Force reflow
            dropdown.style.setProperty('display', 'flex', 'important');
        }
        
        // Force a reflow to ensure styles are applied
        void dropdown.offsetHeight;
        
        // Only load notifications if not already loaded or if dropdown was closed
        // Check if notification list is empty or has only empty state
        const notificationList = document.getElementById('notification-list');
        const isEmpty = !notificationList || 
                       notificationList.innerHTML.trim() === '' || 
                       notificationList.innerHTML.includes('notification-empty');
        
        if (isEmpty) {
            console.log('[Notification] Loading notifications (list is empty)');
            loadNotifications();
        } else {
            console.log('[Notification] Notifications already loaded, skipping API call');
        }
    } else {
        // Closing dropdown
        console.log('[Notification] Closing dropdown');
        dropdown.style.setProperty('display', 'none', 'important');
        dropdown.style.setProperty('visibility', 'hidden', 'important');
        dropdown.style.setProperty('opacity', '0', 'important');
        dropdown.classList.remove('notification-dropdown-open');
        console.log('[Notification] Dropdown closed');
    }
}

// Make function globally accessible
window.toggleNotificationDropdown = toggleNotificationDropdown;

// Mark notification as read
async function markNotificationRead(notificationId) {
    try {
        if (!authToken || !currentUser) {
            console.warn('User not authenticated');
            return;
        }
        
        console.log('[Notification] Marking notification as read:', notificationId);
        await notificationsAPI.markAsRead(notificationId);
        
        // Reload notifications and badge to reflect changes (force reload)
        await loadNotifications(true);
        await loadNotificationBadge();
        
        console.log('[Notification] Successfully marked as read:', notificationId);
    } catch (error) {
        console.error('Error marking notification as read:', error);
        // Show user-friendly error message
        const errorMsg = error.message || 'Failed to mark notification as read';
        showSuccessNotification(errorMsg, 'error');
    }
}

// Make function globally accessible for backward compatibility
window.markNotificationRead = markNotificationRead;

// Mark all notifications as read
async function markAllNotificationsRead() {
    try {
        if (!authToken || !currentUser) {
            console.warn('User not authenticated');
            return;
        }
        
        // Show loading state
        const markAllBtn = document.querySelector('.mark-all-read-btn');
        const originalText = markAllBtn ? markAllBtn.textContent : 'Mark all as read';
        if (markAllBtn) {
            markAllBtn.textContent = 'Marking...';
            markAllBtn.disabled = true;
        }
        
        // Call API
        await notificationsAPI.markAllAsRead();
        
        // Reload notifications and badge to reflect changes (force reload)
        await loadNotifications(true);
        await loadNotificationBadge();
        
        // Restore button state
        if (markAllBtn) {
            markAllBtn.textContent = originalText;
            markAllBtn.disabled = false;
        }
        
        // Show success feedback (optional - can be removed if not needed)
        console.log('All notifications marked as read');
    } catch (error) {
        console.error('Error marking all notifications as read:', error);
        
        // Restore button state on error
        const markAllBtn = document.querySelector('.mark-all-read-btn');
        if (markAllBtn) {
            markAllBtn.textContent = 'Mark all as read';
            markAllBtn.disabled = false;
        }
        
        // Show error message to user
        alert('Failed to mark all notifications as read. Please try again.');
    }
}

// Mobile Menu Toggle
function toggleMobileMenu() {
    const navCenter = document.getElementById('nav-center');
    if (navCenter) {
        navCenter.classList.toggle('active');
    }
}

// Close mobile menu when clicking outside
document.addEventListener('click', (e) => {
    const navCenter = document.getElementById('nav-center');
    const mobileToggle = document.querySelector('.mobile-menu-toggle');
    
    if (navCenter && mobileToggle && !navCenter.contains(e.target) && !mobileToggle.contains(e.target)) {
        navCenter.classList.remove('active');
    }
    
    // Close navigation dropdowns when clicking outside
    // Skip if clicking on a dropdown toggle button
    const isDropdownToggle = e.target.classList.contains('dropdown-toggle') || 
                             e.target.closest('.dropdown-toggle');
    
    if (isDropdownToggle) {
        return; // Don't close dropdowns when clicking the toggle button
    }
    
    const nonTechMenu = document.getElementById('non-technical-menu');
    const interviewMenu = document.getElementById('interview-menu');
    const nonTechDropdown = nonTechMenu ? (nonTechMenu.parentElement || nonTechMenu.closest('.nav-dropdown')) : null;
    const interviewDropdown = interviewMenu ? (interviewMenu.parentElement || interviewMenu.closest('.nav-dropdown')) : null;
    
    // Check if click is outside non-technical dropdown
    if (nonTechDropdown && nonTechDropdown.classList.contains('open')) {
        // Check if click is outside the dropdown container
        const clickedInside = nonTechDropdown.contains(e.target);
        if (!clickedInside) {
            closeNonTechnicalMenu();
        }
    }
    
    // Check if click is outside interview dropdown
    if (interviewDropdown && interviewDropdown.classList.contains('open')) {
        // Check if click is outside the dropdown container
        const clickedInside = interviewDropdown.contains(e.target);
        if (!clickedInside) {
            closeInterviewMenu();
        }
    }
    
    // Close notification dropdown when clicking outside
    const bellBtn = document.getElementById('notification-bell-btn');
    const dropdown = document.getElementById('notification-dropdown');
    
    // Don't close if clicking on the bell button (handled by toggleNotificationDropdown)
    if (bellBtn && bellBtn.contains(e.target)) {
        return;
    }
    
    // Close if dropdown is open and click is outside both bell and dropdown
    if (notificationDropdownOpen && dropdown && 
        !bellBtn.contains(e.target) && 
        !dropdown.contains(e.target)) {
        console.log('[Notification] Clicking outside, closing dropdown');
        notificationDropdownOpen = false;
        dropdown.style.display = 'none';
        dropdown.style.visibility = 'hidden';
        dropdown.style.opacity = '0';
    }
});

// Handle assessment notification click
async function handleAssessmentNotification(notificationId, assessmentId) {
    try {
        console.log('[Notification] Handling assessment notification:', notificationId, assessmentId);
        
        // Mark notification as read first
        await markNotificationRead(notificationId);
        
        // Close notification dropdown
        toggleNotificationDropdown();
        
        // Small delay to ensure notification is marked as read
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Navigate to appropriate assessments page based on user role
        if (currentUser && currentUser.role === 'student') {
            showStudentAssessmentsPage();
        } else {
            // For faculty/admin, show assessment page
            showAssessmentPage();
        }
    } catch (error) {
        console.error('Error handling assessment notification:', error);
        showSuccessNotification('Failed to open assessment. Please try again.', 'error');
    }
}

// Make function globally accessible for backward compatibility
window.handleAssessmentNotification = handleAssessmentNotification;

// Close notification dropdown when clicking outside
document.addEventListener('click', (e) => {
    const bellBtn = document.getElementById('notification-bell-btn');
    const dropdown = document.getElementById('notification-dropdown');
    
    // Don't close if clicking on the bell button (handled by toggleNotificationDropdown)
    if (bellBtn && bellBtn.contains(e.target)) {
        return;
    }
    
    // Close if dropdown is open and click is outside both bell and dropdown
    if (notificationDropdownOpen && dropdown && 
        !bellBtn.contains(e.target) && 
        !dropdown.contains(e.target)) {
        console.log('[Notification] Clicking outside, closing dropdown');
        notificationDropdownOpen = false;
        if (dropdown) {
            dropdown.style.display = 'none';
            dropdown.style.visibility = 'hidden';
            dropdown.style.opacity = '0';
        }
    }
});

// ================= AI Chatbot Functions =================

let aiChatbotOpen = false;

function toggleAIChatbot() {
    const panel = document.getElementById('ai-chatbot-panel');
    const button = document.getElementById('ai-chatbot-button');
    
    if (!panel || !button) return;
    
    aiChatbotOpen = !aiChatbotOpen;
    
    if (aiChatbotOpen) {
        panel.classList.remove('hidden');
        button.style.display = 'none';
        const input = document.getElementById('ai-chatbot-input');
        if (input) {
            setTimeout(() => input.focus(), 100);
        }
    } else {
        panel.classList.add('hidden');
        button.style.display = 'flex';
    }
}

function handleAIChatbotKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendAIChatbotMessage();
    }
}

async function sendAIChatbotMessage() {
    const input = document.getElementById('ai-chatbot-input');
    const sendButton = document.getElementById('ai-chatbot-send');
    const messagesContainer = document.getElementById('ai-chatbot-messages');
    
    if (!input || !messagesContainer) return;
    
    const message = input.value.trim();
    if (!message) return;
    
    // Disable input
    input.disabled = true;
    if (sendButton) sendButton.disabled = true;
    
    // Add user message
    addChatbotMessage('user', message);
    
    // Clear input
    input.value = '';
    
    // Show loading
    const loadingId = addChatbotLoading();
    
    try {
        // Send directly to OpenAI - no validation, no modification
        const response = await studentAPI.chatWithAI(message);
        
        // Remove loading
        removeChatbotLoading(loadingId);
        
        // Add AI response
        if (response && response.message) {
            addChatbotMessage('ai', response.message);
        } else {
            addChatbotMessage('ai', 'Sorry, I encountered an error. Please try again.');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        removeChatbotLoading(loadingId);
        addChatbotMessage('ai', 'Sorry, I\'m having trouble connecting. Please try again.');
    } finally {
        // Re-enable input
        input.disabled = false;
        if (sendButton) sendButton.disabled = false;
        input.focus();
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

function addChatbotMessage(type, content) {
    const messagesContainer = document.getElementById('ai-chatbot-messages');
    if (!messagesContainer) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = type === 'user' ? 'user-message' : 'ai-message';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = type === 'user' ? 'user-message-content' : 'ai-message-content';
    
    // Format content (preserve markdown, code blocks, line breaks)
    const formattedContent = formatChatbotMessage(content);
    contentDiv.innerHTML = formattedContent;
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function formatChatbotMessage(content) {
    // Escape HTML first
    const escapeHtml = (text) => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };
    
    let formatted = escapeHtml(content);
    
    // Format code blocks (between ```)
    formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre class="question-code-block" style="margin: 8px 0;"><code>${escapeHtml(code.trim())}</code></pre>`;
    });
    
    // Format inline code (`code`)
    formatted = formatted.replace(/`([^`]+)`/g, '<code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px; font-family: monospace;">$1</code>');
    
    // Format markdown headers
    formatted = formatted.replace(/^### (.*$)/gm, '<h3>$1</h3>');
    formatted = formatted.replace(/^## (.*$)/gm, '<h2>$1</h2>');
    formatted = formatted.replace(/^# (.*$)/gm, '<h1>$1</h1>');
    
    // Format bold (**text**)
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // Format lists
    formatted = formatted.replace(/^\- (.+)$/gm, '<li>$1</li>');
    formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    // Replace newlines with <br>
    formatted = formatted.replace(/\n/g, '<br>');
    
    return `<p>${formatted}</p>`;
}

function addChatbotLoading() {
    const messagesContainer = document.getElementById('ai-chatbot-messages');
    if (!messagesContainer) return null;
    
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'ai-message';
    loadingDiv.id = 'ai-chatbot-loading';
    
    const loadingContent = document.createElement('div');
    loadingContent.className = 'ai-message-content ai-message-loading';
    loadingContent.innerHTML = '<span></span><span></span><span></span>';
    
    loadingDiv.appendChild(loadingContent);
    messagesContainer.appendChild(loadingDiv);
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return 'ai-chatbot-loading';
}

function removeChatbotLoading(loadingId) {
    if (!loadingId) return;
    const loadingElement = document.getElementById(loadingId);
    if (loadingElement) {
        loadingElement.remove();
    }
}

// ==================== STUDENT ASSESSMENTS ====================

let currentAssessmentAttempt = null;
let assessmentTimer = null;
let assessmentTimeRemaining = 0; // in seconds

function showStudentAssessmentsPage() {
    // Close dropdown menu
    closeNonTechnicalMenu();
    updateActiveNav('Non-Technical');
    showPage('student-assessments');
    
    // Wait a bit for the page to be visible before loading data
    setTimeout(() => {
        loadStudentAssessments();
    }, 100);
}

function loadStudentAssessments() {
    // Ensure page is visible first
    const pageEl = document.getElementById('student-assessments-page');
    if (!pageEl) {
        console.error('Student assessments page not found');
        return;
    }
    
    const loadingEl = document.getElementById('assessments-loading');
    const errorEl = document.getElementById('assessments-error');
    const listEl = document.getElementById('assessments-list');
    const emptyEl = document.getElementById('assessments-empty');
    
    // Check if elements exist before accessing
    if (!loadingEl || !errorEl || !listEl || !emptyEl) {
        console.error('Required elements not found on student assessments page');
        return;
    }
    
    loadingEl.style.display = 'block';
    errorEl.style.display = 'none';
    listEl.innerHTML = '';
    emptyEl.style.display = 'none';
    
    studentAPI.getAssessments()
        .then(response => {
            loadingEl.style.display = 'none';
            
            const assessments = response.assessments || [];
            
            if (assessments.length === 0) {
                emptyEl.style.display = 'block';
                return;
            }
            
            // Load attempt status for each assessment
            const assessmentPromises = assessments.map(assessment => 
                studentAPI.getMyAttempt(assessment.id)
                    .then(res => ({ assessment, attempt: res.attempt }))
                    .catch(() => ({ assessment, attempt: null }))
            );
            
            Promise.all(assessmentPromises)
                .then(results => {
                    renderStudentAssessments(results);
                })
                .catch(err => {
                    console.error('Error loading attempt status:', err);
                    // Still render assessments even if attempt loading fails
                    const fallbackResults = assessments.map(a => ({ assessment: a, attempt: null }));
                    renderStudentAssessments(fallbackResults);
                });
        })
        .catch(error => {
            console.error('Error loading assessments:', error);
            loadingEl.style.display = 'none';
            if (errorEl) {
                errorEl.textContent = error.message || 'Failed to load assessments';
                errorEl.style.display = 'block';
            }
        });
}

// Helper function to get assessment status (upcoming, active, closed)
function getAssessmentStatus(assessment) {
    if (!assessment.start_date || !assessment.end_date || !assessment.start_time || !assessment.end_time) {
        return { status: 'closed', message: 'Time window not configured' };
    }
    
    const now = new Date();
    const startDateStr = assessment.start_date; // Format: YYYY-MM-DD
    const endDateStr = assessment.end_date;
    const startTimeStr = assessment.start_time.substring(0, 5); // Format: HH:MM
    const endTimeStr = assessment.end_time.substring(0, 5);
    
    const startDateTime = new Date(`${startDateStr}T${startTimeStr}:00`);
    const endDateTime = new Date(`${endDateStr}T${endTimeStr}:00`);
    
    if (now < startDateTime) {
        return { status: 'upcoming', message: 'Test not started yet' };
    } else if (now > endDateTime) {
        return { status: 'closed', message: 'Test closed' };
    } else {
        return { status: 'active', message: 'Assessment is active' };
    }
}

// Helper function to check if assessment is currently available (within time window)
function isAssessmentAvailable(assessment) {
    const statusInfo = getAssessmentStatus(assessment);
    return statusInfo.status === 'active';
}

function renderStudentAssessments(results) {
    const listEl = document.getElementById('assessments-list');
    if (!listEl) return;
    
    listEl.innerHTML = results.map(({ assessment, attempt }) => {
        const modeLabel = assessment.assessment_mode === 'technical_only' ? 'Technical Only' : 
                         (assessment.assessment_mode === 'non_technical_only' ? 'Non-Technical Only' : 'Mixed');
        const difficultyLabel = assessment.difficulty ? assessment.difficulty.charAt(0).toUpperCase() + assessment.difficulty.slice(1) : 'N/A';
        const hasAttempted = attempt !== null && attempt.submitted_at;
        const statusInfo = getAssessmentStatus(assessment);
        const isAvailable = statusInfo.status === 'active' && !hasAttempted;
        const score = attempt && attempt.submitted_at ? `${attempt.score}/${attempt.total_marks} (${Math.round((attempt.score / attempt.total_marks) * 100)}%)` : null;
        
        // Status badge styling
        let statusBadge = '';
        if (hasAttempted) {
            statusBadge = `<span style="padding: 6px 12px; background: #2ecc71; color: white; border-radius: 6px; font-size: 12px; font-weight: 600;">Completed</span>`;
        } else if (statusInfo.status === 'active') {
            statusBadge = `<span style="padding: 6px 12px; background: #27ae60; color: white; border-radius: 6px; font-size: 12px; font-weight: 600;">Active</span>`;
        } else if (statusInfo.status === 'upcoming') {
            statusBadge = `<span style="padding: 6px 12px; background: #3498db; color: white; border-radius: 6px; font-size: 12px; font-weight: 600;">Upcoming</span>`;
        } else {
            statusBadge = `<span style="padding: 6px 12px; background: #95a5a6; color: white; border-radius: 6px; font-size: 12px; font-weight: 600;">Closed</span>`;
        }
        
        // Format start and end date/time
        const formatDateTime = (dateStr, timeStr) => {
            if (!dateStr || !timeStr) return 'N/A';
            const date = new Date(`${dateStr}T${timeStr.substring(0, 5)}:00`);
            return date.toLocaleString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                year: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
            });
        };
        const startDateTimeStr = formatDateTime(assessment.start_date, assessment.start_time);
        const endDateTimeStr = formatDateTime(assessment.end_date, assessment.end_time);
        
        return `
            <div class="assessment-card" style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border: 1px solid #e0e0e0;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                    <div style="flex: 1;">
                        <h3 style="margin: 0 0 10px 0; color: #667eea; font-size: 20px;">${assessment.title}</h3>
                        <p style="color: #666; margin: 0 0 15px 0; font-size: 14px;">${assessment.description || 'No description'}</p>
                    </div>
                    ${statusBadge}
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <div>
                        <strong style="color: #333; font-size: 12px;">Mode:</strong>
                        <div style="color: #666; font-size: 14px;">${modeLabel}</div>
                    </div>
                    <div>
                        <strong style="color: #333; font-size: 12px;">Questions:</strong>
                        <div style="color: #666; font-size: 14px;">${assessment.question_count || 0}</div>
                    </div>
                    <div>
                        <strong style="color: #333; font-size: 12px;">Duration:</strong>
                        <div style="color: #666; font-size: 14px;">${formatAssessmentDateTimeRange(assessment)}</div>
                    </div>
                    <div>
                        <strong style="color: #333; font-size: 12px;">Difficulty:</strong>
                        <div style="color: #666; font-size: 14px;">${difficultyLabel}</div>
                    </div>
                    <div>
                        <strong style="color: #333; font-size: 12px;">Total Marks:</strong>
                        <div style="color: #666; font-size: 14px;">${assessment.total_marks || 0}</div>
                    </div>
                    <div>
                        <strong style="color: #333; font-size: 12px;">Marks:</strong>
                        <div style="color: #666; font-size: 14px;">${score || 'Not attempted'}</div>
                    </div>
                </div>
                
                ${assessment.topic_tags && assessment.topic_tags.length > 0 ? `
                    <div style="margin-bottom: 20px;">
                        <strong style="color: #333; font-size: 12px;">Topics:</strong>
                        <div style="margin-top: 5px;">
                            ${assessment.topic_tags.map(tag => `
                                <span style="display: inline-block; padding: 4px 10px; background: #e0e0e0; border-radius: 4px; font-size: 12px; margin-right: 5px; margin-bottom: 5px;">${tag}</span>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
                
                <div style="display: flex; gap: 10px;">
                    ${hasAttempted ? `
                        <button onclick="viewAssessmentResults(${assessment.id})" class="btn btn-secondary" style="flex: 1; padding: 12px; font-size: 14px; font-weight: 600; border-radius: 8px; background: #6c757d; border: none; color: white; cursor: pointer;">
                            View Results
                        </button>
                    ` : statusInfo.status === 'active' ? `
                        <button onclick="startAssessmentAttempt(${assessment.id})" class="btn btn-primary" style="flex: 1; padding: 12px; font-size: 14px; font-weight: 600; border-radius: 8px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; color: white; cursor: pointer;">
                            Start Assessment
                        </button>
                    ` : statusInfo.status === 'upcoming' ? `
                        <button disabled class="btn btn-secondary" style="flex: 1; padding: 12px; font-size: 14px; font-weight: 600; border-radius: 8px; background: #95a5a6; border: none; color: white; cursor: not-allowed; opacity: 0.6;">
                            Test not started yet
                        </button>
                    ` : `
                        <button disabled class="btn btn-secondary" style="flex: 1; padding: 12px; font-size: 14px; font-weight: 600; border-radius: 8px; background: #95a5a6; border: none; color: white; cursor: not-allowed; opacity: 0.6;">
                            Test closed
                        </button>
                    `}
                </div>
            </div>
        `;
    }).join('');
}

async function startAssessmentAttempt(assessmentId) {
    if (!confirm('Are you sure you want to start this assessment? The timer will begin once you click OK.')) {
        return;
    }
    
    try {
        // Start the attempt
        await studentAPI.startAssessment(assessmentId);
        
        // Load assessment details
        const response = await studentAPI.getAssessment(assessmentId);
        const assessment = response.assessment;
        
        currentAssessmentAttempt = {
            assessment_id: assessmentId,
            assessment: assessment,
            answers: {},
            started_at: new Date()
        };
        
        // Initialize timer based on end date and time
        if (assessment.end_date && assessment.end_time) {
            // Combine end date and time to create end datetime
            const endDateStr = assessment.end_date; // Format: YYYY-MM-DD
            const endTimeStr = assessment.end_time.substring(0, 5); // Format: HH:MM (might be HH:MM:SS)
            const endDateTime = new Date(`${endDateStr}T${endTimeStr}:00`);
            const now = new Date();
            
            // Calculate remaining seconds
            const diffMs = endDateTime - now;
            assessmentTimeRemaining = Math.max(0, Math.floor(diffMs / 1000));
        } else {
            // Fallback: if date/time not available, use a default (this shouldn't happen)
            assessmentTimeRemaining = 3600; // 1 hour default
            console.warn('Assessment end date/time not available, using default timer');
        }
        startAssessmentTimer();
        
        // Show attempt page
        showAssessmentAttemptPage(assessment);
        
    } catch (error) {
        console.error('Error starting assessment:', error);
        showSuccessNotification(error.message || 'Failed to start assessment. Please try again.', 'error');
    }
}

function showAssessmentAttemptPage(assessment) {
    updateActiveNav('Assessments');
    showPage('assessment-attempt');
    
    const titleEl = document.getElementById('attempt-assessment-title');
    if (titleEl) {
        titleEl.textContent = assessment.title;
    }
    
    const descEl = document.getElementById('attempt-assessment-description');
    if (descEl) {
        descEl.textContent = assessment.description || '';
    }
    
    const contentEl = document.getElementById('assessment-attempt-content');
    if (!contentEl) return;
    
    const questions = assessment.questions || [];
    
    contentEl.innerHTML = questions.map((aq, index) => {
        const q = aq.question || {};
        const questionId = q.id;
        
        if (q.type === 'coding') {
            return `
                <div class="question-card" style="background: white; padding: 25px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3 style="margin: 0; color: #667eea;">Question ${index + 1} (Technical) - ${aq.marks} marks</h3>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <strong>Problem:</strong>
                        <div style="margin-top: 10px; padding: 15px; background: #f8f9fa; border-radius: 8px; white-space: pre-wrap;">${q.description || q.title || ''}</div>
                    </div>
                    <div>
                        <strong>Write your solution:</strong>
                        <textarea id="answer-${questionId}" rows="15" style="width: 100%; padding: 15px; border: 2px solid #e0e0e0; border-radius: 8px; font-family: 'Courier New', monospace; margin-top: 10px;" placeholder="Write your code here..."></textarea>
                    </div>
                </div>
            `;
        } else if (q.type === 'mcq') {
            const options = typeof q.options === 'string' ? JSON.parse(q.options) : (q.options || []);
            return `
                <div class="question-card" style="background: white; padding: 25px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3 style="margin: 0; color: #667eea;">Question ${index + 1} (MCQ) - ${aq.marks} marks</h3>
                    </div>
                    <div style="margin-bottom: 20px;">
                        <strong>Question:</strong>
                        <div style="margin-top: 10px; padding: 15px; background: #f8f9fa; border-radius: 8px;">${q.description || q.title || ''}</div>
                    </div>
                    <div>
                        <strong>Select your answer:</strong>
                        <div style="margin-top: 15px;">
                            ${options.map((opt, optIdx) => `
                                <label style="display: flex; align-items: center; padding: 12px; margin-bottom: 10px; border: 2px solid #e0e0e0; border-radius: 8px; cursor: pointer; transition: all 0.3s;" onmouseover="this.style.borderColor='#667eea'" onmouseout="this.style.borderColor='#e0e0e0'">
                                    <input type="radio" name="answer-${questionId}" value="${String.fromCharCode(65 + optIdx)}" style="margin-right: 10px;">
                                    <span>${String.fromCharCode(65 + optIdx)}. ${opt}</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
        } else if (q.type === 'fill_blank') {
            return `
                <div class="question-card" style="background: white; padding: 25px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3 style="margin: 0; color: #667eea;">Question ${index + 1} (Fill-in-the-blank) - ${aq.marks} marks</h3>
                    </div>
                    <div style="margin-bottom: 20px;">
                        <strong>Question:</strong>
                        <div style="margin-top: 10px; padding: 15px; background: #f8f9fa; border-radius: 8px;">${q.description || q.title || ''}</div>
                    </div>
                    <div>
                        <strong>Your answer:</strong>
                        <input type="text" id="answer-${questionId}" style="width: 100%; padding: 12px; margin-top: 10px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 16px;" placeholder="Enter your answer...">
                    </div>
                </div>
            `;
        }
        return '';
    }).join('');
}

function startAssessmentTimer() {
    if (assessmentTimer) {
        clearInterval(assessmentTimer);
    }
    
    updateTimerDisplay();
    
    assessmentTimer = setInterval(() => {
        assessmentTimeRemaining--;
        updateTimerDisplay();
        
        if (assessmentTimeRemaining <= 0) {
            clearInterval(assessmentTimer);
            showSuccessNotification('Time is up! Submitting your assessment...', 'warning');
            submitAssessmentAttempt();
        }
    }, 1000);
}

function updateTimerDisplay() {
    const timerEl = document.getElementById('timer-display');
    const timerContainer = document.getElementById('timer-container');
    if (!timerEl || !timerContainer) return;
    
    const hours = Math.floor(assessmentTimeRemaining / 3600);
    const minutes = Math.floor((assessmentTimeRemaining % 3600) / 60);
    const seconds = assessmentTimeRemaining % 60;
    
    // Format as HH:MM:SS
    timerEl.textContent = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    
    // Change color when time is running out (green -> orange -> red)
    const timerBadge = timerEl.parentElement;
    if (assessmentTimeRemaining < 300) { // Less than 5 minutes
        timerBadge.style.background = '#e74c3c';
        timerBadge.style.boxShadow = '0 2px 8px rgba(231, 76, 60, 0.3)';
    } else if (assessmentTimeRemaining < 600) { // Less than 10 minutes
        timerBadge.style.background = '#f39c12';
        timerBadge.style.boxShadow = '0 2px 8px rgba(243, 156, 18, 0.3)';
    } else {
        timerBadge.style.background = '#27ae60';
        timerBadge.style.boxShadow = '0 2px 8px rgba(39, 174, 96, 0.3)';
    }
}

async function submitAssessmentAttempt() {
    if (!currentAssessmentAttempt) {
        showSuccessNotification('No assessment to submit.', 'error');
        return;
    }
    
    if (assessmentTimer) {
        clearInterval(assessmentTimer);
    }
    
    // Collect all answers
    const assessment = currentAssessmentAttempt.assessment;
    const questions = assessment.questions || [];
    const answers = {};
    
    questions.forEach(aq => {
        const q = aq.question;
        if (!q) return;
        
        const questionId = q.id;
        
        if (q.type === 'coding') {
            const answerEl = document.getElementById(`answer-${questionId}`);
            if (answerEl) {
                answers[questionId] = answerEl.value.trim();
            }
        } else if (q.type === 'mcq') {
            const selectedOption = document.querySelector(`input[name="answer-${questionId}"]:checked`);
            if (selectedOption) {
                answers[questionId] = selectedOption.value;
            }
        } else if (q.type === 'fill_blank') {
            const answerEl = document.getElementById(`answer-${questionId}`);
            if (answerEl) {
                answers[questionId] = answerEl.value.trim();
            }
        }
    });
    
    try {
        const response = await studentAPI.submitAssessment(currentAssessmentAttempt.assessment_id, answers);
        
        showSuccessNotification('Assessment submitted successfully!');
        
        // Show results
        showAssessmentResults(response);
        
    } catch (error) {
        console.error('Error submitting assessment:', error);
        showSuccessNotification(error.message || 'Failed to submit assessment. Please try again.', 'error');
    }
}

function showAssessmentResults(result) {
    updateActiveNav('Assessments');
    showPage('assessment-results');
    
    const contentEl = document.getElementById('assessment-results-content');
    if (!contentEl) return;
    
    const score = result.score || 0;
    const totalMarks = result.total_marks || 0;
    const percentage = result.percentage || 0;
    
    contentEl.innerHTML = `
        <div class="card" style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; margin-bottom: 30px;">
            <h2 style="color: #667eea; margin-bottom: 20px;">Assessment Results</h2>
            <div style="font-size: 48px; font-weight: bold; color: ${percentage >= 70 ? '#2ecc71' : percentage >= 50 ? '#f39c12' : '#e74c3c'}; margin-bottom: 10px;">
                ${percentage.toFixed(1)}%
            </div>
            <div style="font-size: 24px; color: #666; margin-bottom: 30px;">
                Score: ${score} / ${totalMarks}
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 30px;">
                <div>
                    <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Time Taken</div>
                    <div style="font-size: 18px; font-weight: 600; color: #333;">${result.attempt?.time_taken_minutes || 0} minutes</div>
                </div>
                <div>
                    <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Submitted At</div>
                    <div style="font-size: 18px; font-weight: 600; color: #333;">${result.attempt?.submitted_at ? new Date(result.attempt.submitted_at).toLocaleString() : 'N/A'}</div>
                </div>
                <div>
                    <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Status</div>
                    <div style="font-size: 18px; font-weight: 600; color: ${percentage >= 70 ? '#2ecc71' : percentage >= 50 ? '#f39c12' : '#e74c3c'};">${percentage >= 70 ? 'Passed' : percentage >= 50 ? 'Average' : 'Failed'}</div>
                </div>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <button onclick="showStudentAssessmentsPage()" class="btn btn-primary" style="padding: 12px 30px; font-size: 16px; font-weight: 600; border-radius: 8px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; color: white; cursor: pointer;">
                Back to Assessments
            </button>
        </div>
    `;
    
    // Clear attempt state
    currentAssessmentAttempt = null;
    assessmentTimeRemaining = 0;
}

function viewAssessmentResults(assessmentId) {
    studentAPI.getMyAttempt(assessmentId)
        .then(response => {
            const attempt = response.attempt;
            if (!attempt) {
                showSuccessNotification('No attempt found for this assessment.', 'error');
                return;
            }
            
            // Get assessment details
            studentAPI.getAssessment(assessmentId)
                .then(assessmentResponse => {
                    const result = {
                        score: attempt.score,
                        total_marks: attempt.total_marks,
                        percentage: attempt.total_marks > 0 ? (attempt.score / attempt.total_marks * 100) : 0,
                        attempt: attempt
                    };
                    showAssessmentResults(result);
                });
        })
        .catch(error => {
            console.error('Error loading attempt:', error);
            showSuccessNotification('Failed to load assessment results.', 'error');
        });
}

// ==================== AVAILABLE ASSESSMENTS (Faculty/Admin) ====================

function showAvailableAssessments() {
    updateActiveNav('Non-Technical');
    showPage('available-assessments');
    loadAvailableAssessments();
}

function loadAvailableAssessments() {
    const loadingEl = document.getElementById('available-assessments-loading');
    const errorEl = document.getElementById('available-assessments-error');
    const listEl = document.getElementById('available-assessments-list');
    const emptyEl = document.getElementById('available-assessments-empty');
    
    if (loadingEl) loadingEl.style.display = 'block';
    if (errorEl) errorEl.style.display = 'none';
    if (listEl) listEl.innerHTML = '';
    if (emptyEl) emptyEl.style.display = 'none';
    
    facultyAPI.getAssessments()
        .then(response => {
            if (loadingEl) loadingEl.style.display = 'none';
            
            const assessments = response.assessments || [];
            
            if (assessments.length === 0) {
                if (emptyEl) emptyEl.style.display = 'block';
                return;
            }
            
            renderAvailableAssessments(assessments);
        })
        .catch(error => {
            console.error('Error loading assessments:', error);
            if (loadingEl) loadingEl.style.display = 'none';
            if (errorEl) {
                errorEl.textContent = error.message || 'Failed to load assessments';
                errorEl.style.display = 'block';
            }
        });
}

function renderAvailableAssessments(assessments) {
    const listEl = document.getElementById('available-assessments-list');
    if (!listEl) return;
    
    listEl.innerHTML = assessments.map(assessment => {
        const modeLabel = assessment.assessment_mode === 'technical_only' ? 'Technical Only' : 
                         (assessment.assessment_mode === 'non_technical_only' ? 'Non-Technical Only' : 'Mixed');
        const difficultyLabel = assessment.difficulty ? assessment.difficulty.charAt(0).toUpperCase() + assessment.difficulty.slice(1) : 'N/A';
        const statusBadge = assessment.status === 'published' 
            ? '<span style="padding: 6px 12px; background: #2ecc71; color: white; border-radius: 6px; font-size: 12px; font-weight: 600;">Published</span>'
            : '<span style="padding: 6px 12px; background: #95a5a6; color: white; border-radius: 6px; font-size: 12px; font-weight: 600;">Draft</span>';
        
        return `
            <div class="assessment-card" style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border: 1px solid #e0e0e0;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                    <div style="flex: 1;">
                        <h3 style="margin: 0 0 10px 0; color: #667eea; font-size: 20px;">${assessment.title}</h3>
                        <p style="color: #666; margin: 0 0 15px 0; font-size: 14px;">${assessment.description || 'No description'}</p>
                    </div>
                    ${statusBadge}
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <div>
                        <strong style="color: #333; font-size: 12px;">Mode:</strong>
                        <div style="color: #666; font-size: 14px;">${modeLabel}</div>
                    </div>
                    <div>
                        <strong style="color: #333; font-size: 12px;">Questions:</strong>
                        <div style="color: #666; font-size: 14px;">${assessment.question_count || 0}</div>
                    </div>
                    <div>
                        <strong style="color: #333; font-size: 12px;">Duration:</strong>
                        <div style="color: #666; font-size: 14px;">${formatAssessmentDateTimeRange(assessment)}</div>
                    </div>
                    <div>
                        <strong style="color: #333; font-size: 12px;">Difficulty:</strong>
                        <div style="color: #666; font-size: 14px;">${difficultyLabel}</div>
                    </div>
                    <div>
                        <strong style="color: #333; font-size: 12px;">Total Marks:</strong>
                        <div style="color: #666; font-size: 14px;">${assessment.total_marks || 0}</div>
                    </div>
                    <div>
                        <strong style="color: #333; font-size: 12px;">Created:</strong>
                        <div style="color: #666; font-size: 14px;">${assessment.created_at ? new Date(assessment.created_at).toLocaleDateString() : 'N/A'}</div>
                    </div>
                </div>
                
                ${assessment.topic_tags && assessment.topic_tags.length > 0 ? `
                    <div style="margin-bottom: 20px;">
                        <strong style="color: #333; font-size: 12px;">Topics:</strong>
                        <div style="margin-top: 5px;">
                            ${assessment.topic_tags.map(tag => `
                                <span style="display: inline-block; padding: 4px 10px; background: #e0e0e0; border-radius: 4px; font-size: 12px; margin-right: 5px; margin-bottom: 5px;">${tag}</span>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
                
                <div style="display: flex; gap: 10px;">
                    <button onclick="editAssessment(${assessment.id})" class="btn btn-secondary" style="flex: 1; padding: 12px; font-size: 14px; font-weight: 600; border-radius: 8px; background: #667eea; border: none; color: white; cursor: pointer;">
                        Edit
                    </button>
                    <button onclick="viewAssessmentAttempts(${assessment.id})" class="btn btn-primary" style="flex: 1; padding: 12px; font-size: 14px; font-weight: 600; border-radius: 8px; background: #28a745; border: none; color: white; cursor: pointer;">
                        View Results
                    </button>
                    <button onclick="deleteAssessment(${assessment.id})" class="btn btn-danger" style="flex: 1; padding: 12px; font-size: 14px; font-weight: 600; border-radius: 8px; background: #ff6b6b; border: none; color: white; cursor: pointer;">
                        Delete
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

async function editAssessment(assessmentId) {
    try {
        const response = await facultyAPI.getAssessment(assessmentId);
        const assessment = response.assessment;
        
        // Set current assessment
        currentAssessment = assessment;
        
        // Load questions
        assessmentQuestions = assessment.questions || [];
        
        // Navigate to assessment page
        showAssessmentPage();
        
        // Populate Step 1 form
        document.getElementById('assessment-title').value = assessment.title || '';
        document.getElementById('assessment-description').value = assessment.description || '';
        document.getElementById('assessment-difficulty').value = assessment.difficulty || 'medium';
        
        // Set datetime pickers
        if (assessment.start_date && assessment.start_time) {
            const startTime = assessment.start_time.substring(0, 5); // HH:MM
            const startDateTimeStr = `${assessment.start_date} ${startTime}`;
            // Convert to format that Flatpickr can understand (YYYY-MM-DD HH:MM)
            const startDate = new Date(`${assessment.start_date}T${startTime}:00`);
            if (startDateTimePicker) {
                startDateTimePicker.setDate(startDate, false);
            }
            // Also set hidden inputs
            document.getElementById('assessment-start-date').value = assessment.start_date;
            document.getElementById('assessment-start-time').value = startTime;
        }
        
        if (assessment.end_date && assessment.end_time) {
            const endTime = assessment.end_time.substring(0, 5); // HH:MM
            const endDate = new Date(`${assessment.end_date}T${endTime}:00`);
            if (endDateTimePicker) {
                endDateTimePicker.setDate(endDate, false);
            }
            // Also set hidden inputs
            document.getElementById('assessment-end-date').value = assessment.end_date;
            document.getElementById('assessment-end-time').value = endTime;
        }
        
        // Set assessment mode
        const modeRadios = document.querySelectorAll('input[name="assessment-mode"]');
        modeRadios.forEach(radio => {
            if (radio.value === assessment.assessment_mode) {
                radio.checked = true;
            }
        });
        
        // Set batch assignments
        const batchCheckboxes = Array.from(document.querySelectorAll('input[name="assigned-batches"]'));
        const bothCheckbox = document.getElementById('batch-both-checkbox');
        if (assessment.assigned_batches && Array.isArray(assessment.assigned_batches)) {
            batchCheckboxes.forEach(batch => {
                batch.checked = assessment.assigned_batches.includes(parseInt(batch.value));
            });
            if (bothCheckbox) bothCheckbox.checked = batchCheckboxes.length > 0 && batchCheckboxes.every(batch => batch.checked);
        } else {
            // NULL means all batches - uncheck all
            batchCheckboxes.forEach(batch => {
                batch.checked = false;
            });
            if (bothCheckbox) bothCheckbox.checked = false;
        }
        
        // Set topic tags
        if (assessment.topic_tags && assessment.topic_tags.length > 0) {
            document.getElementById('assessment-tags').value = assessment.topic_tags.join(', ');
        }
        
        // Go to step 2 to show questions
        goToAssessmentStep(2);
        
    } catch (error) {
        console.error('Error loading assessment:', error);
        showSuccessNotification('Failed to load assessment for editing.', 'error');
    }
}

async function viewAssessmentAttempts(assessmentId) {
    try {
        const response = await facultyAPI.getAssessmentAttempts(assessmentId);
        showAssessmentResultsPage(response.assessment, response.attempts);
    } catch (error) {
        console.error('Error loading assessment attempts:', error);
        showSuccessNotification('Failed to load assessment results.', 'error');
    }
}

async function deleteAssessment(assessmentId) {
    if (!confirm('Are you sure you want to delete this assessment? This action cannot be undone.')) {
        return;
    }
    
    try {
        await facultyAPI.deleteAssessment(assessmentId);
        showSuccessNotification('Assessment deleted successfully!');
        loadAvailableAssessments();
    } catch (error) {
        console.error('Error deleting assessment:', error);
        showSuccessNotification(error.message || 'Failed to delete assessment.', 'error');
    }
}

function showAssessmentResultsPage(assessment, attempts) {
    updateActiveNav('Non-Technical');
    showPage('assessment-results-list');
    
    const contentEl = document.getElementById('assessment-results-list-content');
    if (!contentEl) {
        console.error('Assessment results list content element not found');
        return;
    }
    
    const percentage = attempts.length > 0 
        ? attempts.reduce((sum, a) => sum + (a.total_marks > 0 ? (a.score / a.total_marks * 100) : 0), 0) / attempts.length 
        : 0;
    
    contentEl.innerHTML = `
        <div style="margin-bottom: 20px;">
            <button onclick="showAvailableAssessments()" class="btn btn-secondary" style="padding: 10px 20px; font-size: 14px; font-weight: 600; border-radius: 8px; background: #6c757d; border: none; color: white; cursor: pointer;">
                â† Back to Assessments
            </button>
        </div>
        
        <div class="page-header" style="margin-bottom: 30px;">
            <h2 style="margin: 0; color: #667eea;">${assessment.title} - Results</h2>
        </div>
        
        <div style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 30px;">
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;">
                <div style="text-align: center;">
                    <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Total Attempts</div>
                    <div style="font-size: 32px; font-weight: bold; color: #667eea;">${attempts.length}</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Average Score</div>
                    <div style="font-size: 32px; font-weight: bold; color: #28a745;">${percentage.toFixed(1)}%</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Total Marks</div>
                    <div style="font-size: 32px; font-weight: bold; color: #333;">${assessment.total_marks || 0}</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Questions</div>
                    <div style="font-size: 32px; font-weight: bold; color: #333;">${assessment.question_count || 0}</div>
                </div>
            </div>
        </div>
        
        ${attempts.length === 0 ? `
            <div style="background: white; padding: 40px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center;">
                <p style="color: #666; font-size: 16px;">No students have attempted this assessment yet.</p>
            </div>
        ` : `
            <div style="background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h3 style="margin: 0 0 20px 0; color: #333;">Student Results</h3>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f8f9fa; border-bottom: 2px solid #e0e0e0;">
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Student Name</th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Registration No</th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Email</th>
                                <th style="padding: 12px; text-align: center; font-weight: 600; color: #333;">Score</th>
                                <th style="padding: 12px; text-align: center; font-weight: 600; color: #333;">Percentage</th>
                                <th style="padding: 12px; text-align: center; font-weight: 600; color: #333;">Time Taken</th>
                                <th style="padding: 12px; text-align: center; font-weight: 600; color: #333;">Submitted At</th>
                                <th style="padding: 12px; text-align: center; font-weight: 600; color: #333;">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${attempts.map(attempt => {
                                const attemptPercentage = attempt.total_marks > 0 ? (attempt.score / attempt.total_marks * 100) : 0;
                                const statusColor = attemptPercentage >= 70 ? '#2ecc71' : attemptPercentage >= 50 ? '#f39c12' : '#e74c3c';
                                const statusText = attemptPercentage >= 70 ? 'Passed' : attemptPercentage >= 50 ? 'Average' : 'Failed';
                                return `
                                    <tr style="border-bottom: 1px solid #e0e0e0;">
                                        <td style="padding: 12px; color: #333;">${attempt.user_name || 'Unknown'}</td>
                                        <td style="padding: 12px; color: #333;">${attempt.user_reg_no || 'N/A'}</td>
                                        <td style="padding: 12px; color: #333;">${attempt.user_email || 'N/A'}</td>
                                        <td style="padding: 12px; text-align: center; color: #333;">${attempt.score} / ${attempt.total_marks}</td>
                                        <td style="padding: 12px; text-align: center; font-weight: 600; color: ${statusColor};">${attemptPercentage.toFixed(1)}%</td>
                                        <td style="padding: 12px; text-align: center; color: #666;">${attempt.time_taken_minutes || 0} min</td>
                                        <td style="padding: 12px; text-align: center; color: #666;">${attempt.submitted_at ? new Date(attempt.submitted_at).toLocaleString() : 'N/A'}</td>
                                        <td style="padding: 12px; text-align: center;">
                                            <span style="padding: 4px 12px; background: ${statusColor}; color: white; border-radius: 4px; font-size: 12px; font-weight: 600;">${statusText}</span>
                                        </td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `}
    `;
}

