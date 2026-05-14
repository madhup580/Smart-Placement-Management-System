/**
 * Proctoring Mechanism for AI Virtual Interview
 * Enforces fullscreen mode and monitors tab visibility
 * Automatically terminates interview on violations
 */

let proctoringActive = false;
let fullscreenMode = false;
let tabSwitchCount = 0;
let tabSwitchWarningShown = false;
let visibilityCheckInterval = null;
let fullscreenCheckInterval = null;
let backgroundProcessCheckInterval = null;

// Track all intervals and timeouts to stop them
let trackedIntervals = new Set();
let trackedTimeouts = new Set();

// Save original functions before any overrides
let originalSetInterval = window.setInterval;
let originalSetTimeout = window.setTimeout;
let originalClearInterval = window.clearInterval;
let originalClearTimeout = window.clearTimeout;
let originalWindowOpen = window.open;
let originalGetDisplayMedia = null;

// Proctoring configuration
const PROCTORING_CONFIG = {
    MAX_TAB_SWITCHES: 1,  // Allow 1 tab switch before termination
    CHECK_INTERVAL: 500,   // Check every 500ms
    WARNING_DURATION: 3000, // Show warning for 3 seconds
    BACKGROUND_CHECK_INTERVAL: 1000 // Check for background processes every 1 second
};

/**
 * Initialize proctoring when interview starts
 */
function initializeProctoring() {
    if (proctoringActive) {
        console.log('[Proctoring] Already active');
        return;
    }
    
    console.log('[Proctoring] Initializing proctoring mechanism...');
    proctoringActive = true;
    tabSwitchCount = 0;
    tabSwitchWarningShown = false;
    
    // Request fullscreen mode
    requestFullscreen();
    
    // Monitor tab visibility
    setupVisibilityMonitoring();
    
    // Monitor fullscreen state
    setupFullscreenMonitoring();
    
    // Prevent context menu (right-click)
    preventContextMenu();
    
    // Prevent keyboard shortcuts (F11, Alt+Tab, etc.)
    preventKeyboardShortcuts();
    
    // Show proctoring notice
    showProctoringNotice();
    
    // Stop all background processes
    stopAllBackgroundProcesses();
    
    // Monitor and block background processes
    setupBackgroundProcessMonitoring();
    
    // Block other tabs/windows
    blockOtherTabs();
    
    // Prevent screen sharing
    preventScreenSharing();
}

/**
 * Request fullscreen mode
 */
function requestFullscreen() {
    const element = document.documentElement;
    
    try {
        if (element.requestFullscreen) {
            element.requestFullscreen().then(() => {
                fullscreenMode = true;
                console.log('[Proctoring] Fullscreen mode enabled');
            }).catch((error) => {
                console.error('[Proctoring] Fullscreen request failed:', error);
                showFullscreenWarning();
            });
        } else if (element.webkitRequestFullscreen) {
            element.webkitRequestFullscreen();
            fullscreenMode = true;
        } else if (element.mozRequestFullScreen) {
            element.mozRequestFullScreen();
            fullscreenMode = true;
        } else if (element.msRequestFullscreen) {
            element.msRequestFullscreen();
            fullscreenMode = true;
        } else {
            console.warn('[Proctoring] Fullscreen API not supported');
            showFullscreenWarning();
        }
    } catch (error) {
        console.error('[Proctoring] Fullscreen error:', error);
        showFullscreenWarning();
    }
}

/**
 * Setup visibility monitoring (tab switch detection)
 */
function setupVisibilityMonitoring() {
    // Listen for visibility change
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Also check window focus
    window.addEventListener('blur', handleWindowBlur);
    window.addEventListener('focus', handleWindowFocus);
    
    // Periodic check (backup)
    visibilityCheckInterval = setInterval(() => {
        if (document.hidden && proctoringActive) {
            handleTabSwitch();
        }
    }, PROCTORING_CONFIG.CHECK_INTERVAL);
}

/**
 * Setup fullscreen monitoring
 */
function setupFullscreenMonitoring() {
    // Listen for fullscreen change events
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);
    
    // Periodic check
    fullscreenCheckInterval = setInterval(() => {
        if (proctoringActive && !isFullscreen()) {
            handleFullscreenExit();
        }
    }, PROCTORING_CONFIG.CHECK_INTERVAL);
}

/**
 * Check if currently in fullscreen
 */
function isFullscreen() {
    return !!(
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement
    );
}

/**
 * Handle visibility change (tab switch)
 */
