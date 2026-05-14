/**
 * Centralized Error Handler
 * Prevents blank pages and provides graceful error recovery
 */

class ErrorHandler {
    constructor() {
        this.errorCount = 0;
        this.maxErrors = 5;
    }

    /**
     * Handle errors gracefully with fallbacks
     */
    handle(error, context = 'Unknown', fallback = null) {
        this.errorCount++;
        console.error(`[ErrorHandler] ${context}:`, error);

        // Prevent error loops
        if (this.errorCount > this.maxErrors) {
            console.error('[ErrorHandler] Too many errors, showing safe fallback');
            this.showSafeFallback();
            return;
        }

        // Try fallback if provided
        if (fallback && typeof fallback === 'function') {
            try {
                fallback();
            } catch (fallbackError) {
                console.error('[ErrorHandler] Fallback also failed:', fallbackError);
                this.showSafeFallback();
            }
        } else {
            this.showSafeFallback();
        }
    }

    /**
     * Show safe fallback UI
     */
    showSafeFallback() {
        const mainApp = document.getElementById('main-app');
        if (mainApp) {
            mainApp.innerHTML = `
                <div style="padding: 40px; text-align: center;">
                    <h2>⚠️ Something went wrong</h2>
                    <p>We're having trouble loading this page. Please try:</p>
                    <ul style="text-align: left; display: inline-block;">
                        <li>Refreshing the page</li>
                        <li>Checking your internet connection</li>
                        <li>Clearing your browser cache</li>
                    </ul>
                    <button onclick="window.location.reload()" class="btn-primary" style="margin-top: 20px;">
                        Reload Page
                    </button>
                </div>
            `;
        }
    }

    /**
     * Reset error count
     */
    reset() {
        this.errorCount = 0;
    }
}

// Export singleton
window.errorHandler = new ErrorHandler();
