/**
 * Selfie Capture and Face Verification Module
 * Handles selfie capture, registration, and continuous face verification during interview
 */

// Selfie capture state
let selfieStream = null;
let selfieCaptured = false;
let selfieImageBase64 = null;
let selfieSessionId = null;
let faceVerificationActive = false;
let faceVerificationInterval = null;
let faceMismatchCount = 0;
const MAX_FACE_MISMATCHES = 2;

// API base URL
function getFaceVerificationApiUrl() {
    if (window.API_BASE_URL) {
        return window.API_BASE_URL;
    }
    if (typeof window.getApiBaseUrl === 'function') {
        return window.getApiBaseUrl();
    }
    const configScript = document.getElementById('api-config');
    if (configScript && configScript.dataset.apiUrl) {
        return configScript.dataset.apiUrl;
    }
    return 'http://localhost:5000/api';
}

/**
 * Start camera for selfie capture
 */
async function startSelfieCamera() {
    try {
        const video = document.getElementById('selfie-video');
        const placeholder = document.getElementById('selfie-placeholder');
        const startBtn = document.getElementById('start-selfie-camera-btn');
        const captureBtn = document.getElementById('capture-selfie-btn');
        const statusDiv = document.getElementById('selfie-status');
        
        statusDiv.innerHTML = '<p style="color: #667eea;">Starting camera...</p>';
        
        // Request camera access
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: 'user'
            }
        });
        
        selfieStream = stream;
        video.srcObject = stream;
        video.style.display = 'block';
        placeholder.style.display = 'none';
        startBtn.style.display = 'none';
        captureBtn.style.display = 'inline-block';
        
        statusDiv.innerHTML = '<p style="color: #4caf50;">Camera ready. Position your face clearly and click "Capture Selfie"</p>';
        
    } catch (error) {
        console.error('Error starting camera:', error);
        const statusDiv = document.getElementById('selfie-status');
        statusDiv.innerHTML = `<p style="color: #f44336;">Error: ${error.message}. Please allow camera access and try again.</p>`;
        
        if (typeof customAlert === 'function') {
            customAlert(
                `Camera access denied: ${error.message}\n\nPlease allow camera access in your browser settings and try again.`,
                'Camera Access Required',
                '📹',
                'warning'
            );
        } else {
            alert(`Camera access denied: ${error.message}`);
        }
    }
}

/**
 * Capture selfie from video
 */
function captureSelfie() {
    try {
        const video = document.getElementById('selfie-video');
        const canvas = document.getElementById('selfie-canvas');
        const preview = document.getElementById('selfie-preview');
        const previewImage = document.getElementById('selfie-preview-image');
        const captureBtn = document.getElementById('capture-selfie-btn');
        const retakeBtn = document.getElementById('retake-selfie-btn');
        const continueBtn = document.getElementById('continue-after-selfie-btn');
        const statusDiv = document.getElementById('selfie-status');
        
        // Set canvas dimensions
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        if (!video.videoWidth || !video.videoHeight) {
        throw new Error('Camera not ready yet. Please wait a second and try again.');
        }
        
        // Draw video frame to canvas
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert to base64
        selfieImageBase64 = canvas.toDataURL('image/jpeg', 0.9);
        
        // Show preview
        previewImage.src = selfieImageBase64;
        video.style.display = 'none';
        preview.style.display = 'block';
        
        // Update buttons
        captureBtn.style.display = 'none';
        retakeBtn.style.display = 'inline-block';
        continueBtn.style.display = 'inline-block';
        
        statusDiv.innerHTML = '<p style="color: #4caf50;">✓ Selfie captured! Review and click "Continue" or "Retake"</p>';
        selfieCaptured = true;
        
        // Stop camera stream
        if (selfieStream) {
            selfieStream.getTracks().forEach(track => track.stop());
            selfieStream = null;
        }
        
    } catch (error) {
        console.error('Error capturing selfie:', error);
        const statusDiv = document.getElementById('selfie-status');
        statusDiv.innerHTML = `<p style="color: #f44336;">Error capturing selfie: ${error.message}</p>`;
    }
}

/**
 * Retake selfie
 */
