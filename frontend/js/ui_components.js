/**
 * UI/UX Components
 * Skeleton loaders, toast notifications, undo actions, keyboard navigation, accessibility
 */

// ============================================================================
// 1. SKELETON LOADERS WITH SHIMMER EFFECTS
// ============================================================================

class SkeletonLoader {
    /**
     * Create a skeleton loader element
     * @param {string} type - 'text', 'circle', 'rect', 'card', 'table'
     * @param {object} options - { width, height, lines, className }
     */
    static create(type = 'text', options = {}) {
        const skeleton = document.createElement('div');
        skeleton.className = `skeleton-loader skeleton-${type} ${options.className || ''}`;
        skeleton.setAttribute('aria-label', 'Loading content');
        skeleton.setAttribute('role', 'status');
        
        switch (type) {
            case 'text':
                return SkeletonLoader._createTextSkeleton(skeleton, options);
            case 'circle':
                return SkeletonLoader._createCircleSkeleton(skeleton, options);
            case 'rect':
                return SkeletonLoader._createRectSkeleton(skeleton, options);
            case 'card':
                return SkeletonLoader._createCardSkeleton(skeleton, options);
            case 'table':
                return SkeletonLoader._createTableSkeleton(skeleton, options);
            default:
                return skeleton;
        }
    }
    
    static _createTextSkeleton(element, options) {
        const lines = options.lines || 3;
        for (let i = 0; i < lines; i++) {
            const line = document.createElement('div');
            line.className = 'skeleton-line';
            line.style.width = i === lines - 1 ? '60%' : '100%';
            element.appendChild(line);
        }
        return element;
    }
    
    static _createCircleSkeleton(element, options) {
        element.style.width = options.width || '50px';
        element.style.height = options.height || '50px';
        element.style.borderRadius = '50%';
        return element;
    }
    
    static _createRectSkeleton(element, options) {
        element.style.width = options.width || '100%';
        element.style.height = options.height || '20px';
        return element;
    }
    
    static _createCardSkeleton(element, options) {
        const header = document.createElement('div');
        header.className = 'skeleton-line';
        header.style.width = '40%';
        header.style.marginBottom = '16px';
        element.appendChild(header);
        
        for (let i = 0; i < 3; i++) {
            const line = document.createElement('div');
            line.className = 'skeleton-line';
            line.style.width = i === 2 ? '70%' : '100%';
            line.style.marginBottom = '8px';
            element.appendChild(line);
        }
        return element;
    }
    
    static _createTableSkeleton(element, options) {
        const rows = options.rows || 5;
        const cols = options.cols || 4;
        
        for (let i = 0; i < rows; i++) {
            const row = document.createElement('div');
            row.className = 'skeleton-table-row';
            for (let j = 0; j < cols; j++) {
                const cell = document.createElement('div');
                cell.className = 'skeleton-line';
                cell.style.width = `${100 / cols}%`;
                row.appendChild(cell);
            }
            element.appendChild(row);
        }
        return element;
    }
    
    /**
     * Replace content with skeleton loader
     * @param {HTMLElement} container - Container to show skeleton in
     * @param {string} type - Skeleton type
     * @param {object} options - Options
     */
    static show(container, type = 'text', options = {}) {
        if (!container) return;
        
        // Store original content
        if (!container.dataset.originalContent) {
            container.dataset.originalContent = container.innerHTML;
        }
        
        container.innerHTML = '';
        const skeleton = SkeletonLoader.create(type, options);
        container.appendChild(skeleton);
        container.classList.add('skeleton-container');
    }
    
    /**
     * Hide skeleton and restore content
     * @param {HTMLElement} container - Container to restore
     */
    static hide(container) {
        if (!container) return;
        
        container.classList.remove('skeleton-container');
        if (container.dataset.originalContent) {
            container.innerHTML = container.dataset.originalContent;
            delete container.dataset.originalContent;
        }
    }
}

// ============================================================================
// 2. TOAST NOTIFICATIONS
// ============================================================================

class ToastManager {
    constructor() {
        this.container = null;
        this.toasts = [];
        this.maxToasts = 5;
        this.init();
    }
    
    init() {
        // Create toast container
        this.container = document.createElement('div');
        this.container.id = 'toast-container';
        this.container.className = 'toast-container';
        this.container.setAttribute('aria-live', 'polite');
        this.container.setAttribute('aria-atomic', 'false');
        document.body.appendChild(this.container);
    }
    
    /**
     * Show a toast notification
     * @param {string} message - Toast message
     * @param {string} type - 'success', 'error', 'warning', 'info'
     * @param {object} options - { duration, action, onAction }
     */
    show(message, type = 'info', options = {}) {
        const toast = this._createToast(message, type, options);
        this.container.appendChild(toast);
        this.toasts.push(toast);
        
        // Limit number of toasts
        if (this.toasts.length > this.maxToasts) {
            const oldest = this.toasts.shift();
            this._removeToast(oldest);
        }
        
        // Animate in
        requestAnimationFrame(() => {
            toast.classList.add('toast-show');
        });
        
        // Auto remove
        const duration = options.duration || (type === 'error' ? 5000 : 3000);
        setTimeout(() => {
            this._removeToast(toast);
        }, duration);
        
        return toast;
    }
    
