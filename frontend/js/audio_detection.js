/**
 * Audio Detection Module
 * Monitors microphone audio for background noise during interview
 */

// Audio detection state
let audioDetectionActive = false;
let audioContext = null;
let mediaStream = null;
let audioProcessor = null;
let noiseWarningCount = 0;
const MAX_NOISE_WARNINGS = 3;
const AUDIO_CHUNK_DURATION = 1500; // 1.5 seconds (faster detection)
const DETECTION_INTERVAL = 1500; // Check every 1.5 seconds (more real-time)
const NOISE_CONFIDENCE_THRESHOLD = 0.55; // Lowered threshold for better sensitivity

// API base URL
function getAudioDetectionApiUrl() {
    if (window.API_BASE_URL) {
        return window.API_BASE_URL;
    }
    if (typeof window.getApiBaseUrl === 'function') {
        return window.getApiBaseUrl();
    }
    return 'http://localhost:5000/api';
}

/**
 * Start audio detection monitoring
 */
async function startAudioDetection(sessionId) {
    if (audioDetectionActive) {
        console.log('[Audio Detection] Already active');
        return;
    }
    
    console.log('[Audio Detection] Starting audio detection for session:', sessionId);
    audioDetectionActive = true;
    noiseWarningCount = 0;
    
    try {
        // Get microphone access
        mediaStream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                sampleRate: 16000
            } 
        });
        
        // Create audio context
        audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000
        });
        
        // Create audio source from microphone
        const source = audioContext.createMediaStreamSource(mediaStream);
        
        // Create script processor for audio chunks
        const bufferSize = 4096;
        audioProcessor = audioContext.createScriptProcessor(bufferSize, 1, 1);
        
        let audioBuffer = [];
        let lastDetectionTime = Date.now();
        const maxBufferSize = 24000; // ~1.5 seconds at 16kHz (faster, more real-time)
        
        audioProcessor.onaudioprocess = (event) => {
            if (!audioDetectionActive) return;
            
            try {
                // Collect audio data
                const inputData = event.inputBuffer.getChannelData(0);
                
                // Validate input data
                if (!inputData || inputData.length === 0) {
                    return;
                }
                
                // Add to buffer
                audioBuffer.push(new Float32Array(inputData));
                
                // Prevent buffer from growing too large
                if (audioBuffer.length > 100) {
                    // Keep only last 50 chunks
                    audioBuffer = audioBuffer.slice(-50);
                }
                
                // Check if we have enough data for detection interval (1.5 seconds)
                const currentTime = Date.now();
                if (currentTime - lastDetectionTime >= DETECTION_INTERVAL) {
                    lastDetectionTime = currentTime;
                    
                    // Combine audio buffer
                    const totalLength = audioBuffer.reduce((sum, arr) => sum + arr.length, 0);
                    
                    // Only process if we have meaningful data
                    if (totalLength < 1000) { // Less than ~60ms at 16kHz
                        audioBuffer = [];
                        return;
                    }
                    
                    const combinedAudio = new Float32Array(totalLength);
                    let offset = 0;
                    for (const arr of audioBuffer) {
                        if (offset + arr.length <= combinedAudio.length) {
                            combinedAudio.set(arr, offset);
                            offset += arr.length;
                        }
                    }
                    
                    // Limit to max buffer size
                    const finalAudio = combinedAudio.slice(0, Math.min(combinedAudio.length, maxBufferSize));
                    
                    // Convert to base64 and send for detection (async, don't block)
                    processAudioChunk(finalAudio, sessionId).catch(err => {
                        console.error('[Audio Detection] Error in processAudioChunk:', err);
                    });
                    
                    // Clear buffer
                    audioBuffer = [];
                }
            } catch (error) {
                console.error('[Audio Detection] Error in audio processor:', error);
                // Clear buffer on error
                audioBuffer = [];
            }
        };
        
        // Connect processor
        source.connect(audioProcessor);
        audioProcessor.connect(audioContext.destination);
        
        console.log('[Audio Detection] ✅ Audio monitoring started');
        
    } catch (error) {
        console.error('[Audio Detection] Error starting audio detection:', error);
        audioDetectionActive = false;
        
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            console.warn('[Audio Detection] Microphone permission denied');
        }
    }
}

/**
 * Process audio chunk and send to backend
 */
