"""
Authentication routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from models import User, db
from utils.auth import get_current_user
from utils.security import get_client_identifier

auth_bp = Blueprint('auth', __name__)

# Rate limiter - will be set by app.py
limiter = None

def set_limiter(app_limiter):
    """Set limiter from app"""
    global limiter
    limiter = app_limiter

# Helper to apply rate limit decorator
def rate_limit_if_available(limit_str, key_func=None):
    """Apply rate limit decorator if limiter is available"""
    def decorator(f):
        if limiter:
            if key_func:
                return limiter.limit(limit_str, key_func=key_func)(f)
            else:
                return limiter.limit(limit_str)(f)
        return f
    return decorator

@auth_bp.route('/', methods=['GET'])
def auth_info():
    """Auth endpoints information"""
    return jsonify({
        'message': 'Authentication endpoints',
        'endpoints': [
            'POST /api/auth/register - Register new user',
            'POST /api/auth/login - Login user',
            'GET /api/auth/me - Get current user (requires auth)',
            'POST /api/auth/refresh - Refresh token (requires auth)',
            'POST /api/auth/logout - Logout (requires auth)',
            'GET /api/auth/batches - Get active batches for registration'
        ]
    }), 200

@auth_bp.route('/batches', methods=['GET'])
def get_batches():
    """Get active batches for registration (public endpoint)"""
    try:
        from models import Batch
        batches = Batch.query.filter_by(is_active=True).order_by(Batch.id).all()
        return jsonify({
            'batches': [batch.to_dict() for batch in batches]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/register', methods=['POST'])
@rate_limit_if_available("5 per hour")
def register():
    """Register a new user"""
    try:
        import re
        data = request.get_json()
        username = data.get('username', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        reg_no = data.get('reg_no', '').strip()
        college_email = data.get('college_email', '').strip().lower()
        password = data.get('password')
        role = data.get('role', 'student')
        batch_id = data.get('batch_id')
        
        # Validation
        if not username or not first_name or not last_name or not reg_no or not college_email or not password or not role:
            return jsonify({'error': 'All fields are required'}), 400
        
        # Validate first name (alphabets only)
        if not re.match(r'^[A-Za-z\s]+$', first_name):
            return jsonify({'error': 'First name must contain only alphabets'}), 400
        
        # Validate last name (alphabets only)
        if not re.match(r'^[A-Za-z\s]+$', last_name):
            return jsonify({'error': 'Last name must contain only alphabets'}), 400
        
        # Validate registration number (alphanumeric)
        if not re.match(r'^[A-Za-z0-9]+$', reg_no):
            return jsonify({'error': 'Registration number must be alphanumeric'}), 400
        
        # Validate college email (must end with @audisankara.ac.in)
        if not college_email.endswith('@audisankara.ac.in'):
            return jsonify({'error': 'College email must end with @audisankara.ac.in'}), 400
        
        # Validate role
        if role not in ['student', 'faculty', 'admin']:
            return jsonify({'error': 'Invalid role. Must be student or faculty'}), 400
        
        # Validate password strength
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(college_email=college_email).first():
            return jsonify({'error': 'College email already exists'}), 400
        
        if User.query.filter_by(reg_no=reg_no).first():
            return jsonify({'error': 'Registration number already exists'}), 400
        
        # Validate batch_id if provided (for students)
        if role == 'student' and batch_id:
            from models import Batch
            batch = Batch.query.get(batch_id)
            if not batch:
                return jsonify({'error': 'Invalid batch_id'}), 400
        elif role == 'student' and not batch_id:
            from models import Batch
            batch = Batch.query.filter_by(is_active=True).order_by(Batch.id).first()
            if not batch:
                return jsonify({'error': 'No active batches available for student registration'}), 400
            batch_id = batch.id
        
        # Create new user
        full_name = f"{first_name} {last_name}"
        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            reg_no=reg_no,
            college_email=college_email,
            email=college_email,  # Set email to college_email for backward compatibility
            role=role,
            full_name=full_name,
            batch_id=batch_id if role == 'student' and batch_id else None
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Create tokens using TokenRefreshManager
        from utils.security import TokenRefreshManager, AuditLogger
        token_manager = TokenRefreshManager()
        tokens = token_manager.create_tokens(user.id)
        
        # Log successful registration
        AuditLogger.log_action(
            user_id=user.id,
            action='register',
            resource='auth',
            status='success',
            details={'role': role, 'username': username},
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'message': 'User registered successfully',
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'token_type': tokens['token_type'],
            'expires_in': tokens['expires_in'],
            'user': user.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"[Register Error] {str(e)}")
        print(f"[Register Trace] {error_trace}")
        # Return user-friendly error message
        return jsonify({
            'error': str(e),
            'message': 'Registration failed. Please check your input and try again.'
        }), 500

@auth_bp.route('/login', methods=['POST'])
@rate_limit_if_available("10 per 15 minutes", key_func=get_client_identifier)
def login():
    """Login user with brute force protection, rate limiting, and audit logging"""
    from utils.security import (
        RedisBruteForceProtection,
        TokenRefreshManager,
        AuditLogger,
        protect_against_attacks
    )
    
    @protect_against_attacks
    def _login():
        try:
            data = request.get_json()
            username = data.get('username', '').strip()
            password = data.get('password')
            
            if not username or not password:
                AuditLogger.log_action(
                    user_id=None,
                    action='login_attempt',
                    resource='auth',
                    status='failure',
                    details={'reason': 'missing_credentials'},
                    ip_address=request.remote_addr
                )
                return jsonify({'error': 'Username and password required'}), 400
            
            # Lock by username, not browser/IP, so one failed demo login
            # cannot block every student using the same machine.
            client_id = f"login:{username.lower()}"
            brute_force = RedisBruteForceProtection(max_attempts=8, lockout_duration=60)

            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                if not user.is_active:
                    AuditLogger.log_action(
                        user_id=user.id,
                        action='login_attempt',
                        resource='auth',
                        status='failure',
                        details={'reason': 'account_deactivated'},
                        ip_address=request.remote_addr
                    )
                    return jsonify({'error': 'Account is deactivated'}), 403

                # A correct password should always clear previous failed attempts.
                brute_force.record_success(client_id)

                token_manager = TokenRefreshManager()
                tokens = token_manager.create_tokens(user.id)

                AuditLogger.log_action(
                    user_id=user.id,
                    action='login',
                    resource='auth',
                    status='success',
                    ip_address=request.remote_addr
                )

                return jsonify({
                    'message': 'Login successful',
                    'access_token': tokens['access_token'],
                    'refresh_token': tokens['refresh_token'],
                    'expires_in': tokens['expires_in'],
                    'token_type': tokens['token_type'],
                    'user': user.to_dict()
                }), 200

            is_locked, remaining_seconds = brute_force.is_locked(client_id)
            if is_locked:
                minutes = remaining_seconds // 60
                seconds = remaining_seconds % 60
                AuditLogger.log_action(
                    user_id=None,
                    action='login_attempt',
                    resource='auth',
                    status='blocked',
                    details={'reason': 'account_locked', 'username': username},
                    ip_address=request.remote_addr
                )
                return jsonify({
                    'error': 'Too many failed login attempts. Account temporarily locked.',
                    'lockout_remaining': remaining_seconds,
                    'message': f'Please try again in {minutes}m {seconds}s'
                }), 429

            if not user or not user.check_password(password):
                # Record failed attempt
                is_locked = brute_force.record_failed_attempt(client_id)
                remaining = brute_force.get_remaining_attempts(client_id)
                
                AuditLogger.log_action(
                    user_id=user.id if user else None,
                    action='login_attempt',
                    resource='auth',
                    status='failure',
                    details={'reason': 'invalid_credentials', 'username': username, 'remaining_attempts': remaining},
                    ip_address=request.remote_addr
                )
                
                if is_locked:
                    return jsonify({
                        'error': 'Too many failed login attempts. Account temporarily locked.',
                        'lockout_remaining': brute_force.is_locked(client_id)[1] or 60,
                        'message': 'Please try again in 1 minute'
                    }), 429
                
                return jsonify({
                    'error': 'Invalid credentials',
                    'remaining_attempts': remaining
                }), 401
        
        except Exception as e:
            AuditLogger.log_action(
                user_id=None,
                action='login_attempt',
                resource='auth',
                status='error',
                details={'error': str(e)},
                ip_address=request.remote_addr
            )
            return jsonify({'error': str(e)}), 500
    
    return _login()

# Google OAuth routes removed - not needed for registration

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token"""
    from utils.security import TokenRefreshManager, AuditLogger
    
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            AuditLogger.log_action(
                user_id=user_id,
                action='token_refresh',
                resource='auth',
                status='failure',
                details={'reason': 'invalid_user'},
                ip_address=request.remote_addr
            )
            return jsonify({'error': 'Invalid token'}), 401
        
        # Get refresh token from request
        data = request.get_json() or {}
        refresh_token = data.get('refresh_token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not refresh_token:
            return jsonify({'error': 'Refresh token required'}), 400
        
        # Use TokenRefreshManager to refresh token
        token_manager = TokenRefreshManager()
        new_tokens = token_manager.refresh_access_token(refresh_token)
        
        if not new_tokens:
            AuditLogger.log_action(
                user_id=user_id,
                action='token_refresh',
                resource='auth',
                status='failure',
                details={'reason': 'invalid_refresh_token'},
                ip_address=request.remote_addr
            )
            return jsonify({'error': 'Invalid refresh token'}), 401
        
        # Log successful token refresh
        AuditLogger.log_action(
            user_id=user_id,
            action='token_refresh',
            resource='auth',
            status='success',
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'access_token': new_tokens['access_token'],
            'token_type': new_tokens['token_type'],
            'expires_in': new_tokens['expires_in']
        }), 200
    
    except Exception as e:
        AuditLogger.log_action(
            user_id=None,
            action='token_refresh',
            resource='auth',
            status='error',
            details={'error': str(e)},
            ip_address=request.remote_addr
        )
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_info():
    """Get current user information"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client-side token removal)"""
    return jsonify({'message': 'Logged out successfully'}), 200

