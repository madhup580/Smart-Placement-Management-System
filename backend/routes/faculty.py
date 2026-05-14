"""
Faculty routes
"""
from flask import Blueprint, request, jsonify, make_response, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Quiz, Question, QuizQuestion, QuizAttempt, QuizAssignment, User, CodeSubmission, Notification, InterviewSession, Assessment, AssessmentQuestion, AssessmentAttempt, db
from utils.auth import role_required
from datetime import datetime, date, time
import json
import csv
import io

faculty_bp = Blueprint('faculty', __name__)

@faculty_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@role_required(['faculty', 'admin'])
def dashboard():
    """Get faculty dashboard data with batch analytics"""
    try:
        user_id = get_jwt_identity()
        
        # Get quizzes created by faculty
        quizzes = Quiz.query.filter_by(created_by=user_id).all()
        
        # Get total students
        total_students = User.query.filter_by(role='student', is_active=True).count()
        
        # Get recent quiz attempts
        recent_attempts = QuizAttempt.query.join(Quiz)\
            .filter(Quiz.created_by == user_id)\
            .order_by(QuizAttempt.submitted_at.desc())\
            .limit(10)\
            .all()
        
        # Calculate batch analytics
        all_students = User.query.filter_by(role='student', is_active=True).all()
        total_coding_submissions = CodeSubmission.query.count()
        total_accepted_submissions = CodeSubmission.query.filter_by(status='accepted').count()
        total_quiz_attempts = QuizAttempt.query.count()
        
        # Calculate average quiz score
        quiz_scores = [attempt.score for attempt in QuizAttempt.query.all() if attempt.score is not None]
        avg_quiz_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
        
        batch_analytics = {
            'total_students': total_students,
            'total_submissions': total_coding_submissions,
            'total_quiz_attempts': total_quiz_attempts,
            'batch_avg_accuracy': (total_accepted_submissions / total_coding_submissions * 100) if total_coding_submissions > 0 else 0,
            'batch_avg_quiz_score': round(avg_quiz_score, 2)
        }
        
        return jsonify({
            'quizzes': [q.to_dict() for q in quizzes],
            'recent_attempts': [a.to_dict() for a in recent_attempts],
            'batch_analytics': batch_analytics
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@faculty_bp.route('/students/performance', methods=['GET'])
@jwt_required()
@role_required(['faculty', 'admin'])
def get_student_performance():
    """Get student performance data for faculty/admin dashboard"""
    try:
        student_id = request.args.get('student_id', type=int)
        
        if student_id:
            # Get performance for specific student
            student = User.query.get_or_404(student_id)
            if student.role != 'student':
                return jsonify({'error': 'User is not a student'}), 400
            
            submissions = CodeSubmission.query.filter_by(user_id=student_id).all()
            quiz_attempts = QuizAttempt.query.filter_by(user_id=student_id).all()
            
            total_submissions = len(submissions)
            accepted_submissions = len([s for s in submissions if s.status == 'accepted'])
            accuracy = (accepted_submissions / total_submissions * 100) if total_submissions > 0 else 0
            
            total_quizzes = len(quiz_attempts)
            quiz_scores = [a.score for a in quiz_attempts if a.score is not None]
            avg_quiz_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
            
            return jsonify({
                'performance': [{
                    'student': student.to_dict(),
                    'total_submissions': total_submissions,
                    'accepted_submissions': accepted_submissions,
                    'accuracy': round(accuracy, 2),
                    'total_quizzes': total_quizzes,
                    'avg_quiz_score': round(avg_quiz_score, 2)
                }]
            }), 200
        
        # Get performance for all students
        students = User.query.filter_by(role='student', is_active=True).all()
        performance_data = []
        
        for student in students:
            submissions = CodeSubmission.query.filter_by(user_id=student.id).all()
            quiz_attempts = QuizAttempt.query.filter_by(user_id=student.id).all()
            
            total_submissions = len(submissions)
            accepted_submissions = len([s for s in submissions if s.status == 'accepted'])
            accuracy = (accepted_submissions / total_submissions * 100) if total_submissions > 0 else 0
            
            total_quizzes = len(quiz_attempts)
            quiz_scores = [a.score for a in quiz_attempts if a.score is not None]
            avg_quiz_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
            
            performance_data.append({
                'student': student.to_dict(),
                'total_submissions': total_submissions,
                'accepted_submissions': accepted_submissions,
                'accuracy': round(accuracy, 2),
                'total_quizzes': total_quizzes,
                'avg_quiz_score': round(avg_quiz_score, 2)
            })
        
        return jsonify({'performance': performance_data}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/students/<int:student_id>/details', methods=['GET'])
@jwt_required()
@role_required(['faculty', 'admin'])
def get_student_details(student_id):
    """Get detailed student performance data including submissions, quizzes, and interviews - Faculty/Admin only"""
    try:
        # Get student
        student = User.query.get_or_404(student_id)
        if student.role != 'student':
            return jsonify({'error': 'User is not a student'}), 400
        
        # Get code submissions
        code_submissions = CodeSubmission.query.filter_by(user_id=student_id).order_by(CodeSubmission.submitted_at.desc()).all()
        
        # Get quiz attempts
        quiz_attempts = QuizAttempt.query.filter_by(user_id=student_id).order_by(QuizAttempt.submitted_at.desc()).all()
        
        # Get interview sessions
        interview_sessions = InterviewSession.query.filter_by(user_id=student_id).order_by(InterviewSession.started_at.desc()).all()
        
        # Calculate summary
        total_code_submissions = len(code_submissions)
        accepted_submissions = len([s for s in code_submissions if s.status == 'accepted'])
        total_quiz_attempts = len(quiz_attempts)
        total_interview_attempts = len(interview_sessions)
        completed_interviews = len([i for i in interview_sessions if i.is_completed])
        
        # Format code practice submissions with question details
        code_practice_data = []
        for submission in code_submissions:
            submission_dict = submission.to_dict()
            # Get question directly from database to ensure it's loaded
            question = Question.query.get(submission.question_id) if submission.question_id else None
            if question:
                submission_dict['question'] = {
                    'id': question.id,
                    'title': question.title,
                    'description': question.description
                }
            code_practice_data.append(submission_dict)
        
        # Format quiz attempts with quiz details
        quiz_attempts_data = []
        for attempt in quiz_attempts:
            attempt_dict = attempt.to_dict()
            # Get quiz directly from database if relationship doesn't exist
            quiz = Quiz.query.get(attempt.quiz_id) if attempt.quiz_id else None
            if quiz:
                attempt_dict['quiz'] = {
                    'id': quiz.id,
                    'title': quiz.title,
                    'description': quiz.description
                }
            quiz_attempts_data.append(attempt_dict)
        
        # Format interview sessions
        interview_attempts_data = []
        for session in interview_sessions:
            interview_attempts_data.append({
                'id': session.id,
                'interview_type': session.interview_type,
                'final_score': session.final_score,
                'is_completed': session.is_completed,
                'started_at': session.started_at.isoformat() if session.started_at else None,
                'ended_at': session.ended_at.isoformat() if session.ended_at else None
            })
        
        return jsonify({
            'student': student.to_dict(),
            'summary': {
                'total_code_submissions': total_code_submissions,
                'accepted_submissions': accepted_submissions,
                'total_quiz_attempts': total_quiz_attempts,
                'total_interview_attempts': total_interview_attempts,
                'completed_interviews': completed_interviews
            },
            'code_practice': code_practice_data,
            'quiz_attempts': quiz_attempts_data,
            'interview_attempts': interview_attempts_data
        }), 200
    
    except Exception as e:
        current_app.logger.error(f'Error in get_student_details for student_id={student_id}: {str(e)}', exc_info=True)
        return jsonify({'error': f'Failed to load student details: {str(e)}'}), 500

@faculty_bp.route('/export/student-performance/pdf', methods=['GET'])
@jwt_required()
@role_required(['faculty', 'admin'])
def export_student_performance_pdf():
    """Export student performance as PDF"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from io import BytesIO
        
        # Get student performance data
        students = User.query.filter_by(role='student', is_active=True).all()
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Title
        styles = getSampleStyleSheet()
        title = Paragraph("Student Performance Report", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Prepare data
        data = [['Student Name', 'Username', 'Submissions', 'Accuracy %', 'Quizzes', 'Avg Quiz Score']]
        
        for student in students:
            submissions = CodeSubmission.query.filter_by(user_id=student.id).all()
            quiz_attempts = QuizAttempt.query.filter_by(user_id=student.id).all()
            
            total_submissions = len(submissions)
            accepted_submissions = len([s for s in submissions if s.status == 'accepted'])
            accuracy = (accepted_submissions / total_submissions * 100) if total_submissions > 0 else 0
            
            total_quizzes = len(quiz_attempts)
            quiz_scores = [a.score for a in quiz_attempts if a.score is not None]
            avg_quiz_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
            
            data.append([
                student.full_name or 'N/A',
                student.username,
                str(total_submissions),
                f"{accuracy:.2f}%",
                str(total_quizzes),
                f"{avg_quiz_score:.2f}"
            ])
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        # Create response
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=student_performance_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        return response
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/export/batch-analytics/csv', methods=['GET'])
@jwt_required()
@role_required(['faculty', 'admin'])
def export_batch_analytics_csv():
    """Export batch analytics as CSV"""
    try:
        all_students = User.query.filter_by(role='student', is_active=True).all()
        
        csv_data = []
        csv_data.append(['STUDENT PERFORMANCE REPORT'])
        csv_data.append(['Generated On', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')])
        csv_data.append([])
        csv_data.append(['Student Name', 'Username', 'Submissions', 'Accepted', 'Accuracy %', 'Quizzes', 'Avg Quiz Score'])
        
        total_coding_submissions = 0
        total_accepted_submissions = 0
        total_quiz_attempts = 0
        total_quiz_score = 0
        
        for student in all_students:
            submissions = CodeSubmission.query.filter_by(user_id=student.id).all()
            quiz_attempts = QuizAttempt.query.filter_by(user_id=student.id).all()
            
            total_submissions = len(submissions)
            accepted_submissions = len([s for s in submissions if s.status == 'accepted'])
            accuracy = (accepted_submissions / total_submissions * 100) if total_submissions > 0 else 0
            
            total_quizzes = len(quiz_attempts)
            quiz_scores = [a.score for a in quiz_attempts if a.score is not None]
            avg_quiz_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
            
            csv_data.append([
                student.full_name or 'N/A',
                student.username,
                str(total_submissions),
                str(accepted_submissions),
                f"{accuracy:.2f}",
                str(total_quizzes),
                f"{avg_quiz_score:.2f}"
            ])
            
            total_coding_submissions += total_submissions
            total_accepted_submissions += accepted_submissions
            total_quiz_attempts += total_quizzes
            total_quiz_score += avg_quiz_score * total_quizzes
        
        # Add summary row
        batch_avg_accuracy = (total_accepted_submissions / total_coding_submissions * 100) if total_coding_submissions > 0 else 0
        batch_avg_quiz_score = (total_quiz_score / total_quiz_attempts) if total_quiz_attempts > 0 else 0
        
        csv_data.append([])
        csv_data.append(['BATCH SUMMARY', '', '', '', '', '', ''])
        csv_data.append(['Total Students', str(len(all_students)), '', '', '', '', ''])
        csv_data.append(['Total Submissions', str(total_coding_submissions), '', '', '', '', ''])
        csv_data.append(['Total Accepted', str(total_accepted_submissions), '', '', '', '', ''])
        csv_data.append(['Batch Avg Accuracy %', f"{batch_avg_accuracy:.2f}", '', '', '', '', ''])
        csv_data.append(['Total Quiz Attempts', str(total_quiz_attempts), '', '', '', '', ''])
        csv_data.append(['Batch Avg Quiz Score', f"{batch_avg_quiz_score:.2f}", '', '', '', '', ''])
        csv_data.append(['Generated On', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), '', '', '', '', ''])
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(csv_data)
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=batch_analytics_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==================== ASSESSMENT MANAGEMENT (Faculty/Admin Only) ====================

@faculty_bp.route('/assessments', methods=['GET'])
@jwt_required()
@role_required(['faculty', 'admin'])
def list_assessments():
    """List all assessments - Faculty/Admin only"""
    try:
        module_type = request.args.get('module_type')  # Filter by module_type for strict segregation
        query = Assessment.query.filter_by(is_active=True)
        
        if module_type:
            if module_type not in ['CodePractice', 'Non-Technical', 'Interview', 'Resources']:
                return jsonify({'error': 'Invalid module_type. Must be one of: CodePractice, Non-Technical, Interview, Resources'}), 400
            query = query.filter_by(module_type=module_type)
        
        assessments = query.order_by(Assessment.created_at.desc()).all()
        return jsonify({
            'assessments': [a.to_dict() for a in assessments]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/assessments', methods=['POST'])
@jwt_required()
@role_required(['faculty', 'admin'])
def create_assessment():
    """Create a new assessment (Step 1: Basic Info) - Faculty/Admin only"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400
        if not data.get('assessment_mode'):
            return jsonify({'error': 'Assessment mode is required'}), 400
        if data.get('assessment_mode') not in ['technical_only', 'non_technical_only', 'mixed']:
            return jsonify({'error': 'Invalid assessment mode. Must be: technical_only, non_technical_only, or mixed'}), 400
        if not data.get('start_date'):
            return jsonify({'error': 'Start date is required'}), 400
        if not data.get('end_date'):
            return jsonify({'error': 'End date is required'}), 400
        if not data.get('start_time'):
            return jsonify({'error': 'Start time is required'}), 400
        if not data.get('end_time'):
            return jsonify({'error': 'End time is required'}), 400
        if not data.get('difficulty'):
            return jsonify({'error': 'Difficulty is required'}), 400
        if data.get('difficulty') not in ['easy', 'medium', 'hard', 'na']:
            return jsonify({'error': 'Difficulty must be: easy, medium, hard, or na'}), 400
        
        # Parse date and time strings
        try:
            start_date_obj = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
            start_time_obj = datetime.strptime(data.get('start_time'), '%H:%M').time()
            end_time_obj = datetime.strptime(data.get('end_time'), '%H:%M').time()
        except ValueError as e:
            return jsonify({'error': f'Invalid date or time format: {str(e)}'}), 400
        
        # Validate that end datetime is after start datetime
        start_datetime = datetime.combine(start_date_obj, start_time_obj)
        end_datetime = datetime.combine(end_date_obj, end_time_obj)
        if end_datetime <= start_datetime:
            return jsonify({'error': 'End date and time must be after start date and time'}), 400
        
        # Validate module_type
        module_type = data.get('module_type', 'Non-Technical')  # Default to Non-Technical for backward compatibility
        if module_type not in ['CodePractice', 'Non-Technical', 'Interview', 'Resources']:
            return jsonify({'error': 'module_type must be one of: CodePractice, Non-Technical, Interview, Resources'}), 400
        
        # Handle assigned_batches (list of batch IDs: [1, 2] or [1] or [2], null means all batches)
        assigned_batches = data.get('assigned_batches')  # Can be None, [1], [2], or [1, 2]
        if assigned_batches is not None:
            if not isinstance(assigned_batches, list):
                return jsonify({'error': 'assigned_batches must be a list of batch IDs'}), 400
            from models import Batch
            active_batch_ids = {batch.id for batch in Batch.query.filter_by(is_active=True).all()}
            if not all(isinstance(bid, int) and bid in active_batch_ids for bid in assigned_batches):
                return jsonify({'error': 'assigned_batches must contain only active batch IDs'}), 400
            assigned_batches_json = json.dumps(assigned_batches)
        else:
            assigned_batches_json = None  # NULL means all batches
        
        # Create assessment (as draft initially)
        assessment = Assessment(
            title=data.get('title'),
            description=data.get('description', ''),
            assessment_mode=data.get('assessment_mode'),
            module_type=module_type,
            start_date=start_date_obj,
            end_date=end_date_obj,
            start_time=start_time_obj,
            end_time=end_time_obj,
            difficulty=data.get('difficulty'),
            topic_tags=','.join(data.get('topic_tags', [])) if isinstance(data.get('topic_tags'), list) else data.get('topic_tags', ''),
            status='draft',  # Start as draft
            created_by=user_id,
            is_active=True,
            assigned_batches=assigned_batches_json
        )
        
        db.session.add(assessment)
        db.session.flush()
        
        # Add questions to assessment if provided
        question_ids = data.get('question_ids', [])
        if question_ids:
            total_marks = 0
            for idx, q_id in enumerate(question_ids):
                question = Question.query.get(q_id)
                if question:
                    marks = data.get('question_marks', {}).get(str(q_id), 10)
                    assessment_question = AssessmentQuestion(
                        assessment_id=assessment.id,
                        question_id=q_id,
                        order=idx,
                        marks=marks
                    )
                    db.session.add(assessment_question)
                    total_marks += marks
            
            assessment.total_marks = total_marks
        
        db.session.commit()
        
        return jsonify({
            'message': 'Assessment created successfully (Draft)',
            'assessment': assessment.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/assessments/<int:assessment_id>', methods=['GET'])
@jwt_required()
@role_required(['faculty', 'admin'])
def get_assessment(assessment_id):
    """Get assessment details with questions - Faculty/Admin only"""
    try:
        assessment = Assessment.query.get_or_404(assessment_id)
        assessment_dict = assessment.to_dict()
        assessment_dict['questions'] = [aq.to_dict() for aq in assessment.questions]
        return jsonify({'assessment': assessment_dict}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/assessments/<int:assessment_id>', methods=['PUT'])
@jwt_required()
@role_required(['faculty', 'admin'])
def update_assessment(assessment_id):
    """Update an assessment - Faculty/Admin only"""
    try:
        assessment = Assessment.query.get_or_404(assessment_id)
        data = request.get_json()
        
        if data.get('title'):
            assessment.title = data['title']
        if data.get('description') is not None:
            assessment.description = data['description']
        if data.get('assessment_mode'):
            if data['assessment_mode'] not in ['technical_only', 'non_technical_only', 'mixed']:
                return jsonify({'error': 'Invalid assessment mode'}), 400
            assessment.assessment_mode = data['assessment_mode']
        if data.get('module_type'):
            if data['module_type'] not in ['CodePractice', 'Non-Technical', 'Interview', 'Resources']:
                return jsonify({'error': 'Invalid module_type. Must be one of: CodePractice, Non-Technical, Interview, Resources'}), 400
            assessment.module_type = data['module_type']
        if 'assigned_batches' in data:
            assigned_batches = data['assigned_batches']
            if assigned_batches is not None:
                if not isinstance(assigned_batches, list):
                    return jsonify({'error': 'assigned_batches must be a list of batch IDs'}), 400
                from models import Batch
                active_batch_ids = {batch.id for batch in Batch.query.filter_by(is_active=True).all()}
                if not all(isinstance(bid, int) and bid in active_batch_ids for bid in assigned_batches):
                    return jsonify({'error': 'assigned_batches must contain only active batch IDs'}), 400
                assessment.assigned_batches = json.dumps(assigned_batches)
            else:
                assessment.assigned_batches = None  # NULL means all batches
        if data.get('start_date'):
            try:
                assessment.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid start date format'}), 400
        if data.get('end_date'):
            try:
                assessment.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid end date format'}), 400
        if data.get('start_time'):
            try:
                assessment.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
            except ValueError:
                return jsonify({'error': 'Invalid start time format'}), 400
        if data.get('end_time'):
            try:
                assessment.end_time = datetime.strptime(data['end_time'], '%H:%M').time()
            except ValueError:
                return jsonify({'error': 'Invalid end time format'}), 400
        # Validate that end datetime is after start datetime if both are being updated
        if (data.get('start_date') or data.get('start_time') or data.get('end_date') or data.get('end_time')):
            start_date_obj = assessment.start_date
            end_date_obj = assessment.end_date
            start_time_obj = assessment.start_time
            end_time_obj = assessment.end_time
            start_datetime = datetime.combine(start_date_obj, start_time_obj)
            end_datetime = datetime.combine(end_date_obj, end_time_obj)
            if end_datetime <= start_datetime:
                return jsonify({'error': 'End date and time must be after start date and time'}), 400
        if data.get('difficulty'):
            if data['difficulty'] not in ['easy', 'medium', 'hard', 'na']:
                return jsonify({'error': 'Difficulty must be: easy, medium, hard, or na'}), 400
            assessment.difficulty = data['difficulty']
        if data.get('topic_tags'):
            assessment.topic_tags = ','.join(data['topic_tags']) if isinstance(data['topic_tags'], list) else data['topic_tags']
        if data.get('status'):
            if data['status'] not in ['draft', 'published']:
                return jsonify({'error': 'Invalid status'}), 400
            assessment.status = data['status']
            if data['status'] == 'published' and not assessment.published_at:
                assessment.published_at = datetime.utcnow()
        
        # Update questions if provided
        if 'question_ids' in data:
            # Remove existing questions
            AssessmentQuestion.query.filter_by(assessment_id=assessment_id).delete()
            
            # Add new questions
            question_ids = data.get('question_ids', [])
            total_marks = 0
            for idx, q_id in enumerate(question_ids):
                question = Question.query.get(q_id)
                if question:
                    marks = data.get('question_marks', {}).get(str(q_id), 10)
                    assessment_question = AssessmentQuestion(
                        assessment_id=assessment.id,
                        question_id=q_id,
                        order=idx,
                        marks=marks
                    )
                    db.session.add(assessment_question)
                    total_marks += marks
            
            assessment.total_marks = total_marks
        
        db.session.commit()
        
        return jsonify({
            'message': 'Assessment updated successfully',
            'assessment': assessment.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/assessments/<int:assessment_id>', methods=['DELETE'])
@jwt_required()
@role_required(['faculty', 'admin'])
def delete_assessment(assessment_id):
    """Delete (deactivate) an assessment - Faculty/Admin only"""
    try:
        assessment = Assessment.query.get_or_404(assessment_id)
        assessment.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Assessment deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/assessments/<int:assessment_id>/attempts', methods=['GET'])
@jwt_required()
@role_required(['faculty', 'admin'])
def get_assessment_attempts(assessment_id):
    """Get all student attempts for an assessment - Faculty/Admin only"""
    try:
        assessment = Assessment.query.get_or_404(assessment_id)
        attempts = AssessmentAttempt.query.filter_by(assessment_id=assessment_id).order_by(AssessmentAttempt.submitted_at.desc()).all()
        
        attempts_data = [attempt.to_dict() for attempt in attempts]
        
        return jsonify({
            'assessment': assessment.to_dict(),
            'attempts': attempts_data,
            'total_attempts': len(attempts_data)
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/assessments/<int:assessment_id>/questions', methods=['POST'])
@jwt_required()
@role_required(['faculty', 'admin'])
def add_question_to_assessment(assessment_id):
    """Add a question to an assessment (create new or add existing) - Faculty/Admin only"""
    try:
        assessment = Assessment.query.get_or_404(assessment_id)
        data = request.get_json()
        
        # Check if creating new question or adding existing
        if data.get('create_new'):
            # Create new question first
            user_id = get_jwt_identity()
            question_data = data.get('question_data', {})
            
            if not question_data.get('title'):
                return jsonify({'error': 'Question title is required'}), 400
            if not question_data.get('description'):
                return jsonify({'error': 'Question description is required'}), 400
            if not question_data.get('type'):
                return jsonify({'error': 'Question type is required'}), 400
            
            # Validate assessment mode compatibility
            question_type = question_data.get('type')
            if assessment.assessment_mode == 'technical_only' and question_type != 'coding':
                return jsonify({'error': 'Only coding questions allowed in technical-only assessment'}), 400
            if assessment.assessment_mode == 'non_technical_only' and question_type == 'coding':
                return jsonify({'error': 'Coding questions not allowed in non-technical-only assessment'}), 400
            
            # Create question - ensure module_type matches assessment
            question = Question(
                title=question_data.get('title'),
                description=question_data.get('description'),
                type=question_type,
                module_type=assessment.module_type,  # Use assessment's module_type
                difficulty=question_data.get('difficulty', assessment.difficulty),
                tags=','.join(question_data.get('tags', [])) if isinstance(question_data.get('tags'), list) else question_data.get('tags', ''),
                created_by=user_id,
                is_active=True
            )
            
            # Type-specific fields
            if question_type == 'coding':
                question.test_cases = json.dumps(question_data.get('test_cases', []))
                question.starter_code = question_data.get('starter_code', '')
                question.solution = question_data.get('solution', '')
            elif question_type == 'mcq':
                question.options = json.dumps(question_data.get('options', []))
                question.correct_answer = question_data.get('correct_answer', '')
                question.marks = question_data.get('marks', 1)
            elif question_type == 'fill_blank':
                question.blanks = json.dumps(question_data.get('blanks', []))
            
            db.session.add(question)
            db.session.flush()
            question_id = question.id
        else:
            # Use existing question
            question_id = data.get('question_id')
            if not question_id:
                return jsonify({'error': 'question_id is required'}), 400
            
            question = Question.query.get(question_id)
            if not question:
                return jsonify({'error': 'Question not found'}), 404
            
            # Validate that the question's module_type matches the assessment's module_type (STRICT SEGREGATION)
            if question.module_type != assessment.module_type:
                return jsonify({'error': f'Question module_type ({question.module_type}) does not match assessment module_type ({assessment.module_type})'}), 400
            
            # Validate assessment mode compatibility
            if assessment.assessment_mode == 'technical_only' and question.type != 'coding':
                return jsonify({'error': 'Only coding questions allowed in technical-only assessment'}), 400
            if assessment.assessment_mode == 'non_technical_only' and question.type == 'coding':
                return jsonify({'error': 'Coding questions not allowed in non-technical-only assessment'}), 400
        
        # Check if question already exists in assessment
        existing = AssessmentQuestion.query.filter_by(
            assessment_id=assessment_id,
            question_id=question_id
        ).first()
        
        if existing:
            return jsonify({'error': 'Question already added to assessment'}), 400
        
        # Get next order number
        max_order = db.session.query(db.func.max(AssessmentQuestion.order)).filter_by(
            assessment_id=assessment_id
        ).scalar() or -1
        
        marks = data.get('marks', question.marks if hasattr(question, 'marks') and question.marks else 10)
        
        assessment_question = AssessmentQuestion(
            assessment_id=assessment_id,
            question_id=question_id,
            order=max_order + 1,
            marks=marks
        )
        
        db.session.add(assessment_question)
        
        # Update total marks
        assessment.total_marks = (assessment.total_marks or 0) + marks
        
        db.session.commit()
        
        return jsonify({
            'message': 'Question added to assessment successfully',
            'assessment_question': assessment_question.to_dict(),
            'assessment': assessment.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/assessments/<int:assessment_id>/questions/<int:question_id>', methods=['DELETE'])
@jwt_required()
@role_required(['faculty', 'admin'])
def remove_question_from_assessment(assessment_id, question_id):
    """Remove a question from an assessment - Faculty/Admin only"""
    try:
        assessment = Assessment.query.get_or_404(assessment_id)
        assessment_question = AssessmentQuestion.query.filter_by(
            assessment_id=assessment_id,
            question_id=question_id
        ).first_or_404()
        
        # Update total marks
        assessment.total_marks = max(0, (assessment.total_marks or 0) - assessment_question.marks)
        
        db.session.delete(assessment_question)
        db.session.commit()
        
        return jsonify({
            'message': 'Question removed from assessment successfully',
            'assessment': assessment.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/assessments/<int:assessment_id>/questions/reorder', methods=['POST'])
@jwt_required()
@role_required(['faculty', 'admin'])
def reorder_assessment_questions(assessment_id):
    """Reorder questions in an assessment - Faculty/Admin only"""
    try:
        assessment = Assessment.query.get_or_404(assessment_id)
        data = request.get_json()
        
        question_orders = data.get('question_orders', [])  # List of {assessment_question_id: order}
        
        for item in question_orders:
            aq_id = item.get('assessment_question_id')
            new_order = item.get('order')
            
            if aq_id and new_order is not None:
                assessment_question = AssessmentQuestion.query.filter_by(
                    id=aq_id,
                    assessment_id=assessment_id
                ).first()
                
                if assessment_question:
                    assessment_question.order = new_order
        
        db.session.commit()
        
        return jsonify({
            'message': 'Questions reordered successfully',
            'assessment': assessment.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/assessments/<int:assessment_id>/publish', methods=['POST'])
@jwt_required()
@role_required(['faculty', 'admin'])
def publish_assessment(assessment_id):
    """Publish an assessment - Faculty/Admin only"""
    try:
        assessment = Assessment.query.get_or_404(assessment_id)
        
        # Validate that assessment has questions
        if not assessment.questions or len(assessment.questions) == 0:
            return jsonify({'error': 'Cannot publish assessment without questions'}), 400
        
        assessment.status = 'published'
        assessment.published_at = datetime.utcnow()
        
        # Create notifications for all students
        students = User.query.filter_by(role='student', is_active=True).all()
        for student in students:
            notification = Notification(
                user_id=student.id,
                title='New Assessment Published',
                message=f'A new assessment "{assessment.title}" has been published. Click to view and attempt!',
                type='assessment',
                link=f'assessment:{assessment_id}'  # Custom link format for assessment
            )
            db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Assessment published successfully',
            'assessment': assessment.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/questions', methods=['GET'])
@jwt_required()
@role_required(['faculty', 'admin'])
def list_questions():
    """List all questions (for faculty/admin - includes inactive)"""
    try:
        module_type = request.args.get('module_type')  # Filter by module_type for strict segregation
        query = Question.query
        
        if module_type:
            if module_type not in ['CodePractice', 'Non-Technical', 'Interview', 'Resources']:
                return jsonify({'error': 'Invalid module_type. Must be one of: CodePractice, Non-Technical, Interview, Resources'}), 400
            query = query.filter_by(module_type=module_type)
        
        questions = query.order_by(Question.created_at.desc()).all()
        return jsonify({
            'questions': [q.to_dict() for q in questions]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/questions/<int:question_id>', methods=['DELETE'])
@jwt_required()
@role_required(['faculty', 'admin'])
def delete_question(question_id):
    """Delete (deactivate) a question"""
    try:
        question = Question.query.get_or_404(question_id)
        question.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Question deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== ASSESSMENT MANAGEMENT (Faculty/Admin Only) ====================

@faculty_bp.route('/questions', methods=['POST'])
@jwt_required()
@role_required(['student', 'faculty', 'admin'])
def create_question():
    """Create a new question (Coding, MCQ, or Fill-in-the-blank) - All users can create questions"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400
        if not data.get('description'):
            return jsonify({'error': 'Description is required'}), 400
        if not data.get('type') or data.get('type') not in ['coding', 'mcq', 'fill_blank']:
            return jsonify({'error': 'Type must be coding, mcq, or fill_blank'}), 400
        if not data.get('module_type') or data.get('module_type') not in ['CodePractice', 'Non-Technical', 'Interview', 'Resources']:
            return jsonify({'error': 'module_type is required and must be one of: CodePractice, Non-Technical, Interview, Resources'}), 400
        
        question_type = data.get('type')
        module_type = data.get('module_type')
        
        # Create question
        question = Question(
            title=data.get('title'),
            description=data.get('description'),
            type=question_type,
            module_type=module_type,
            difficulty=data.get('difficulty', 'medium'),  # easy, medium, hard
            company_id=data.get('company_id'),
            tags=','.join(data.get('tags', [])) if isinstance(data.get('tags'), list) else data.get('tags', ''),
            created_by=user_id,
            is_active=True
        )
        
        # Type-specific fields
        if question_type == 'coding':
            question.test_cases = json.dumps(data.get('test_cases', []))
            question.starter_code = data.get('starter_code', '')
            question.solution = data.get('solution', '')
        elif question_type == 'mcq':
            question.options = json.dumps(data.get('options', []))
            question.correct_answer = data.get('correct_answer', '')
            question.marks = data.get('marks', 1)
        elif question_type == 'fill_blank':
            question.blanks = json.dumps(data.get('blanks', []))
        
        db.session.add(question)
        db.session.flush()
        
        # Notify all students about the new question
        question_type_label = 'Coding Question' if question_type == 'coding' else 'Non-Technical Question'
        students = User.query.filter_by(role='student', is_active=True).all()
        for student in students:
            notification = Notification(
                user_id=student.id,
                title=f'New {question_type_label} Added',
                message=f'A new {question_type_label.lower()} "{question.title}" has been added. Start practicing!',
                type='question',
                link=f'/coding/questions/{question.id}' if question_type == 'coding' else f'/non-technical'
            )
            db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Question created successfully',
            'question': question.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/questions/<int:question_id>', methods=['PUT'])
@jwt_required()
@role_required(['faculty', 'admin'])
def update_question(question_id):
    """Update a question - Faculty/Admin only"""
    try:
        question = Question.query.get_or_404(question_id)
        data = request.get_json()
        
        if data.get('title'):
            question.title = data['title']
        if data.get('description'):
            question.description = data['description']
        if data.get('difficulty'):
            question.difficulty = data['difficulty']
        if data.get('tags'):
            question.tags = ','.join(data['tags']) if isinstance(data['tags'], list) else data['tags']
        
        # Type-specific updates
        if question.type == 'coding':
            if 'test_cases' in data:
                question.test_cases = json.dumps(data['test_cases'])
            if 'starter_code' in data:
                question.starter_code = data['starter_code']
            if 'solution' in data:
                question.solution = data['solution']
        elif question.type == 'mcq':
            if 'options' in data:
                question.options = json.dumps(data['options'])
            if 'correct_answer' in data:
                question.correct_answer = data['correct_answer']
            if 'marks' in data:
                question.marks = data['marks']
        elif question.type == 'fill_blank':
            if 'blanks' in data:
                question.blanks = json.dumps(data['blanks'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Question updated successfully',
            'question': question.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/submissions/<int:submission_id>/evaluate', methods=['POST'])
@jwt_required()
@role_required(['faculty', 'admin'])
def evaluate_submission(submission_id):
    """Add manual evaluation comment to a code submission"""
    try:
        user_id = get_jwt_identity()
        submission = CodeSubmission.query.get_or_404(submission_id)
        data = request.get_json()
        
        comment = data.get('comment', '')
        if not comment:
            return jsonify({'error': 'Comment is required'}), 400
        
        submission.evaluation_comment = comment
        submission.evaluated_by = user_id
        submission.evaluated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Evaluation added successfully',
            'submission': submission.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@faculty_bp.route('/feedback', methods=['POST'])
@jwt_required()
@role_required(['faculty', 'admin'])
def provide_feedback():
    """Provide feedback to a student - Faculty/Admin only"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        student_id = data.get('student_id')
        title = data.get('title', 'Feedback from Faculty')
        message = data.get('message')
        link = data.get('link', '')
        
        if not student_id:
            return jsonify({'error': 'Student ID is required'}), 400
        
        if not message or not message.strip():
            return jsonify({'error': 'Feedback message is required'}), 400
        
        # Verify student exists and is a student
        student = User.query.get_or_404(student_id)
        if student.role != 'student':
            return jsonify({'error': 'User is not a student'}), 400
        
        # Create notification for the student
        notification = Notification(
            user_id=student_id,
            title=title,
            message=message,
            link=link if link else None,
            type='feedback',
            is_read=False
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'message': 'Feedback sent successfully',
            'notification': notification.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