async function processAudioChunk(audioData, sessionId) {
    if (!audioDetectionActive) return;
    
    try {
        // Validate audio data
        if (!audioData || audioData.length === 0) {
            console.warn('[Audio Detection] Empty audio data, skipping');
            return;
        }
        
        // Convert Float32Array to Int16 PCM
        const int16Buffer = new Int16Array(audioData.length);
        for (let i = 0; i < audioData.length; i++) {
            // Clamp to [-1, 1] and convert to 16-bit
            const sample = Math.max(-1, Math.min(1, audioData[i]));
            int16Buffer[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
        }
        
        // Convert to base64 - handle large arrays by chunking
        let base64Audio;
        try {
            const uint8Array = new Uint8Array(int16Buffer.buffer);
            // For large arrays, convert in chunks to avoid stack overflow
            if (uint8Array.length > 65536) {
                let binaryString = '';
                for (let i = 0; i < uint8Array.length; i += 8192) {
                    const chunk = uint8Array.slice(i, Math.min(i + 8192, uint8Array.length));
                    binaryString += String.fromCharCode.apply(null, chunk);
                }
                base64Audio = btoa(binaryString);
            } else {
                base64Audio = btoa(String.fromCharCode.apply(null, uint8Array));
            }
        } catch (e) {
            console.error('[Audio Detection] Error encoding to base64:', e);
            return;
        }
        
        // Send to backend for detection
        const token = localStorage.getItem('token') || localStorage.getItem('authToken');
        if (!token) {
            console.warn('[Audio Detection] No auth token available');
            return;
        }
        
        const response = await fetch(`${getAudioDetectionApiUrl()}/audio-detect/detect`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                audio_chunk: base64Audio,
                sample_rate: 16000
            })
        });
        
        if (!response.ok) {
            // Don't spam console with errors - log once per session
            if (!window._audioErrorLogged) {
                console.error('[Audio Detection] API error:', response.status, response.statusText);
                window._audioErrorLogged = true;
                // Reset after 10 seconds
                setTimeout(() => { window._audioErrorLogged = false; }, 10000);
            }
            
            // Try to get error details
            try {
                const errorData = await response.json();
                if (errorData.error) {
                    console.error('[Audio Detection] Error details:', errorData.error);
                }
            } catch (e) {
                // Ignore JSON parse errors
            }
            return;
        }
        
        const result = await response.json();
        
        // Check if there was an error in processing
        if (result.error) {
            console.warn('[Audio Detection] Processing error:', result.error);
            // Don't treat processing errors as noise
            return;
        }
        
        // Handle noise detection
        if (result.noise && result.confidence >= NOISE_CONFIDENCE_THRESHOLD) {
            console.log('[Audio Detection] ✅ Noise detected:', result.noise_type, 'confidence:', result.confidence.toFixed(2));
            // Show top-right indicator immediately
            showAudioIndicator(result.noise_type);
            handleNoiseDetected(result, sessionId);
        } else {
            // No noise detected, hide indicators
            hideAudioIndicator();
            // Hide warning if it was showing (only if not at max warnings)
            if (noiseWarningCount < MAX_NOISE_WARNINGS) {
                hideAudioWarning();
            }
        }
        
    } catch (error) {
        console.error('[Audio Detection] Error processing audio chunk:', error);
    }
}

/**
 * Handle noise detection
 */
function handleNoiseDetected(result, sessionId) {
    noiseWarningCount++;
    
    console.log(`[Audio Detection] Warning ${noiseWarningCount}: ${result.noise_type} (confidence: ${result.confidence.toFixed(2)})`);
    
    // Show warning
    showAudioWarning(noiseWarningCount, result.noise_type);
    
    // Check if we should terminate
    if (noiseWarningCount >= MAX_NOISE_WARNINGS) {
        console.log('[Audio Detection] Maximum warnings reached. Terminating interview...');
        terminateInterviewDueToNoise(sessionId);
    }
}

/**
 * Show audio warning panel (center modal)
 */
