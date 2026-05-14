"""
Admin routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User, Company, Question, CodeSubmission, QuizAttempt, Batch, db
from utils.auth import role_required
from sqlalchemy import func
from datetime import datetime
import json

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@role_required(['admin'])
def dashboard():
    """Get admin dashboard statistics with batch analytics"""
    try:
        total_students = User.query.filter_by(role='student').count()
        total_faculty = User.query.filter_by(role='faculty').count()
        total_questions = Question.query.count()
        total_companies = Company.query.count()
        active_students = User.query.filter_by(role='student', is_active=True).count()
        
        # Batch Analytics
        all_students = User.query.filter_by(role='student', is_active=True).all()
        total_coding_submissions = CodeSubmission.query.count()
        total_accepted = CodeSubmission.query.filter_by(status='accepted').count()
        total_quiz_attempts = QuizAttempt.query.count()
        
        batch_avg_accuracy = (total_accepted / total_coding_submissions * 100) if total_coding_submissions > 0 else 0
        avg_quiz_score = db.session.query(func.avg(QuizAttempt.score)).scalar() or 0
        
        return jsonify({
            'total_students': total_students,
            'total_faculty': total_faculty,
            'active_students': active_students,
            'total_questions': total_questions,
            'total_companies': total_companies,
            'batch_analytics': {
                'total_students': active_students,
                'total_submissions': total_coding_submissions,
                'total_quiz_attempts': total_quiz_attempts,
                'batch_avg_accuracy': round(batch_avg_accuracy, 2),
                'batch_avg_quiz_score': round(avg_quiz_score, 2)
            }
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@role_required(['admin'])
def list_users():
    """List all users"""
    try:
        role = request.args.get('role')
        is_active = request.args.get('is_active')
        
        query = User.query
        
        if role:
            query = query.filter_by(role=role)
        if is_active is not None:
            query = query.filter_by(is_active=is_active.lower() == 'true')
        
        users = query.all()
        
        return jsonify({
            'users': [u.to_dict() for u in users]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
@role_required(['admin'])
def update_user(user_id):
    """Update user (activate/deactivate, change role)"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'role' in data and data['role'] in ['student', 'faculty', 'admin']:
            user.role = data['role']
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'batch_id' in data:
            # Only admin can change batch
            batch_id = data['batch_id']
            if batch_id is not None:
                batch = Batch.query.get(batch_id)
                if not batch:
                    return jsonify({'error': 'Invalid batch_id'}), 400
            user.batch_id = batch_id
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@role_required(['admin'])
def delete_user(user_id):
    """Delete user and all associated data"""
    try:
        from models import Leaderboard, CodeSubmission, QuizAttempt, Post, Resource, Notification, InterviewSession, ResumeData, JobDescriptionData, InterviewAnswer, InterviewResult
        
        user = User.query.get_or_404(user_id)
        
        # Don't allow deleting yourself
        current_user_id = get_jwt_identity()
        if user.id == current_user_id:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        # Delete related data in correct order to avoid foreign key constraint violations
        # 1. Delete InterviewSession related data first
        sessions_to_delete = InterviewSession.query.filter_by(user_id=user_id).all()
        session_ids = [s.id for s in sessions_to_delete]
        if session_ids:
            InterviewResult.query.filter(InterviewResult.session_id.in_(session_ids)).delete(synchronize_session=False)
            InterviewAnswer.query.filter(InterviewAnswer.session_id.in_(session_ids)).delete(synchronize_session=False)
            ResumeData.query.filter(ResumeData.session_id.in_(session_ids)).delete(synchronize_session=False)
            JobDescriptionData.query.filter(JobDescriptionData.session_id.in_(session_ids)).delete(synchronize_session=False)
            InterviewSession.query.filter(InterviewSession.id.in_(session_ids)).delete(synchronize_session=False)
        
        # 2. Delete Leaderboard entry
        Leaderboard.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        
        # 3. Delete CodeSubmissions
        CodeSubmission.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        
        # 4. Delete QuizAttempts
        QuizAttempt.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        
        # 5. Delete Posts
        Post.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        
        # 6. Delete Resources
        Resource.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        
        # 7. Delete Notifications
        Notification.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        
        # 8. Finally, delete the user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'message': 'User and all associated data deleted successfully'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@admin_bp.route('/companies', methods=['POST'])
