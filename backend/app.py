"""
Main Flask application entry point
"""
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import os
import pymysql
import sys

# Load environment variables before importing config so .env values are available
# while Config class attributes are created.
load_dotenv()

from config import config

# WebSocket support (optional - will work without it)
try:
    from utils.websocket_handler import init_socketio
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("[INFO] WebSocket support not available. Install: pip install flask-socketio")

# Register PyMySQL as MySQLdb for SQLAlchemy compatibility
pymysql.install_as_MySQLdb()

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    # CORS configuration - allow all origins for development
    # Simplified CORS setup - apply to all routes
    CORS(app, 
         resources={r"/*": {
             "origins": "*",
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
             "allow_headers": ["Content-Type", "Authorization", "X-CSRF-Token"],
             "supports_credentials": True,
             "expose_headers": ["Content-Type", "Authorization"]
         }},
         supports_credentials=True)
    jwt = JWTManager(app)
    
    # Initialize rate limiter with Redis support
    from utils.security import get_client_identifier
    from config import Config
    
    # Determine storage URI - use Redis only when explicitly configured.
    # Avoid probing localhost Redis on demo machines because it can delay startup.
    storage_uri = "memory://"
    if hasattr(Config, 'REDIS_URL') and Config.REDIS_URL:
        storage_uri = Config.REDIS_URL
        print(f"[App] Using Redis for rate limiting: {Config.REDIS_URL}")
    else:
        print("[App] Redis URL not configured, using in-memory rate limiting")
    
    limiter = Limiter(
        app=app,
        key_func=get_client_identifier,  # Use custom identifier (IP + user_id if authenticated)
        default_limits=["200 per day", "50 per hour"],
        storage_uri=storage_uri,
        headers_enabled=True  # Include rate limit info in headers
    )
    app.limiter = limiter
    
    # Add security headers and CORS headers
    @app.after_request
    def after_request(response):
        from utils.security import add_security_headers
        from flask import request
        response = add_security_headers(response)
        
        # Ensure CORS headers are always present for API routes
        if request.path.startswith('/api'):
            # Always set CORS headers explicitly
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRF-Token'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        
        return response
    
    # Initialize WebSocket (optional)
    if WEBSOCKET_AVAILABLE:
        try:
            socketio = init_socketio(app)
            app.socketio = socketio
            print("[OK] WebSocket support initialized")
        except Exception as e:
            print(f"[WARN] WebSocket initialization failed: {e}")
            app.socketio = None
    else:
        app.socketio = None
    
    # Handle OPTIONS requests for CORS preflight (before JWT validation)
    # This must run before JWT validation to prevent redirects on preflight requests
    @app.before_request
    def handle_preflight():
        from flask import request, jsonify, make_response
        if request.method == "OPTIONS":
            response = make_response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-CSRF-Token"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
            return response
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Health check and info endpoints
    @app.route('/', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        from flask import jsonify
        return jsonify({
            'status': 'ok',
            'message': 'Interview Preparation Platform API',
            'version': '1.0.0'
        }), 200
    
    @app.route('/api', methods=['GET'])
    def api_info():
        """API information endpoint"""
        from flask import jsonify
        return jsonify({
            'status': 'ok',
            'message': 'Interview Preparation Platform API',
            'endpoints': {
                'auth': '/api/auth/login, /api/auth/register, /api/auth/me',
                'student': '/api/student/dashboard, /api/student/performance',
                'faculty': '/api/faculty/dashboard',
                'admin': '/api/admin/dashboard',
                'coding': '/api/coding/questions',
                'quiz': '/api/quiz/list',
                'resources': '/api/resources',
                'interview': '/api/interview/status, /api/interview/start-interview',
                'notifications': '/api/notifications',
                'leaderboard': '/api/leaderboard'
            }
        }), 200
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.faculty import faculty_bp
    from routes.admin import admin_bp
    from routes.quiz import quiz_bp
    from routes.coding import coding_bp
    from routes.resources import resources_bp
    from routes.leaderboard import leaderboard_bp
    from routes.notifications import notifications_bp
    from routes.posts import posts_bp
    enable_interview = os.environ.get('ENABLE_INTERVIEW', '1') == '1'
    if enable_interview:
        from routes.interview import interview_bp
    else:
        from flask import Blueprint, jsonify
        interview_bp = Blueprint('interview', __name__)

        @interview_bp.route('/status', methods=['GET'])
        def interview_status_stub():
            return jsonify({'available': False, 'enabled': False}), 200
    enable_proctoring = os.environ.get('ENABLE_PROCTORING', '1') == '1'
    if enable_proctoring:
        from routes.device_detection import device_detection_bp
        from routes.face_verification import face_verification_bp
        from routes.audio_detection import audio_detection_bp
    else:
        from flask import Blueprint, jsonify
        device_detection_bp = Blueprint('device_detection', __name__)
        face_verification_bp = Blueprint('face_verification', __name__)
        audio_detection_bp = Blueprint('audio_detection', __name__)

        @device_detection_bp.route('/status', methods=['GET'])
        def device_detection_status_stub():
            return jsonify({'available': False, 'enabled': False}), 200

        @face_verification_bp.route('/status', methods=['GET'])
        def face_verification_status_stub():
            return jsonify({'available': False, 'enabled': False}), 200

        @audio_detection_bp.route('/status', methods=['GET'])
        def audio_detection_status_stub():
            return jsonify({'available': False, 'enabled': False}), 200
    
    # Register blueprints with API versioning (v1)
    # Both versioned and unversioned for backward compatibility
    # Use unique names for versioned routes to avoid conflicts
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth', name='auth_v1')
    app.register_blueprint(student_bp, url_prefix='/api/v1/student', name='student_v1')
    app.register_blueprint(faculty_bp, url_prefix='/api/v1/faculty', name='faculty_v1')
    app.register_blueprint(admin_bp, url_prefix='/api/v1/admin', name='admin_v1')
    app.register_blueprint(quiz_bp, url_prefix='/api/v1/quiz', name='quiz_v1')
    app.register_blueprint(coding_bp, url_prefix='/api/v1/coding', name='coding_v1')
    app.register_blueprint(resources_bp, url_prefix='/api/v1/resources', name='resources_v1')
    app.register_blueprint(leaderboard_bp, url_prefix='/api/v1/leaderboard', name='leaderboard_v1')
    app.register_blueprint(notifications_bp, url_prefix='/api/v1/notifications', name='notifications_v1')
    app.register_blueprint(interview_bp, url_prefix='/api/v1/interview', name='interview_v1')
    app.register_blueprint(device_detection_bp, url_prefix='/api/v1/device-detection', name='device_detection_v1')
    app.register_blueprint(face_verification_bp, url_prefix='/api/v1/face', name='face_verification_v1')
    app.register_blueprint(audio_detection_bp, url_prefix='/api/v1/audio-detect', name='audio_detection_v1')
    app.register_blueprint(posts_bp, url_prefix='/api/v1', name='posts_v1')
    
    # Backward compatibility: Register unversioned routes (default names)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(student_bp, url_prefix='/api/student')
    app.register_blueprint(faculty_bp, url_prefix='/api/faculty')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(quiz_bp, url_prefix='/api/quiz')
    app.register_blueprint(coding_bp, url_prefix='/api/coding')
    app.register_blueprint(resources_bp, url_prefix='/api/resources')
    app.register_blueprint(leaderboard_bp, url_prefix='/api/leaderboard')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(interview_bp, url_prefix='/api/interview')
    app.register_blueprint(device_detection_bp, url_prefix='/api/device-detection')
    app.register_blueprint(face_verification_bp, url_prefix='/api/face')
    app.register_blueprint(audio_detection_bp, url_prefix='/api/audio-detect')
    app.register_blueprint(posts_bp, url_prefix='/api')
    
    # Initialize database with error handling
    from models import db
    db.init_app(app)
    
    # Initialize device detector early (non-blocking)
    def initialize_device_detector():
        """Initialize device detector in background - non-blocking"""
        try:
            if os.environ.get('ENABLE_PROCTORING', '1') != '1':
                print("[INFO] Proctoring disabled; skipping device detector initialization")
                return
            from utils.device_detector import get_detector, DEPENDENCIES_AVAILABLE
            if DEPENDENCIES_AVAILABLE:
                print("[INFO] Initializing device detector...")
                detector = get_detector()
                if detector.is_loaded:
                    print("[OK] Device detector initialized successfully!")
                else:
                    print("[WARN] Device detector model not loaded - detection will be disabled")
            else:
                print("[WARN] Device detection dependencies not available - install: pip install opencv-python ultralytics numpy torch torchvision")
        except Exception as e:
            print(f"[WARN] Error initializing device detector: {e}")
            print("[INFO] Device detection will be disabled")
    
    # Initialize device detector in background (non-blocking)
    import threading
    detector_thread = threading.Thread(target=initialize_device_detector, daemon=True)
    detector_thread.start()
    
    # Initialize database lazily (don't connect during import)
    initialized = False
    
    def initialize_database():
        """Initialize database - called on first request"""
        nonlocal initialized
        if initialized:
            return
        
        with app.app_context():
            try:
                # Test database connection
                with db.engine.connect() as conn:
                    conn.close()
                print("[OK] Database connection established successfully!")
                
                # Create all tables
                db.create_all()
                print("[OK] Database tables created/verified!")
                
                # Seed initial data (only once) - optional
                try:
                    from seed_data import seed_initial_data
                    seed_initial_data()
                    print("[OK] Initial data seeded!")
                except ImportError:
                    # seed_data.py is optional - skip if not found
                    print("[INFO] seed_data.py not found - skipping initial data seeding")
                except Exception as seed_error:
                    # Other errors during seeding are non-critical
                    print(f"[WARN] Error during data seeding: {seed_error}")
                    print("[INFO] Continuing without seed data...")
                
                initialized = True
            except Exception as e:
                # Only show database connection error for actual DB issues
                error_msg = str(e)
                if "No module named 'seed_data'" in error_msg:
                    # This is not a database error - it's a missing optional file
                    print(f"\n[INFO] Optional seed_data.py module not found: {error_msg}")
                    print("[INFO] This is not a database error. The application will continue normally.\n")
                    initialized = True  # Continue anyway
                else:
                    # Actual database connection error
                    print(f"\n[ERROR] Database connection error: {error_msg}")
                    print("\nPlease ensure:")
                    print("1. MySQL server is running")
                    print("2. Database exists")
                    print("3. Connection credentials are correct")
                    print("4. DATABASE_URL environment variable is set\n")
                # Don't fail - will retry on next request
    
    # Initialize on first request
    @app.before_request
    def before_request():
        initialize_database()
    
    # Serve static files with proper cache headers
    @app.after_request
    def set_cache_headers(response):
        """Set cache headers based on environment"""
        from flask import request
        
        # In development: disable caching for all static files
        if app.config.get('DEBUG', False):
            if request.path.endswith(('.html', '.css', '.js', '.json')):
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
        # In production: cache static assets with versioning
        else:
            if request.path.endswith(('.css', '.js')):
                # Cache for 1 year, but rely on version query params for invalidation
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            elif request.path.endswith('.html'):
                # HTML should not be cached
                response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        
        return response
    
    return app

# Create app instance for local development
env = os.environ.get('FLASK_ENV', 'development')
app = create_app(env)

if __name__ == '__main__':
    # Local development settings
    port = int(os.environ.get('PORT', 5000))
    debug = True
    
    app.run(debug=debug, host='0.0.0.0', port=port)