function showAudioWarning(count, noiseType) {
    const warningPanel = document.getElementById('audio-warning-panel');
    if (!warningPanel) {
        console.warn('[Audio Detection] Warning panel not found in DOM');
        return;
    }
    
    const warningText = document.getElementById('audio-warning-text');
    const warningMessage = document.getElementById('audio-warning-message');
    const warningCount = document.getElementById('audio-warning-count');
    
    if (warningText) {
        warningText.textContent = '⚠️ Background Noise Detected';
    }
    
    if (warningMessage) {
        let message = 'Please move to a quiet environment.';
        if (noiseType) {
            const noiseTypeMap = {
                'loud_sound': 'Loud sound detected. Please move to a quiet environment.',
                'music_tv_multiple_voices': 'Music/TV or multiple voices detected. Please move to a quiet environment.',
                'keyboard_phone_fan': 'Keyboard, phone, or fan noise detected. Please move to a quiet environment.',
                'multiple_voices': 'Multiple voices detected. Please move to a quiet environment.',
                'background_chatter': 'Background chatter detected. Please move to a quiet environment.'
            };
            message = noiseTypeMap[noiseType] || 'Please move to a quiet environment.';
        }
        warningMessage.textContent = message;
    }
    
    if (warningCount) {
        if (count >= MAX_NOISE_WARNINGS) {
            warningCount.textContent = 'FINAL WARNING: Interview will end.';
            warningCount.style.color = '#ffffff';
            warningCount.style.background = 'rgba(255, 68, 68, 0.5)';
            warningCount.style.fontWeight = 'bold';
        } else {
            warningCount.textContent = `Warning ${count} of ${MAX_NOISE_WARNINGS}`;
            warningCount.style.color = '#ffffff';
            warningCount.style.background = 'rgba(0, 0, 0, 0.3)';
            warningCount.style.fontWeight = 'normal';
        }
    }
    
    // Show center modal with animation
    warningPanel.classList.remove('hidden');
    console.log(`[Audio Detection] Warning ${count} displayed: ${noiseType || 'unknown'}`);
    
    // Auto-hide after 4 seconds (shorter for better UX)
    setTimeout(() => {
        if (noiseWarningCount < MAX_NOISE_WARNINGS) {
            hideAudioWarning();
        }
    }, 4000);
}

/**
 * Show audio detection indicator (top right)
 */
function showAudioIndicator(noiseType) {
    const indicator = document.getElementById('audio-detection-indicator');
    if (!indicator) return;
    
    indicator.classList.remove('hidden');
}

/**
 * Hide audio detection indicator (top right)
 */
function hideAudioIndicator() {
    const indicator = document.getElementById('audio-detection-indicator');
    if (indicator) {
        indicator.classList.add('hidden');
    }
}

/**
 * Hide audio warning panel
 */
function hideAudioWarning() {
    const warningPanel = document.getElementById('audio-warning-panel');
    if (warningPanel) {
        // Only hide if we haven't reached max warnings
        if (noiseWarningCount < MAX_NOISE_WARNINGS) {
            warningPanel.classList.add('hidden');
        }
    }
    // Also hide indicator when warning is hidden
    hideAudioIndicator();
}

/**
 * Stop audio detection
 */
function stopAudioDetection() {
    if (!audioDetectionActive) {
        return;
    }
    
    console.log('[Audio Detection] Stopping audio detection...');
    audioDetectionActive = false;
    noiseWarningCount = 0;
    
    // Hide all UI elements
    hideAudioWarning();
    hideAudioIndicator();
    
    // Stop audio processor
    if (audioProcessor) {
        try {
            audioProcessor.disconnect();
            audioProcessor = null;
        } catch (e) {
            console.error('[Audio Detection] Error disconnecting processor:', e);
        }
    }
    
    // Close audio context
    if (audioContext) {
        try {
            audioContext.close();
            audioContext = null;
        } catch (e) {
            console.error('[Audio Detection] Error closing audio context:', e);
        }
    }
    
    // Stop media stream tracks
    if (mediaStream) {
        try {
            mediaStream.getTracks().forEach(track => {
                track.stop();
                console.log('[Audio Detection] Stopped audio track:', track.kind);
            });
            mediaStream = null;
        } catch (e) {
            console.error('[Audio Detection] Error stopping media stream:', e);
        }
    }
    
    // Hide warning panel
    hideAudioWarning();
    
    console.log('[Audio Detection] ✅ Audio detection stopped');
}

/**
 * Terminate interview due to noise
 */
async function terminateInterviewDueToNoise(sessionId) {
    // Stop audio detection first
    stopAudioDetection();
    
    // Show termination message
    if (typeof customAlert === 'function') {
        await customAlert(
            'Interview terminated due to repeated background noise.\n\n' +
            'Please ensure you are in a quiet environment for future interviews.',
            'Interview Terminated',
            '🔇',
            'error'
        );
    } else {
        alert('Interview terminated due to repeated background noise.');
    }
    
    // End interview automatically
    if (typeof endInterviewAutomatically === 'function') {
        endInterviewAutomatically();
    } else if (typeof showInterviewResults === 'function') {
        showInterviewResults({
            interview_completed: true,
            final_score: 0,
            termination_reason: 'Background noise violation'
        });
    }
}

// Export functions to window
if (typeof window !== 'undefined') {
    window.startAudioDetection = startAudioDetection;
    window.stopAudioDetection = stopAudioDetection;
    window.showAudioWarning = showAudioWarning;
    window.hideAudioWarning = hideAudioWarning;
}

console.log('[Audio Detection] ✅ Module loaded');