function retakeSelfie() {
    const video = document.getElementById('selfie-video');
    const preview = document.getElementById('selfie-preview');
    const captureBtn = document.getElementById('capture-selfie-btn');
    const retakeBtn = document.getElementById('retake-selfie-btn');
    const continueBtn = document.getElementById('continue-after-selfie-btn');
    const placeholder = document.getElementById('selfie-placeholder');
    const startBtn = document.getElementById('start-selfie-camera-btn');
    const statusDiv = document.getElementById('selfie-status');
    
    // Reset state
    selfieCaptured = false;
    selfieImageBase64 = null;
    
    // Hide preview, show placeholder
    preview.style.display = 'none';
    video.style.display = 'none';
    placeholder.style.display = 'block';
    
    // Update buttons
    retakeBtn.style.display = 'none';
    continueBtn.style.display = 'none';
    startBtn.style.display = 'inline-block';
    captureBtn.style.display = 'none';
    
    statusDiv.innerHTML = '';
}

/**
 * Register selfie and continue to interview type selection
 */
async function continueAfterSelfie() {
    if (!selfieImageBase64) {
        if (typeof customAlert === 'function') {
            customAlert('Please capture a selfie first.', 'Selfie Required', '📸', 'warning');
        } else {
            alert('Please capture a selfie first.');
        }
        return;
    }
    
    const continueBtn = document.getElementById('continue-after-selfie-btn');
    const statusDiv = document.getElementById('selfie-status');
    
    continueBtn.disabled = true;
    statusDiv.innerHTML = '<p style="color: #667eea;">Registering selfie...</p>';
    
    try {
        const token = localStorage.getItem('token') || localStorage.getItem('authToken');
        if (!token) {
            throw new Error('Authentication token not found. Please login again.');
        }
        
        const response = await fetch(`${getFaceVerificationApiUrl()}/face/register-selfie`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                selfie_image: selfieImageBase64.split(',')[1]
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            console.error('[Selfie Registration] API Error:', {
                status: response.status,
                statusText: response.statusText,
                error: data.error,
                data: data
            });
            throw new Error(data.error || `Failed to register selfie (${response.status})`);
        }
        
        // Store session ID for later use
        selfieSessionId = data.session_id;
        localStorage.setItem('selfieSessionId', selfieSessionId);
        
        statusDiv.innerHTML = '<p style="color: #4caf50;">✓ Selfie registered successfully!</p>';
        
        // Hide selfie capture section, show interview type selection
        setTimeout(() => {
            document.getElementById('selfie-capture-section').style.display = 'none';
            document.getElementById('interview-type-selection').style.display = 'block';
        }, 1000);
        
    } catch (error) {
        console.error('Error registering selfie:', error);
        statusDiv.innerHTML = `<p style="color: #f44336;">Error: ${error.message}</p>`;
        continueBtn.disabled = false;
        
        if (typeof customAlert === 'function') {
            customAlert(
                `Failed to register selfie: ${error.message}\n\nPlease try again.`,
                'Registration Failed',
                '❌',
                'error'
            );
        } else {
            alert(`Failed to register selfie: ${error.message}`);
        }
    }
}

/**
 * Verify live face against selfie before starting interview
 */
async function verifyFaceBeforeInterview(sessionId) {
    return new Promise(async (resolve, reject) => {
        const video = document.getElementById('interview-video');
        if (!video || !video.srcObject) {
            reject(new Error('Video stream not available'));
            return;
        }
        
        // Wait for video to be ready
        if (video.readyState < 2) {
            await new Promise((resolve) => {
                video.onloadedmetadata = () => resolve();
                setTimeout(() => resolve(), 2000); // Timeout after 2 seconds
            });
        }
        
        // Capture frame
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const liveImageBase64 = canvas.toDataURL('image/jpeg', 0.9);
        
        // Get session ID
        const finalSessionId = sessionId || parseInt(localStorage.getItem('selfieSessionId'));
        if (!finalSessionId) {
            reject(new Error('Selfie session ID not found. Please capture selfie first.'));
            return;
        }
        
        console.log('[Face Verification] Verifying face with session_id:', finalSessionId);
        
        try {
            const token = localStorage.getItem('token') || localStorage.getItem('authToken');
            if (!token) {
                reject(new Error('Authentication token not found. Please login again.'));
                return;
            }
            
            const response = await fetch(`${getFaceVerificationApiUrl()}/face/verify-face`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    live_image: liveImageBase64.split(',')[1],
                    session_id: finalSessionId
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                console.error('[Face Verification] API Error:', {
                    status: response.status,
                    statusText: response.statusText,
                    error: data.error,
                    data: data
                });
                throw new Error(data.error || `Face verification failed (${response.status})`);
            }
            
            console.log('[Face Verification] Verification successful:', data);
            resolve(data);
            
        } catch (error) {
            console.error('[Face Verification] Error:', error);
            reject(error);
        }
    });
}