function handleVisibilityChange() {
    if (!proctoringActive) return;
    
    if (document.hidden) {
        console.warn('[Proctoring] Tab switched or window hidden');
        handleTabSwitch();
    } else {
        console.log('[Proctoring] Tab visible again');
        // User returned - but still count as violation
    }
}

/**
 * Handle window blur (lost focus)
 */
function handleWindowBlur() {
    if (!proctoringActive) return;
    
    // Small delay to avoid false positives (e.g., clicking on page)
    setTimeout(() => {
        if (document.hidden && proctoringActive) {
            handleTabSwitch();
        }
    }, 100);
}

/**
 * Handle window focus (gained focus)
 */
function handleWindowFocus() {
    if (!proctoringActive) return;
    // Just log - tab switch already handled
}

/**
 * Handle tab switch violation
 */
function handleTabSwitch() {
    if (!proctoringActive) return;
    
    tabSwitchCount++;
    console.warn(`[Proctoring] Tab switch detected (count: ${tabSwitchCount})`);
    
    if (tabSwitchCount > PROCTORING_CONFIG.MAX_TAB_SWITCHES) {
        // Terminate interview immediately
        terminateInterviewForViolation('Tab switching detected. Interview terminated due to proctoring violation.');
    } else {
        // Show warning
        showTabSwitchWarning();
    }
}

/**
 * Handle fullscreen exit
 */
function handleFullscreenExit() {
    if (!proctoringActive) return;
    
    console.warn('[Proctoring] Fullscreen exited');
    
    // Show warning and request fullscreen again
    showFullscreenWarning();
    
    // Try to re-enter fullscreen after short delay
    setTimeout(() => {
        if (proctoringActive && !isFullscreen()) {
            requestFullscreen();
            
            // If still not fullscreen after 2 seconds, terminate
            setTimeout(() => {
                if (proctoringActive && !isFullscreen()) {
                    terminateInterviewForViolation('Fullscreen mode required. Interview terminated due to proctoring violation.');
                }
            }, 2000);
        }
    }, 500);
}

/**
 * Handle fullscreen change event
 */
function handleFullscreenChange() {
    if (!proctoringActive) return;
    
    if (isFullscreen()) {
        fullscreenMode = true;
        console.log('[Proctoring] Entered fullscreen');
        hideFullscreenWarning();
    } else {
        fullscreenMode = false;
        console.warn('[Proctoring] Exited fullscreen');
        handleFullscreenExit();
    }
}

/**
 * Show tab switch warning
 */
function showTabSwitchWarning() {
    if (tabSwitchWarningShown) return;
    
    tabSwitchWarningShown = true;
    
    const warningMessage = tabSwitchCount === 1 
        ? '⚠️ Tab switch detected! Please stay on this page. Another switch will terminate the interview.'
        : '⚠️ Final warning! Tab switch detected again. Interview will be terminated.';
    
    if (typeof customAlert === 'function') {
        customAlert(
            warningMessage,
            'Proctoring Warning',
            '⚠️',
            'warning'
        );
    } else {
        alert(warningMessage);
    }
    
    // Reset warning flag after duration
    setTimeout(() => {
        tabSwitchWarningShown = false;
    }, PROCTORING_CONFIG.WARNING_DURATION);
}

/**
 * Show fullscreen warning
 */
function showFullscreenWarning() {
    const warningDiv = document.getElementById('fullscreen-warning');
    if (warningDiv) {
        warningDiv.style.display = 'block';
    }
}

/**
 * Hide fullscreen warning
 */
function hideFullscreenWarning() {
    const warningDiv = document.getElementById('fullscreen-warning');
    if (warningDiv) {
        warningDiv.style.display = 'none';
    }
}

/**
 * Terminate interview for proctoring violation
 */
