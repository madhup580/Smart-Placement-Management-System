/**
 * Loading States Manager
 * Provides better loading indicators and states for async operations
 */

// Loading state management
const loadingStates = {
    resume: false,
    jd: false,
    interview: false,
    face_verification: false,
    device_detection: false,
    audio_detection: false
};

/**
 * Show loading indicator
 */
function showLoading(type, message = 'Loading...') {
    loadingStates[type] = true;
    
    // Create or update loading overlay
    let loadingOverlay = document.getElementById('loading-overlay');
    if (!loadingOverlay) {
        loadingOverlay = document.createElement('div');
        loadingOverlay.id = 'loading-overlay';
        loadingOverlay.className = 'loading-overlay';
        document.body.appendChild(loadingOverlay);
    }
    
    loadingOverlay.innerHTML = `
        <div class="loading-content">
            <div class="loading-spinner"></div>
            <div class="loading-message">${message}</div>
        </div>
    `;
    
    loadingOverlay.classList.remove('hidden');
}

/**
 * Hide loading indicator
 */
function hideLoading(type) {
    loadingStates[type] = false;
    
    // Check if any loading state is still active
    const anyLoading = Object.values(loadingStates).some(state => state === true);
    
    if (!anyLoading) {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.classList.add('hidden');
        }
    }
}

/**
 * Show progress indicator
 */
function showProgress(type, progress, message = '') {
    let progressBar = document.getElementById(`progress-${type}`);
    if (!progressBar) {
        progressBar = document.createElement('div');
        progressBar.id = `progress-${type}`;
        progressBar.className = 'progress-bar';
        document.body.appendChild(progressBar);
    }
    
    progressBar.innerHTML = `
        <div class="progress-content">
            <div class="progress-fill" style="width: ${progress}%"></div>
            <div class="progress-text">${message || `${progress}%`}</div>
        </div>
    `;
    
    progressBar.classList.remove('hidden');
}

/**
 * Hide progress indicator
 */
function hideProgress(type) {
    const progressBar = document.getElementById(`progress-${type}`);
    if (progressBar) {
        progressBar.classList.add('hidden');
    }
}

/**
 * Show inline loading spinner
 * Enhanced with skeleton loaders
 */
function showInlineLoading(elementId, message = '', skeletonType = 'text') {
    const element = document.getElementById(elementId);
    if (element) {
        // Use skeleton loader if available
        if (window.SkeletonLoader) {
            window.SkeletonLoader.show(element, skeletonType, { lines: 3 });
        } else {
            // Fallback to old method
            element.classList.add('loading');
            if (message) {
                const loadingText = document.createElement('div');
                loadingText.className = 'loading-text';
                loadingText.textContent = message;
                element.appendChild(loadingText);
            }
        }
    }
}

/**
 * Hide inline loading spinner
 * Enhanced with skeleton loaders
 */
function hideInlineLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        // Use skeleton loader if available
        if (window.SkeletonLoader) {
            window.SkeletonLoader.hide(element);
        } else {
            // Fallback to old method
            element.classList.remove('loading');
            const loadingText = element.querySelector('.loading-text');
            if (loadingText) {
                loadingText.remove();
            }
        }
    }
}

// Export functions
if (typeof window !== 'undefined') {
    window.showLoading = showLoading;
    window.hideLoading = hideLoading;
    window.showProgress = showProgress;
    window.hideProgress = hideProgress;
    window.showInlineLoading = showInlineLoading;
    window.hideInlineLoading = hideInlineLoading;
}

