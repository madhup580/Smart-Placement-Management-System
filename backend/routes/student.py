"""
Student routes
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import os
import json
from models import User, Question, CodeSubmission, Quiz, QuizQuestion, QuizAttempt, Resource, Notification, InterviewSession, ChatHistory, UsageStats, Assessment, AssessmentQuestion, AssessmentAttempt, db
from utils.auth import role_required, get_current_user
from utils.leaderboard import update_leaderboard
from utils.assessment_validation import check_assessment_time_window, validate_assessment_access

student_bp = Blueprint('student', __name__)

@student_bp.route('/', methods=['GET'])
def student_info():
    """Student endpoints information"""
    return jsonify({
        'message': 'Student endpoints',
        'endpoints': [
            'GET /api/student/dashboard - Get dashboard data (requires auth)',
            'GET /api/student/performance - Get performance metrics (requires auth)',
            'GET /api/student/questions - Get questions (requires auth)',
            'GET /api/student/resources - Get resources (requires auth)',
            'GET /api/student/placement-readiness - Get placement readiness score (requires auth)'
        ]
    }), 200

@student_bp.route('/server-time', methods=['GET'])
@jwt_required()
def get_server_time():
    """Get current server time for client synchronization"""
    return jsonify({
        'server_time': datetime.utcnow().isoformat(),
        'timestamp': datetime.utcnow().timestamp()
    }), 200

@student_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@role_required(['student'])
def dashboard():
    """Get student dashboard data"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Get recent submissions
        recent_submissions = CodeSubmission.query.filter_by(user_id=user_id)\
            .order_by(CodeSubmission.submitted_at.desc()).limit(5).all()
        
        # Get recent quiz attempts
        recent_quizzes = QuizAttempt.query.filter_by(user_id=user_id)\
            .order_by(QuizAttempt.submitted_at.desc()).limit(5).all()
        
        # Get unread notifications
        unread_notifications = Notification.query.filter_by(
            user_id=user_id, is_read=False
        ).order_by(Notification.created_at.desc()).limit(10).all()
        
        # Get available quizzes
        available_quizzes = Quiz.query.filter_by(is_active=True).limit(5).all()
        
        # Get coding questions
        coding_questions = Question.query.filter_by(
            type='coding', is_active=True
        ).limit(10).all()
        
        return jsonify({
            'user': user.to_dict(),
            'recent_submissions': [s.to_dict() for s in recent_submissions],
            'recent_quizzes': [q.to_dict() for q in recent_quizzes],
            'notifications': [n.to_dict() for n in unread_notifications],
            'available_quizzes': [q.to_dict() for q in available_quizzes],
            'coding_questions': [q.to_dict() for q in coding_questions]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@student_bp.route('/performance', methods=['GET'])
@jwt_required()
@role_required(['student'])
def performance():
    """Get student performance analytics"""
    try:
        user_id = get_jwt_identity()
        
        # Get all submissions
        submissions = CodeSubmission.query.filter_by(user_id=user_id).all()
        total_submissions = len(submissions)
        accepted_submissions = len([s for s in submissions if s.status == 'accepted'])
        accuracy = (accepted_submissions / total_submissions * 100) if total_submissions > 0 else 0
        
        # Get quiz attempts
        quiz_attempts = QuizAttempt.query.filter_by(user_id=user_id).all()
        total_quizzes = len(quiz_attempts)
        avg_quiz_score = sum(q.score for q in quiz_attempts) / total_quizzes if total_quizzes > 0 else 0
        
        # Language-wise performance
        language_stats = {}
        for submission in submissions:
            lang = submission.language
            if lang not in language_stats:
                language_stats[lang] = {'total': 0, 'accepted': 0}
            language_stats[lang]['total'] += 1
            if submission.status == 'accepted':
                language_stats[lang]['accepted'] += 1
        
        # Difficulty-wise performance
        difficulty_stats = {}
        for submission in submissions:
            diff = submission.question.difficulty if submission.question else 'unknown'
            if diff not in difficulty_stats:
                difficulty_stats[diff] = {'total': 0, 'accepted': 0}
            difficulty_stats[diff]['total'] += 1
            if submission.status == 'accepted':
                difficulty_stats[diff]['accepted'] += 1
        
        return jsonify({
            'total_submissions': total_submissions,
            'accepted_submissions': accepted_submissions,
            'accuracy': round(accuracy, 2),
            'total_quizzes': total_quizzes,
            'avg_quiz_score': round(avg_quiz_score, 2),
            'language_stats': language_stats,
            'difficulty_stats': difficulty_stats
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@student_bp.route('/questions', methods=['GET'])
@jwt_required()
def get_questions():
    """Get questions with filters"""
    try:
        question_type = request.args.get('type')  # coding, mcq, fill_blank
        module_type = request.args.get('module_type')  # CodePractice, Non-Technical, Interview, Resources
        difficulty = request.args.get('difficulty')
        company_id = request.args.get('company_id')
        exclude_quiz_questions = request.args.get('exclude_quiz_questions', 'false').lower() == 'true'
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        query = Question.query.filter_by(is_active=True)
        
        # REQUIRED: Filter by module_type to enforce strict segregation
        if module_type:
            if module_type not in ['CodePractice', 'Non-Technical', 'Interview', 'Resources']:
                return jsonify({'error': 'Invalid module_type. Must be one of: CodePractice, Non-Technical, Interview, Resources'}), 400
            query = query.filter_by(module_type=module_type)
        else:
            # If module_type not provided, default based on question_type for backward compatibility
            # But this should ideally always be provided
            if question_type == 'coding':
                query = query.filter_by(module_type='CodePractice')
            elif question_type in ['mcq', 'fill_blank']:
                query = query.filter_by(module_type='Non-Technical')
        
        if question_type:
            query = query.filter_by(type=question_type)
        if difficulty:
            query = query.filter_by(difficulty=difficulty)
        if company_id:
            query = query.filter_by(company_id=company_id)
        
        # Exclude questions that are part of any quiz (for non-technical page)
        if exclude_quiz_questions:
            # Get all question IDs that are used in quizzes
            quiz_question_ids = [q[0] for q in db.session.query(QuizQuestion.question_id).distinct().all()]
            if quiz_question_ids:
                query = query.filter(~Question.id.in_(quiz_question_ids))
        
        questions = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Hide test cases from students (LeetCode-style)
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id) if user_id else None
        hide_test_cases = current_user and current_user.role == 'student'
        
        return jsonify({
            'questions': [q.to_dict(hide_test_cases=hide_test_cases) for q in questions.items],
            'total': questions.total,
            'page': page,
            'per_page': per_page,
            'pages': questions.pages
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@student_bp.route('/resources', methods=['GET'])
@jwt_required()
def get_resources():
    """Get learning resources - accessible to everyone"""
    try:
        resource_type = request.args.get('type')
        company_id = request.args.get('company_id')
        
        # Show all resources to everyone (no filtering by is_public or user_id)
        query = Resource.query
        
        if resource_type:
            query = query.filter_by(type=resource_type)
        if company_id:
            query = query.filter_by(company_id=company_id)
        
        resources = query.order_by(Resource.created_at.desc()).all()
        
        return jsonify({
            'resources': [r.to_dict() for r in resources]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@student_bp.route('/placement-readiness', methods=['GET'])
@jwt_required()
@role_required(['student', 'faculty', 'admin'])
def placement_readiness():
    """Get Placement Readiness Score for a user"""
    try:
        # Allow faculty/admin to view any student's score, or students to view their own
        target_user_id = request.args.get('user_id')
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            return jsonify({'error': 'Current user not found'}), 404
        
        # Determine which user's score to calculate
        if target_user_id and current_user.role in ['faculty', 'admin']:
            user_id = int(target_user_id)
        else:
            user_id = current_user_id
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # 1. Calculate Code Practice Score (from code submissions)
        # This is the main coding performance metric based on test cases passed
        coding_submissions = CodeSubmission.query.filter_by(user_id=user_id).all()
        code_practice_scores = []
        for submission in coding_submissions:
            if (submission.total_test_cases and submission.total_test_cases > 0 and 
                submission.test_cases_passed is not None):
                percentage = (submission.test_cases_passed / submission.total_test_cases) * 100
                code_practice_scores.append(percentage)
        code_practice_score = sum(code_practice_scores) / len(code_practice_scores) if code_practice_scores else 0
        
        # 2. Calculate Non-Technical Score (from ALL quiz attempts)
        # Include all quiz attempts - both Non-Technical quizzes and regular quizzes
        # This combines all quiz performance into the Non-Technical score
        quiz_attempts = QuizAttempt.query.filter_by(user_id=user_id).all()
        non_technical_scores = []
        for attempt in quiz_attempts:
            try:
                # Include all quiz attempts that have valid scores
                # The score field is already stored as a percentage (0-100) in QuizAttempt
                # Score is calculated as: (obtained_marks / total_marks) * 100
                if attempt.score is not None and attempt.score >= 0:
                    # Score is already a percentage, use it directly
                    non_technical_scores.append(attempt.score)
            except Exception as e:
                # Skip if attempt has issues
                print(f"Warning: Could not process quiz attempt {attempt.id}: {str(e)}")
                continue
        
        non_technical_score = sum(non_technical_scores) / len(non_technical_scores) if non_technical_scores else 0
        
        # 3. Calculate AI Virtual Interview Score (from completed interviews)
        completed_interviews = InterviewSession.query.filter_by(
            user_id=user_id, 
            is_completed=True
        ).all()
        interview_scores = []
        for interview in completed_interviews:
            if interview.final_score is not None:
                interview_scores.append(interview.final_score)
        interview_score = sum(interview_scores) / len(interview_scores) if interview_scores else 0
        
        # Calculate overall Placement Readiness Score (simple average)
        # Formula: (Code Practice + Non-Technical + AI Interview) / 3
        # Always include all 3 components, even if score is 0
        placement_readiness_score = (code_practice_score + non_technical_score + interview_score) / 3
        
        return jsonify({
            'placement_readiness_score': round(placement_readiness_score, 2),
            'breakdown': {
                'code_practice': round(code_practice_score, 2),
                'non_technical': round(non_technical_score, 2),
                'interview': round(interview_score, 2)
            },
            'data_available': {
                'code_practice': len(code_practice_scores) > 0,
                'non_technical': len(non_technical_scores) > 0,
                'interview': len(interview_scores) > 0
            },
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name
            }
        }), 200
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in placement_readiness endpoint: {error_trace}")
        return jsonify({
            'error': str(e),
            'trace': error_trace if current_app.config.get('DEBUG', False) else None
        }), 500

@student_bp.route('/progress-trends', methods=['GET'])
@jwt_required()
@role_required(['student', 'faculty', 'admin'])
def progress_trends():
    """Get progress trends for last 7 days"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import cast, Date
        
        target_user_id = request.args.get('user_id')
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            return jsonify({'error': 'Current user not found'}), 404
        
        if target_user_id and current_user.role in ['faculty', 'admin']:
            user_id = int(target_user_id)
        else:
            user_id = current_user_id
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get last 7 days
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=6)  # 7 days including today
        
        # Initialize data structure for 7 days
        dates = [(start_date + timedelta(days=i)).isoformat() for i in range(7)]
        trends = {
            'dates': dates,
            'placement_scores': [0] * 7,
            'coding_accuracy': [0] * 7,
            'interview_scores': [0] * 7
        }
        
        # Calculate Placement Readiness Score for each day
        for i, date_str in enumerate(dates):
            date_obj = datetime.fromisoformat(date_str).date()
            
            # Get submissions up to this date
            submissions_by_date = CodeSubmission.query.filter(
                CodeSubmission.user_id == user_id,
                cast(CodeSubmission.submitted_at, Date) <= date_obj
            ).all()
            
            # Get quiz attempts up to this date
            quiz_attempts_by_date = QuizAttempt.query.filter(
                QuizAttempt.user_id == user_id,
                cast(QuizAttempt.submitted_at, Date) <= date_obj
            ).all()
            
            # Get interviews up to this date
            interviews_by_date = InterviewSession.query.filter(
                InterviewSession.user_id == user_id,
                InterviewSession.is_completed == True,
                cast(InterviewSession.ended_at, Date) <= date_obj
            ).all()
            
            # Calculate scores for this date (same logic as placement_readiness)
            code_practice_scores = []
            for submission in submissions_by_date:
                if (submission.total_test_cases and submission.total_test_cases > 0 and 
                    submission.test_cases_passed is not None):
                    percentage = (submission.test_cases_passed / submission.total_test_cases) * 100
                    code_practice_scores.append(percentage)
            code_practice_score = sum(code_practice_scores) / len(code_practice_scores) if code_practice_scores else 0
            
            non_technical_scores = [attempt.score for attempt in quiz_attempts_by_date if attempt.score is not None and attempt.score >= 0]
            non_technical_score = sum(non_technical_scores) / len(non_technical_scores) if non_technical_scores else 0
            
            interview_scores = [interview.final_score for interview in interviews_by_date if interview.final_score is not None]
            interview_score = sum(interview_scores) / len(interview_scores) if interview_scores else 0
            
            # Calculate Placement Readiness Score
            placement_score = (code_practice_score + non_technical_score + interview_score) / 3
            
            # Calculate Coding Accuracy
            if submissions_by_date:
                accepted = len([s for s in submissions_by_date if s.status == 'accepted'])
                coding_accuracy = (accepted / len(submissions_by_date)) * 100
            else:
                coding_accuracy = 0
            
            trends['placement_scores'][i] = round(placement_score, 2)
            trends['coding_accuracy'][i] = round(coding_accuracy, 2)
            trends['interview_scores'][i] = round(interview_score, 2)
        
        return jsonify(trends), 200
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'trace': traceback.format_exc() if current_app.config.get('DEBUG', False) else None
        }), 500

@student_bp.route('/daily-streaks', methods=['GET'])
@jwt_required()
@role_required(['student', 'faculty', 'admin'])
def daily_streaks():
    """Get daily streaks for coding, quiz, and interview"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import cast, Date
        
        target_user_id = request.args.get('user_id')
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            return jsonify({'error': 'Current user not found'}), 404
        
        if target_user_id and current_user.role in ['faculty', 'admin']:
            user_id = int(target_user_id)
        else:
            user_id = current_user_id
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        today = datetime.utcnow().date()
        
        # Calculate Coding Streak
        coding_streak = 0
        current_date = today
        while True:
            # Check if user has any submission on this date
            submissions_today = CodeSubmission.query.filter(
                CodeSubmission.user_id == user_id,
                cast(CodeSubmission.submitted_at, Date) == current_date
            ).first()
            
            if submissions_today:
                coding_streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        # Calculate Quiz Streak
        quiz_streak = 0
        current_date = today
        while True:
            quiz_today = QuizAttempt.query.filter(
                QuizAttempt.user_id == user_id,
                cast(QuizAttempt.submitted_at, Date) == current_date
            ).first()
            
            if quiz_today:
                quiz_streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        # Calculate Interview Streak
        interview_streak = 0
        current_date = today
        while True:
            interview_today = InterviewSession.query.filter(
                InterviewSession.user_id == user_id,
                InterviewSession.is_completed == True,
                cast(InterviewSession.ended_at, Date) == current_date
            ).first()
            
            if interview_today:
                interview_streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        return jsonify({
            'coding_streak': coding_streak,
            'quiz_streak': quiz_streak,
            'interview_streak': interview_streak,
            'total_streak': max(coding_streak, quiz_streak, interview_streak)  # Best streak
        }), 200
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'trace': traceback.format_exc() if current_app.config.get('DEBUG', False) else None
        }), 500

def _local_ai_assistant_response(message):
    """Useful fallback assistant for demos when the external AI API is unavailable."""
    text = (message or "").strip()
    lower = text.lower()

    if any(word in lower for word in ["python", "list", "dictionary", "tuple", "function"]):
        return (
            "Here is a quick Python placement answer: focus on input parsing, data structures, "
            "and clean output. For coding practice, use lists for ordered data, dictionaries for "
            "fast lookup, sets for uniqueness, and functions to keep logic readable. Example for "
            "two-sum style problems: store each value in a dictionary with its index, then check "
            "whether target - value already exists."
        )

    if any(word in lower for word in ["java", "oops", "object", "class", "inheritance", "polymorphism"]):
        return (
            "For Java interview preparation, revise OOP clearly: encapsulation protects data, "
            "inheritance reuses behavior, polymorphism lets one interface have many forms, and "
            "abstraction hides implementation details. In coding rounds, use public class Main, "
            "Scanner or BufferedReader for input, and print exactly the expected output."
        )

    if any(word in lower for word in ["sql", "database", "dbms", "join", "primary key", "foreign key"]):
        return (
            "For SQL/DBMS, remember these core points: a primary key uniquely identifies each row, "
            "a foreign key connects tables, INNER JOIN returns matching rows, LEFT JOIN keeps all "
            "left table rows, and normalization reduces duplicate data. Practice SELECT, WHERE, "
            "GROUP BY, HAVING, ORDER BY, and JOIN queries."
        )

    if any(word in lower for word in ["resume", "cv", "project", "job description", "jd"]):
        return (
            "For resume and job description preparation, match your resume to the role. Keep a "
            "strong summary, list technical skills clearly, write projects with problem, tools, "
            "implementation, and result, and include keywords from the job description honestly."
        )

    if any(word in lower for word in ["interview", "hr", "tell me", "strength", "weakness"]):
        return (
            "For interviews, answer in a structured way: give a short direct answer, add one real "
            "example, then connect it to the role. For HR questions, stay honest and positive. "
            "For technical questions, explain the concept first, then give a small example."
        )

    if any(word in lower for word in ["code", "program", "algorithm", "coding", "practice"]):
        return (
            "For coding practice, first understand input and output, then write the simplest correct "
            "logic, and finally test edge cases. Common edge cases are empty input, duplicates, "
            "single element, no answer, and large values. Keep output formatting exact."
        )

    return (
        "I can help with coding practice, Python, Java, SQL/DBMS, resume preparation, job "
        "descriptions, HR questions, and interview preparation. Ask your exact doubt and I will "
        "give a direct answer with an example."
    )

@student_bp.route('/ai-chat', methods=['POST'])
@jwt_required()
@role_required(['student'])
def ai_chat():
    """ChatGPT-like AI chatbot - direct OpenAI integration"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get chat history (last 10 messages for context)
        # Wrap in try-except in case table doesn't exist yet
        try:
            recent_messages = ChatHistory.query.filter_by(user_id=user_id)\
                .order_by(ChatHistory.created_at.desc())\
                .limit(10)\
                .all()
        except Exception as db_error:
            # If table doesn't exist, start with empty history
            print(f"[AI Chat] ChatHistory table not found, starting with empty history: {db_error}")
            recent_messages = []
        
        # Build conversation history
        conversation = []
        for msg in reversed(recent_messages):
            conversation.append({
                'role': msg.role,
                'content': msg.message
            })
        
        # Add current user message
        conversation.append({
            'role': 'user',
            'content': message
        })
        
        # System prompt - simple and direct
        system_prompt = {
            'role': 'system',
            'content': 'You are a helpful AI assistant.\nAnswer all questions directly and clearly like ChatGPT.\nDo not ask the user to rephrase.\nDo not show menus or categories.\nDo not mention system configuration or backend details.'
        }
        
        # Try OpenAI API
        openai_api_key = current_app.config.get('OPENAI_API_KEY')
        openai_model = current_app.config.get('OPENAI_MODEL', 'gpt-4o-mini')
        
        # Cost-saving: Dynamic max_tokens based on message length
        message_length = len(message)
        if message_length < 50:
            # Short/simple questions - use fewer tokens
            max_tokens = current_app.config.get('AI_CHAT_MAX_TOKENS_SIMPLE', 500)
        elif message_length > 200:
            # Complex questions - allow more tokens
            max_tokens = current_app.config.get('AI_CHAT_MAX_TOKENS_COMPLEX', 2000)
        else:
            # Medium questions - default
            max_tokens = current_app.config.get('AI_CHAT_MAX_TOKENS_DEFAULT', 1500)
        
        print(f"[AI Chat] Request received. API configured: {bool(openai_api_key)}, model: {openai_model}")
        
        ai_response = None
        usage_data = None  # Track usage for cost calculation
        
        if openai_api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_api_key, timeout=20.0, max_retries=1)
                
                # Build messages: system prompt + conversation history
                messages = [system_prompt] + conversation
                
                print(f"[AI Chat] Sending request with {len(messages)} messages.")
                response = client.chat.completions.create(
                    model=openai_model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=max_tokens  # Use dynamic max_tokens
                )
                
                ai_response = response.choices[0].message.content.strip()
                
                # Extract usage data for cost tracking
                if hasattr(response, 'usage') and response.usage:
                    usage_data = {
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                        'total_tokens': response.usage.total_tokens
                    }
                    print(f"[AI Chat Usage] Tokens - Prompt: {usage_data['prompt_tokens']}, Completion: {usage_data['completion_tokens']}, Total: {usage_data['total_tokens']}")
                
                print("[AI Chat] External AI response received.")
                
            except ImportError as import_err:
                # OpenAI library not installed
                print(f"[AI Chat Error] OpenAI library not installed: {import_err}")
                print("[AI Chat Error] Please run: pip install openai>=1.12.0")
                ai_response = None
            except Exception as e:
                # Log error internally with full traceback
                import traceback
                error_trace = traceback.format_exc()
                error_str = str(e)
                print(f"[AI Chat OpenAI Error] {error_str}")
                print(f"[AI Chat OpenAI Error Trace] {error_trace}")
                
                # Check for specific errors
                if 'quota' in error_str.lower() or '429' in error_str or 'insufficient_quota' in error_str.lower():
                    print("[AI Chat Error] External AI quota limit reached.")
                    ai_response = _local_ai_assistant_response(message)
                elif 'invalid' in error_str.lower() or '401' in error_str or 'unauthorized' in error_str.lower():
                    print("[AI Chat Error] External AI authorization failed.")
                    ai_response = _local_ai_assistant_response(message)
                else:
                    ai_response = _local_ai_assistant_response(message)
        
        # If no API key or API failed, keep the assistant useful for demos.
        if not ai_response:
            print(f"[AI Chat] Using local fallback. API configured: {bool(openai_api_key)}")
            ai_response = _local_ai_assistant_response(message)
        
        print(f"[AI Chat] Final response length: {len(ai_response) if ai_response else 0}")
        
        # Calculate and save usage stats (cost tracking)
        if usage_data and openai_api_key:
            try:
                # Get pricing for the model
                pricing = current_app.config.get('OPENAI_PRICING', {}).get(openai_model, {})
                if pricing:
                    input_cost = (usage_data['prompt_tokens'] * pricing.get('input', 0))
                    output_cost = (usage_data['completion_tokens'] * pricing.get('output', 0))
                    total_cost = input_cost + output_cost
                    
                    print(f"[AI Chat Cost] Input: ${input_cost:.6f}, Output: ${output_cost:.6f}, Total: ${total_cost:.6f}")
                    
                    # Save usage stats
                    usage_stat = UsageStats(
                        user_id=user_id,
                        model=openai_model,
                        prompt_tokens=usage_data['prompt_tokens'],
                        completion_tokens=usage_data['completion_tokens'],
                        total_tokens=usage_data['total_tokens'],
                        cost_usd=total_cost
                    )
                    db.session.add(usage_stat)
                    db.session.commit()
                    print(f"[AI Chat] Usage stats saved successfully.")
            except Exception as usage_error:
                # If UsageStats table doesn't exist, just log and continue
                print(f"[AI Chat] Could not save usage stats (table may not exist): {usage_error}")
                db.session.rollback()
        
        # Save to chat history (only if table exists)
        try:
            user_msg = ChatHistory(
                user_id=user_id,
                role='user',
                message=message
            )
            assistant_msg = ChatHistory(
                user_id=user_id,
                role='assistant',
                message=ai_response
            )
            
            db.session.add(user_msg)
            db.session.add(assistant_msg)
            db.session.commit()
        except Exception as db_error:
            # If table doesn't exist, just log and continue
            print(f"[AI Chat] Could not save to ChatHistory (table may not exist): {db_error}")
            db.session.rollback()
            # Still return the response even if we can't save history
        
        print(f"[AI Chat] Final response saved.")
        
        return jsonify({
            'message': ai_response,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"[AI Chat Error] {str(e)}")
        print(f"[AI Chat Error Trace] {error_trace}")
        
        # If it's a database error (table doesn't exist), provide helpful message
        if 'chat_history' in str(e).lower() or 'table' in str(e).lower():
            return jsonify({
                'message': "Chat feature is being set up. Please run the migration script: python backend/migrate_chat_history.py"
            }), 200
        
        # Return generic error message, don't expose details
        return jsonify({
            'message': "I'm having trouble processing your request. Please try again."
        }), 200  # Return 200 so frontend doesn't show error

@student_bp.route('/ai-chat/usage', methods=['GET'])
@jwt_required()
@role_required(['student'])
def ai_chat_usage():
    """Get AI chat usage statistics and costs for the current user"""
    try:
        user_id = get_jwt_identity()
        
        # Get all usage stats for this user
        try:
            usage_stats = UsageStats.query.filter_by(user_id=user_id)\
                .order_by(UsageStats.created_at.desc())\
                .all()
        except Exception as db_error:
            # If table doesn't exist, return empty stats
            print(f"[AI Chat Usage] UsageStats table not found: {db_error}")
            return jsonify({
                'total_requests': 0,
                'total_tokens': 0,
                'total_cost_usd': 0.0,
                'average_cost_per_request': 0.0,
                'usage_by_model': {},
                'recent_usage': []
            }), 200
        
        # Calculate totals
        total_requests = len(usage_stats)
        total_tokens = sum(stat.total_tokens for stat in usage_stats)
        total_cost = sum(float(stat.cost_usd) for stat in usage_stats)
        avg_cost = total_cost / total_requests if total_requests > 0 else 0.0
        
        # Group by model
        usage_by_model = {}
        for stat in usage_stats:
            model = stat.model
            if model not in usage_by_model:
                usage_by_model[model] = {
                    'requests': 0,
                    'tokens': 0,
                    'cost': 0.0
                }
            usage_by_model[model]['requests'] += 1
            usage_by_model[model]['tokens'] += stat.total_tokens
            usage_by_model[model]['cost'] += float(stat.cost_usd)
        
        # Get recent usage (last 10)
        recent_usage = [stat.to_dict() for stat in usage_stats[:10]]
        
        return jsonify({
            'total_requests': total_requests,
            'total_tokens': total_tokens,
            'total_cost_usd': round(total_cost, 6),
            'average_cost_per_request': round(avg_cost, 6),
            'usage_by_model': usage_by_model,
            'recent_usage': recent_usage
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"[AI Chat Usage Error] {str(e)}")
        print(f"[AI Chat Usage Error Trace] {error_trace}")
        return jsonify({'error': 'Failed to fetch usage statistics'}), 500

# ==================== ASSESSMENT ROUTES (Student) ====================

@student_bp.route('/assessments', methods=['GET'])
@jwt_required()
@role_required(['student'])
def list_assessments():
    """List all published assessments available for students (filtered by batch)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        module_type = request.args.get('module_type')  # Filter by module_type for strict segregation
        query = Assessment.query.filter_by(
            status='published',
            is_active=True
        )
        
        if module_type:
            if module_type not in ['CodePractice', 'Non-Technical', 'Interview', 'Resources']:
                return jsonify({'error': 'Invalid module_type. Must be one of: CodePractice, Non-Technical, Interview, Resources'}), 400
            query = query.filter_by(module_type=module_type)
        
        # Get all matching assessments first
        all_assessments = query.order_by(Assessment.created_at.desc()).all()
        
        # Filter by batch assignment: only show assessments assigned to student's batch or all batches (NULL)
        if user and user.batch_id:
            filtered_assessments = []
            for assessment in all_assessments:
                if assessment.assigned_batches is None:
                    # NULL means available to all batches
                    filtered_assessments.append(assessment)
                else:
                    try:
                        batch_ids = json.loads(assessment.assigned_batches)
                        if user.batch_id in batch_ids:
                            filtered_assessments.append(assessment)
                    except (json.JSONDecodeError, TypeError):
                        # Invalid JSON, skip this assessment
                        continue
            assessments = filtered_assessments
        else:
            assessments = all_assessments
        
        return jsonify({
            'assessments': [a.to_dict() for a in assessments]
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@student_bp.route('/assessments/<int:assessment_id>', methods=['GET'])
@jwt_required()
@role_required(['student'])
def get_assessment(assessment_id):
    """Get assessment details with questions (for attempting) - Student only"""
    try:
        assessment = Assessment.query.filter_by(
            id=assessment_id,
            status='published',
            is_active=True
        ).first_or_404()
        
        user_id = get_jwt_identity()
        
        # Validate access (check time window, but allow access if already started)
        can_access, error_msg, status = validate_assessment_access(assessment, user_id, check_submitted=False)
        
        # Still return assessment data even if time window expired (for viewing results)
        # But include status info
        
        # Get questions ordered by their order in assessment
        assessment_questions = AssessmentQuestion.query.filter_by(
            assessment_id=assessment_id
        ).order_by(AssessmentQuestion.order).all()
        
        # Check if student has already attempted this assessment
        existing_attempt = AssessmentAttempt.query.filter_by(
            user_id=user_id,
            assessment_id=assessment_id
        ).first()
        
        # Get time window status
        _, time_status, time_message = check_assessment_time_window(assessment)
        
        assessment_dict = assessment.to_dict()
        assessment_dict['questions'] = [aq.to_dict() for aq in assessment_questions]
        assessment_dict['has_attempted'] = existing_attempt is not None
        assessment_dict['previous_attempt'] = existing_attempt.to_dict() if existing_attempt else None
        assessment_dict['time_status'] = time_status  # 'upcoming', 'active', 'closed'
        assessment_dict['time_message'] = time_message
        assessment_dict['can_access'] = can_access
        
        return jsonify({'assessment': assessment_dict}), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@student_bp.route('/assessments/<int:assessment_id>/start', methods=['POST'])
@jwt_required()
@role_required(['student'])
def start_assessment(assessment_id):
    """Start an assessment attempt - Student only"""
    try:
        user_id = get_jwt_identity()
        
        # Verify assessment exists and is published
        assessment = Assessment.query.filter_by(
            id=assessment_id,
            status='published',
            is_active=True
        ).first_or_404()
        
        # Validate time window access (server-side validation)
        can_access, error_msg, status = validate_assessment_access(assessment, user_id, check_submitted=False)
        
        if not can_access:
            return jsonify({
                'error': error_msg,
                'status': status
            }), 403
        
        # Check if student has already submitted an attempt
        existing_attempt = AssessmentAttempt.query.filter_by(
            user_id=user_id,
            assessment_id=assessment_id
        ).first()
        
        if existing_attempt and existing_attempt.submitted_at:
            return jsonify({
                'error': 'You have already submitted this assessment',
                'attempt': existing_attempt.to_dict()
            }), 400
        
        # If attempt exists but not submitted, return it (allow re-entry)
        if existing_attempt and not existing_attempt.submitted_at:
            return jsonify({
                'message': 'Resuming assessment attempt',
                'attempt': existing_attempt.to_dict()
            }), 200
        
        # Create new attempt
        attempt = AssessmentAttempt(
            user_id=user_id,
            assessment_id=assessment_id,
            started_at=datetime.utcnow(),
            answers=json.dumps({}),
            score=0,
            total_marks=assessment.total_marks or 0
        )
        
        db.session.add(attempt)
        db.session.commit()
        
        return jsonify({
            'message': 'Assessment started',
            'attempt': attempt.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@student_bp.route('/assessments/<int:assessment_id>/submit', methods=['POST'])
@jwt_required()
@role_required(['student'])
def submit_assessment(assessment_id):
    """Submit assessment answers - Student only"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Verify assessment exists and is published
        assessment = Assessment.query.filter_by(
            id=assessment_id,
            status='published',
            is_active=True
        ).first_or_404()
        
        # Validate time window access (server-side validation)
        # Allow submission even if time just expired (grace period of 1 minute)
        can_access, error_msg, status = validate_assessment_access(assessment, user_id, check_submitted=False)
        
        # Check if end time has passed (with 1 minute grace period)
        from datetime import timedelta
        now = datetime.utcnow()
        end_datetime = datetime.combine(assessment.end_date, assessment.end_time)
        grace_period_end = end_datetime + timedelta(minutes=1)
        
        if now > grace_period_end:
            return jsonify({
                'error': 'Assessment submission deadline has passed',
                'status': 'closed'
            }), 403
        
        # Get or create attempt
        attempt = AssessmentAttempt.query.filter_by(
            user_id=user_id,
            assessment_id=assessment_id
        ).first()
        
        if not attempt:
            # Create new attempt if doesn't exist
            attempt = AssessmentAttempt(
                user_id=user_id,
                assessment_id=assessment_id,
                started_at=datetime.utcnow()
            )
            db.session.add(attempt)
        
        # Get answers
        answers = data.get('answers', {})  # Format: {question_id: answer}
        
        # Calculate score
        assessment_questions = AssessmentQuestion.query.filter_by(
            assessment_id=assessment_id
        ).all()
        
        total_score = 0
        total_marks = 0
        
        for aq in assessment_questions:
            question = aq.question
            if not question:
                continue
            
            total_marks += aq.marks
            question_id = str(question.id)
            
            if question_id in answers:
                answer = answers[question_id]
                
                # Auto-evaluate based on question type
                if question.type == 'coding':
                    # For coding questions, check test cases
                    # This is a simplified version - you might want to run actual code execution
                    # For now, we'll just store the answer
                    pass
                elif question.type == 'mcq':
                    # Check if answer matches correct answer
                    if str(answer).strip().upper() == str(question.correct_answer).strip().upper():
                        total_score += aq.marks
                elif question.type == 'fill_blank':
                    # Check if answer matches any of the blanks
                    blanks = json.loads(question.blanks) if question.blanks else []
                    if answer in blanks or (isinstance(blanks, list) and any(str(a).strip().lower() == str(answer).strip().lower() for a in blanks)):
                        total_score += aq.marks
        
        # Update attempt
        attempt.answers = json.dumps(answers)
        attempt.score = total_score
        attempt.total_marks = total_marks
        attempt.submitted_at = datetime.utcnow()
        
        # Calculate time taken
        if attempt.started_at:
            time_diff = attempt.submitted_at - attempt.started_at
            attempt.time_taken_minutes = int(time_diff.total_seconds() / 60)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Assessment submitted successfully',
            'attempt': attempt.to_dict(),
            'score': total_score,
            'total_marks': total_marks,
            'percentage': (total_score / total_marks * 100) if total_marks > 0 else 0
        }), 200
    
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@student_bp.route('/assessments/attempts', methods=['GET'])
@jwt_required()
@role_required(['student'])
def get_my_attempts():
    """Get all assessment attempts by the current student"""
    try:
        user_id = get_jwt_identity()
        
        attempts = AssessmentAttempt.query.filter_by(
            user_id=user_id
        ).order_by(AssessmentAttempt.submitted_at.desc()).all()
        
        return jsonify({
            'attempts': [a.to_dict() for a in attempts]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@student_bp.route('/assessments/<int:assessment_id>/attempt', methods=['GET'])
@jwt_required()
@role_required(['student'])
def get_my_attempt(assessment_id):
    """Get student's attempt for a specific assessment"""
    try:
        user_id = get_jwt_identity()
        
        attempt = AssessmentAttempt.query.filter_by(
            user_id=user_id,
            assessment_id=assessment_id
        ).first()
        
        if not attempt:
            return jsonify({'error': 'Attempt not found'}), 404
        
        return jsonify({
            'attempt': attempt.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    # Handle DSA (Data Structures and Algorithms) - HIGH PRIORITY
    if any(word in message_lower for word in ['dsa', 'data structure', 'data structures', 'algorithm', 'algorithms']):
        if 'dsa' in message_lower or ('data structure' in message_lower and 'algorithm' in message_lower):
            return """## Data Structures and Algorithms (DSA)

**DSA** stands for **Data Structures and Algorithms**.

### Data Structures:
Ways to organize and store data efficiently:
- **Arrays**: Contiguous memory, indexed access
- **Linked Lists**: Dynamic size, nodes connected
- **Stacks**: LIFO (Last In First Out)
- **Queues**: FIFO (First In First Out)
- **Trees**: Hierarchical data (Binary Tree, BST, AVL)
- **Graphs**: Nodes and edges representation
- **Hash Tables**: Key-value pairs for fast lookup

### Algorithms:
Step-by-step procedures to solve problems:
- **Sorting**: Bubble, Quick, Merge, Heap Sort
- **Searching**: Linear, Binary Search
- **Graph Algorithms**: BFS, DFS, Dijkstra
- **Dynamic Programming**: Memoization, tabulation
- **Greedy Algorithms**: Optimal local choices

### Why DSA?
- **Efficiency**: Solve problems faster
- **Optimization**: Reduce time and space complexity
- **Interview Essential**: Core of technical interviews
- **Problem Solving**: Foundation for complex programming

### Example:
```python
# Binary Search Algorithm
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

**Time Complexity**: O(log n)"""
        elif 'data structure' in message_lower:
            return """## Data Structures

**Data Structures** are ways to organize and store data in computer memory for efficient access and modification.

### Types:
- **Linear**: Arrays, Linked Lists, Stacks, Queues
- **Non-Linear**: Trees, Graphs
- **Hash-based**: Hash Tables, Hash Maps

### Common Operations:
- **Insert**: Add data
- **Delete**: Remove data
- **Search**: Find data
- **Traverse**: Visit all elements

### Time Complexity:
- Array access: O(1)
- Linked List search: O(n)
- Hash Table lookup: O(1) average"""
        elif 'algorithm' in message_lower:
            return """## Algorithms

**Algorithms** are step-by-step procedures to solve problems efficiently.

### Types:
- **Sorting**: Organize data in order
- **Searching**: Find specific data
- **Graph**: Traverse networks
- **Dynamic Programming**: Optimize recursive solutions
- **Greedy**: Make optimal local choices

### Complexity Analysis:
- **Time Complexity**: How long it takes
- **Space Complexity**: How much memory it uses

### Example - Binary Search:
```python
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```"""
    
    # Check if it's a conceptual question
    is_conceptual = any(word in message_lower for word in [
        'explain', 'what is', 'what are', 'define', 'tell me about', 'describe',
        'how does', 'how do', 'what does', 'meaning of', 'concept of', 'stands for'
    ])
    
    # Handle OOPS concepts
    if is_conceptual and any(word in message_lower for word in ['oops', 'object oriented', 'object-oriented', 'oop']):
        return """## Object-Oriented Programming (OOP)

**What is OOP?**
Object-Oriented Programming is a programming paradigm that organizes code around objects and classes, making it easier to manage and maintain complex programs.

### Core Concepts:

**1. Class and Object**
- **Class**: A blueprint or template for creating objects
- **Object**: An instance of a class (a real-world entity)

**Example:**
```python
class Car:
    def __init__(self, brand, model):
        self.brand = brand
        self.model = model

# Creating an object
my_car = Car("Toyota", "Camry")
```

**2. Encapsulation**
- Bundling data (attributes) and methods (functions) together
- Data hiding using access modifiers (private, protected, public)

**3. Inheritance**
- A class can inherit properties and methods from another class
- Promotes code reusability

**Example:**
```python
class Vehicle:
    def start(self):
        print("Vehicle started")

class Car(Vehicle):  # Car inherits from Vehicle
    pass

my_car = Car()
my_car.start()  # Inherited method
```

**4. Polymorphism**
- Same interface, different implementations
- "One interface, many forms"
- Method overriding and overloading

**5. Abstraction**
- Hiding complex implementation details
- Showing only essential features

### Why OOP?
- **Modularity**: Code is organized into reusable components
- **Maintainability**: Easier to update and debug
- **Scalability**: Easy to extend functionality
- **Real-world modeling**: Mirrors real-world entities"""
    
    # Handle other conceptual questions
    if is_conceptual:
        # Check for specific topics
        if any(word in message_lower for word in ['dbms', 'database', 'sql']):
            return """## Database Management System (DBMS)

**What is DBMS?**
A Database Management System is software that manages databases, allowing users to store, retrieve, and manipulate data efficiently.

### Key Concepts:
- **Database**: Organized collection of data
- **Tables**: Data stored in rows and columns
- **SQL**: Structured Query Language for database operations
- **ACID Properties**: Atomicity, Consistency, Isolation, Durability
- **Normalization**: Organizing data to reduce redundancy

### Common Operations:
- **CREATE**: Create tables/databases
- **INSERT**: Add data
- **SELECT**: Retrieve data
- **UPDATE**: Modify data
- **DELETE**: Remove data"""
        
        elif any(word in message_lower for word in ['os', 'operating system']):
            return """## Operating System (OS)

**What is an Operating System?**
An Operating System is system software that manages computer hardware and software resources, providing services for computer programs.

### Key Functions:
- **Process Management**: Managing running programs
- **Memory Management**: Allocating and managing RAM
- **File System**: Organizing and storing files
- **Device Management**: Controlling hardware devices
- **Security**: User authentication and access control

### Types:
- **Windows**: Microsoft's OS
- **Linux**: Open-source OS
- **macOS**: Apple's OS
- **Unix**: Multi-user OS"""
        
        elif any(word in message_lower for word in ['cn', 'computer network', 'networking']):
            return """## Computer Networks (CN)

**What is a Computer Network?**
A Computer Network is a collection of interconnected devices (computers, servers, routers) that can communicate and share resources.

### Key Concepts:
- **Protocol**: Rules for communication (TCP/IP, HTTP, FTP)
- **Topology**: Network layout (Star, Bus, Ring, Mesh)
- **OSI Model**: 7-layer network architecture
- **TCP/IP**: Transmission Control Protocol/Internet Protocol
- **LAN/WAN**: Local/Wide Area Networks

### Common Protocols:
- **HTTP/HTTPS**: Web communication
- **TCP**: Reliable data transmission
- **UDP**: Fast, connectionless transmission
- **SMTP**: Email transmission"""
        
        elif any(word in message_lower for word in ['polymorphism', 'inheritance', 'encapsulation', 'abstraction']):
            return """## OOP Core Concepts

**Polymorphism**: Same interface, different implementations. Allows objects of different types to be treated through the same interface.

**Inheritance**: A class can inherit properties and methods from a parent class, promoting code reusability.

**Encapsulation**: Bundling data and methods together, hiding internal details from outside access.

**Abstraction**: Showing only essential features while hiding implementation details.

Each concept helps make code more modular, maintainable, and scalable."""
        
        elif any(word in message_lower for word in ['stack', 'queue']):
            if 'stack' in message_lower and 'queue' in message_lower:
                return """## Stack and Queue

**Stack** is a linear data structure that follows LIFO (Last In First Out) principle. The last element added is the first one to be removed.

**Queue** is a linear data structure that follows FIFO (First In First Out) principle. The first element added is the first one to be removed.

### Stack:
- **Operations**: Push (add), Pop (remove), Peek (view top)
- **Use cases**: Function calls, undo operations, expression evaluation
- **Example**: Browser back button uses a stack

```python
# Stack implementation
stack = []
stack.append(1)  # Push
stack.append(2)
top = stack.pop()  # Pop - returns 2
```

### Queue:
- **Operations**: Enqueue (add), Dequeue (remove), Front (view)
- **Use cases**: Task scheduling, BFS algorithm, printer queue
- **Example**: Waiting line at a ticket counter

```python
# Queue implementation
from collections import deque
queue = deque()
queue.append(1)  # Enqueue
queue.append(2)
front = queue.popleft()  # Dequeue - returns 1
```

### Key Differences:
- **Stack**: LIFO, operations at one end (top)
- **Queue**: FIFO, operations at both ends (front and rear)"""
            elif 'stack' in message_lower:
                return """## Stack

A **Stack** is a linear data structure that follows LIFO (Last In First Out) principle. Think of it like a stack of plates - you add plates on top and remove from the top.

### Operations:
- **Push**: Add element to the top
- **Pop**: Remove element from the top
- **Peek/Top**: View the top element without removing

### Use Cases:
- Function call stack
- Undo operations
- Expression evaluation (infix to postfix)
- Browser back button

### Implementation:
```python
stack = []
stack.append(1)  # Push
stack.append(2)
top = stack[-1]  # Peek
element = stack.pop()  # Pop - returns 2
```

### Time Complexity:
- Push: O(1)
- Pop: O(1)
- Peek: O(1)"""
            else:  # queue only
                return """## Queue

A **Queue** is a linear data structure that follows FIFO (First In First Out) principle. Think of it like a line at a ticket counter - first person in line is served first.

### Operations:
- **Enqueue**: Add element to the rear
- **Dequeue**: Remove element from the front
- **Front**: View the front element

### Use Cases:
- Task scheduling
- BFS (Breadth-First Search) algorithm
- Printer queue
- Message queues

### Implementation:
```python
from collections import deque
queue = deque()
queue.append(1)  # Enqueue
queue.append(2)
front = queue[0]  # Front
element = queue.popleft()  # Dequeue - returns 1
```

### Time Complexity:
- Enqueue: O(1)
- Dequeue: O(1)
- Front: O(1)"""
        
        # Generic conceptual response - provide basic direct answer
        # Never mention API configuration - just provide helpful guidance
        return f"""I can help explain '{message}'.

Here's a basic explanation:

**{message}** is a concept that can be explained in detail. For a comprehensive answer with examples and code snippets, please try asking a more specific question or rephrasing your query.

If you're asking about:
- **Programming concepts**: Try "Explain [concept] with examples"
- **Data structures**: Try "What is [data structure] and how does it work?"
- **Algorithms**: Try "How does [algorithm] work step by step?"
- **Interview questions**: Try "How to answer [interview question]?"

Feel free to ask follow-up questions for more details!"""
    
    # Performance-related questions - fetch user data when needed
    if any(word in message_lower for word in ['my score', 'my performance', 'my accuracy', 'my readiness', 'why is my', 'how to improve my', 'score is low', 'performance is', 'accuracy is']):
        # Get user's actual performance data
        code_submissions = CodeSubmission.query.filter_by(user_id=user_id).all()
        quiz_attempts = QuizAttempt.query.filter_by(user_id=user_id).all()
        interview_sessions = InterviewSession.query.filter_by(user_id=user_id, is_completed=True).all()
        
        code_practice_score = 0
        if code_submissions:
            total = len(code_submissions)
            passed = sum(1 for s in code_submissions if s.status == 'accepted')
            code_practice_score = (passed / total * 100) if total > 0 else 0
        
        quiz_score = 0
        if quiz_attempts:
            scores = [a.score for a in quiz_attempts if a.score is not None]
            quiz_score = sum(scores) / len(scores) if scores else 0
        
        interview_score = 0
        if interview_sessions:
            scores = [s.final_score for s in interview_sessions if s.final_score is not None]
            interview_score = sum(scores) / len(scores) if scores else 0
        
        if code_practice_score < 50:
            return f"Your Code Practice score is {code_practice_score:.1f}%. To improve:\n\n1. **Practice regularly**: Try solving at least 1-2 coding problems daily\n2. **Start with easy problems**: Build confidence with easier questions first\n3. **Review solutions**: After solving, review optimal solutions to learn better approaches\n4. **Focus on fundamentals**: Master basic data structures (arrays, strings) before moving to advanced topics\n\nYour current accuracy is {context.get('accuracy', 0):.1f}%. Keep practicing!"
        
        elif quiz_score < 50:
            return f"Your Non-Technical/Quiz score is {quiz_score:.1f}%. To improve:\n\n1. **Take more quizzes**: You've taken {len(quiz_attempts)} quiz(es). Aim for at least 5-10 quizzes\n2. **Review wrong answers**: After each quiz, review questions you got wrong\n3. **Practice HR questions**: Focus on common interview questions about your background, strengths, and goals\n4. **Time management**: Practice answering questions within time limits\n\nKeep practicing to improve your placement readiness!"
        
        elif interview_score < 50:
            return f"Your AI Virtual Interview score is {interview_score:.1f}%. To improve:\n\n1. **Practice more interviews**: You've completed {len(interview_sessions)} interview(s). Practice regularly\n2. **Prepare common questions**: Practice answers for 'Tell me about yourself', 'Why this company?', etc.\n3. **Work on communication**: Speak clearly, maintain eye contact (in video interviews), and be confident\n4. **Review feedback**: After each interview, review the AI feedback and work on weak areas\n\nYour overall Placement Readiness Score is {context.get('placement_readiness', 0):.1f}%. Focus on improving all three components!"
        
        else:
            return f"Great job! Your scores are:\n\n- Code Practice: {code_practice_score:.1f}%\n- Non-Technical: {quiz_score:.1f}%\n- AI Virtual Interview: {interview_score:.1f}%\n\nYour overall Placement Readiness Score is {context.get('placement_readiness', 0):.1f}%. Keep up the good work and continue practicing to maintain and improve your scores!"
    
    elif any(word in message_lower for word in ['coding', 'code', 'program', 'solve', 'problem']):
        return """I can help you with coding! Here are some tips:

1. **Start with the problem statement**: Read carefully and understand what's being asked
2. **Break it down**: Divide complex problems into smaller sub-problems
3. **Think before coding**: Plan your approach (pseudocode) before writing code
4. **Test your code**: Always test with sample inputs before submitting
5. **Practice regularly**: Try solving problems daily!

If you have a specific coding question, feel free to ask!"""
    
    elif any(word in message_lower for word in ['quiz', 'non-technical', 'hr', 'interview question']):
        return """I can help with non-technical and HR questions!

**Common HR Questions:**
1. Tell me about yourself
2. Why do you want to join this company?
3. What are your strengths and weaknesses?
4. Where do you see yourself in 5 years?
5. Why should we hire you?

**Tips:**
- Be honest and authentic
- Prepare STAR method (Situation, Task, Action, Result) for behavioral questions
- Research the company before interviews
- Practice your answers out loud

Keep practicing!"""
    
    elif any(word in message_lower for word in ['interview', 'prepare', 'tips', 'advice']):
        return """Here are interview preparation tips:

**Before the Interview:**
1. Research the company and role thoroughly
2. Prepare answers for common questions
3. Practice coding problems
4. Review your resume and be ready to explain any point
5. Prepare questions to ask the interviewer

**During the Interview:**
1. Be confident and maintain eye contact
2. Listen carefully before answering
3. Use the STAR method for behavioral questions
4. Show enthusiasm and interest
5. Ask thoughtful questions

Keep practicing to improve!"""
    
    elif any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! How can I help you?"
    
    elif 'help' in message_lower:
        return "I can help with coding, programming concepts, algorithms, data structures, DBMS, OS, CN, interviews, and more. What would you like to know?"
    
    else:
        # For any other question - provide a helpful direct response
        # Never mention API configuration - just answer or guide
        return f"""I can help with '{message}'.

Could you provide more details or rephrase your question? For example:
- If asking about a concept: "Explain [concept]"
- If asking how to do something: "How to [action]"
- If asking what something is: "What is [thing]"

Feel free to ask follow-up questions!"""


