"""
Enhanced AI Virtual Interview routes for TR and HR interview types
Supports interview type selection, resume/JD upload, and structured interview flow
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.file_extractor import extract_text_from_file
from utils.resume_processor import process_resume, process_job_description
from utils.resume_nlp import process_resume_advanced, process_job_description_advanced
from utils.career_intelligence_engine import analyze_resume_intelligence
from utils.interview_ai import (
    generate_interview_question, determine_phase_tr, determine_phase_hr,
    evaluate_answer, calculate_final_score_tr, calculate_final_score_hr,
    generate_interview_summary, generate_practice_materials
)
from utils.adaptive_interview_engine import (
    InterviewState, AnswerAnalyzer, DecisionEngine, MemoryLayer,
    TopicFlowController, AdaptiveQuestionGenerator, update_interview_state
)
# New FastAPI-based AI Interviewer
try:
    from interview_ai_fastapi import process_interview_answer, InterviewMemory as FastAPIInterviewMemory
    from interview_summary_generator import generate_interview_summary
    FASTAPI_AI_AVAILABLE = True
except ImportError:
    FASTAPI_AI_AVAILABLE = False
    print("[Interview] FastAPI AI Interviewer not available, using fallback")
    generate_interview_summary = None
from utils.async_utils import run_in_background, get_task_status
from models import db, InterviewSession, ResumeData, JobDescriptionData, InterviewAnswer, InterviewResult, Notification
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import tempfile
import json

# WebSocket support (optional)
try:
    from utils.websocket_handler import emit_proctoring_status, emit_warning, emit_interview_status
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    def emit_proctoring_status(*args, **kwargs): pass
    def emit_warning(*args, **kwargs): pass
    def emit_interview_status(*args, **kwargs): pass

interview_bp = Blueprint('interview', __name__)

@interview_bp.route('/status', methods=['GET'])
def interview_status():
    """Health/status endpoint for the AI virtual interview module."""
    return jsonify({
        'available': True,
        'enabled': True,
        'features': {
            'resume_upload': True,
            'job_description_upload': True,
            'ai_questions': True,
            'face_verification': True
        }
    }), 200

@interview_bp.route('/session/<int:session_id>', methods=['GET'])
@jwt_required()
def get_session(session_id):
    """
    Get interview session state for rehydration
    GET /api/interview/session/<session_id>
    """
    try:
        user_id = get_jwt_identity()
        session = InterviewSession.query.get(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        if session.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({
            'session_id': session.id,
            'interview_state': session.interview_state,
            'conversation': session.conversation,
            'question_number': session.question_number,
            'total_questions': session.total_questions,
            'is_completed': session.is_completed
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/select-interview-type', methods=['POST'])
@jwt_required()
def select_interview_type():
    """
    STEP 1: Select interview type (TR or HR)
    POST /api/interview/select-interview-type
    Body: { "interview_type": "TR" | "HR" }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        interview_type = data.get('interview_type', '').upper()
        
        if interview_type not in ['TR', 'HR']:
            return jsonify({'error': 'Invalid interview type. Must be "TR" (Technical) or "HR"'}), 400
        
        # Store interview type in session (could use Flask session or return to frontend to store)
        # For now, we'll return it and frontend can pass it to subsequent requests
        return jsonify({
            'message': 'Interview type selected',
            'interview_type': interview_type,
            'next_step': 'upload_resume_jd'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/upload-resume', methods=['POST'])
@jwt_required()
def upload_resume():
    """
    STEP 2: Upload and process resume
    POST /api/interview/upload-resume
    Form data: file (PDF, JPG, PNG, TXT)
    """
    try:
        user_id = get_jwt_identity()
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'txt', 'docx', 'doc']
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Unsupported file type. Allowed: {", ".join(allowed_extensions)}'}), 400
        
        # Save file temporarily
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"{user_id}_{filename}")
        file.save(temp_file_path)
        
        try:
            # Process resume asynchronously for better performance
            def process_resume_async(file_path, ext):
                """Async resume processing function"""
                try:
                    # Extract text from file
                    extracted_text = extract_text_from_file(file_path, ext)
                    
                    # Process resume using advanced NLP (with fallback to basic)
                    try:
                        resume_data = process_resume_advanced(extracted_text)
                        processing_method = 'advanced_nlp'
                    except Exception as e:
                        print(f"[Interview] Advanced NLP failed, using fallback: {e}")
                        resume_data = process_resume(extracted_text)
                        processing_method = 'basic'
                    
                    return {
                        'success': True,
                        'resume_text': extracted_text,
                        'resume_data': resume_data,
                        'processing_method': processing_method
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'error': str(e)
                    }
            
            # Run processing in background for large files, synchronous for small files
            file_size = os.path.getsize(temp_file_path) if os.path.exists(temp_file_path) else 0
            use_async = file_size > 1024 * 1024  # Use async for files > 1MB
            
            if use_async:
                # Process asynchronously
                task_id = run_in_background(process_resume_async, temp_file_path, file_ext)
                return jsonify({
                    'message': 'Resume upload accepted, processing in background',
                    'task_id': task_id,
                    'status': 'processing',
                    'filename': filename
                }), 202  # Accepted - processing
            else:
                # Process synchronously for small files
                result = process_resume_async(temp_file_path, file_ext)
                
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                
                if result['success']:
                    # ===== CAREER INTELLIGENCE ENGINE =====
                    # Perform comprehensive career intelligence analysis
                    career_intelligence = analyze_resume_intelligence(result['resume_text'])
                    
                    # Merge intelligence into resume_data
                    resume_data = result['resume_data']
                    resume_data['career_intelligence'] = career_intelligence
                    resume_data['skill_strengths'] = career_intelligence.get('skill_strengths', {})
                    resume_data['experience_depth'] = career_intelligence.get('experience_depth', {})
                    resume_data['career_path'] = career_intelligence.get('career_path', {})
                    resume_data['analyzed_projects'] = career_intelligence.get('projects', [])
                    resume_data['intelligence_summary'] = career_intelligence.get('summary', {})
                    # ===== END CAREER INTELLIGENCE ENGINE =====
                    
                    return jsonify({
                        'message': 'Resume uploaded and processed successfully',
                        'resume_text': result['resume_text'][:500] + '...' if len(result['resume_text']) > 500 else result['resume_text'],
                        'resume_data': resume_data,
                        'filename': filename,
                        'processing_method': result['processing_method'],
                        'career_intelligence': career_intelligence  # Full intelligence report
                    }), 200
                else:
                    return jsonify({'error': f'Error processing resume: {result["error"]}'}), 500
        
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return jsonify({'error': f'Error processing resume: {str(e)}'}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/upload-jd', methods=['POST'])
@jwt_required()
def upload_jd():
    """
    STEP 2: Upload and process Job Description
    POST /api/interview/upload-jd
    Form data: file (PDF, TXT)
    Body (optional): resume_skills (JSON array) for skill mapping
    """
    try:
        user_id = get_jwt_identity()
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        allowed_extensions = ['pdf', 'txt', 'jpg', 'jpeg', 'png', 'docx', 'doc']
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Unsupported file type. Allowed: PDF, DOCX, TXT, JPG, PNG'}), 400
        
        # Get resume skills from request if provided (for skill mapping)
        resume_skills = request.form.get('resume_skills')
        if resume_skills:
            try:
                resume_skills = json.loads(resume_skills)
            except:
                resume_skills = None
        
        # Save file temporarily
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"{user_id}_jd_{filename}")
        file.save(temp_file_path)
        
        try:
            # Extract text from file
            extracted_text = extract_text_from_file(temp_file_path, file_ext)
            
            # Process JD using advanced NLP (with fallback to basic)
            try:
                # Get resume data if available for advanced matching
                resume_data = None
                if resume_skills:
                    # Create minimal resume_data structure for matching
                    resume_data = {'skills': resume_skills}
                
                jd_data = process_job_description_advanced(extracted_text, resume_data)
                processing_method = 'advanced_nlp'
            except Exception as e:
                print(f"[Interview] Advanced NLP failed, using fallback: {e}")
                jd_data = process_job_description(extracted_text, resume_skills)
                processing_method = 'basic'
            
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            # ===== CAREER INTELLIGENCE ENGINE =====
            # If resume data is available in session, calculate role suitability
            role_suitability = None
            if resume_skills:
                # Get resume intelligence from session if available
                # For now, create basic structure for role fit calculation
                from utils.career_intelligence_engine import RoleSuitabilityEngine
                resume_intelligence = {
                    'skill_strengths': {skill: 0.7 for skill in resume_skills},  # Default strength
                    'experience_depth': {'overall_depth': 0.6, 'career_level': 'Developer'},
                    'projects': [],
                    'total_experience_years': 2
                }
                role_suitability = RoleSuitabilityEngine.calculate_role_fit(resume_intelligence, jd_data)
                jd_data['role_suitability'] = role_suitability
            # ===== END CAREER INTELLIGENCE ENGINE =====
            
            return jsonify({
                'message': 'Job description uploaded and processed successfully',
                'jd_text': extracted_text[:500] + '...' if len(extracted_text) > 500 else extracted_text,
                'jd_data': jd_data,
                'filename': filename,
                'processing_method': processing_method,
                'role_suitability': role_suitability  # Role fit analysis if resume available
            }), 200
        
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return jsonify({'error': f'Error processing job description: {str(e)}'}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/start-interview', methods=['POST'])
@jwt_required()
def start_interview():
    """
    STEP 3 & 4: Start interview session
    POST /api/interview/start-interview
    Body: {
        "interview_type": "TR" | "HR",
        "resume_text": "...",
        "job_description": "...",
        "resume_data": {...},
        "jd_data": {...},
        "resume_file_path": "...",
        "jd_file_path": "..."
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        interview_type = data.get('interview_type', 'TR').upper()
        resume_text = data.get('resume_text', '')
        job_description = data.get('job_description', '')
        resume_data_dict = data.get('resume_data', {})
        jd_data_dict = data.get('jd_data', {})
        resume_file_path = data.get('resume_file_path', '')
        jd_file_path = data.get('jd_file_path', '')
        selfie_session_id = data.get('selfie_session_id')  # Link to selfie session
        
        if interview_type not in ['TR', 'HR']:
            return jsonify({'error': 'Invalid interview type. Must be "TR" or "HR"'}), 400
        
        # Enhanced NLP matching if both resume and JD are provided
        if resume_text and job_description and (not resume_data_dict or not jd_data_dict):
            try:
                # Process with advanced NLP for better matching
                if not resume_data_dict:
                    resume_data_dict = process_resume_advanced(resume_text)
                if not jd_data_dict:
                    jd_data_dict = process_job_description_advanced(job_description, resume_data_dict)
            except Exception as e:
                print(f"[Interview] Advanced NLP processing failed, using provided data: {e}")
                # Fallback to basic processing if advanced fails
                if not resume_data_dict:
                    resume_data_dict = process_resume(resume_text)
                if not jd_data_dict:
                    jd_data_dict = process_job_description(job_description, resume_data_dict.get('skills'))
        
        # ===== CAREER INTELLIGENCE ENGINE =====
        # Perform comprehensive career intelligence analysis
        if resume_text:
            career_intelligence = analyze_resume_intelligence(resume_text, jd_data_dict)
            
            # Merge intelligence into resume_data_dict
            if resume_data_dict:
                resume_data_dict['career_intelligence'] = career_intelligence
                resume_data_dict['skill_strengths'] = career_intelligence.get('skill_strengths', {})
                resume_data_dict['experience_depth'] = career_intelligence.get('experience_depth', {})
                resume_data_dict['career_path'] = career_intelligence.get('career_path', {})
                resume_data_dict['analyzed_projects'] = career_intelligence.get('projects', [])
                resume_data_dict['intelligence_summary'] = career_intelligence.get('summary', {})
            
            # Add role suitability to jd_data_dict
            if jd_data_dict and career_intelligence.get('role_suitability'):
                jd_data_dict['role_suitability'] = career_intelligence.get('role_suitability')
        # ===== END CAREER INTELLIGENCE ENGINE =====
        
        # Calculate dynamic number of questions based on resume and JD
        from utils.interview_ai import calculate_total_questions
        
        # Determine experience level from resume data
        experience_level = 'fresher'  # Default
        if resume_data_dict:
            experience_years = resume_data_dict.get('experience_years', 0)
            if experience_years >= 3:
                experience_level = 'experienced'
            elif experience_years >= 1:
                experience_level = 'intermediate'
        
        # Calculate total questions dynamically
        total_questions = calculate_total_questions(
            interview_type=interview_type,
            resume_data=resume_data_dict,
            jd_data=jd_data_dict,
            experience_level=experience_level
        )
        
        # If selfie_session_id provided, get selfie embedding from that session
        selfie_embedding = None
        selfie_registered_at = None
        if selfie_session_id:
            temp_session = InterviewSession.query.filter_by(id=selfie_session_id, user_id=user_id).first()
            if temp_session and temp_session.selfie_embedding:
                selfie_embedding = temp_session.selfie_embedding
                selfie_registered_at = temp_session.selfie_registered_at
        
        # Initialize adaptive interview state
        interview_state = InterviewState(interview_type, resume_data_dict, jd_data_dict)
        
        # Initialize topics from resume and JD
        topics = TopicFlowController.initialize_topics(interview_state)
        if topics:
            interview_state.current_topic = topics[0]
            interview_state.topics_covered.append(topics[0])
        
        # Initialize adaptive interview state
        interview_state = InterviewState(interview_type, resume_data_dict, jd_data_dict)
        
        # Initialize topics from resume and JD
        topics = TopicFlowController.initialize_topics(interview_state)
        if topics:
            interview_state.current_topic = topics[0]
            interview_state.topics_covered.append(topics[0])
        
        # Create interview session
        session = InterviewSession(
            user_id=user_id,
            resume_text=resume_text,
            job_description=job_description,
            interview_type=interview_type,
            experience_level=experience_level,
            resume_file_path=resume_file_path,
            jd_file_path=jd_file_path,
            current_phase='introduction',
            question_number=0,
            total_questions=total_questions,  # Dynamic based on resume and JD
            selfie_embedding=selfie_embedding,  # Copy selfie embedding to interview session
            selfie_registered_at=selfie_registered_at
        )
        
        db.session.add(session)
        db.session.flush()  # Get session.id
        
        # Store resume data
        if resume_data_dict:
            resume_data = ResumeData(
                session_id=session.id,
                skills=json.dumps(resume_data_dict.get('skills', [])),
                programming_languages=json.dumps(resume_data_dict.get('programming_languages', [])),
                projects=json.dumps(resume_data_dict.get('projects', [])),
                certificates=json.dumps(resume_data_dict.get('certificates', [])),
                experience_years=resume_data_dict.get('experience_years', 0)
            )
            db.session.add(resume_data)
        
        # Store JD data
        if jd_data_dict:
            # Truncate job_title to 200 characters (database limit)
            job_title = jd_data_dict.get('job_title')
            if job_title and len(job_title) > 200:
                job_title = job_title[:200].strip()
            
            # Truncate experience_required to 50 characters (database limit)
            experience_required = jd_data_dict.get('experience_required')
            if experience_required and len(experience_required) > 50:
                experience_required = experience_required[:50].strip()
            
            jd_data = JobDescriptionData(
                session_id=session.id,
                required_skills=json.dumps(jd_data_dict.get('required_skills', [])),
                matching_skills=json.dumps(jd_data_dict.get('matching_skills', [])),
                missing_skills=json.dumps(jd_data_dict.get('missing_skills', [])),
                job_title=job_title,
                experience_required=experience_required
            )
            db.session.add(jd_data)
        
        db.session.commit()
        
        # Generate first question: "Introduce yourself"
        first_question = generate_interview_question(
            interview_type=interview_type,
            resume_text=resume_text,
            job_description=job_description,
            phase='introduction',
            question_number=0,
            conversation_history=[],
            experience_level=experience_level,
            resume_data=resume_data_dict,
            jd_data=jd_data_dict
        )
        
        # Ensure question is not empty
        if not first_question or first_question.strip() == '':
            print("[Interview] Warning: Generated question is empty, using fallback")
            if interview_type == 'TR':
                first_question = "Please introduce yourself and tell us about your technical background, including your programming experience and any projects you've worked on."
            else:
                first_question = "Please introduce yourself and tell us about your background, your career goals, and why you're interested in this role."
        
        print(f"[Interview] Generated first question: {first_question[:100]}...")
        
        # Update session
        session.question_number = 1
        session.total_questions_asked = 1
        
        # Add first question to conversation (with state)
        initial_conversation.append({
            'type': 'question',
            'content': first_question,
            'phase': 'introduction',
            'question_number': 1,
            'timestamp': datetime.utcnow().isoformat()
        })
        session.conversation = json.dumps(initial_conversation)
        db.session.commit()
        
        return jsonify({
            'session_id': session.id,
            'question': first_question,
            'interview_type': interview_type,
            'phase': 'introduction',
            'question_number': 1,
            'total_questions': session.total_questions
        }), 200
    
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error starting interview: {error_trace}")  # Log full error for debugging
        # Return user-friendly error message
        error_msg = str(e)
        if 'Unknown column' in error_msg or 'resume_file_path' in error_msg or 'final_score' in error_msg or 'score_breakdown' in error_msg:
            error_msg = 'Database schema mismatch. Please run: python backend/migrate_interview_columns.py'
        return jsonify({
            'error': error_msg,
            'error_type': type(e).__name__
        }), 500

@interview_bp.route('/submit-answer', methods=['POST'])
@jwt_required()
def submit_answer():
    """
    STEP 6: Submit answer and get next question
    POST /api/interview/submit-answer
    Body: {
        "session_id": 123,
        "answer": "...",
        "time_taken_seconds": 120
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        session_id = data.get('session_id')
        answer = data.get('answer', '')
        time_taken_seconds = data.get('time_taken_seconds', 0)
        
        if not session_id or not answer:
            return jsonify({'error': 'Session ID and answer required'}), 400
        
        # Get session
        session = InterviewSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        if session.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        if session.is_completed:
            return jsonify({'error': 'Interview already completed'}), 400
        
        # Load conversation and resume/JD data
        conversation = json.loads(session.conversation) if session.conversation else []
        
        # Get last question
        last_question = None
        last_phase = 'introduction'
        for msg in reversed(conversation):
            if msg.get('type') == 'question':
                last_question = msg.get('content')
                last_phase = msg.get('phase', 'introduction')
                break
        
        if not last_question:
            return jsonify({'error': 'No question found'}), 400
        
        # Get resume and JD data
        resume_data_obj = ResumeData.query.filter_by(session_id=session_id).first()
        jd_data_obj = JobDescriptionData.query.filter_by(session_id=session_id).first()
        
        resume_data = resume_data_obj.to_dict() if resume_data_obj else None
        jd_data = jd_data_obj.to_dict() if jd_data_obj else None
        
        # ===== NEW FASTAPI-BASED AI INTERVIEWER =====
        # Load interview memory from Redis first (for persistence), then from session
        interview_memory_dict = None
        
        # Try loading from Redis first (most reliable)
        if FASTAPI_AI_AVAILABLE:
            try:
                from interview_ai_fastapi import load_interview_memory
                redis_memory = load_interview_memory(session_id)
                if redis_memory:
                    interview_memory_dict = redis_memory
                    print(f"[Interview] Loaded memory from Redis for session {session_id}")
            except Exception as e:
                print(f"[Interview] Error loading from Redis: {e}")
        
        # Fallback to session.interview_state if Redis not available
        if not interview_memory_dict and session.interview_state:
            try:
                interview_memory_dict = json.loads(session.interview_state)
            except:
                pass
        
        # If no memory exists, create new one
        if not interview_memory_dict:
            if FASTAPI_AI_AVAILABLE:
                interview_memory = FastAPIInterviewMemory(
                    interview_type=session.interview_type,
                    resume_data=resume_data or {},
                    jd_data=jd_data or {}
                )
                interview_memory.start_time = datetime.utcnow()
                interview_memory.question_count = session.question_number
                interview_memory.total_questions = session.total_questions
                interview_memory_dict = interview_memory.to_dict()
            else:
                # Fallback to old system
                interview_memory_dict = None
        
        # Use new FastAPI AI if available
        if FASTAPI_AI_AVAILABLE and interview_memory_dict:
            try:
                # Process answer using new AI interviewer (with session_id for memory persistence)
                result = process_interview_answer(
                    interview_memory_dict=interview_memory_dict,
                    current_question=last_question,
                    user_answer=answer,
                    session_id=session_id  # Pass session_id for Redis persistence
                )
                
                # Extract results
                analysis = result.get('analysis', {})
                updated_memory = result.get('updated_memory', interview_memory_dict)
                decision = result.get('decision', 'continue')
                decision_reason = result.get('decision_reason', '')
                next_question = result.get('next_question', 'Can you tell me more?')
                
                # Convert to evaluation format
                evaluation = {
                    'feedback': f"{analysis.get('strengths', [])} {analysis.get('weaknesses', [])}".strip() or 'Good answer.',
                    'correctness': analysis.get('correctness', 5.0),
                    'clarity': analysis.get('clarity', 5.0),
                    'depth': analysis.get('depth', 5.0),
                    'confidence': analysis.get('confidence', 5.0),
                    'overall_score': analysis.get('overall_score', 5.0),
                    'contradiction_detected': analysis.get('contradiction_detected', False),
                    'difficulty_level': updated_memory.get('current_difficulty', 'medium').title(),
                    'follow_up_needed': analysis.get('follow_up_needed', False),
                    'follow_up_reason': analysis.get('follow_up_reason', ''),
                    'topic': analysis.get('topic', 'general')
                }
                
                # Update session with new memory
                session.interview_state = json.dumps(updated_memory)
                
                # Determine if follow-up is needed
                follow_up_needed = decision in ['followup', 'clarification']
                
            except Exception as e:
                print(f"[Interview] FastAPI AI error: {e}")
                import traceback
                traceback.print_exc()
                # Fallback to old system
                FASTAPI_AI_AVAILABLE = False
        
        # Fallback to old adaptive engine if FastAPI AI not available
        if not FASTAPI_AI_AVAILABLE or not interview_memory_dict:
            # ===== OLD ADAPTIVE INTERVIEW ENGINE (FALLBACK) =====
            # Load interview state from conversation (stored as state message)
            interview_state = None
            for msg in reversed(conversation):
                if msg.get('type') == 'state' and 'interview_state' in msg:
                    try:
                        state_dict = msg.get('interview_state')
                        interview_state = InterviewState.from_dict(state_dict, resume_data, jd_data)
                        break
                    except Exception as e:
                        print(f"[Adaptive Interview] Error loading state: {e}")
                        break
            
            # If no state found, initialize new one
            if not interview_state:
                interview_state = InterviewState(session.interview_type, resume_data, jd_data)
                # Initialize topics
                topics = TopicFlowController.initialize_topics(interview_state)
                if topics:
                    interview_state.current_topic = topics[0]
                    interview_state.topics_covered.append(topics[0])
            
            # Analyze answer using adaptive engine
            analysis = AnswerAnalyzer.analyze_answer(
                question=last_question,
                answer=answer,
                interview_state=interview_state,
                conversation_history=conversation
            )
            
            # Detect contradictions using memory layer
            claims = MemoryLayer.extract_claims(answer, analysis)
            contradiction_detected, contradiction_details = MemoryLayer.detect_contradictions(
                answer, claims, interview_state
            )
            
            # Update analysis with contradiction detection
            if contradiction_detected:
                analysis['contradiction_detected'] = True
                analysis['contradiction_details'] = contradiction_details
            
            # Make decision on next action
            decision = DecisionEngine.decide_next_action(interview_state, analysis)
            
            # Update interview state
            update_interview_state(interview_state, last_question, answer, analysis, decision)
            
            # Generate adaptive question based on decision
            next_question = AdaptiveQuestionGenerator.generate_adaptive_question(
                interview_state=interview_state,
                decision=decision,
                conversation_history=conversation
            )
            
            # Convert analysis to evaluation format (for backward compatibility)
            evaluation = {
                'feedback': analysis.get('follow_up_reason', 'Good answer.') if analysis.get('needs_follow_up') else 'Good answer.',
                'correctness': analysis.get('correctness', 0.5) * 10,  # Convert 0-1 to 0-10
                'clarity': analysis.get('clarity', 0.5) * 10,
                'depth': analysis.get('depth', 0.5) * 10,
                'confidence': analysis.get('confidence', 0.5) * 10,
                'overall_score': analysis.get('score', 0.5) * 10,
                'contradiction_detected': analysis.get('contradiction_detected', False),
                'difficulty_level': ['Easy', 'Medium', 'Hard', 'Very Hard', 'Expert'][min(4, interview_state.difficulty_level - 1)],
                'follow_up_needed': analysis.get('needs_follow_up', False),
                'follow_up_reason': analysis.get('follow_up_reason', ''),
                'weakness_indicators': analysis.get('weakness_indicators', []),
                'strength_indicators': analysis.get('strength_indicators', [])
            }
            
            follow_up_needed = decision.get('action') == 'follow_up' or decision.get('action') == 'clarify_contradiction'
            # ===== END OLD ADAPTIVE INTERVIEW ENGINE =====
        
        # Save answer to database
        interview_answer = InterviewAnswer(
            session_id=session_id,
            question_number=session.question_number,
            question=last_question,
            answer=answer,
            phase=last_phase,
            correctness_score=evaluation['correctness'],
            clarity_score=evaluation['clarity'],
            confidence_score=evaluation['confidence'],
            overall_score=evaluation['overall_score'],
            feedback=evaluation['feedback'],
            time_taken_seconds=time_taken_seconds
        )
        # Note: depth_score, contradiction_detected, difficulty_level stored in conversation
        db.session.add(interview_answer)
        
        # Add answer and evaluation to conversation
        conversation.append({
            'type': 'answer',
            'content': answer,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        conversation.append({
            'type': 'evaluation',
            'feedback': evaluation['feedback'],
            'correctness': evaluation['correctness'],
            'clarity': evaluation['clarity'],
            'depth': evaluation.get('depth', 0),
            'confidence': evaluation['confidence'],
            'overall_score': evaluation['overall_score'],
            'contradiction_detected': evaluation.get('contradiction_detected', False),
            'difficulty_level': evaluation.get('difficulty_level', 'Medium'),
            'follow_up_needed': evaluation.get('follow_up_needed', False),
            'follow_up_reason': evaluation.get('follow_up_reason', ''),
            'timestamp': datetime.utcnow().isoformat()
        })
        
        session.total_answers += 1
        
        # ===== FLOW CONTROL =====
        # follow_up_needed is already set above (from FastAPI AI or old system)
        difficulty_level = evaluation.get('difficulty_level', 'Medium')
        
        # Check if interview should complete
        if FASTAPI_AI_AVAILABLE and session.interview_state:
            # Use updated memory to check completion
            try:
                updated_memory = json.loads(session.interview_state)
                question_count = updated_memory.get('question_count', session.question_number)
                total_questions = updated_memory.get('total_questions', session.total_questions)
                
                if question_count >= total_questions:
                    # Interview complete
                    return complete_interview(session, conversation, resume_data, jd_data, interview_answer)
            except:
                pass
        elif not FASTAPI_AI_AVAILABLE and 'interview_state' in locals() and interview_state:
            # Old system check
            if hasattr(interview_state, 'total_questions') and interview_state.total_questions >= getattr(interview_state, 'max_questions', 10):
                return complete_interview(session, conversation, resume_data, jd_data, interview_answer)
        
        # Update phase and question number
        if not follow_up_needed:
            # Determine next phase (legacy system)
            if session.interview_type == 'TR':
                next_phase = determine_phase_tr(session.question_number + 1, resume_data, jd_data)
            else:
                next_phase = determine_phase_hr(session.question_number + 1)
            session.current_phase = next_phase
            session.question_number += 1
            session.total_questions_asked += 1
        # else: follow-up, don't increment question number
        # ===== END FLOW CONTROL =====
        
        # Add next question to conversation
        conversation.append({
            'type': 'question',
            'content': next_question,
            'phase': session.current_phase if not follow_up_needed else last_phase,
            'question_number': session.question_number if not follow_up_needed else session.question_number,
            'is_follow_up': follow_up_needed,
            'difficulty_level': difficulty_level,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Save interview state/memory to conversation
        if FASTAPI_AI_AVAILABLE and session.interview_state:
            # Save FastAPI memory
            try:
                memory_dict = json.loads(session.interview_state)
                state_found = False
                for msg in conversation:
                    if msg.get('type') == 'state':
                        msg['interview_memory'] = memory_dict
                        msg['timestamp'] = datetime.utcnow().isoformat()
                        state_found = True
                        break
                
                if not state_found:
                    conversation.insert(0, {
                        'type': 'state',
                        'interview_memory': memory_dict,
                        'timestamp': datetime.utcnow().isoformat()
                    })
            except:
                pass
        elif not FASTAPI_AI_AVAILABLE and 'interview_state' in locals() and interview_state:
            # Save old interview state
            state_found = False
            for msg in conversation:
                if msg.get('type') == 'state':
                    msg['interview_state'] = interview_state.to_dict()
                    msg['timestamp'] = datetime.utcnow().isoformat()
                    state_found = True
                    break
            
            if not state_found:
                conversation.insert(0, {
                    'type': 'state',
                    'interview_state': interview_state.to_dict(),
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        # Update session
        session.conversation = json.dumps(conversation)
        db.session.commit()
        
        return jsonify({
            'session_id': session.id,
            'feedback': evaluation['feedback'],
            'scores': {
                'correctness': evaluation['correctness'],
                'clarity': evaluation['clarity'],
                'depth': evaluation.get('depth', 0),
                'confidence': evaluation['confidence'],
                'overall': evaluation['overall_score']
            },
            'contradiction_detected': evaluation.get('contradiction_detected', False),
            'difficulty_level': difficulty_level,
            'follow_up_needed': follow_up_needed,
            'follow_up_reason': evaluation.get('follow_up_reason', ''),
            'next_question': next_question,
            'interview_type': session.interview_type,
            'phase': session.current_phase if not follow_up_needed else last_phase,
            'question_number': session.question_number,
            'total_questions': session.total_questions,
            # AI Interviewer metadata
            'ai_metadata': {
                'decision': decision if FASTAPI_AI_AVAILABLE else decision.get('action', 'continue') if 'decision' in locals() else 'continue',
                'decision_reason': decision_reason if FASTAPI_AI_AVAILABLE and 'decision_reason' in locals() else (decision.get('reason', '') if 'decision' in locals() else ''),
                'current_topic': (json.loads(session.interview_state).get('current_topic') if FASTAPI_AI_AVAILABLE and session.interview_state else None) or (interview_state.current_topic if not FASTAPI_AI_AVAILABLE and 'interview_state' in locals() and interview_state else None),
                'current_difficulty': (json.loads(session.interview_state).get('current_difficulty', 'medium') if FASTAPI_AI_AVAILABLE and session.interview_state else difficulty_level) if FASTAPI_AI_AVAILABLE else (difficulty_level if not FASTAPI_AI_AVAILABLE else 'medium'),
                'confidence_level': (json.loads(session.interview_state).get('confidence_level', 0.5) if FASTAPI_AI_AVAILABLE and session.interview_state else 0.5) if FASTAPI_AI_AVAILABLE else (interview_state.confidence_score if 'interview_state' in locals() and interview_state else 0.5),
                'weak_areas': (json.loads(session.interview_state).get('weak_topics', [])[:3] if FASTAPI_AI_AVAILABLE and session.interview_state else []) if FASTAPI_AI_AVAILABLE else (interview_state.weak_areas[:3] if 'interview_state' in locals() and interview_state else []),
                'strong_areas': (json.loads(session.interview_state).get('strong_topics', [])[:3] if FASTAPI_AI_AVAILABLE and session.interview_state else []) if FASTAPI_AI_AVAILABLE else (interview_state.strong_areas[:3] if 'interview_state' in locals() and interview_state else [])
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def complete_interview(session, conversation, resume_data, jd_data, last_answer):
    """Helper function to complete interview and calculate final results"""
    try:
        # Get all answers
        answers = InterviewAnswer.query.filter_by(session_id=session.id).order_by(InterviewAnswer.question_number).all()
        
        # Convert to list of dicts for scoring
        answers_list = []
        for ans in answers:
            answers_list.append({
                'phase': ans.phase,
                'overall_score': ans.overall_score,
                'correctness_score': ans.correctness_score,
                'clarity_score': ans.clarity_score,
                'confidence_score': ans.confidence_score
            })
        
        # Calculate final score based on interview type
        if session.interview_type == 'TR':
            score_result = calculate_final_score_tr(answers_list)
        else:
            score_result = calculate_final_score_hr(answers_list)
        
        # Generate summary using new AI interviewer summary generator
        summary_data = {}
        if FASTAPI_AI_AVAILABLE and generate_interview_summary and session.interview_state:
            try:
                # Use new AI summary generator
                interview_memory_dict = json.loads(session.interview_state)
                summary_data = generate_interview_summary(interview_memory_dict)
                
                # Map to old format for backward compatibility
                summary_data = {
                    'strengths': summary_data.get('strengths', []),
                    'weaknesses': summary_data.get('weaknesses', []),
                    'improvements': summary_data.get('improvement_roadmap', []),
                    'suggested_resources': [],
                    'weak_skills': summary_data.get('weaknesses', []),
                    'candidate_level': summary_data.get('candidate_level', 'junior'),
                    'hire_probability': summary_data.get('hire_probability', 50),
                    'communication_quality': summary_data.get('communication_quality', 'average'),
                    'learning_ability': summary_data.get('learning_ability', 'moderate')
                }
            except Exception as e:
                print(f"[Interview] Error generating AI summary: {e}")
                # Fallback to old summary generator
                summary_data = generate_interview_summary(
                    conversation_history=conversation,
                    interview_type=session.interview_type,
                    final_score=score_result['total_score'],
                    resume_text=session.resume_text,
                    job_description=session.job_description,
                    score_breakdown=score_result.get('breakdown')
                )
        else:
            # Use old summary generator
            summary_data = generate_interview_summary(
                conversation_history=conversation,
                interview_type=session.interview_type,
                final_score=score_result['total_score'],
                resume_text=session.resume_text,
                job_description=session.job_description,
                score_breakdown=score_result.get('breakdown')
            )
        
        # Generate practice materials based on weak skills (handle errors gracefully)
        weak_skills = summary_data.get('weak_skills', [])
        practice_materials = {}
        if weak_skills:
            try:
                practice_materials = generate_practice_materials(weak_skills, session.interview_type)
            except Exception as e:
                print(f"[Interview] Error generating practice materials: {e}")
                # Continue without practice materials - not critical
                practice_materials = {}
        
        # Save final result - check if it already exists (update instead of insert)
        result = InterviewResult.query.filter_by(session_id=session.id).first()
        
        if result:
            # Update existing result
            result.total_score = score_result['total_score']
            result.strengths = json.dumps(summary_data.get('strengths', []))
            result.weaknesses = json.dumps(summary_data.get('weaknesses', []))
            result.improvements = json.dumps(summary_data.get('improvements', []))
            result.suggested_resources = json.dumps(summary_data.get('suggested_resources', []))
        else:
            # Create new result
            result = InterviewResult(
                session_id=session.id,
                total_score=score_result['total_score'],
                strengths=json.dumps(summary_data.get('strengths', [])),
                weaknesses=json.dumps(summary_data.get('weaknesses', [])),
                improvements=json.dumps(summary_data.get('improvements', [])),
                suggested_resources=json.dumps(summary_data.get('suggested_resources', []))
            )
            db.session.add(result)
        
        # Set component scores
        breakdown = score_result.get('breakdown', {})
        if session.interview_type == 'TR':
            result.introduction_score = breakdown.get('introduction_score', 0)
            result.projects_resume_score = breakdown.get('projects_resume_score', 0)
            result.programming_score = breakdown.get('programming_score', 0)
            result.jd_gap_skills_score = breakdown.get('jd_gap_skills_score', 0)
            result.communication_score = breakdown.get('communication_score', 0)
        else:
            result.hr_introduction_score = breakdown.get('hr_introduction_score', 0)
            result.hr_communication_score = breakdown.get('hr_communication_score', 0)
            result.hr_confidence_score = breakdown.get('hr_confidence_score', 0)
            result.hr_behavioral_score = breakdown.get('hr_behavioral_score', 0)
        
        # Update session
        session.final_score = score_result['total_score']
        session.score_breakdown = json.dumps(breakdown)
        # Store full summary data as JSON (including weak_skills) for practice recommendations
        session.evaluation_summary = json.dumps(summary_data)
        session.is_completed = True
        session.ended_at = datetime.utcnow()
        session.conversation = json.dumps(conversation)
        
        # Create notification for interview completion with feedback
        feedback_summary = summary_data.get('summary', '')[:200]  # First 200 chars
        if len(summary_data.get('summary', '')) > 200:
            feedback_summary += '...'
        
        notification = Notification(
            user_id=session.user_id,
            title='Interview Completed - Feedback Available',
            message=f'Your {session.interview_type} interview is complete! Score: {score_result["total_score"]:.1f}%. {feedback_summary}',
            type='interview_feedback',
            link=f'/interview/result/{session.id}'
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'session_id': session.id,
            'interview_completed': True,
            'final_score': score_result['total_score'],
            'score_breakdown': breakdown,
            'summary': summary_data.get('summary', ''),
            'strengths': summary_data.get('strengths', []),
            'weaknesses': summary_data.get('weaknesses', []),
            'weak_skills': summary_data.get('weak_skills', []),
            'improvements': summary_data.get('improvements', []),
            'suggested_resources': summary_data.get('suggested_resources', []),
            'practice_materials': practice_materials
        }), 200
    
    except Exception as e:
        db.session.rollback()
        raise e

@interview_bp.route('/end-interview/<int:session_id>', methods=['POST'])
@jwt_required()
def end_interview(session_id):
    """
    STEP 8: End interview early and get results
    POST /api/interview/end-interview/<session_id>
    """
    try:
        user_id = get_jwt_identity()
        session = InterviewSession.query.get_or_404(session_id)
        
        if session.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        if session.is_completed:
            # Return existing results
            result = InterviewResult.query.filter_by(session_id=session_id).first()
            if result:
                return jsonify({
                    'message': 'Interview already completed',
                    'result': result.to_dict(),
                    'session': session.to_dict()
                }), 200
        
        # Complete the interview
        conversation = json.loads(session.conversation) if session.conversation else []
        resume_data_obj = ResumeData.query.filter_by(session_id=session_id).first()
        jd_data_obj = JobDescriptionData.query.filter_by(session_id=session_id).first()
        
        resume_data = resume_data_obj.to_dict() if resume_data_obj else None
        jd_data = jd_data_obj.to_dict() if jd_data_obj else None
        
        # Get last answer if exists
        last_answer = InterviewAnswer.query.filter_by(session_id=session_id).order_by(InterviewAnswer.question_number.desc()).first()
        
        return complete_interview(session, conversation, resume_data, jd_data, last_answer)
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/interview-result/<int:session_id>', methods=['GET'])
@jwt_required()
def get_interview_result(session_id):
    """
    STEP 8: Get final interview result
    GET /api/interview/interview-result/<session_id>
    """
    try:
        user_id = get_jwt_identity()
        session = InterviewSession.query.get_or_404(session_id)
        
        if session.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        result = InterviewResult.query.filter_by(session_id=session_id).first()
        if not result:
            return jsonify({'error': 'Interview result not found. Interview may not be completed yet.'}), 404
        
        # Get weak skills from evaluation summary if available
        weak_skills = []
        if session.evaluation_summary:
            try:
                # evaluation_summary is stored as JSON with full summary_data
                summary_dict = json.loads(session.evaluation_summary) if isinstance(session.evaluation_summary, str) else {}
                weak_skills = summary_dict.get('weak_skills', [])
            except (json.JSONDecodeError, TypeError):
                # Fallback: If evaluation_summary is just text (old format), try to get from result
                try:
                    result_dict = result.to_dict()
                    # Weak skills might be in weaknesses field
                    weaknesses = result_dict.get('weaknesses', [])
                    if isinstance(weaknesses, str):
                        weaknesses = json.loads(weaknesses)
                    weak_skills = weaknesses[:3] if weaknesses else []  # Use first 3 as weak skills
                except:
                    pass
        
        # Generate practice materials if weak skills found
        practice_materials = {}
        if weak_skills:
            practice_materials = generate_practice_materials(weak_skills, session.interview_type)
        
        result_dict = result.to_dict()
        result_dict['weak_skills'] = weak_skills
        result_dict['practice_materials'] = practice_materials
        
        # Also include summary data if available from evaluation_summary
        if session.evaluation_summary:
            try:
                summary_dict = json.loads(session.evaluation_summary) if isinstance(session.evaluation_summary, str) else {}
                if isinstance(summary_dict, dict):
                    result_dict['summary'] = summary_dict.get('summary', '')
                    # Only override if not already set from result
                    if not result_dict.get('strengths'):
                        result_dict['strengths'] = summary_dict.get('strengths', [])
                    if not result_dict.get('weaknesses'):
                        result_dict['weaknesses'] = summary_dict.get('weaknesses', [])
                    if not result_dict.get('improvements'):
                        result_dict['improvements'] = summary_dict.get('improvements', [])
                    if not result_dict.get('suggested_resources'):
                        result_dict['suggested_resources'] = summary_dict.get('suggested_resources', [])
                    if not result_dict.get('weak_skills'):
                        result_dict['weak_skills'] = summary_dict.get('weak_skills', [])
            except (json.JSONDecodeError, TypeError):
                # If evaluation_summary is just text, use it as summary
                if isinstance(session.evaluation_summary, str) and not result_dict.get('summary'):
                    result_dict['summary'] = session.evaluation_summary
        
        return jsonify({
            'session': session.to_dict(),
            'result': result_dict
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/session-details/<int:session_id>', methods=['GET'])
@jwt_required()
def get_session_details(session_id):
    """Get interview session details"""
    try:
        user_id = get_jwt_identity()
        session = InterviewSession.query.get_or_404(session_id)
        
        if session.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({
            'session': session.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/practice-recommendations/<int:session_id>', methods=['GET'])
@jwt_required()
def get_practice_recommendations(session_id):
    """
    Get practice recommendations based on weak skills from interview
    GET /api/interview/practice-recommendations/<session_id>
    """
    try:
        user_id = get_jwt_identity()
        session = InterviewSession.query.get_or_404(session_id)
        
        if session.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        if not session.is_completed:
            return jsonify({'error': 'Interview not completed yet'}), 400
        
        # Get weak skills from evaluation summary
        weak_skills = []
        try:
            # Try to get from evaluation_summary JSON (stored as full summary_data)
            if session.evaluation_summary:
                summary_dict = json.loads(session.evaluation_summary) if isinstance(session.evaluation_summary, str) else {}
                weak_skills = summary_dict.get('weak_skills', [])
            
            # If not found, try to get from result weaknesses field as fallback
            if not weak_skills:
                result = InterviewResult.query.filter_by(session_id=session_id).first()
                if result and result.weaknesses:
                    try:
                        weaknesses = json.loads(result.weaknesses) if isinstance(result.weaknesses, str) else result.weaknesses
                        weak_skills = weaknesses[:5] if isinstance(weaknesses, list) else []  # Use first 5 as weak skills
                    except (json.JSONDecodeError, TypeError):
                        pass
        except Exception as e:
            print(f"Error extracting weak skills: {e}")
        
        # Generate practice materials
        practice_materials = {}
        if weak_skills:
            practice_materials = generate_practice_materials(weak_skills, session.interview_type)
        
        return jsonify({
            'weak_skills': weak_skills,
            'practice_materials': practice_materials,
            'interview_type': session.interview_type
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

