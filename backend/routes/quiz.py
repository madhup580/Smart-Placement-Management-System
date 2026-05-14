"""
Quiz routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Quiz, QuizQuestion, QuizAttempt, QuizAssignment, Question, User, Notification, db
from utils.auth import role_required
from utils.leaderboard import update_leaderboard
from datetime import datetime
import json

quiz_bp = Blueprint('quiz', __name__)

@quiz_bp.route('/list', methods=['GET'])
@jwt_required()
def list_quizzes():
    """Get list of available quizzes"""
    try:
        company_id = request.args.get('company_id')
        is_active = request.args.get('is_active', 'true').lower() == 'true'
        
        query = Quiz.query.filter_by(is_active=is_active)
        
        if company_id:
            query = query.filter_by(company_id=company_id)
        
        quizzes = query.order_by(Quiz.created_at.desc()).all()
        
        return jsonify({
            'quizzes': [q.to_dict() for q in quizzes]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@quiz_bp.route('/<int:quiz_id>', methods=['GET'])
@jwt_required()
def get_quiz(quiz_id):
    """Get quiz details with access control"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        quiz = Quiz.query.get_or_404(quiz_id)
        
        # Check if quiz is locked
        if quiz.is_locked():
            return jsonify({
                'error': 'This quiz has been locked after the deadline',
                'quiz': quiz.to_dict(),
                'is_locked': True
            }), 403
        
        # Check if student is assigned to this quiz (only for students)
        if user and user.role == 'student':
            # Check if quiz is assigned to entire batch or specific students
            if quiz.assignment_type == 'selected_students':
                assignment = QuizAssignment.query.filter_by(quiz_id=quiz_id, user_id=user_id).first()
                if not assignment:
                    return jsonify({
                        'error': 'You are not assigned to this quiz',
                        'quiz': quiz.to_dict(),
                        'is_assigned': False
                    }), 403
        
        quiz_questions = QuizQuestion.query.filter_by(quiz_id=quiz_id)\
            .order_by(QuizQuestion.order).all()
        
        quiz_data = quiz.to_dict()
        quiz_data['questions'] = [q.to_dict() for q in quiz_questions]
        
        return jsonify({
            'quiz': quiz_data,
            'is_locked': False,
            'is_assigned': True
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@quiz_bp.route('/quizzes', methods=['POST'])
@jwt_required()
@role_required(['faculty', 'admin'])
def create_quiz():

    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()

        title = data.get('title')
        description = data.get('description', '')
        duration_minutes = data.get('duration_minutes', 60)
        question_ids = data.get('question_ids', [])
        question_marks = data.get('question_marks', {})
        total_marks = data.get('total_marks', 0)

        if not title:
            return jsonify({
                "error": "Title is required"
            }), 400

        if not question_ids:
            return jsonify({
                "error": "At least one question is required"
            }), 400

        # Create quiz
        quiz = Quiz(
            title=title,
            description=description,
            duration_minutes=duration_minutes,
            total_marks=total_marks,
            created_by=user_id
        )

        db.session.add(quiz)
        db.session.flush()

        # Add questions
        for order, question_id in enumerate(question_ids):

            question = Question.query.get(question_id)

            if not question:
                continue

            marks = question_marks.get(str(question_id), 1)

            quiz_question = QuizQuestion(
                quiz_id=quiz.id,
                question_id=question_id,
                marks=marks,
                order=order
            )

            db.session.add(quiz_question)

        db.session.commit()

        return jsonify({
            "message": "Quiz created successfully",
            "quiz": quiz.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()

        import traceback
        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500

@quiz_bp.route('/<int:quiz_id>/attempt', methods=['POST'])
@jwt_required()
@role_required(['student', 'faculty', 'admin'])
def attempt_quiz(quiz_id):
    """Submit quiz attempt with deadline and assignment checks"""
    try:
        from datetime import datetime
        from flask_jwt_extended import get_jwt_identity
        
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        answers = data.get('answers', {})  # {question_id: answer}
        
        quiz = Quiz.query.get_or_404(quiz_id)
        
        # Check if quiz is locked
        if quiz.is_locked():
            return jsonify({'error': 'This quiz has been locked after the deadline. Submissions are no longer accepted.'}), 403
        
        # Check if student is assigned to this quiz (only for students)
        if user.role == 'student':
            if quiz.assignment_type == 'selected_students':
                assignment = QuizAssignment.query.filter_by(quiz_id=quiz_id, user_id=user_id).first()
                if not assignment:
                    return jsonify({'error': 'You are not assigned to this quiz'}), 403
        quiz_questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).all()
        
        # Calculate score and track per-question results
        total_marks = 0
        obtained_marks = 0
        question_results = {}
        
        for qq in quiz_questions:
            question = qq.question
            total_marks += qq.marks
            question_marks = 0
            is_correct = False
            
            if question.type == 'mcq':
                user_answer = answers.get(str(question.id))
                if user_answer == question.correct_answer:
                    obtained_marks += qq.marks
                    question_marks = qq.marks
                    is_correct = True
            elif question.type == 'fill_blank':
                user_answers = answers.get(str(question.id), {})
                blanks = json.loads(question.blanks) if question.blanks else []
                correct_count = 0
                for blank in blanks:
                    blank_id = blank.get('id')
                    correct_answer = blank.get('answer', '').lower().strip()
                    user_answer = user_answers.get(str(blank_id), '').lower().strip()
                    if user_answer == correct_answer:
                        correct_count += 1
                
                if len(blanks) > 0:
                    partial_marks = (correct_count / len(blanks)) * qq.marks
                    obtained_marks += partial_marks
                    question_marks = partial_marks
                    is_correct = (correct_count == len(blanks))
            
            question_results[question.id] = {
                'is_correct': is_correct,
                'marks_obtained': question_marks,
                'marks_total': qq.marks,
                'user_answer': answers.get(str(question.id), ''),
                'correct_answer': question.correct_answer
            }
        
        score = (obtained_marks / total_marks * 100) if total_marks > 0 else 0
        
        # Create quiz attempt
        attempt = QuizAttempt(
            user_id=user_id,
            quiz_id=quiz_id,
            answers=json.dumps(answers),
            score=score,
            total_marks=total_marks,
            submitted_at=datetime.utcnow()
        )
        
        db.session.add(attempt)
        db.session.commit()
        
        # Update leaderboard
        update_leaderboard(user_id)
        
        # Create notification
        notification = Notification(
            user_id=user_id,
            title='Quiz Submitted',
            message=f'Your quiz "{quiz.title}" has been submitted. Score: {score:.2f}%',
            type='quiz_result',
            link=f'/quiz/{quiz_id}/result/{attempt.id}'
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'attempt': attempt.to_dict(),
            'score': score,
            'obtained_marks': obtained_marks,
            'total_marks': total_marks,
            'question_results': question_results,
            'answers': answers
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@quiz_bp.route('/attempts', methods=['GET'])
@jwt_required()
def get_attempts():
    """Get user's quiz attempts"""
    try:
        user_id = get_jwt_identity()
        quiz_id = request.args.get('quiz_id')
        
        query = QuizAttempt.query.filter_by(user_id=user_id)
        
        if quiz_id:
            query = query.filter_by(quiz_id=quiz_id)
        
        attempts = query.order_by(QuizAttempt.submitted_at.desc()).all()
        
        return jsonify({
            'attempts': [a.to_dict() for a in attempts]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@quiz_bp.route('/quizzes/<int:quiz_id>', methods=['DELETE'])
@jwt_required()
@role_required(['faculty', 'admin'])
def delete_quiz(quiz_id):

    try:
        quiz = Quiz.query.get_or_404(quiz_id)

        # Delete related quiz questions
        QuizQuestion.query.filter_by(quiz_id=quiz_id).delete()

        # Delete quiz attempts
        QuizAttempt.query.filter_by(quiz_id=quiz_id).delete()

        # Delete assignments
        QuizAssignment.query.filter_by(quiz_id=quiz_id).delete()

        # Delete quiz
        db.session.delete(quiz)

        db.session.commit()

        return jsonify({
            "message": "Quiz deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()

        import traceback
        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500