@jwt_required()
@role_required(['admin'])
def create_company():
    """Create a new company"""
    try:
        data = request.get_json()
        
        company = Company(
            name=data.get('name'),
            description=data.get('description'),
            logo_url=data.get('logo_url')
        )
        
        db.session.add(company)
        db.session.commit()
        
        return jsonify({
            'message': 'Company created successfully',
            'company': company.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/companies', methods=['GET'])
@jwt_required()
def list_companies():
    """List all companies"""
    try:
        companies = Company.query.all()
        
        return jsonify({
            'companies': [c.to_dict() for c in companies]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/companies/<int:company_id>', methods=['DELETE'])
@jwt_required()
@role_required(['faculty', 'admin'])
def delete_company(company_id):
    """Delete a company"""
    try:
        from models import Question, Post, Resource, Quiz, QuizQuestion, CodeSubmission
        
        company = Company.query.get_or_404(company_id)
        
        # Get all questions for this company first
        questions_with_company = Question.query.filter_by(company_id=company_id).all()
        question_ids = [q.id for q in questions_with_company]
        
        # Delete in correct order to avoid foreign key constraint violations
        # 1. Delete code submissions that reference these questions
        if question_ids:
            CodeSubmission.query.filter(CodeSubmission.question_id.in_(question_ids)).delete(synchronize_session=False)
        
        # 2. Delete quiz questions that reference these questions
        if question_ids:
            QuizQuestion.query.filter(QuizQuestion.question_id.in_(question_ids)).delete(synchronize_session=False)
        
        # 3. Delete questions (now safe since code_submissions are deleted)
        Question.query.filter_by(company_id=company_id).delete(synchronize_session=False)
        
        # 4. Delete posts
        Post.query.filter_by(company_id=company_id).delete(synchronize_session=False)
        
        # 5. Delete resources
        Resource.query.filter_by(company_id=company_id).delete(synchronize_session=False)
        
        # 6. Delete quizzes (this will cascade to quiz_questions)
        Quiz.query.filter_by(company_id=company_id).delete(synchronize_session=False)
        
        # 7. Finally, delete the company
        db.session.delete(company)
        db.session.commit()
        
        return jsonify({
            'message': 'Company deleted successfully'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error deleting company: {error_trace}")
        return jsonify({'error': str(e), 'trace': error_trace}), 500

@admin_bp.route('/questions/<int:question_id>/approve', methods=['POST'])
@jwt_required()
@role_required(['admin'])
def approve_question(question_id):
    """Approve a question"""
    try:
        question = Question.query.get_or_404(question_id)
        question.is_active = True
        
        db.session.commit()
        
        return jsonify({
            'message': 'Question approved',
            'question': question.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/questions/<int:question_id>/reject', methods=['POST'])
@jwt_required()
@role_required(['admin'])
def reject_question(question_id):
    """Reject/deactivate a question"""
    try:
        question = Question.query.get_or_404(question_id)
        question.is_active = False
        
        db.session.commit()
        
        return jsonify({
            'message': 'Question rejected',
            'question': question.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== ADMIN PRIVILEGES - Faculty Management ====================

@admin_bp.route('/faculty', methods=['GET'])
@jwt_required()
@role_required(['admin'])
def list_faculty():
    """List all faculty members"""
    try:
        faculty = User.query.filter_by(role='faculty').all()
        return jsonify({
            'faculty': [f.to_dict() for f in faculty]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/faculty/<int:faculty_id>', methods=['PUT'])
@jwt_required()
@role_required(['admin'])
def update_faculty(faculty_id):
    """Update faculty member (activate/deactivate)"""
    try:
        faculty = User.query.get_or_404(faculty_id)
        if faculty.role != 'faculty':
            return jsonify({'error': 'User is not a faculty member'}), 400
        
        data = request.get_json()
        if 'is_active' in data:
            faculty.is_active = data['is_active']
        
        db.session.commit()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Faculty updated successfully',
            'faculty': faculty.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/activity-logs', methods=['GET'])
@jwt_required()
@role_required(['admin'])
def get_all_activity_logs():
    """Get all activity logs (admin has full access)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        activity_type = request.args.get('activity_type')
        entity_type = request.args.get('entity_type')
        
        query = ActivityLog.query
        
        if activity_type:
            query = query.filter_by(activity_type=activity_type)
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        
        logs = query.order_by(ActivityLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'logs': [log.to_dict() for log in logs.items],
            'total': logs.total,
            'page': page,
            'per_page': per_page,
            'pages': logs.pages
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

