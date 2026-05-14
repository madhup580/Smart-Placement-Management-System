/**
 * Device Detection Module
 * Captures frames from video element and sends to backend for device detection
 */

// Immediately log that script is loading
console.log('[Device Detection] Script file is executing...');

// Wrap critical parts in try-catch to prevent silent failures
try {

// Export function placeholders to window IMMEDIATELY (before function definition)
// This ensures they're available even if script execution is interrupted
if (typeof window !== 'undefined') {
    // Initialize as undefined (not null) to allow proper assignment later
    window.startDeviceDetection = undefined;
    window.stopDeviceDetection = undefined;
    window._startDeviceDetection = undefined;
    window._stopDeviceDetection = undefined;
    console.log('[Device Detection] Window placeholders initialized');
}

// Device detection state
let deviceDetectionActive = false;
let detectionInterval = null;
let warningCount = 0;
let lastDetectionTime = null;
let detectionTimeout = null;
const MAX_WARNINGS = 3;
const DETECTION_INTERVAL = 1500; // Check every 1.5 seconds (faster real-time detection)
const WARNING_DISAPPEAR_DELAY = 2000; // Warning disappears 2 seconds after device removed

// API base URL - use window.API_BASE_URL if available (set by api.js), otherwise get it
// Don't declare const API_BASE_URL to avoid conflict with api.js
function getDeviceDetectionApiUrl() {
    // First, check if api.js has already set it
    if (window.API_BASE_URL) {
        return window.API_BASE_URL;
    }
    
    // If api.js function is available, use it
    if (typeof window.getApiBaseUrl === 'function') {
        return window.getApiBaseUrl();
    }
    
    // Fallback: get from config script tag
    const configScript = document.getElementById('api-config');
    if (configScript && configScript.dataset.apiUrl) {
        return configScript.dataset.apiUrl;
    }
    
    // Final fallback
    return 'http://localhost:5000/api';
}

// Use a function to get API URL instead of a const to avoid conflicts
// This will be called when needed, not at module load time
let _deviceDetectionApiUrl = null;
function getDeviceDetectionApiUrlCached() {
    if (!_deviceDetectionApiUrl) {
        _deviceDetectionApiUrl = getDeviceDetectionApiUrl();
    }
    return _deviceDetectionApiUrl;
}

console.log('[Device Detection] API URL getter initialized');

/**
 * Start device detection monitoring
 */
function startDeviceDetection(sessionId) {
    // Export to window immediately when function is called (ensures it's available)
    if (typeof window !== 'undefined' && (!window.startDeviceDetection || typeof window.startDeviceDetection !== 'function')) {
        window.startDeviceDetection = startDeviceDetection;
        console.log('[Device Detection] Function exported during execution');
    }
    if (deviceDetectionActive) {
        console.log('[Device Detection] Already active');
        return;
    }
    
    console.log('[Device Detection] Starting device detection for session:', sessionId);
    
    const videoElement = document.getElementById('interview-video');
    if (!videoElement) {
        console.error('[Device Detection] Video element not found');
        return;
    }
    
    if (!videoElement.srcObject) {
        console.warn('[Device Detection] Video srcObject not available yet, will retry...');
        // Retry after a short delay
        setTimeout(() => startDeviceDetection(sessionId), 1000);
        return;
    }
    
    deviceDetectionActive = true;
    warningCount = 0;
    lastDetectionTime = null;
    
    console.log('[Device Detection] Device detection monitoring starting...');
    
    // Check detection status first
    checkDetectionStatus().then(available => {
        console.log('[Device Detection] Service available:', available);
        if (!available) {
            console.warn('[Device Detection] Service not available - continuing anyway for testing');
            // Continue anyway - status check might fail but detection could still work
        }
        
        console.log('[Device Detection] Starting periodic detection every', DETECTION_INTERVAL, 'ms');
        
        // Start periodic frame capture and detection
        detectionInterval = setInterval(() => {
            if (deviceDetectionActive) {
                captureAndDetect(sessionId);
            }
        }, DETECTION_INTERVAL);
        
        // Initial detection after a short delay to ensure video is ready
        setTimeout(() => {
            if (deviceDetectionActive) {
                captureAndDetect(sessionId);
            }
        }, 1000);
    }).catch(error => {
        console.error('[Device Detection] Error checking status:', error);
        // Continue anyway - might be auth issue but detection endpoint might still work
        console.log('[Device Detection] Continuing detection despite status check error');
        
        // Start periodic frame capture and detection anyway
        detectionInterval = setInterval(() => {
            if (deviceDetectionActive) {
                captureAndDetect(sessionId);
            }
        }, DETECTION_INTERVAL);
        
        setTimeout(() => {
            if (deviceDetectionActive) {
                captureAndDetect(sessionId);
            }
        }, 1000);
    });
}

/**
 * Stop device detection monitoring
 */
function stopDeviceDetection() {
    if (!deviceDetectionActive) {
        return;
    }
    
    deviceDetectionActive = false;
    
    if (detectionInterval) {
        clearInterval(detectionInterval);
        detectionInterval = null;
    }
    
    if (detectionTimeout) {
        clearTimeout(detectionTimeout);
        detectionTimeout = null;
    }
    
    // Hide warning panel
    hideDeviceWarning();
    
    console.log('Device detection stopped');
}

// Export functions IMMEDIATELY after they're defined (before any other code runs)
// This ensures they're available even if later code fails
(function exportFunctionsImmediately() {
    try {
        if (typeof startDeviceDetection === 'function' && typeof stopDeviceDetection === 'function') {
            window.startDeviceDetection = startDeviceDetection;
            window.stopDeviceDetection = stopDeviceDetection;
            window._startDeviceDetection = startDeviceDetection;
            window._stopDeviceDetection = stopDeviceDetection;
            if (typeof globalThis !== 'undefined') {
                globalThis.startDeviceDetection = startDeviceDetection;
                globalThis.stopDeviceDetection = stopDeviceDetection;
            }
            console.log('[Device Detection] ✅ Functions exported immediately after definition');
        } else {
            console.error('[Device Detection] ❌ Functions not defined when trying to export immediately');
            console.error('[Device Detection] startDeviceDetection type:', typeof startDeviceDetection);
            console.error('[Device Detection] stopDeviceDetection type:', typeof stopDeviceDetection);
        }
    } catch (e) {
        console.error('[Device Detection] ❌ Error exporting functions immediately:', e);
    }
})();

/**
 * Check if device detection service is available
 */
async function checkDetectionStatus() {
    try {
        const response = await fetch(`${getDeviceDetectionApiUrlCached()}/device-detection/status`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('Device detection status:', data);
            return data.available === true;
        }
        
        return false;
    } catch (error) {
        console.error('Error checking detection status:', error);
        return false;
    }
}

/**
 * Capture frame from video element and send for detection
 */
async function captureAndDetect(sessionId) {
    if (!deviceDetectionActive) {
        console.log('[Device Detection] Not active, skipping frame capture');
        return;
    }
    
    const videoElement = document.getElementById('interview-video');
    if (!videoElement) {
        console.warn('[Device Detection] Video element not found');
        return;
    }
    
    if (!videoElement.srcObject) {
        console.warn('[Device Detection] Video srcObject not available');
        return;
    }
    
    if (videoElement.readyState < 2) {
        console.log('[Device Detection] Video not ready, readyState:', videoElement.readyState);
        return;
    }
    
    try {
        // Capture frame to canvas
        const canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth || 640;
        canvas.height = videoElement.videoHeight || 480;
        
        if (canvas.width === 0 || canvas.height === 0) {
            console.warn('[Device Detection] Invalid video dimensions:', canvas.width, canvas.height);
            return;
        }
        
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        
        // Convert to base64 (use lower quality for faster transmission)
        const frameData = canvas.toDataURL('image/jpeg', 0.7);
        
        console.log('[Device Detection] Frame captured, sending for detection...', {
            width: canvas.width,
            height: canvas.height,
            dataLength: frameData.length
        });
        
        // Send to backend for detection
        await sendFrameForDetection(frameData, sessionId);
        
    } catch (error) {
        console.error('[Device Detection] Error capturing frame:', error);
    }
}

/**
 * Send frame to backend for device detection
 */
async function sendFrameForDetection(frameData, sessionId) {
    try {
        const token = localStorage.getItem('authToken');
        if (!token) {
            console.warn('[Device Detection] No auth token available');
            return;
        }
        
        console.log('[Device Detection] Sending frame to backend...');
        
        const response = await fetch(`${getDeviceDetectionApiUrlCached()}/device-detection/detect`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                frame: frameData,
                session_id: sessionId
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[Device Detection] Detection failed:', {
                status: response.status,
                statusText: response.statusText,
                error: errorText.substring(0, 200)
            });
            // Don't throw - just log and continue trying
            return;
        }
        
        const result = await response.json();
        
        console.log('[Device Detection] Detection result:', {
            detected: result.detected,
            count: result.count,
            devices: result.devices ? result.devices.map(d => d.class || d) : [],
            error: result.error
        });
        
        // Handle detection result
        handleDetectionResult(result);
        
    } catch (error) {
        console.error('[Device Detection] Error sending frame for detection:', error);
    }
}