    _createToast(message, type, options) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        
        // Icon
        const icon = this._getIcon(type);
        toast.innerHTML = `
            <div class="toast-icon">${icon}</div>
            <div class="toast-content">
                <div class="toast-message">${message}</div>
                ${options.action ? `<button class="toast-action" aria-label="${options.action}">${options.action}</button>` : ''}
            </div>
            <button class="toast-close" aria-label="Close notification" onclick="window.toastManager._removeToast(this.parentElement)">
                <span aria-hidden="true">&times;</span>
            </button>
        `;
        
        // Action handler
        if (options.action && options.onAction) {
            const actionBtn = toast.querySelector('.toast-action');
            actionBtn.addEventListener('click', () => {
                options.onAction();
                this._removeToast(toast);
            });
        }
        
        return toast;
    }
    
    _getIcon(type) {
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || icons.info;
    }
    
    _removeToast(toast) {
        if (!toast || !toast.parentElement) return;
        
        toast.classList.add('toast-hide');
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
            const index = this.toasts.indexOf(toast);
            if (index > -1) {
                this.toasts.splice(index, 1);
            }
        }, 300);
    }
    
    success(message, options = {}) {
        return this.show(message, 'success', options);
    }
    
    error(message, options = {}) {
        return this.show(message, 'error', options);
    }
    
    warning(message, options = {}) {
        return this.show(message, 'warning', options);
    }
    
    info(message, options = {}) {
        return this.show(message, 'info', options);
    }
}

// ============================================================================
// 3. UNDO ACTION SYSTEM
// ============================================================================

class UndoManager {
    constructor() {
        this.history = [];
        this.maxHistory = 50;
        this.currentIndex = -1;
    }
    
    /**
     * Register an action for undo
     * @param {string} description - Action description
     * @param {function} undoFn - Function to undo the action
     * @param {function} redoFn - Function to redo the action (optional)
     */
    register(description, undoFn, redoFn = null) {
        // Remove any future history if we're in the middle
        if (this.currentIndex < this.history.length - 1) {
            this.history = this.history.slice(0, this.currentIndex + 1);
        }
        
        const action = {
            description,
            undo: undoFn,
            redo: redoFn,
            timestamp: Date.now()
        };
        
        this.history.push(action);
        this.currentIndex = this.history.length - 1;
        
        // Limit history size
        if (this.history.length > this.maxHistory) {
            this.history.shift();
            this.currentIndex--;
        }
        
        // Show toast notification
        if (window.toastManager) {
            window.toastManager.info(description, {
                action: 'Undo',
                onAction: () => this.undo()
            });
        }
    }
    
    /**
     * Undo last action
     */
    undo() {
        if (this.currentIndex < 0) {
            if (window.toastManager) {
                window.toastManager.warning('Nothing to undo');
            }
            return false;
        }
        
        const action = this.history[this.currentIndex];
        if (action.undo) {
            action.undo();
            this.currentIndex--;
            
            if (window.toastManager) {
                window.toastManager.info(`Undone: ${action.description}`, {
                    action: 'Redo',
                    onAction: () => this.redo()
                });
            }
            return true;
        }
        return false;
    }
    
    /**
     * Redo last undone action
     */
    redo() {
        if (this.currentIndex >= this.history.length - 1) {
            if (window.toastManager) {
                window.toastManager.warning('Nothing to redo');
            }
            return false;
        }
        
        this.currentIndex++;
        const action = this.history[this.currentIndex];
        if (action.redo) {
            action.redo();
            
            if (window.toastManager) {
                window.toastManager.info(`Redone: ${action.description}`, {
                    action: 'Undo',
                    onAction: () => this.undo()
                });
            }
            return true;
        }
        return false;
    }
    
    /**
     * Clear history
     */
    clear() {
        this.history = [];
        this.currentIndex = -1;
    }
}

// ============================================================================
// 4. KEYBOARD NAVIGATION
// ============================================================================

class KeyboardNavigation {
    constructor() {
        this.shortcuts = new Map();
        this.focusableSelectors = 'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])';
        this.init();
    }
    
    init() {
        // Global keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyDown(e));
        
        // Focus trap for modals
        document.addEventListener('keydown', (e) => this.handleFocusTrap(e));
        
        // Register default shortcuts
        this.registerDefaultShortcuts();
    }
    
    /**
     * Register a keyboard shortcut
     * @param {string} key - Key combination (e.g., 'Ctrl+S', 'Escape')
     * @param {function} handler - Handler function
     * @param {object} options - { preventDefault, description }
     */
    register(key, handler, options = {}) {
        const normalized = this._normalizeKey(key);
        this.shortcuts.set(normalized, { handler, options });
    }
    
    _normalizeKey(key) {
        return key.toLowerCase().replace(/\s+/g, '');
    }
    