async function terminateInterviewForViolation(reason) {
    if (!proctoringActive) return;
    
    console.error('[Proctoring] Terminating interview:', reason);
    
    // Stop proctoring
    stopProctoring();
    
    // Show termination message
    if (typeof customAlert === 'function') {
        await customAlert(
            reason + '\n\nThe interview has been automatically terminated.',
            'Interview Terminated',
            '❌',
            'error'
        );
    } else {
        alert(reason + '\n\nThe interview has been automatically terminated.');
    }
    
    // End interview session
    if (window.currentSessionId) {
        try {
            // Call end interview API
            const token = localStorage.getItem('token') || localStorage.getItem('authToken');
            if (token) {
                await fetch(`${window.API_BASE_URL || 'http://localhost:5000/api'}/interview/end-interview/${window.currentSessionId}`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        termination_reason: reason
                    })
                });
            }
        } catch (error) {
            console.error('[Proctoring] Error ending interview:', error);
        }
    }
    
    // Redirect to results or interview page
    setTimeout(() => {
        // Stop camera and microphone
        if (typeof cleanupInterviewMedia === 'function') {
            cleanupInterviewMedia();
        } else if (typeof stopInterviewMedia === 'function') {
            stopInterviewMedia();
        }
        
        // Show results or restart
        if (typeof showInterviewResults === 'function' && window.currentSessionId) {
            // Try to show results if available
        } else {
            // Reload interview page
            if (typeof showInterview === 'function') {
                showInterview();
            } else {
                location.reload();
            }
        }
    }, 2000);
}

/**
 * Stop all background processes
 */
function stopAllBackgroundProcesses() {
    console.log('[Proctoring] Stopping all background processes...');
    
    // Stop all tracked intervals (except our own monitoring intervals)
    trackedIntervals.forEach(intervalId => {
        if (intervalId !== visibilityCheckInterval && 
            intervalId !== fullscreenCheckInterval && 
            intervalId !== backgroundProcessCheckInterval) {
            try {
                originalClearInterval(intervalId);
                console.log('[Proctoring] Stopped background interval:', intervalId);
            } catch (e) {
                console.warn('[Proctoring] Error clearing interval:', e);
            }
        }
    });
    
    // Stop all tracked timeouts (except short UI ones)
    trackedTimeouts.forEach(timeoutId => {
        try {
            originalClearTimeout(timeoutId);
            console.log('[Proctoring] Stopped background timeout:', timeoutId);
        } catch (e) {
            console.warn('[Proctoring] Error clearing timeout:', e);
        }
    });
    trackedTimeouts.clear();
    
    // Stop all media streams except interview stream
    stopBackgroundMediaStreams();
    
    // Stop Web Workers if any
    stopWebWorkers();
    
    // Stop Service Workers if any
    stopServiceWorkers();
    
    console.log('[Proctoring] ✅ All background processes stopped');
}

/**
 * Stop background media streams (except interview stream)
 */
function stopBackgroundMediaStreams() {
    try {
        // Get all media tracks from all video/audio elements
        const allMediaElements = document.querySelectorAll('video, audio');
        allMediaElements.forEach(element => {
            // Skip interview video element
            if (element.id === 'interview-video' || element.id === 'selfie-video') {
                return;
            }
            
            if (element.srcObject) {
                const stream = element.srcObject;
                stream.getTracks().forEach(track => {
                    track.stop();
                    console.log('[Proctoring] Stopped background media track:', track.kind);
                });
                element.srcObject = null;
            }
        });
    } catch (error) {
        console.warn('[Proctoring] Error stopping background media:', error);
    }
}

/**
 * Stop Web Workers
 */
function stopWebWorkers() {
    try {
        // Note: We can't enumerate all workers, but we can prevent new ones
        // Override Worker constructor to block new workers
        if (proctoringActive && typeof Worker !== 'undefined') {
            const OriginalWorker = window.Worker;
            window.Worker = function(...args) {
                console.warn('[Proctoring] Blocked Web Worker creation during proctored interview');
                if (typeof customAlert === 'function') {
                    customAlert(
                        'Web Workers are disabled during the proctored interview.',
                        'Proctoring Violation',
                        '⚠️',
                        'warning'
                    );
                }
                throw new Error('Web Workers are disabled during proctored interview');
            };
        }
    } catch (error) {
        console.warn('[Proctoring] Error blocking Web Workers:', error);
    }
}

/**
 * Stop Service Workers
 */
function stopServiceWorkers() {
    try {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.getRegistrations().then(registrations => {
                registrations.forEach(registration => {
                    registration.unregister().then(() => {
                        console.log('[Proctoring] Unregistered service worker:', registration.scope);
                    }).catch(error => {
                        console.warn('[Proctoring] Error unregistering service worker:', error);
                    });
                });
            });
        }
    } catch (error) {
        console.warn('[Proctoring] Error stopping service workers:', error);
    }
}

/**
 * Setup background process monitoring
 */
