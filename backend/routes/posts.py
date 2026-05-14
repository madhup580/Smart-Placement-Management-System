"""
Posts routes for company-related posts
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Post, Company, User
from utils.auth import role_required
from werkzeug.utils import secure_filename
from config import Config
import os

posts_bp = Blueprint('posts', __name__)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['pdf', 'jpg', 'jpeg', 'png']

@posts_bp.route('/posts', methods=['POST'])
@jwt_required()
@role_required(['student', 'faculty', 'admin'])
def create_post():
    """Create a new company post with MCQ question and optional file upload"""
    try:
        user_id = get_jwt_identity()
        
        # Get form data (all fields are optional)
        company_name = request.form.get('company_name', '').strip()
        question = request.form.get('question', '').strip()
        options_json = request.form.get('options', '[]')
        correct_answer = request.form.get('correct_answer', '')
        description = request.form.get('description', '').strip()
        
        # Validate that at least some content is provided
        has_content = False
        if company_name:
            has_content = True
        if question:
            has_content = True
        if description:
            has_content = True
        if 'file' in request.files and request.files['file'].filename:
            has_content = True
        
        if not has_content:
            return jsonify({'error': 'Please provide at least company name, question, description, or file'}), 400
        
        # Parse options if provided
        import json
        options = []
        if options_json:
            try:
                options = json.loads(options_json) if isinstance(options_json, str) else options_json
            except:
                options = []
        
        # If question is provided, validate options and correct answer
        if question:
            if len(options) < 2:
                return jsonify({'error': 'At least 2 options are required when providing a question'}), 400
            if not correct_answer:
                return jsonify({'error': 'Correct answer is required when providing a question'}), 400
        
        # Find or create company (if company name provided)
        company_id = None
        if company_name:
            company = Company.query.filter_by(name=company_name).first()
            if not company:
                # Create new company if it doesn't exist
                company = Company(
                    name=company_name,
                    description=f'Company: {company_name}'
                )
                db.session.add(company)
                db.session.flush()  # Get the ID without committing
            
            company_id = company.id
        else:
            # If no company name, use a default or create a generic one
            company = Company.query.filter_by(name='General').first()
            if not company:
                company = Company(
                    name='General',
                    description='General interview questions'
                )
                db.session.add(company)
                db.session.flush()
            company_id = company.id
        
        # Handle file upload (optional)
        file_path = None
        file_type = None
        
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_ext = filename.rsplit('.', 1)[1].lower()
                    
                    # Ensure upload folder exists
                    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                    file_path = os.path.join(Config.UPLOAD_FOLDER, f"post_{user_id}_{filename}")
                    file.save(file_path)
                    file_path = os.path.abspath(file_path)
                    file_type = file_ext
                else:
                    return jsonify({'error': 'Invalid file type. Only PDF, JPG, PNG are allowed'}), 400
        
        # Create MCQ question data structure (only if question data provided)
        mcq_questions_json = None
        if question and options and correct_answer:
            mcq_question = {
                'question': question,
                'options': options,
                'correct_answer': correct_answer
            }
            mcq_questions_json = json.dumps([mcq_question])
        
        # Generate title
        title = f"{company_name} - Interview Question" if company_name else "Interview Question"
        if not company_name and not question:
            title = "Interview Post"
        
        # Create post with question data
        post = Post(
            title=title,
            content=description if description else None,  # Store description in content field
            file_path=file_path,
            file_type=file_type,
            company_id=int(company_id),
            user_id=user_id,
            post_type='question',
            tags='',
            mcq_questions=mcq_questions_json,  # Store as array with single question or None
            coding_questions=None
        )
        
        db.session.add(post)
        db.session.commit()
        
        return jsonify({
            'message': 'Question added successfully',
            'post': post.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@posts_bp.route('/posts', methods=['GET'])
@jwt_required()
def list_posts():
    """List all posts, optionally filtered by company"""
    try:
        company_id = request.args.get('company_id', type=int)
        post_type = request.args.get('post_type')
        limit = request.args.get('limit', type=int, default=50)
        
        query = Post.query.filter_by(is_active=True)
        
        if company_id:
            query = query.filter_by(company_id=company_id)
        
        if post_type:
            query = query.filter_by(post_type=post_type)
        
        posts = query.order_by(Post.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'posts': [post.to_dict() for post in posts]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@posts_bp.route('/posts/<int:post_id>', methods=['GET'])
@jwt_required()
def get_post(post_id):
    """Get a specific post"""
    try:
        post = Post.query.get_or_404(post_id)
        
        if not post.is_active:
            return jsonify({'error': 'Post not found'}), 404
        
        return jsonify({
            'post': post.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@posts_bp.route('/posts/<int:post_id>/file', methods=['GET'])
@jwt_required()
def get_post_file(post_id):
    """Download a post's attached file"""
    try:
        from flask import send_file
        post = Post.query.get_or_404(post_id)
        
        if not post.is_active or not post.file_path:
            return jsonify({'error': 'File not found'}), 404
        
        if not os.path.exists(post.file_path):
            return jsonify({'error': 'File not found on server'}), 404
        
        return send_file(post.file_path, as_attachment=True)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@posts_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@jwt_required()
@role_required(['faculty', 'admin'])
def delete_post(post_id):
    """Delete a post (soft delete)"""
    try:
        user_id = get_jwt_identity()
        post = Post.query.get_or_404(post_id)
        
        # Check if user created the post or is admin
        user = User.query.get(user_id)
        if post.user_id != user_id and user.role != 'admin':
            return jsonify({'error': 'You do not have permission to delete this post'}), 403
        
        # Soft delete
        post.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'Post deleted successfully'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

