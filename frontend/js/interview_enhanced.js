/**
 * Enhanced AI Virtual Interview Flow Management
 * Supports TR (Technical) and HR interview types with structured flow
 */

// Interview state - Made globally accessible to avoid conflicts with app.js
let currentInterviewType = null;  // 'TR' or 'HR'
let currentSessionId = null;
let interviewResumeData = null;
let interviewJDData = null;
let interviewResumeText = '';
let interviewJDText = '';
let interviewStartTime = null;
let currentQuestionStartTime = null;
let interviewStream = null;
let recognition = null;
let isRecording = false;
let currentTranscript = '';

// Make variables globally accessible for backward compatibility with old code
if (typeof window !== 'undefined') {
    window.currentSessionId = currentSessionId;
    window.interviewStream = interviewStream;
    window.recognition = recognition;
    window.isRecording = isRecording;
    window.currentTranscript = currentTranscript;
}

// Ensure interview type selection is hidden if no selfie exists (safety check)
function ensureSelfieBeforeTypeSelection() {
    const selfieSessionId = localStorage.getItem('selfieSessionId');
    const typeSelection = document.getElementById('interview-type-selection');
    const selfieSection = document.getElementById('selfie-capture-section');
    
    if (!selfieSessionId && typeSelection && selfieSection) {
        // No selfie captured - hide type selection, show selfie section
        typeSelection.style.display = 'none';
        selfieSection.style.display = 'block';
    }
}

// Run check when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ensureSelfieBeforeTypeSelection);
} else {
    ensureSelfieBeforeTypeSelection();
}

// Also check when interview page becomes visible (safety net)
if (typeof document !== 'undefined' && document.addEventListener) {
    // Check when page visibility changes
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            ensureSelfieBeforeTypeSelection();
        }
    });
}

