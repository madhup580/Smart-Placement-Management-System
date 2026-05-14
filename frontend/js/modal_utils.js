/**
 * Custom Modal Utilities
 * Replaces native alert() and confirm() with custom dark-themed modals
 */

// Modal state
let modalResolve = null;
let currentModalType = null;

/**
 * Show custom alert modal
 * @param {string} message - The message to display
 * @param {string} title - Optional title (default: "Alert")
 * @param {string} icon - Optional icon emoji (default: "⚠️")
 * @param {string} type - Optional type: "warning", "error", "info" (default: "warning")
 * @returns {Promise<void>}
 */
function customAlert(message, title = 'Alert', icon = '⚠️', type = 'warning') {
    // Also show toast notification for better UX
    if (window.toastManager) {
        const toastType = type === 'error' ? 'error' : type === 'success' ? 'success' : type === 'info' ? 'info' : 'warning';
        window.toastManager.show(message, toastType);
    }
    
    return new Promise((resolve) => {
        const overlay = document.getElementById('custom-modal-overlay');
        const modalIcon = document.getElementById('custom-modal-icon');
        const modalTitle = document.getElementById('custom-modal-title');
        const modalMessage = document.getElementById('custom-modal-message');
        const modalButtons = document.getElementById('custom-modal-buttons');
        const okButton = document.getElementById('custom-modal-ok');
        
        if (!overlay || !modalIcon || !modalTitle || !modalMessage || !modalButtons || !okButton) {
            // Fallback to native alert if modal elements not found
            console.warn('Custom modal elements not found, using native alert');
            alert(message);
            resolve();
            return;
        }
        
        // Set content
        modalIcon.textContent = icon;
        modalTitle.textContent = title;
        modalMessage.textContent = message;
        
        // Set icon type class
        modalIcon.className = 'custom-modal-icon';
        if (type === 'error') {
            modalIcon.classList.add('error');
        } else if (type === 'info') {
            modalIcon.classList.add('info');
        } else {
            modalIcon.classList.add('warning');
        }
        
        // Setup buttons - single OK button
        modalButtons.innerHTML = '';
        const btn = okButton.cloneNode(true);
        btn.textContent = 'OK';
        btn.className = 'custom-modal-btn custom-modal-btn-primary';
        btn.onclick = () => {
            closeCustomModal();
            resolve();
        };
        modalButtons.appendChild(btn);
        
        // Show modal
        overlay.classList.remove('hidden');
        currentModalType = 'alert';
        
        // Focus the button for keyboard accessibility
        setTimeout(() => {
            btn.focus();
        }, 100);
        
        // Handle Enter key
        const handleKeyPress = (e) => {
            if (e.key === 'Enter' || e.key === 'Escape') {
                btn.click();
            }
        };
        document.addEventListener('keydown', handleKeyPress);
        
        // Store cleanup function
        modalResolve = () => {
            document.removeEventListener('keydown', handleKeyPress);
            resolve();
        };
    });
}

/**
 * Show custom confirm modal
 * @param {string} message - The message to display
 * @param {string} title - Optional title (default: "Confirm")
 * @param {string} icon - Optional icon emoji (default: "❓")
 * @param {string} okText - Optional OK button text (default: "OK")
 * @param {string} cancelText - Optional Cancel button text (default: "Cancel")
 * @returns {Promise<boolean>} - Returns true if OK clicked, false if Cancel clicked
 */
function customConfirm(message, title = 'Confirm', icon = '❓', okText = 'OK', cancelText = 'Cancel') {
    return new Promise((resolve) => {
        const overlay = document.getElementById('custom-modal-overlay');
        const modalIcon = document.getElementById('custom-modal-icon');
        const modalTitle = document.getElementById('custom-modal-title');
        const modalMessage = document.getElementById('custom-modal-message');
        const modalButtons = document.getElementById('custom-modal-buttons');
        
        if (!overlay || !modalIcon || !modalTitle || !modalMessage || !modalButtons) {
            // Fallback to native confirm if modal elements not found
            console.warn('Custom modal elements not found, using native confirm');
            const result = confirm(message);
            resolve(result);
            return;
        }
        
        // Set content
        modalIcon.textContent = icon;
        modalTitle.textContent = title;
        modalMessage.textContent = message;
        
        // Set icon type class
        modalIcon.className = 'custom-modal-icon';
        modalIcon.classList.add('info');
        
        // Setup buttons - OK and Cancel
        modalButtons.innerHTML = '';
        
        // Cancel button
        const cancelBtn = document.createElement('button');
        cancelBtn.textContent = cancelText;
        cancelBtn.className = 'custom-modal-btn custom-modal-btn-secondary';
        cancelBtn.onclick = () => {
            closeCustomModal();
            resolve(false);
        };
        modalButtons.appendChild(cancelBtn);
        
        // OK button
        const okBtn = document.createElement('button');
        okBtn.textContent = okText;
        okBtn.className = 'custom-modal-btn custom-modal-btn-primary';
        okBtn.onclick = () => {
            closeCustomModal();
            resolve(true);
        };
        modalButtons.appendChild(okBtn);
        
        // Show modal
        overlay.classList.remove('hidden');
        currentModalType = 'confirm';
        
        // Focus the OK button for keyboard accessibility
        setTimeout(() => {
            okBtn.focus();
        }, 100);
        
        // Handle keyboard
        const handleKeyPress = (e) => {
            if (e.key === 'Enter') {
                okBtn.click();
            } else if (e.key === 'Escape') {
                cancelBtn.click();
            }
        };
        document.addEventListener('keydown', handleKeyPress);
        
        // Store cleanup function
        modalResolve = () => {
            document.removeEventListener('keydown', handleKeyPress);
        };
    });
}

/**
 * Close the custom modal
 */
function closeCustomModal() {
    const overlay = document.getElementById('custom-modal-overlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
    if (modalResolve) {
        modalResolve();
        modalResolve = null;
    }
    currentModalType = null;
}

// Close modal on overlay click (outside the modal content)
document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.getElementById('custom-modal-overlay');
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            // Only close if clicking the overlay itself, not the modal content
            if (e.target === overlay) {
                if (currentModalType === 'alert') {
                    // For alerts, clicking outside also closes
                    closeCustomModal();
                }
                // For confirms, clicking outside doesn't close (user must choose)
            }
        });
    }
});

// Export functions to global scope
window.customAlert = customAlert;
window.customConfirm = customConfirm;
window.closeCustomModal = closeCustomModal;

// Override native alert and confirm (optional - can be enabled if desired)
// Uncomment these lines to globally replace native alerts/confirms:
/*
window.alert = function(message) {
    return customAlert(message, 'Alert', '⚠️', 'warning');
};

window.confirm = function(message) {
    return customConfirm(message, 'Confirm', '❓', 'OK', 'Cancel');
};
*/

console.log('[Modal Utils] Custom modal utilities loaded');

