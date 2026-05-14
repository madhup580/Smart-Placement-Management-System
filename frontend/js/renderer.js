/**
 * Centralized Renderer
 */

// Cache DOM elements
const DOMCache = {
    authPage: null,
    mainApp: null,
    pageContents: {},
    codingQuestionView: null,
    aiChatbotContainer: null
};

function initializeDOMCache() {
    DOMCache.authPage = document.getElementById('auth-page');
    DOMCache.mainApp = document.getElementById('main-app');
    DOMCache.codingQuestionView = document.getElementById('coding-question-view');
    DOMCache.aiChatbotContainer = document.getElementById('ai-chatbot-container');

    document.querySelectorAll('.page-content').forEach(page => {
        if (page.id) DOMCache.pageContents[page.id] = page;
    });
}

/* ================== MAIN RENDER ================== */

function render() {
    const state = getState();

    renderAuth(state.auth);
    renderNavigation(state.navigation);
    renderUIVisibility(state.ui);
    renderPageContent(state.navigation.currentPage, state.navigation.questionId);
}

/* ================== AUTH ================== */

function renderAuth(authState) {
    if (!DOMCache.authPage || !DOMCache.mainApp) {
        initializeDOMCache();
        if (!DOMCache.authPage || !DOMCache.mainApp) return;
    }

    if (authState.isAuthenticated) {
        DOMCache.authPage.style.display = 'none';
        DOMCache.mainApp.style.display = 'block';
    } else {
        DOMCache.authPage.style.display = 'block';
        DOMCache.mainApp.style.display = 'none';
    }
}

/* ================== NAV ================== */

function renderNavigation(navState) {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle(
            'active',
            link.getAttribute('href') === `#${navState.currentPage}`
        );
    });
}

/* ================== UI ================== */

function renderUIVisibility(uiState) {
    Object.values(DOMCache.pageContents).forEach(p => p && (p.style.display = 'none'));

    if (uiState.currentPageVisible) {
        const id = `${uiState.currentPageVisible}-page`;
        const page = DOMCache.pageContents[id] || document.getElementById(id);
        if (page) page.style.display = 'block';
    }

    if (DOMCache.codingQuestionView) {
        DOMCache.codingQuestionView.style.display =
            uiState.codingQuestionViewVisible ? 'flex' : 'none';
    }

    if (DOMCache.aiChatbotContainer) {
        DOMCache.aiChatbotContainer.style.display =
            uiState.aiChatbotVisible ? 'block' : 'none';
    }
}

/* ================== PAGE RENDER ================== */

function renderPageContent(pageName, questionId = null) {
    if (!pageName) return;

    try {
        const pageId = `${pageName}-page`;
        const page =
            DOMCache.pageContents[pageId] ||
            document.getElementById(pageId) ||
            document.getElementById(pageName);

        if (!page) {
            navigateToPage('dashboard', null, true);
            return;
        }

        page.style.display = 'block';

        // ✅ Prevent infinite loop
        const ui = getState('ui');
        const codingVisible = pageName === 'coding' && questionId !== null;

        if (
            ui.currentPageVisible !== pageName ||
            ui.codingQuestionViewVisible !== codingVisible
        ) {
            updateUIVisibility(
                {
                    currentPageVisible: pageName,
                    codingQuestionViewVisible: codingVisible
                },
                true
            );
        }

        // ✅ Prevent multiple API calls
        const pages = getState('pages');
        if (!pages[pageName]?.loaded && !pages[pageName]?.loading) {
            loadPageData(pageName, questionId);
        }
    } catch (e) {
        console.error('[Renderer Error]', e);
    }
}

/* ================== LOAD DATA ================== */

function loadPageData(pageName, questionId = null) {
    const pages = getState('pages');

    if (pages[pageName]?.loading) return;

    updateState('pages', { [pageName]: { loading: true } }, true);
    updateState('ui', { loading: true }, true);

    switch (pageName) {
        case 'dashboard':
            loadDashboard?.();
            break;

        case 'coding':
            loadCodingPage?.();
            if (questionId) {
                setTimeout(() => openCodingQuestion?.(questionId, false), 100);
            }
            break;

        case 'quizzes':
            loadQuizzesPage?.();
            break;

        case 'non-technical':
            loadNonTechnicalPage?.();
            break;

        case 'companies':
            loadCompaniesPage?.();
            break;

        case 'resources':
            loadResourcesPage?.();
            break;

        case 'leaderboard':
            loadLeaderboard?.();
            break;

        case 'chatbot':
        case 'ai-interview':
            loadChatbotPage?.();
            break;

        case 'student-assessments':
            loadStudentAssessments?.();
            break;

        case 'available-assessments':
            loadAvailableAssessments?.();
            break;
    }

    updateState('pages', {
        [pageName]: { loaded: true, loading: false }
    }, true);

    updateState('ui', { loading: false }, true);
}

/* ================== RENDER QUEUE ================== */

let _isRendering = false;
let _renderScheduled = false;

function debouncedRender() {
    if (_renderScheduled) return;

    _renderScheduled = true;

    requestAnimationFrame(() => {
        if (_isRendering) return;

        _isRendering = true;
        _renderScheduled = false;

        try {
            render();
        } finally {
            _isRendering = false;
        }
    });
}

/* ================== STATE SUBSCRIPTIONS ================== */

function setupStateSubscriptions() {
    if (typeof subscribeToState !== 'function') {
        return setTimeout(setupStateSubscriptions, 100);
    }

    subscribeToState('auth', debouncedRender);
    subscribeToState('navigation', debouncedRender);
    subscribeToState('ui', debouncedRender);

    console.log('[Renderer] Subscribed');
}

/* ================== INIT ================== */

let initialized = false;

function initRenderer() {
    if (initialized) return;
    initialized = true;

    initializeDOMCache();
    setupStateSubscriptions();
    render(); // ✅ ONLY ONCE
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRenderer);
} else {
    initRenderer();
}

/* ================== EXPORT ================== */

window.render = render;
window.debouncedRender = debouncedRender;
window.initializeDOMCache = initializeDOMCache;