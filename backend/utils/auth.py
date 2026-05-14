"""
Authentication utilities
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from models import User, db

def role_required(roles):
    """Decorator to check if user has required role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            
            if not user:
                print(f"[Role Check] User not found for user_id: {user_id}")
                return jsonify({'error': 'User not found'}), 403
            
            user_role = user.role.lower().strip() if user.role else None
            # Normalize required roles to lowercase for comparison
            required_roles = [r.lower().strip() for r in roles]
            
            print(f"[Role Check] User ID: {user_id}, Username: {user.username}, Role: '{user.role}' (normalized: '{user_role}'), Required: {roles} (normalized: {required_roles})")
            
            if not user_role or user_role not in required_roles:
                print(f"[Role Check] Access denied. User role '{user.role}' (normalized: '{user_role}') not in required roles: {roles}")
                return jsonify({
                    'error': 'Insufficient permissions',
                    'user_role': user.role,
                    'required_roles': roles,
                    'message': f'You need one of these roles: {", ".join(roles)}. Your current role is: {user.role}'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    """Get current authenticated user"""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        return User.query.get(user_id)
    except:
        return None