function setupBackgroundProcessMonitoring() {
    // Override setInterval to track and block new intervals
    if (proctoringActive) {
        window.setInterval = function(...args) {
            const intervalId = originalSetInterval.apply(window, args);
            trackedIntervals.add(intervalId);
            console.warn('[Proctoring] New interval detected and will be cleared:', intervalId);
            // Clear it after a short delay to allow legitimate UI updates
            originalSetTimeout(() => {
                if (intervalId !== visibilityCheckInterval && 
                    intervalId !== fullscreenCheckInterval && 
                    intervalId !== backgroundProcessCheckInterval) {
                    originalClearInterval(intervalId);
                    trackedIntervals.delete(intervalId);
                }
            }, 100);
            return intervalId;
        };
        
        // Override setTimeout to track long timeouts
        window.setTimeout = function(...args) {
            const delay = args[1] || 0;
            // Block timeouts longer than 100ms (allow short ones for UI)
            if (delay > 100) {
                console.warn('[Proctoring] Blocked long timeout during proctored interview:', delay);
                return originalSetTimeout(() => {}, 0); // Return dummy timeout
            }
            const timeoutId = originalSetTimeout.apply(window, args);
            trackedTimeouts.add(timeoutId);
            return timeoutId;
        };
    }
    
    // Periodic check for background processes
    backgroundProcessCheckInterval = originalSetInterval(() => {
        if (!proctoringActive) return;
        
        // Check for new media streams
        stopBackgroundMediaStreams();
        
        // Check for new tabs/windows
        checkForNewTabs();
        
        // Check for screen sharing
        checkScreenSharing();
    }, PROCTORING_CONFIG.BACKGROUND_CHECK_INTERVAL);
}

/**
 * Block other tabs/windows
 */
function blockOtherTabs() {
    // Prevent window.open
    if (proctoringActive) {
        // originalWindowOpen is already saved at top level
        window.open = function(...args) {
            console.warn('[Proctoring] Blocked window.open during proctored interview');
            if (typeof customAlert === 'function') {
                customAlert(
                    'Opening new windows/tabs is not allowed during the proctored interview.',
                    'Proctoring Violation',
                    '⚠️',
                    'warning'
                );
            }
            return null;
        };
    }
    
    // Monitor for window close attempts
    window.addEventListener('beforeunload', (e) => {
        if (proctoringActive) {
            e.preventDefault();
            e.returnValue = 'You cannot close this window during the proctored interview.';
            return e.returnValue;
        }
    });
}

/**
 * Check for new tabs/windows
 */
function checkForNewTabs() {
    try {
        // Check if focus is on this window
        if (!document.hasFocus() && proctoringActive) {
            handleTabSwitch();
        }
    } catch (error) {
        console.warn('[Proctoring] Error checking for new tabs:', error);
    }
}

/**
 * Prevent screen sharing
 */
function preventScreenSharing() {
    // Override getDisplayMedia to prevent screen sharing
    if (proctoringActive && navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
        originalGetDisplayMedia = navigator.mediaDevices.getDisplayMedia;
        navigator.mediaDevices.getDisplayMedia = function(...args) {
            console.warn('[Proctoring] Blocked screen sharing during proctored interview');
            if (typeof customAlert === 'function') {
                customAlert(
                    'Screen sharing is not allowed during the proctored interview.',
                    'Proctoring Violation',
                    '⚠️',
                    'warning'
                );
            }
            return Promise.reject(new Error('Screen sharing is disabled during proctored interview'));
        };
    }
}

/**
 * Check for screen sharing
 */
function checkScreenSharing() {
    // Monitor for screen sharing attempts
    // This is limited by browser security, but we can prevent new screen sharing
    // Note: We can't detect existing screen sharing due to browser security restrictions
}

/**
 * Stop proctoring
 */