// STEP 1: Select Interview Type (ONLY after selfie is captured)
function selectInterviewType(type, element) {
    try {
        // CRITICAL: Check if selfie was captured first
        const selfieSessionId = localStorage.getItem('selfieSessionId');
        if (!selfieSessionId) {
            // Selfie not captured - show warning and redirect to selfie capture
            if (typeof customAlert === 'function') {
                customAlert(
                    'Please capture your selfie first before selecting interview type.\n\nThis is required for face verification during the interview.',
                    'Selfie Required',
                    '📸',
                    'warning'
                ).then(() => {
                    // Redirect to selfie capture section
                    const selfieSection = document.getElementById('selfie-capture-section');
                    const typeSelection = document.getElementById('interview-type-selection');
                    if (selfieSection && typeSelection) {
                        typeSelection.style.display = 'none';
                        selfieSection.style.display = 'block';
                        // Scroll to selfie section
                        selfieSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                });
            } else {
                alert('Please capture your selfie first before selecting interview type.');
                // Redirect to selfie capture section
                const selfieSection = document.getElementById('selfie-capture-section');
                const typeSelection = document.getElementById('interview-type-selection');
                if (selfieSection && typeSelection) {
                    typeSelection.style.display = 'none';
                    selfieSection.style.display = 'block';
                    selfieSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
            return;
        }
        
        console.log('Selecting interview type:', type);
        currentInterviewType = type;
        
        // Update UI - highlight selected card
        document.querySelectorAll('.interview-type-card').forEach(card => {
            card.classList.remove('selected');
        });
        if (element) {
            element.classList.add('selected');
        }
        
        // Show upload section and hide type selection and selfie section
        const typeSelection = document.getElementById('interview-type-selection');
        const uploadSection = document.getElementById('interview-upload');
        const selfieSection = document.getElementById('selfie-capture-section');
        
        if (!typeSelection) {
            console.error('interview-type-selection element not found');
            alert('Error: Interview type selection section not found. Please refresh the page.');
            return;
        }
        
        if (!uploadSection) {
            console.error('interview-upload element not found');
            alert('Error: Interview upload section not found. Please refresh the page.');
            return;
        }
        
        // Hide selfie section and type selection, show upload section
        if (selfieSection) selfieSection.style.display = 'none';
        typeSelection.style.display = 'none';
        uploadSection.style.display = 'block';
        
        // Store interview type
        localStorage.setItem('selectedInterviewType', type);
        
        console.log('Interview type selected successfully:', type);
    } catch (error) {
        console.error('Error in selectInterviewType:', error);
        alert('Error selecting interview type: ' + error.message);
    }
}

function goBackToTypeSelection() {
    document.getElementById('interview-upload').style.display = 'none';
    document.getElementById('interview-type-selection').style.display = 'block';
    currentInterviewType = null;
    localStorage.removeItem('selectedInterviewType');
}

function goBackToSelfieCapture() {
    document.getElementById('interview-type-selection').style.display = 'none';
    document.getElementById('selfie-capture-section').style.display = 'block';
    // Clear selfie session to force new capture
    localStorage.removeItem('selfieSessionId');
    if (typeof retakeSelfie === 'function') {
        retakeSelfie();
    }
}

// STEP 2: Handle Resume Upload
async function handleResumeUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const fileNameDiv = document.getElementById('resume-file-name');
    const resumeTextarea = document.getElementById('resume-text');
    
    fileNameDiv.innerHTML = `<div class="upload-status">Uploading ${file.name}...</div>`;
    
    try {
        const result = await interviewAPI.uploadResume(file);
        interviewResumeText = result.resume_text || '';
        interviewResumeData = result.resume_data || null;
        
        if (resumeTextarea) {
            resumeTextarea.value = result.resume_text || '';
            resumeTextarea.style.display = 'block';
        }
        
        fileNameDiv.innerHTML = `
            <div class="upload-status success">
                ✓ ${result.filename} - Processed successfully
                ${result.resume_data ? `<br><small>Extracted: ${result.resume_data.skills?.length || 0} skills, ${result.resume_data.programming_languages?.length || 0} languages</small>` : ''}
            </div>
        `;
    } catch (error) {
        fileNameDiv.innerHTML = `<div class="upload-status error">✗ Error: ${error.message}</div>`;
        alert(`Error uploading resume: ${error.message}`);
    }
}

// STEP 2: Handle JD Upload
async function handleJDUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const fileNameDiv = document.getElementById('jd-file-name');
    const jdTextarea = document.getElementById('job-description');
    
    fileNameDiv.innerHTML = `<div class="upload-status">Uploading ${file.name}...</div>`;
    
    try {
        // Get resume skills for mapping
        const resumeSkills = interviewResumeData?.skills || [];
        const formData = new FormData();
        formData.append('file', file);
        if (resumeSkills.length > 0) {
            formData.append('resume_skills', JSON.stringify(resumeSkills));
        }
        
        const result = await interviewAPI.uploadJD(file, resumeSkills);
        interviewJDText = result.jd_text || '';
        interviewJDData = result.jd_data || null;
        
        if (jdTextarea) {
            jdTextarea.value = result.jd_text || '';
            jdTextarea.style.display = 'block';
        }
        
        fileNameDiv.innerHTML = `
            <div class="upload-status success">
                ✓ ${result.filename} - Processed successfully
                ${result.jd_data ? `<br><small>Required: ${result.jd_data.required_skills?.length || 0} skills, Missing: ${result.jd_data.missing_skills?.length || 0} skills</small>` : ''}
            </div>
        `;
    } catch (error) {
        fileNameDiv.innerHTML = `<div class="upload-status error">✗ Error: ${error.message}</div>`;
        alert(`Error uploading job description: ${error.message}`);
    }
}

// STEP 3: Process Uploads and Start Interview
async function processUploadsAndStart() {
    // Get interview type
    if (!currentInterviewType) {
        currentInterviewType = localStorage.getItem('selectedInterviewType');
        if (!currentInterviewType) {
            alert('Please select an interview type first');
            goBackToTypeSelection();
            return;
        }
    }
    
    // Get resume text (from upload or textarea)
    const resumeTextarea = document.getElementById('resume-text');
    if (resumeTextarea && resumeTextarea.value) {
        interviewResumeText = resumeTextarea.value;
    }
    
    // Get JD text (from upload or textarea)
    const jdTextarea = document.getElementById('job-description');
    if (jdTextarea && jdTextarea.value) {
        interviewJDText = jdTextarea.value;
    }
    
    if (!interviewResumeText) {
        alert('Please upload or enter your resume');
        return;
    }
    
    try {
        // Get selfie session ID
        const selfieSessionId = localStorage.getItem('selfieSessionId');
        if (!selfieSessionId) {
            if (typeof customAlert === 'function') {
                await customAlert(
                    'Please capture your selfie first before starting the interview.',
                    'Selfie Required',
                    '📸',
                    'warning'
                );
            } else {
                alert('Please capture your selfie first.');
            }
            // Go back to selfie capture
            document.getElementById('interview-upload').style.display = 'none';
            document.getElementById('selfie-capture-section').style.display = 'block';
            return;
        }
        
        // Show loading
        const uploadSection = document.getElementById('interview-upload');
        const chatSection = document.getElementById('interview-chat');
        uploadSection.style.display = 'none';
        chatSection.style.display = 'block';
        
        // Initialize proctoring BEFORE requesting camera
        if (typeof initializeProctoring === 'function') {
            initializeProctoring();
        } else {
            console.warn('[Interview] Proctoring not available. Install proctoring.js');
        }
        
        // Request camera access
        await requestCameraAndMicrophone();
        
        // Wait for video to be ready
        const video = document.getElementById('interview-video');
        await new Promise((resolve) => {
            if (video.readyState >= 2) {
                resolve();
            } else {
                video.onloadedmetadata = () => resolve();
                setTimeout(() => resolve(), 2000); // Timeout after 2 seconds
            }
        });
        
        // Verify face before starting interview
        console.log('[Interview] Verifying face before starting interview...');
        let verificationAttempts = 0;
        const MAX_VERIFICATION_ATTEMPTS = 2;
        let faceVerified = false;
        
        while (verificationAttempts < MAX_VERIFICATION_ATTEMPTS && !faceVerified) {
            verificationAttempts++;
            
            try {
                // Use selfie session ID for initial verification (before interview session is created)
                const verifySessionId = parseInt(selfieSessionId);
                const verificationResult = await verifyFaceBeforeInterview(verifySessionId);
                console.log('[Interview] Face verification result:', verificationResult);
                
                if (verificationResult.matched && verificationResult.status === 'match') {
                    faceVerified = true;
                    console.log('[Interview] ✅ Face verified successfully!');
                } else {
                    const similarity = verificationResult.similarity || 0;
                    const message = verificationResult.status === 'warning' 
                        ? `Face verification warning (Similarity: ${(similarity * 100).toFixed(1)}%). Please align your face properly.`
                        : `Face does not match registered selfie (Similarity: ${(similarity * 100).toFixed(1)}%). Please ensure you are the same person.`;
                    
                    if (verificationAttempts >= MAX_VERIFICATION_ATTEMPTS) {
                        // Final attempt failed
                        if (typeof customAlert === 'function') {
                            await customAlert(
                                `${message}\n\nInterview cannot start. Please try again.`,
                                'Face Verification Failed',
                                '❌',
                                'error'
                            );
                        } else {
                            alert(`${message}\n\nInterview cannot start.`);
                        }
                        
                        // Go back to upload section
                        chatSection.style.display = 'none';
                        uploadSection.style.display = 'block';
                        return;
                    } else {
                        // Show warning and allow retry
                        if (typeof customAlert === 'function') {
                            const retry = await customConfirm(
                                `${message}\n\nAttempt ${verificationAttempts} of ${MAX_VERIFICATION_ATTEMPTS}.\n\nWould you like to try again?`,
                                'Face Verification Warning',
                                '⚠️',
                                'Retry',
                                'Cancel'
                            );
                            if (!retry) {
                                chatSection.style.display = 'none';
                                uploadSection.style.display = 'block';
                                return;
                            }
                        } else {
                            if (!confirm(`${message}\n\nWould you like to try again?`)) {
                                chatSection.style.display = 'none';
                                uploadSection.style.display = 'block';
                                return;
                            }
                        }
                    }
                }
            } catch (error) {
                console.error('[Interview] Face verification error:', error);
                if (verificationAttempts >= MAX_VERIFICATION_ATTEMPTS) {
                    if (typeof customAlert === 'function') {
                        await customAlert(
                            `Face verification failed: ${error.message}\n\nInterview cannot start.`,
                            'Verification Error',
                            '❌',
                            'error'
                        );
                    } else {
                        alert(`Face verification failed: ${error.message}`);
                    }
                    chatSection.style.display = 'none';
                    uploadSection.style.display = 'block';
                    return;
                }
            }
        }
        
        if (!faceVerified) {
            // Should not reach here, but safety check
            chatSection.style.display = 'none';
            uploadSection.style.display = 'block';
            return;
        }
        
        // Start interview (create session first)
        const startData = {
            interview_type: currentInterviewType,
            resume_text: interviewResumeText,
            job_description: interviewJDText,
            resume_data: interviewResumeData,
            jd_data: interviewJDData,
            selfie_session_id: parseInt(selfieSessionId)  // Link to selfie session
        };
        
        const result = await interviewAPI.startInterview(startData);
        currentSessionId = result.session_id;
        
        // Selfie is already linked in backend when creating session
        
        // Update global reference for backward compatibility
        if (typeof window !== 'undefined') {
            window.currentSessionId = currentSessionId;
        }
        interviewStartTime = Date.now();
        currentQuestionStartTime = Date.now();
        
        // Validate and display first question
        console.log('[Interview] API Response:', {
            question: result.question,
            question_number: result.question_number,
            total_questions: result.total_questions,
            session_id: result.session_id
        });
        
        if (!result.question || result.question.trim() === '') {
            console.error('[Interview] ❌ Question is empty or undefined!');
            console.error('[Interview] Full result:', result);
            // Try to get a fallback question
            result.question = result.question || 'Please introduce yourself and tell us about your background.';
            console.warn('[Interview] Using fallback question:', result.question);
        }
        
        // Display first question
        displayQuestion(result.question, result.question_number || 1, result.total_questions || 6, 'introduction');
        
        // Initialize speech recognition
        initializeSpeechRecognition();
        
        // Start device detection monitoring
        // Wait for device_detection.js to load with multiple retries
        function waitForDeviceDetection(maxRetries = 20, delay = 500) {
            let retries = 0;
            
            function checkAndStart() {
                retries++;
                
                // Check multiple ways the function might be available
                const func = window.startDeviceDetection || 
                            window._startDeviceDetection || 
                            (typeof startDeviceDetection !== 'undefined' ? startDeviceDetection : null) ||
                            (typeof globalThis !== 'undefined' && globalThis.startDeviceDetection ? globalThis.startDeviceDetection : null);
                
                if (typeof func === 'function') {
                    console.log('[Interview] ✅ Device detection function found! Starting for session:', currentSessionId);
                    try {
                        // Wait a bit more for video to be ready
                        setTimeout(() => {
                            func(currentSessionId);
                            console.log('[Interview] ✅ Device detection started successfully');
                        }, 3000); // Start after 3 seconds to ensure video is ready
                    } catch (error) {
                        console.error('[Interview] ❌ Error calling startDeviceDetection:', error);
                        console.error('[Interview] Error stack:', error.stack);
                    }
                    return true;
                }
                
                if (retries < maxRetries) {
                    if (retries % 3 === 0) { // Log every 3rd attempt to reduce console spam
                        console.log(`[Interview] Waiting for device detection... (attempt ${retries}/${maxRetries})`);
                    }
                    setTimeout(checkAndStart, delay);
                    return false;
                } else {
                    console.error('[Interview] ❌ Device detection failed to load after', maxRetries, 'attempts');
                    console.error('[Interview] Available on window:', {
                        startDeviceDetection: typeof window.startDeviceDetection,
                        _startDeviceDetection: typeof window._startDeviceDetection,
                        startDeviceDetectionDirect: typeof startDeviceDetection,
                        globalThis: typeof globalThis !== 'undefined' ? typeof globalThis.startDeviceDetection : 'N/A',
                        allWindowKeys: Object.keys(window).filter(k => k.toLowerCase().includes('device'))
                    });
                    
                    // Try to manually trigger by checking if script exists
                    const scripts = Array.from(document.scripts);
                    const deviceScript = scripts.find(s => s.src && s.src.includes('device_detection'));
                    if (deviceScript) {
                        console.warn('[Interview] Device detection script found in DOM but function not available');
                        console.warn('[Interview] Script src:', deviceScript.src);
                        console.warn('[Interview] Script loaded:', deviceScript.readyState);
                    } else {
                        console.error('[Interview] Device detection script not found in DOM!');
                    }
                    
                    return false;
                }
            }
            
            // Start checking immediately, then continue with delays
            checkAndStart();
        }
        
        // Start waiting for device detection
        waitForDeviceDetection();
        
        // Start audio detection monitoring
        if (typeof startAudioDetection === 'function') {
            setTimeout(() => {
                startAudioDetection(currentSessionId);
                console.log('[Interview] ✅ Audio detection started');
            }, 4000); // Start after 4 seconds to allow video/audio to stabilize
        } else {
            console.warn('[Interview] Audio detection function not available');
        }
        
        // Update question counter (ensure it's at least 1)
        const questionNum = result.question_number || 1;
        updateQuestionCounter(questionNum, result.total_questions || 6);
        
        // Update interview type badge
        const badge = document.getElementById('current-interview-type-badge');
        if (badge) {
            badge.textContent = currentInterviewType === 'TR' ? 'Technical Interview' : 'HR Interview';
            badge.className = `interview-type-badge ${currentInterviewType.toLowerCase()}`;
        }
    } catch (error) {
        console.error('Error starting interview:', error);
        // Show detailed error message for debugging
        let errorMessage = 'Failed to start interview.\n\n';
        
        // Check for specific error types
        if (error.message) {
            if (error.message.includes('resume_file_path') || error.message.includes('Unknown column')) {
                errorMessage += 'Database Error: Missing columns in interview_sessions table.\n';
                errorMessage += 'Please run: python backend/migrate_interview_columns.py\n\n';
                errorMessage += 'Full error: ' + error.message;
            } else if (error.message.includes('Cannot connect to server')) {
                errorMessage += 'Connection Error: Cannot connect to backend server.\n';
                errorMessage += 'Please check if the backend is running on localhost:5000.\n\n';
                errorMessage += 'Full error: ' + error.message;
            } else {
                errorMessage += 'Error: ' + error.message;
            }
        } else {
            errorMessage += 'Unknown error occurred. Please check the console for details.';
        }
        
        alert(errorMessage);
        // Show upload section again
        document.getElementById('interview-upload').style.display = 'block';
        document.getElementById('interview-chat').style.display = 'none';
    }
}

// Display question in chat with natural typing effect
async function displayQuestion(question, questionNumber, totalQuestions, phase) {
    console.log('[Interview] displayQuestion called:', { question, questionNumber, totalQuestions, phase });
    
    const chatDiv = document.getElementById('chat-messages');
    if (!chatDiv) {
        console.error('[Interview] chat-messages element not found!');
        return;
    }
    
    // Validate question
    if (!question || question.trim() === '') {
        console.error('[Interview] ❌ Question is empty!');
        question = 'Please introduce yourself and tell us about your background.';
        console.warn('[Interview] Using fallback question');
    }
    
    const phaseLabel = getPhaseLabel(currentInterviewType, phase);
    
    // Create message container
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message question';
    messageDiv.innerHTML = `
        <div class="phase-badge phase-${phase}">${phaseLabel}</div>
        <div class="question-content">
            <div class="interviewer-avatar">👤</div>
            <div class="message-bubble">
                <strong class="interviewer-name">Interviewer</strong>
                <div class="question-text"></div>
                <div class="typing-indicator" style="display: none;">...</div>
            </div>
        </div>
    `;
    
    chatDiv.appendChild(messageDiv);
    chatDiv.scrollTop = chatDiv.scrollHeight;
    
    // Show typing indicator
    const typingIndicator = messageDiv.querySelector('.typing-indicator');
    const questionText = messageDiv.querySelector('.question-text');
    
    if (typingIndicator && questionText) {
        typingIndicator.style.display = 'block';
        
        // Type question character by character for natural feel
        await typeText(questionText, question, 30); // 30ms per character
        
        typingIndicator.style.display = 'none';
    }
    
    // Reset answer input
    const answerText = document.getElementById('answer-text');
    if (answerText) answerText.value = '';
    currentTranscript = '';
    
    // Show submit button with animation
    const submitBtn = document.getElementById('submit-answer-btn');
    if (submitBtn) {
        submitBtn.style.display = 'block';
        submitBtn.style.opacity = '0';
        submitBtn.style.transform = 'translateY(10px)';
        setTimeout(() => {
            submitBtn.style.transition = 'all 0.3s ease';
            submitBtn.style.opacity = '1';
            submitBtn.style.transform = 'translateY(0)';
        }, 100);
    }
    
    console.log('[Interview] ✅ Question displayed successfully');
}

// Type text with natural typing effect
function typeText(element, text, speed = 30) {
    return new Promise((resolve) => {
        let index = 0;
        element.textContent = '';
        
        function type() {
            if (index < text.length) {
                element.textContent += text[index];
                index++;
                setTimeout(type, speed + Math.random() * 20); // Add slight randomness
            } else {
                resolve();
            }
        }
        
        type();
    });
}

function getPhaseLabel(interviewType, phase) {
    if (interviewType === 'TR') {
        const labels = {
            'introduction': 'Introduction',
            'resume': 'Resume-Based Technical',
            'programming': 'Programming Languages',
            'jd_skills': 'JD Required Skills',
            'scenario': 'Scenario-Based'
        };
        return labels[phase] || 'General';
    } else {
        const labels = {
            'introduction': 'Introduction',
            'communication': 'Communication Skills',
            'behavioral': 'Behavioral',
            'situational': 'Situational',
            'career': 'Career Goals'
        };
        return labels[phase] || 'General';
    }
}

function updateQuestionCounter(current, total) {
    console.log('[Interview] updateQuestionCounter called:', { current, total });
    const currentEl = document.getElementById('current-question-number');
    if (currentEl) {
        // Ensure current is at least 1 if it's 0 or undefined
        const displayNum = current && current > 0 ? current : 1;
        currentEl.textContent = displayNum;
        console.log('[Interview] ✅ Question counter updated to:', displayNum);
    } else {
        console.error('[Interview] ❌ current-question-number element not found!');
    }
    // Total questions removed - only showing current question number
}

// STEP 6: Submit Answer
async function submitAnswer() {
    if (!currentSessionId) {
        alert('No active interview session');
        return;
    }
    
    // Stop recording
    stopVoiceRecording();
    
    // Get answer
    const answerTextEl = document.getElementById('answer-text');
    let answer = currentTranscript.trim() || (answerTextEl ? answerTextEl.value.trim() : '');
    
    if (!answer) {
        alert('Please provide an answer');
        return;
    }
    
    // Calculate time taken
    const timeTaken = currentQuestionStartTime ? Math.floor((Date.now() - currentQuestionStartTime) / 1000) : 0;
    currentQuestionStartTime = Date.now();
    
    try {
        // Disable submit button
        const submitBtn = document.getElementById('submit-answer-btn');
        if (submitBtn) submitBtn.disabled = true;
        
        // Display user answer with natural animation
        const chatDiv = document.getElementById('chat-messages');
        if (chatDiv) {
            const answerDiv = document.createElement('div');
            answerDiv.className = 'chat-message answer';
            answerDiv.innerHTML = `
                <div class="message-bubble">
                    <strong class="user-name">You</strong>
                    <div class="answer-text"></div>
                </div>
            `;
            chatDiv.appendChild(answerDiv);
            
            // Type answer with slight delay for natural feel
            const answerText = answerDiv.querySelector('.answer-text');
            if (answerText) {
                await typeText(answerText, answer, 20); // Faster typing for user answers
            }
            
            chatDiv.scrollTop = chatDiv.scrollHeight;
        }
        
        // Submit answer
        const result = await interviewAPI.submitAnswer(currentSessionId, answer, timeTaken);
        
        // Display feedback with natural typing and enhanced formatting
        if (chatDiv && result.feedback) {
            // Create feedback message with typing effect
            const feedbackDiv = document.createElement('div');
            feedbackDiv.className = 'chat-message feedback-enhanced';
            
            // Format feedback to highlight structured methods (STAR, numbered lists, etc.)
            let formattedFeedback = result.feedback;
            
            // Detect and format STAR method mentions
            const starPattern = /(STAR method|Situation.*?Task.*?Action.*?Result)/gi;
            if (starPattern.test(formattedFeedback)) {
                formattedFeedback = formattedFeedback.replace(
                    /(Situation|Task|Action|Result):\s*([^\n-]+)/gi,
                    '<strong>$1:</strong> $2'
                );
            }
            
            // Format numbered lists and bullet points
            formattedFeedback = formattedFeedback.replace(
                /(\d+\.\s+[^\n]+)/g,
                '<div class="feedback-list-item">$1</div>'
            );
            formattedFeedback = formattedFeedback.replace(
                /(-|\*)\s+([^\n]+)/g,
                '<div class="feedback-list-item">• $2</div>'
            );
            
            // Format code blocks or structured examples
            formattedFeedback = formattedFeedback.replace(
                /For example[^:]*:\s*([^\n]+)/gi,
                '<div class="feedback-example"><strong>Example:</strong> $1</div>'
            );
            
            // Preserve line breaks
            formattedFeedback = formattedFeedback.replace(/\n/g, '<br>');
            
            // Create feedback message with typing effect
            feedbackDiv.innerHTML = `
                <div class="feedback-header">
                    <strong>💡 Feedback & Guidance:</strong>
                </div>
                <div class="feedback-content-text"></div>
                ${result.scores ? `
                    <div class="score-display-mini">
                        <span>Correctness: ${result.scores.correctness}/10</span>
                        <span>Clarity: ${result.scores.clarity}/10</span>
                        <span>Confidence: ${result.scores.confidence}/10</span>
                        <span>Overall: ${result.scores.overall}/10</span>
                    </div>
                ` : ''}
            `;
            chatDiv.appendChild(feedbackDiv);
            
            // Type feedback with natural effect
            const feedbackText = feedbackDiv.querySelector('.feedback-content-text');
            if (feedbackText) {
                // Strip HTML for typing, then restore
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = formattedFeedback;
                const plainText = tempDiv.textContent || tempDiv.innerText || '';
                
                await typeText(feedbackText, plainText, 25);
                
                // After typing, restore formatted HTML
                feedbackText.innerHTML = formattedFeedback;
            }
            
            chatDiv.scrollTop = chatDiv.scrollHeight;
        }
        
        // Check if interview is completed
        if (result.interview_completed) {
            showInterviewResults(result);
        } else if (result.next_question) {
            // Display next question
            displayQuestion(result.next_question, result.question_number, result.total_questions, result.phase);
            updateQuestionCounter(result.question_number, result.total_questions);
        }
        
        // Re-enable submit button
        if (submitBtn) submitBtn.disabled = false;
        
    } catch (error) {
        alert(`Error submitting answer: ${error.message}`);
        const submitBtn = document.getElementById('submit-answer-btn');
        if (submitBtn) submitBtn.disabled = false;
    }
}

// STEP 8: Show Interview Results
async function showInterviewResults(result) {
    // CRITICAL: Stop all media streams FIRST before showing results
    cleanupInterviewMedia();
    
    // Also stop selfie stream if it exists
    if (typeof window !== 'undefined' && window.selfieStream) {
        try {
            window.selfieStream.getTracks().forEach(track => {
                track.stop();
                console.log('[Interview] Stopped selfie stream track:', track.kind);
            });
            window.selfieStream = null;
        } catch (e) {
            console.error('[Interview] Error stopping selfie stream:', e);
        }
    }
    
    // Stop selfie video element if it exists
    const selfieVideo = document.getElementById('selfie-video');
    if (selfieVideo && selfieVideo.srcObject) {
        try {
            selfieVideo.srcObject.getTracks().forEach(track => track.stop());
            selfieVideo.srcObject = null;
            console.log('[Interview] Stopped selfie video element');
        } catch (e) {
            console.error('[Interview] Error stopping selfie video:', e);
        }
    }
    
    // Hide interview chat
    document.getElementById('interview-chat').style.display = 'none';
    
    // Show results section
    const resultsSection = document.getElementById('interview-results');
    resultsSection.style.display = 'block';
    
    // Display final score
    const finalScoreEl = document.getElementById('final-score');
    if (finalScoreEl) {
        finalScoreEl.textContent = result.final_score || 0;
    }
    
    // Display interview type
    const typeEl = document.getElementById('interview-type-result');
    if (typeEl) {
        typeEl.textContent = currentInterviewType === 'TR' ? 'Technical Interview' : 'HR Interview';
    }
    
    // Display score breakdown
    const breakdownEl = document.getElementById('score-breakdown');
    if (breakdownEl && result.score_breakdown) {
        const breakdown = typeof result.score_breakdown === 'string' ? 
            JSON.parse(result.score_breakdown) : result.score_breakdown;
        let html = '<div class="breakdown-grid">';
        
        const interviewType = result.interview_type || currentInterviewType || 'TR';
        if (interviewType === 'TR') {
            html += `
                <div class="breakdown-item"><span>Introduction:</span> <strong>${breakdown.introduction_score || 0}/10</strong></div>
                <div class="breakdown-item"><span>Projects & Resume:</span> <strong>${breakdown.projects_resume_score || 0}/10</strong></div>
                <div class="breakdown-item"><span>Programming:</span> <strong>${breakdown.programming_score || 0}/10</strong></div>
                <div class="breakdown-item"><span>JD Gap Skills:</span> <strong>${breakdown.jd_gap_skills_score || 0}/10</strong></div>
                <div class="breakdown-item"><span>Communication:</span> <strong>${breakdown.communication_score || 0}/10</strong></div>
            `;
        } else {
            html += `
                <div class="breakdown-item"><span>Introduction:</span> <strong>${breakdown.hr_introduction_score || 0}/10</strong></div>
                <div class="breakdown-item"><span>Communication:</span> <strong>${breakdown.hr_communication_score || 0}/10</strong></div>
                <div class="breakdown-item"><span>Confidence:</span> <strong>${breakdown.hr_confidence_score || 0}/10</strong></div>
                <div class="breakdown-item"><span>Behavioral:</span> <strong>${breakdown.hr_behavioral_score || 0}/10</strong></div>
            `;
        }
        
        html += '</div>';
        breakdownEl.innerHTML = html;
    }
    
    // Display strengths
    const strengthsList = document.getElementById('strengths-list');
    if (strengthsList && result.strengths) {
        const strengths = Array.isArray(result.strengths) ? result.strengths : 
                         (typeof result.strengths === 'string' ? JSON.parse(result.strengths) : []);
        strengthsList.innerHTML = strengths.map(s => `<li>${s}</li>`).join('');
    }
    
    // Display weaknesses
    const weaknessesList = document.getElementById('weaknesses-list');
    if (weaknessesList && result.weaknesses) {
        const weaknesses = Array.isArray(result.weaknesses) ? result.weaknesses : 
                          (typeof result.weaknesses === 'string' ? JSON.parse(result.weaknesses) : []);
        weaknessesList.innerHTML = weaknesses.map(w => `<li>${w}</li>`).join('');
    }
    
    // Display improvements
    const improvementsList = document.getElementById('improvements-list');
    if (improvementsList && result.improvements) {
        const improvements = Array.isArray(result.improvements) ? result.improvements : 
                           (typeof result.improvements === 'string' ? JSON.parse(result.improvements) : []);
        improvementsList.innerHTML = improvements.map(i => `<li>${i}</li>`).join('');
    }
    
    // Display resources
    const resourcesList = document.getElementById('resources-list-interview');
    if (resourcesList && result.suggested_resources) {
        const resources = Array.isArray(result.suggested_resources) ? result.suggested_resources : 
                         (typeof result.suggested_resources === 'string' ? JSON.parse(result.suggested_resources) : []);
        resourcesList.innerHTML = resources.map(r => `<li>${r}</li>`).join('');
    }
    
    // Display summary
    const summaryEl = document.getElementById('summary-text');
    if (summaryEl) {
        if (result.summary) {
            summaryEl.textContent = typeof result.summary === 'string' ? result.summary : 
                                   (result.summary.get ? result.summary.get('summary', '') : '');
        }
    }
    
    // Display practice recommendations
    const weakSkills = result.weak_skills || [];
    const practiceMaterials = result.practice_materials || {};
    if (weakSkills.length > 0 || Object.keys(practiceMaterials).length > 0) {
        displayPracticeRecommendations(weakSkills, practiceMaterials);
    } else if (currentSessionId) {
        // Try to fetch practice recommendations
        loadPracticeRecommendations(currentSessionId);
    }
    
    // Refresh Placement Readiness Score after interview completion
    if (typeof loadPlacementReadinessScore === 'function') {
        loadPlacementReadinessScore();
    }
}

// Display Practice Recommendations
function displayPracticeRecommendations(weak_skills, practice_materials) {
    const practiceSection = document.getElementById('practice-recommendations');
    if (!practiceSection) {
        // Create practice recommendations section if it doesn't exist
        const resultsSection = document.getElementById('interview-results');
        if (resultsSection) {
            const practiceDiv = document.createElement('div');
            practiceDiv.id = 'practice-recommendations';
            practiceDiv.className = 'practice-recommendations-section';
            resultsSection.appendChild(practiceDiv);
        } else {
            return;
        }
    }
    
    if (!weak_skills || weak_skills.length === 0) {
        practiceSection.innerHTML = '<p style="text-align: center; color: rgba(232,236,243,0.6);">No weak skills detected. Great job!</p>';
        return;
    }
    
    let html = '<h3>🎯 Recommended Practice Based on Weak Areas</h3>';
    
    for (const skill of weak_skills) {
        const practice = practice_materials[skill] || {
            mcq_count: 5,
            coding_count: 1,
            interview_questions_count: 1,
            practice_description: `Practice ${skill}`,
            difficulty_level: 'intermediate'
        };
        
        html += `
            <div class="practice-skill-card">
                <div class="practice-skill-header">
                    <h4>${skill}</h4>
                    <span class="difficulty-badge ${practice.difficulty_level}">${practice.difficulty_level}</span>
                </div>
                <p class="practice-description">${practice.practice_description}</p>
                <div class="practice-recommendations">
                    ${practice.mcq_count > 0 ? `<div class="practice-item"><span class="practice-icon">📝</span> <strong>${practice.mcq_count}</strong> MCQ Questions</div>` : ''}
                    ${practice.coding_count > 0 ? `<div class="practice-item"><span class="practice-icon">💻</span> <strong>${practice.coding_count}</strong> Coding Problems</div>` : ''}
                    ${practice.interview_questions_count > 0 ? `<div class="practice-item"><span class="practice-icon">🎤</span> <strong>${practice.interview_questions_count}</strong> Interview Questions</div>` : ''}
                </div>
            </div>
        `;
    }
    
    practiceSection.innerHTML = html;
    practiceSection.style.display = 'block';
}

// Load Practice Recommendations
async function loadPracticeRecommendations(sessionId) {
    try {
        const data = await interviewAPI.getPracticeRecommendations(sessionId);
        displayPracticeRecommendations(data.weak_skills || [], data.practice_materials || {});
    } catch (error) {
        console.error('Error loading practice recommendations:', error);
    }
}

// End Interview Automatically (without confirmation)
async function endInterviewAutomatically() {
    if (!currentSessionId) return;
    
    // Stop all media immediately when interview ends automatically
    cleanupInterviewMedia();
    
    try {
        const result = await interviewAPI.endInterview(currentSessionId);
        showInterviewResults(result);
    } catch (error) {
        // Ensure media is stopped even if API call fails
        cleanupInterviewMedia();
        
        // Use custom alert for errors
        if (typeof customAlert === 'function') {
            await customAlert(`Error ending interview: ${error.message}`, 'Error', '❌', 'error');
        } else {
            alert(`Error ending interview: ${error.message}`);
        }
    }
}

// End Interview Early (with confirmation)
async function endInterviewEarly() {
    if (!currentSessionId) return;
    
    // Use custom confirm modal
    let confirmed = false;
    if (typeof customConfirm === 'function') {
        confirmed = await customConfirm(
            'Are you sure you want to end the interview? You will receive results based on your answers so far.',
            'End Interview',
            '❓',
            'OK',
            'Cancel'
        );
    } else {
        // Fallback to native confirm
        confirmed = confirm('Are you sure you want to end the interview? You will receive results based on your answers so far.');
    }
    
    if (!confirmed) {
        return;
    }
    
    // Stop all media immediately when user confirms ending
    cleanupInterviewMedia();
    
    try {
        const result = await interviewAPI.endInterview(currentSessionId);
        showInterviewResults(result);
    } catch (error) {
        // Ensure media is stopped even if API call fails
        cleanupInterviewMedia();
        
        // Use custom alert for errors
        if (typeof customAlert === 'function') {
            await customAlert(`Error ending interview: ${error.message}`, 'Error', '❌', 'error');
        } else {
            alert(`Error ending interview: ${error.message}`);
        }
    }
}

// Cleanup function to stop camera, mic, and speech recognition
function cleanupInterviewMedia() {
    console.log('[Interview] Starting media cleanup...');
    
    // Stop proctoring
    if (typeof stopProctoring === 'function') {
        try {
            stopProctoring();
            console.log('[Interview] ✅ Proctoring stopped');
        } catch (e) {
            console.error('[Interview] Error stopping proctoring:', e);
        }
    }
    
    // Stop speech recognition
    if (recognition) {
        try {
            recognition.stop();
            console.log('[Interview] ✅ Speech recognition stopped');
        } catch (e) {
            console.log('[Interview] Speech recognition already stopped');
        }
        recognition = null;
        isRecording = false;
    }
    
    
    // Stop continuous face verification
    if (typeof stopContinuousFaceVerification === 'function') {
        try {
            stopContinuousFaceVerification();
            console.log('[Interview] ✅ Face verification stopped');
        } catch (e) {
            console.error('[Interview] Error stopping face verification:', e);
        }
    }
    
    // Stop audio detection
    if (typeof stopAudioDetection === 'function') {
        try {
            stopAudioDetection();
            console.log('[Interview] ✅ Audio detection stopped');
        } catch (e) {
            console.error('[Interview] Error stopping audio detection:', e);
        }
    }
    
    // Stop device detection
    if (typeof stopDeviceDetection === 'function') {
        try {
            stopDeviceDetection();
            console.log('[Interview] ✅ Device detection stopped');
        } catch (e) {
            console.error('[Interview] Error stopping device detection:', e);
        }
    }
    
    // Stop camera and microphone streams
    if (interviewStream) {
        try {
            interviewStream.getTracks().forEach(track => {
                track.stop();
                console.log('[Interview] ✅ Stopped media track:', track.kind, track.label || '');
            });
            interviewStream = null;
            console.log('[Interview] ✅ Interview stream cleared');
        } catch (e) {
            console.error('[Interview] Error stopping interview stream:', e);
        }
    }
    
    // Clear video element and stop all tracks
    const videoElement = document.getElementById('interview-video');
    if (videoElement) {
        try {
            // Stop all tracks in the video stream before clearing
            if (videoElement.srcObject) {
                const stream = videoElement.srcObject;
                stream.getTracks().forEach(track => {
                    track.stop();
                    console.log('[Interview] ✅ Stopped video element track:', track.kind);
                });
            }
            videoElement.srcObject = null;
            videoElement.muted = false;  // Reset muted state
            console.log('[Interview] ✅ Video element cleared');
        } catch (e) {
            console.error('[Interview] Error clearing video element:', e);
        }
    }
    
    // Also check for any other video elements that might have streams
    const allVideos = document.querySelectorAll('video');
    allVideos.forEach(video => {
        if (video.srcObject) {
            try {
                video.srcObject.getTracks().forEach(track => {
                    track.stop();
                    console.log('[Interview] ✅ Stopped additional video track:', track.kind);
                });
                video.srcObject = null;
            } catch (e) {
                console.error('[Interview] Error stopping additional video:', e);
            }
        }
    });
    
    // Hide recording indicator
    const indicator = document.getElementById('recording-indicator');
    if (indicator) {
        indicator.style.display = 'none';
        console.log('[Interview] ✅ Recording indicator hidden');
    }
    
    // Update global references
    if (typeof window !== 'undefined') {
        window.interviewStream = null;
        window.recognition = null;
        window.isRecording = false;
    }
    
    console.log('[Interview] ✅ Media cleanup completed successfully');
}

// Start New Interview
function startNewInterview() {
    // Cleanup any existing media first
    cleanupInterviewMedia();
    
    // Reset state
    currentSessionId = null;
    currentInterviewType = null;
    interviewResumeData = null;
    interviewJDData = null;
    interviewResumeText = '';
    interviewJDText = '';
    
    // Update global references
    if (typeof window !== 'undefined') {
        window.currentSessionId = null;
        window.currentTranscript = '';
    }
    
    // Hide results, show type selection
    document.getElementById('interview-results').style.display = 'none';
    document.getElementById('interview-type-selection').style.display = 'block';
    
    // Clear file inputs
    document.getElementById('resume-file').value = '';
    document.getElementById('jd-file').value = '';
    document.getElementById('resume-text').value = '';
    document.getElementById('job-description').value = '';
    document.getElementById('resume-file-name').innerHTML = '';
    document.getElementById('jd-file-name').innerHTML = '';
}

function goToDashboard() {
    startNewInterview();
    showDashboard();
}

// Camera and Microphone
async function requestCameraAndMicrophone() {
    try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Camera and microphone access not supported');
        }
        
        // Request media with proper audio constraints to prevent echo
        interviewStream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'user',
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
            videoElement.playsInline = true;
            videoElement.muted = true;  // Extra safety: mute video element
            videoElement.setAttribute('muted', 'true');  // HTML5 muted attribute
            
            await videoElement.play();
            
            console.log('Video stream attached (audio tracks excluded)');
            console.log('Audio tracks available for processing:', interviewStream.getAudioTracks().length);
        }
    } catch (error) {
        console.warn('Camera access failed:', error);
        // Continue without camera - it's optional
    }
}

// Speech Recognition
function initializeSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.warn('Speech recognition not supported');
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
        
        // Update global reference
        if (typeof window !== 'undefined') {
            window.currentTranscript = currentTranscript;
        }
        
        // Update textarea
        const answerText = document.getElementById('answer-text');
        if (answerText) {
            answerText.value = currentTranscript;
        }
    };
    
    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        if (event.error !== 'no-speech') {
            stopVoiceRecording();
        }
    };
    
    recognition.onend = () => {
        if (isRecording) {
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
        alert('Speech recognition not available');
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

// Cleanup on page unload (browser close/refresh)
window.addEventListener('beforeunload', () => {
    cleanupInterviewMedia();
});

// Cleanup when page becomes hidden (tab switch, minimize)
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Optional: cleanup when tab is hidden
        // Uncomment if you want to stop media when tab is switched
        // cleanupInterviewMedia();
    }
});