/**
 * Handle detection result from backend
 */
function handleDetectionResult(result) {
    if (!result) {
        return;
    }
    
    // Clear previous timeout
    if (detectionTimeout) {
        clearTimeout(detectionTimeout);
        detectionTimeout = null;
    }
    
    if (result.detected && result.count > 0) {
        // Device detected
        warningCount++;
        lastDetectionTime = new Date();
        
        const devices = result.devices.map(d => d.class).join(', ');
        
        // Show warning
        showDeviceWarning(devices, warningCount);
        
        // Log detection
        logDeviceDetection(result);
        
        // Check if max warnings reached
        if (warningCount >= MAX_WARNINGS) {
            // Auto-end interview
            setTimeout(() => {
                endInterviewDueToDevice();
            }, 1000);
        }
    } else {
        // No device detected - hide warning after delay
        if (lastDetectionTime) {
            detectionTimeout = setTimeout(() => {
                hideDeviceWarning();
            }, WARNING_DISAPPEAR_DELAY);
        } else {
            hideDeviceWarning();
        }
    }
}

/**
 * Show device warning panel
 */
function showDeviceWarning(devices, count) {
    const warningPanel = document.getElementById('device-warning-panel');
    if (!warningPanel) {
        return;
    }
    
    const warningText = document.getElementById('device-warning-text');
    const warningCount = document.getElementById('device-warning-count');
    
    if (warningText) {
        warningText.textContent = `⚠️ Electronic device detected: ${devices}`;
    }
    
    if (warningCount) {
        warningCount.textContent = `Warning ${count} of ${MAX_WARNINGS}`;
        
        // Change color based on count
        if (count >= MAX_WARNINGS) {
            warningCount.style.color = '#ff4444';
            warningCount.textContent = `⚠️ Final Warning - Interview will end!`;
        } else if (count >= 2) {
            warningCount.style.color = '#ff8800';
        } else {
            warningCount.style.color = '#ffaa00';
        }
    }
    
    warningPanel.classList.add('active');
    warningPanel.classList.remove('hidden');
}