/**
 * Start continuous face verification during interview
 */
function startFaceVerification(sessionId) {
    if (faceVerificationActive) {
        console.log('[Face Verification] Already active');
        return;
    }
    
    console.log('[Face Verification] Starting continuous face verification for session:', sessionId);
    faceVerificationActive = true;
    faceMismatchCount = 0;
    
    // Verify face every 0.8 seconds (faster real-time detection)
    faceVerificationInterval = setInterval(async () => {
        if (!faceVerificationActive) return;
        
        try {
            // Use the interview session ID (which has selfie embedding linked)
            const verifySessionId = sessionId || parseInt(localStorage.getItem('selfieSessionId'));
            const result = await verifyFaceBeforeInterview(verifySessionId);
            
            console.log('[Face Verification] Verification result:', result);
            
            if (result.matched && result.status === 'match') {
                // Face matches - reset mismatch count
                faceMismatchCount = 0;
                hideFaceWarning();
            } else if (result.status === 'warning') {
                // Show warning but don't count as mismatch yet
                showFaceWarning(result.similarity, 'warning');
            } else if (result.status === 'mismatch') {
                // Face mismatch
                faceMismatchCount++;
                showFaceWarning(result.similarity, 'mismatch', faceMismatchCount);
                
                // Auto-terminate after 2 mismatches
                if (faceMismatchCount >= MAX_FACE_MISMATCHES) {
                    console.log('[Face Verification] Maximum mismatches reached. Terminating interview.');
                    stopFaceVerification();
                    
                    if (typeof customAlert === 'function') {
                        await customAlert(
                            'Face verification failed multiple times. Interview terminated automatically.',
                            'Interview Terminated',
                            '⚠️',
                            'error'
                        );
                    }
                    
                    // End interview automatically
                    if (typeof endInterviewAutomatically === 'function') {
                        endInterviewAutomatically('Face verification failed');
                    } else if (typeof endInterviewEarly === 'function') {
                        endInterviewEarly();
                    }
                }
            }
            
        } catch (error) {
            console.error('[Face Verification] Error during verification:', error);
            // Don't stop verification on error - might be temporary
        }
    }, 1000); // Check every 1 second
}

/**
 * Stop face verification
 */
function stopFaceVerification() {
    if (!faceVerificationActive) return;
    
    faceVerificationActive = false;
    if (faceVerificationInterval) {
        clearInterval(faceVerificationInterval);
        faceVerificationInterval = null;
    }
    
    hideFaceWarning();
    console.log('[Face Verification] Stopped');
}

/**
 * Show face warning panel
 */
function showFaceWarning(similarity, type, count = 0) {
    const warningPanel = document.getElementById('face-warning-panel');
    if (!warningPanel) return;
    
    const warningText = document.getElementById('face-warning-text');
    const warningCount = document.getElementById('face-warning-count');
    
    if (type === 'mismatch') {
        warningText.textContent = `⚠️ Face does not match registered selfie. Please align your face properly. (Similarity: ${(similarity * 100).toFixed(1)}%)`;
        warningCount.textContent = `Mismatch ${count} of ${MAX_FACE_MISMATCHES}`;
    } else {
        warningText.textContent = `⚠️ Face verification warning (Similarity: ${(similarity * 100).toFixed(1)}%)`;
        warningCount.textContent = 'Warning';
    }
    
    warningPanel.classList.remove('hidden');
}

/**
 * Hide face warning panel
 */
function hideFaceWarning() {
    const warningPanel = document.getElementById('face-warning-panel');
    if (warningPanel) {
        warningPanel.classList.add('hidden');
    }
}

// Export functions globally
window.startSelfieCamera = startSelfieCamera;
window.captureSelfie = captureSelfie;
window.retakeSelfie = retakeSelfie;
window.continueAfterSelfie = continueAfterSelfie;
window.verifyFaceBeforeInterview = verifyFaceBeforeInterview;
window.startFaceVerification = startFaceVerification;
window.stopFaceVerification = stopFaceVerification;

console.log('[Selfie Verification] Module loaded');

