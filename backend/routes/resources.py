"""
Learning resources routes
"""
from flask import Blueprint, request, jsonify, send_from_directory, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Resource, User, Notification, db
from utils.auth import role_required
from werkzeug.utils import secure_filename
import os

resources_bp = Blueprint('resources', __name__)

@resources_bp.route('', methods=['GET'])
@resources_bp.route('/', methods=['GET'])
@jwt_required()
def list_resources():
    """List learning resources - accessible to authenticated users."""
    try:
        resource_type = request.args.get('type')
        company_id = request.args.get('company_id')

        query = Resource.query

        if resource_type:
            query = query.filter_by(type=resource_type)
        if company_id:
            query = query.filter_by(company_id=company_id)

        resources = query.order_by(Resource.created_at.desc()).all()
        return jsonify({
            'resources': [resource.to_dict() for resource in resources]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def allowed_file(filename):
    """Check if file extension is allowed"""
    from config import Config
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@resources_bp.route('/upload', methods=['POST'])
@jwt_required()
@role_required(['student', 'faculty', 'admin'])
def upload_resource():
    """Upload a learning resource"""
    try:
        user_id = get_jwt_identity()
        from config import Config
        
        resource_type = request.form.get('type')  # pdf, code_snippet, flashcard, notes
        title = request.form.get('title')
        description = request.form.get('description', '')
        company_id = request.form.get('company_id')
        tags = request.form.get('tags', '')
        # All resources are public by default - accessible to everyone
        is_public = True
        
        file_path = None
        content = request.form.get('content', '')
        
        # Handle file upload
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Ensure upload folder exists
                os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                file_path = os.path.join(Config.UPLOAD_FOLDER, f"{user_id}_{filename}")
                file.save(file_path)
                # Convert to absolute path for storage
                file_path = os.path.abspath(file_path)
        
        resource = Resource(
            title=title,
            description=description,
            type=resource_type,
            file_path=file_path,
            content=content,
            user_id=user_id,
            company_id=int(company_id) if company_id else None,
            tags=tags,
            is_public=is_public
        )
        
        db.session.add(resource)
        db.session.commit()
        
        # Notify all students about the new resource
        students = User.query.filter_by(role='student', is_active=True).all()
        for student in students:
            notification = Notification(
                user_id=student.id,
                title='New Resource Available',
                message=f'A new resource "{resource.title}" has been uploaded. Check it out!',
                type='resource',
                link=f'/resources/{resource.id}'
            )
            db.session.add(notification)
        db.session.commit()
        
        # Return resource with file_path
        resource_dict = resource.to_dict()
        print(f"Resource created: ID={resource.id}, Title={resource.title}, File Path={resource.file_path}")  # Debug
        
        return jsonify({
            'message': 'Resource uploaded successfully',
            'resource': resource_dict
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@resources_bp.route('/<int:resource_id>', methods=['GET'])
@jwt_required()
def get_resource(resource_id):
    """Get resource details - accessible to everyone"""
    try:
        resource = Resource.query.get_or_404(resource_id)
        
        # All resources are accessible to everyone
        return jsonify({
            'resource': resource.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@resources_bp.route('/<int:resource_id>/download', methods=['GET'])
@jwt_required()
def download_resource(resource_id):
    """Download/view a resource file - accessible to everyone"""
    try:
        resource = Resource.query.get_or_404(resource_id)
        
        # All resources are accessible to everyone
        
        if not resource.file_path:
            return jsonify({'error': 'No file attached to this resource'}), 404
        
        # Check if file exists
        if not os.path.exists(resource.file_path):
            return jsonify({'error': 'File not found on server'}), 404
        
        # Get original filename (remove user_id prefix)
        filename = os.path.basename(resource.file_path)
        if '_' in filename:
            original_filename = filename.split('_', 1)[-1]
        else:
            original_filename = filename
        
        # Determine MIME type based on file extension
        mime_type = 'application/pdf'  # Default for PDF
        if filename.lower().endswith('.pdf'):
            mime_type = 'application/pdf'
        elif filename.lower().endswith(('.txt', '.text')):
            mime_type = 'text/plain'
        elif filename.lower().endswith(('.doc', '.docx')):
            mime_type = 'application/msword'
        elif filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            mime_type = 'image/jpeg'
        
        return send_file(
            resource.file_path,
            mimetype=mime_type,
            as_attachment=False,  # False = view in browser, True = download
            download_name=original_filename
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@resources_bp.route('/<int:resource_id>', methods=['DELETE'])
@jwt_required()
def delete_resource(resource_id):
    """Delete a resource"""
    try:
        user_id = get_jwt_identity()
        resource = Resource.query.get_or_404(resource_id)
        
        from utils.auth import get_current_user
        user = get_current_user()
        seed_user = User.query.filter_by(username='seed_admin').first()
        is_seed_resource = seed_user and resource.user_id == seed_user.id
        can_delete = (
            resource.user_id == int(user_id)
            or (user and user.role in ['faculty', 'admin'])
            or is_seed_resource
        )

        if not can_delete:
            return jsonify({'error': 'Access denied'}), 403
        
        # Delete file if exists
        if resource.file_path and os.path.exists(resource.file_path):
            os.remove(resource.file_path)
        
        db.session.delete(resource)
        db.session.commit()
        
        return jsonify({
            'message': 'Resource deleted successfully'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