/**
 * Hide device warning panel
 */
function hideDeviceWarning() {
    const warningPanel = document.getElementById('device-warning-panel');
    if (warningPanel) {
        warningPanel.classList.remove('active');
        // Don't hide immediately - let CSS transition handle it
        setTimeout(() => {
            if (!warningPanel.classList.contains('active')) {
                warningPanel.classList.add('hidden');
            }
        }, 300);
    }
}

/**
 * Log device detection to console and potentially backend
 */
function logDeviceDetection(result) {
    const timestamp = new Date().toISOString();
    console.warn(`[Device Detection] ${timestamp}: ${result.count} device(s) detected:`, result.devices);
    
    // Could send to backend logging endpoint here if needed
}

/**
 * End interview due to device detection
 */
async function endInterviewDueToDevice() {
    stopDeviceDetection();
    
    // Show warning notification first
    if (typeof customAlert === 'function') {
        // Show warning modal (don't await - show it and continue)
        customAlert(
            'Multiple electronic devices were detected during the interview.\n' +
            'The interview has been automatically ended for security reasons.\n\n' +
            'Please contact support if you believe this is an error.',
            'Interview Terminated',
            '⚠️',
            'error'
        );
    } else {
        // Fallback to native alert if custom modal not available
        alert(
            '⚠️ Interview Terminated\n\n' +
            'Multiple electronic devices were detected during the interview.\n' +
            'The interview has been automatically ended for security reasons.\n\n' +
            'Please contact support if you believe this is an error.'
        );
    }
    
    // Automatically end interview without asking for confirmation
    // Give a short delay to show the warning, then automatically end
    setTimeout(() => {
        // Close the modal if it's still open
        if (typeof closeCustomModal === 'function') {
            closeCustomModal();
        }
        
        // End the interview automatically
        if (typeof endInterviewAutomatically === 'function') {
            endInterviewAutomatically();
        } else if (typeof showInterviewResults === 'function') {
            // Create a result object indicating termination
            showInterviewResults({
                interview_completed: true,
                final_score: 0,
                termination_reason: 'Device detection violation'
            });
        }
    }, 2000); // 2 second delay to show warning, then auto-end
}

/**
 * Show detection status message
 */
function showDetectionStatus(message, type = 'info') {
    console.log(`[Device Detection Status] ${type.toUpperCase()}: ${message}`);
    // Could show a toast notification here
}