    handleKeyDown(e) {
        const key = this._getKeyString(e);
        const normalized = this._normalizeKey(key);
        
        const shortcut = this.shortcuts.get(normalized);
        if (shortcut) {
            if (shortcut.options.preventDefault !== false) {
                e.preventDefault();
            }
            shortcut.handler(e);
        }
    }
    
    _getKeyString(e) {
        const parts = [];
        if (e.ctrlKey) parts.push('Ctrl');
        if (e.altKey) parts.push('Alt');
        if (e.shiftKey) parts.push('Shift');
        if (e.metaKey) parts.push('Meta');
        
        const key = e.key === ' ' ? 'Space' : e.key;
        parts.push(key);
        
        return parts.join('+');
    }
    
    registerDefaultShortcuts() {
        // Escape to close modals
        this.register('Escape', () => {
            const modals = document.querySelectorAll('.custom-modal.show');
            modals.forEach(modal => {
                const closeBtn = modal.querySelector('.modal-close, [data-dismiss="modal"]');
                if (closeBtn) closeBtn.click();
            });
        });
        
        // Ctrl+Z for undo
        this.register('Ctrl+Z', (e) => {
            if (window.undoManager) {
                window.undoManager.undo();
            }
        });
        
        // Ctrl+Y or Ctrl+Shift+Z for redo
        this.register('Ctrl+Y', (e) => {
            if (window.undoManager) {
                window.undoManager.redo();
            }
        });
        
        this.register('Ctrl+Shift+Z', (e) => {
            if (window.undoManager) {
                window.undoManager.redo();
            }
        });
        
        // Ctrl+K for search (if search exists)
        this.register('Ctrl+K', () => {
            const searchInput = document.querySelector('input[type="search"], #search-input');
            if (searchInput) {
                searchInput.focus();
            }
        });
    }
    
    handleFocusTrap(e) {
        // Focus trap for modals
        if (e.key === 'Tab') {
            const modal = document.querySelector('.custom-modal.show');
            if (!modal) return;
            
            const focusableElements = modal.querySelectorAll(this.focusableSelectors);
            if (focusableElements.length === 0) return;
            
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];
            
            if (e.shiftKey) {
                // Shift+Tab
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                }
            } else {
                // Tab
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        }
    }
    
    /**
     * Get all registered shortcuts (for help menu)
     */
    getShortcuts() {
        const shortcuts = [];
        this.shortcuts.forEach((value, key) => {
            shortcuts.push({
                key,
                description: value.options.description || ''
            });
        });
        return shortcuts;
    }
}

// ============================================================================
// 5. ACCESSIBILITY HELPERS
// ============================================================================

class AccessibilityHelper {
    /**
     * Add ARIA labels to elements
     * @param {HTMLElement} element - Element to label
     * @param {string} label - ARIA label
     */
    static setLabel(element, label) {
        if (!element) return;
        element.setAttribute('aria-label', label);
    }
    
    /**
     * Announce message to screen readers
     * @param {string} message - Message to announce
     * @param {string} priority - 'polite' or 'assertive'
     */
    static announce(message, priority = 'polite') {
        const announcement = document.createElement('div');
        announcement.setAttribute('role', 'status');
        announcement.setAttribute('aria-live', priority);
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            announcement.remove();
        }, 1000);
    }
    
    /**
     * Make element focusable
     * @param {HTMLElement} element - Element to make focusable
     * @param {number} tabIndex - Tab index (default: 0)
     */
    static makeFocusable(element, tabIndex = 0) {
        if (!element) return;
        element.setAttribute('tabindex', tabIndex);
    }
    
    /**
     * Add skip link for keyboard navigation
     * @param {string} targetId - ID of target element
     * @param {string} text - Link text
     */
    static addSkipLink(targetId, text = 'Skip to main content') {
        const skipLink = document.createElement('a');
        skipLink.href = `#${targetId}`;
        skipLink.textContent = text;
        skipLink.className = 'skip-link';
        skipLink.setAttribute('aria-label', text);
        
        document.body.insertBefore(skipLink, document.body.firstChild);
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUIComponents);
} else {
    initUIComponents();
}

function initUIComponents() {
    // Initialize Toast Manager
    window.toastManager = new ToastManager();
    
    // Initialize Undo Manager
    window.undoManager = new UndoManager();
    
    // Initialize Keyboard Navigation
    window.keyboardNav = new KeyboardNavigation();
    
    // Add skip link
    const mainContent = document.getElementById('main-app') || document.querySelector('main');
    if (mainContent) {
        AccessibilityHelper.addSkipLink(mainContent.id || 'main-content', 'Skip to main content');
    }
    
    // Expose global helpers
    window.SkeletonLoader = SkeletonLoader;
    window.AccessibilityHelper = AccessibilityHelper;
    
    console.log('[UI Components] Initialized: Toast, Undo, Keyboard Navigation, Accessibility');
}

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        SkeletonLoader,
        ToastManager,
        UndoManager,
        KeyboardNavigation,
        AccessibilityHelper
    };
}