function stopProctoring() {
    if (!proctoringActive) return;
    
    console.log('[Proctoring] Stopping proctoring...');
    proctoringActive = false;
    fullscreenMode = false;
    
    // Restore original functions
    window.setInterval = originalSetInterval;
    window.setTimeout = originalSetTimeout;
    window.clearInterval = originalClearInterval;
    window.clearTimeout = originalClearTimeout;
    
    // Restore window.open
    if (originalWindowOpen) {
        window.open = originalWindowOpen;
    }
    
    // Restore getDisplayMedia
    if (originalGetDisplayMedia && navigator.mediaDevices) {
        navigator.mediaDevices.getDisplayMedia = originalGetDisplayMedia;
        originalGetDisplayMedia = null;
    }
    
    // Clear intervals
    if (visibilityCheckInterval) {
        originalClearInterval(visibilityCheckInterval);
        visibilityCheckInterval = null;
    }
    
    if (fullscreenCheckInterval) {
        originalClearInterval(fullscreenCheckInterval);
        fullscreenCheckInterval = null;
    }
    
    if (backgroundProcessCheckInterval) {
        originalClearInterval(backgroundProcessCheckInterval);
        backgroundProcessCheckInterval = null;
    }
    
    // Clear all tracked intervals and timeouts
    trackedIntervals.forEach(intervalId => {
        try {
            originalClearInterval(intervalId);
        } catch (e) {
            // Ignore errors
        }
    });
    trackedIntervals.clear();
    
    trackedTimeouts.forEach(timeoutId => {
        try {
            originalClearTimeout(timeoutId);
        } catch (e) {
            // Ignore errors
        }
    });
    trackedTimeouts.clear();
    
    // Remove event listeners
    document.removeEventListener('visibilitychange', handleVisibilityChange);
    window.removeEventListener('blur', handleWindowBlur);
    window.removeEventListener('focus', handleWindowFocus);
    window.removeEventListener('beforeunload', () => {});
    document.removeEventListener('fullscreenchange', handleFullscreenChange);
    document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
    document.removeEventListener('MSFullscreenChange', handleFullscreenChange);
    
    // Exit fullscreen if still in it
    if (isFullscreen()) {
        try {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            } else if (document.mozCancelFullScreen) {
                document.mozCancelFullScreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            }
        } catch (error) {
            console.error('[Proctoring] Error exiting fullscreen:', error);
        }
    }
    
    // Hide warnings
    hideFullscreenWarning();
    hideProctoringNotice();
}

/**
 * Prevent context menu (right-click)
 */
function preventContextMenu() {
    document.addEventListener('contextmenu', (e) => {
        if (proctoringActive) {
            e.preventDefault();
            showProctoringViolation('Right-click is disabled during the interview.');
            return false;
        }
    }, false);
}

/**
 * Prevent keyboard shortcuts
 */
function preventKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        if (!proctoringActive) return;
        
        // Prevent F11 (fullscreen toggle)
        if (e.key === 'F11') {
            e.preventDefault();
            showProctoringViolation('Keyboard shortcuts are disabled during the interview.');
            return false;
        }
        
        // Prevent Alt+Tab (Alt key combinations)
        if (e.altKey && (e.key === 'Tab' || e.keyCode === 9)) {
            e.preventDefault();
            showProctoringViolation('Alt+Tab is disabled during the interview.');
            return false;
        }
        
        // Prevent Ctrl+Shift+T (reopen closed tab)
        if (e.ctrlKey && e.shiftKey && e.key === 'T') {
            e.preventDefault();
            showProctoringViolation('Keyboard shortcuts are disabled during the interview.');
            return false;
        }
        
        // Prevent Ctrl+W (close tab)
        if (e.ctrlKey && e.key === 'w') {
            e.preventDefault();
            showProctoringViolation('Closing tab is disabled during the interview.');
            return false;
        }
    }, false);
}

/**
 * Show proctoring violation warning
 */
function showProctoringViolation(message) {
    if (typeof customAlert === 'function') {
        customAlert(
            message + '\n\nRepeated violations may result in interview termination.',
            'Proctoring Violation',
            '⚠️',
            'warning'
        );
    } else {
        alert(message);
    }
}

/**
 * Show proctoring notice
 */
function showProctoringNotice() {
    // Create or show proctoring notice banner
    let noticeDiv = document.getElementById('proctoring-notice');
    if (!noticeDiv) {
        noticeDiv = document.createElement('div');
        noticeDiv.id = 'proctoring-notice';
        noticeDiv.className = 'proctoring-notice';
        noticeDiv.innerHTML = `
            <div class="proctoring-notice-content">
                <div class="proctoring-icon">🔒</div>
                <div class="proctoring-text">
                    <strong>Proctored Interview Active</strong>
                    <small>Fullscreen mode required. Tab switching monitored. All background processes stopped.</small>
                </div>
            </div>
        `;
        document.body.appendChild(noticeDiv);
    }
    noticeDiv.style.display = 'block';
}

/**
 * Hide proctoring notice
 */
function hideProctoringNotice() {
    const noticeDiv = document.getElementById('proctoring-notice');
    if (noticeDiv) {
        noticeDiv.style.display = 'none';
    }
}

// Export functions
if (typeof window !== 'undefined') {
    window.initializeProctoring = initializeProctoring;
    window.stopProctoring = stopProctoring;
    window.isProctoringActive = () => proctoringActive;
    window.requestFullscreen = requestFullscreen; // Export for button onclick
}