// CRITICAL: Export functions for global access - MUST be at the end of the file
// Use IIFE to ensure clean execution context
(function forceExportFunctions() {
    'use strict';
    
    try {
        // First, delete any existing properties that might block assignment
        if (window.hasOwnProperty('startDeviceDetection')) {
            try {
                delete window.startDeviceDetection;
            } catch (e) {
                // If delete fails, try to overwrite
                window.startDeviceDetection = undefined;
            }
        }
        if (window.hasOwnProperty('stopDeviceDetection')) {
            try {
                delete window.stopDeviceDetection;
            } catch (e) {
                window.stopDeviceDetection = undefined;
            }
        }
        
        // Now assign functions directly
        if (typeof startDeviceDetection === 'function' && typeof stopDeviceDetection === 'function') {
            // Direct assignment - most reliable method
            window.startDeviceDetection = startDeviceDetection;
            window.stopDeviceDetection = stopDeviceDetection;
            window._startDeviceDetection = startDeviceDetection;
            window._stopDeviceDetection = stopDeviceDetection;
            
            // Also export to globalThis
            if (typeof globalThis !== 'undefined') {
                globalThis.startDeviceDetection = startDeviceDetection;
                globalThis.stopDeviceDetection = stopDeviceDetection;
            }
            
            console.log('[Device Detection] ✅ Primary export successful');
            console.log('[Device Detection] Verified:', {
                window_startDeviceDetection: typeof window.startDeviceDetection,
                window_stopDeviceDetection: typeof window.stopDeviceDetection,
                window__startDeviceDetection: typeof window._startDeviceDetection
            });
        } else {
            console.error('[Device Detection] ❌ Functions not defined! Types:', {
                startDeviceDetection: typeof startDeviceDetection,
                stopDeviceDetection: typeof stopDeviceDetection
            });
        }
    } catch (e) {
        console.error('[Device Detection] ❌ Error in primary export:', e);
        console.error('[Device Detection] Error stack:', e.stack);
    }
})();

// Also export after DOM is ready (redundant but safe)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        if (typeof startDeviceDetection === 'function') {
            window.startDeviceDetection = startDeviceDetection;
            window.stopDeviceDetection = stopDeviceDetection;
            window._startDeviceDetection = startDeviceDetection;
            window._stopDeviceDetection = stopDeviceDetection;
            console.log('[Device Detection] ✅ Functions re-exported after DOM ready');
        }
    });
} else {
    // DOM already loaded, ensure export
    if (typeof startDeviceDetection === 'function') {
        window.startDeviceDetection = startDeviceDetection;
        window.stopDeviceDetection = stopDeviceDetection;
        window._startDeviceDetection = startDeviceDetection;
        window._stopDeviceDetection = stopDeviceDetection;
        console.log('[Device Detection] ✅ Functions re-exported (DOM already ready)');
    }
}

// Log that the script has loaded and functions are available
console.log('[Device Detection] ✅ Script loaded successfully!', {
    startDeviceDetection: typeof window.startDeviceDetection === 'function',
    stopDeviceDetection: typeof window.stopDeviceDetection === 'function',
    _startDeviceDetection: typeof window._startDeviceDetection === 'function',
    API_BASE_URL: getDeviceDetectionApiUrlCached(),
    timestamp: new Date().toISOString(),
    documentReadyState: document.readyState
});

// Verify function is callable
if (typeof window.startDeviceDetection === 'function') {
    console.log('[Device Detection] ✅ Function is ready to use');
} else {
    console.error('[Device Detection] ❌ Function export failed!');
    console.error('[Device Detection] startDeviceDetection type:', typeof startDeviceDetection);
    console.error('[Device Detection] window.startDeviceDetection type:', typeof window.startDeviceDetection);
    
    // Last resort: try to export again
    try {
        if (typeof startDeviceDetection === 'function') {
            window.startDeviceDetection = startDeviceDetection;
            window.stopDeviceDetection = stopDeviceDetection;
            console.log('[Device Detection] ✅ Functions exported in last resort attempt');
        }
    } catch (e) {
        console.error('[Device Detection] ❌ Last resort export also failed:', e);
    }
}

// Final verification after a short delay
setTimeout(() => {
    if (typeof window.startDeviceDetection === 'function') {
        console.log('[Device Detection] ✅ Final verification: Function is available');
    } else {
        console.error('[Device Detection] ❌ Final verification: Function still not available');
        console.error('[Device Detection] Available window properties:', Object.keys(window).filter(k => k.toLowerCase().includes('device')));
    }
}, 1000);

} catch (error) {
    // Critical error handler - ensure exports happen even if script fails
    console.error('[Device Detection] ❌ CRITICAL ERROR in script execution:', error);
    console.error('[Device Detection] Error stack:', error.stack);
    
    // Try to export functions even if there was an error
    try {
        if (typeof startDeviceDetection === 'function') {
            window.startDeviceDetection = startDeviceDetection;
            window.stopDeviceDetection = stopDeviceDetection;
            console.log('[Device Detection] ✅ Functions exported despite error');
        } else {
            console.error('[Device Detection] ❌ Functions not defined, cannot export');
        }
    } catch (exportError) {
        console.error('[Device Detection] ❌ Failed to export functions after error:', exportError);
    }
}

