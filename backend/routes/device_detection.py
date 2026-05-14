"""
Device Detection API Routes
Handles device detection requests and WebSocket connections
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.device_detector import get_detector
from models import db, DeviceDetectionLog
import logging
from datetime import datetime

# WebSocket support (optional)
try:
    from utils.websocket_handler import emit_proctoring_status, emit_warning
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    def emit_proctoring_status(*args, **kwargs): pass
    def emit_warning(*args, **kwargs): pass

logger = logging.getLogger(__name__)

device_detection_bp = Blueprint('device_detection', __name__)

@device_detection_bp.route('/detect', methods=['POST'])
@jwt_required()
def detect_devices():
    """
    Detect devices in a video frame
    
    Request body:
        {
            "frame": "base64_encoded_image",
            "session_id": "interview_session_id"
        }
    
    Returns:
        {
            "detected": bool,
            "devices": [...],
            "count": int,
            "timestamp": str
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'frame' not in data:
            logger.warning("Device detection request missing frame data")
            return jsonify({
                'error': 'Missing frame data'
            }), 400
        
        frame = data.get('frame')
        session_id = data.get('session_id')
        user_id = get_jwt_identity()
        
        logger.info(f"Device detection request from user {user_id}, session {session_id}, frame size: {len(frame) if frame else 0}")
        
        # Get detector instance
        detector = get_detector()
        
        if not detector.is_loaded:
            logger.warning("Device detector not loaded")
            return jsonify({
                'detected': False,
                'devices': [],
                'count': 0,
                'error': 'Detector not loaded'
            }), 200
        
        # Run detection
        logger.debug("Running detection on frame...")
        result = detector.detect_from_base64(frame)
        logger.info(f"Detection result: detected={result.get('detected')}, count={result.get('count')}, devices={result.get('devices')}")
        
        # Add session info
        result['session_id'] = session_id
        result['user_id'] = user_id
        
        # Log detection if device found
        if result['detected']:
            logger.warning(
                f"Device detected for user {user_id}, session {session_id}: "
                f"{result['count']} device(s) - {[d['class'] for d in result['devices']]}"
            )
            
            # Save detection to database
            try:
                # Count existing warnings for this session
                existing_warnings = DeviceDetectionLog.query.filter_by(
                    user_id=user_id,
                    session_id=str(session_id) if session_id else None
                ).count()
                
                for device in result['devices']:
                    detection_log = DeviceDetectionLog(
                        user_id=user_id,
                        session_id=str(session_id) if session_id else None,
                        detected_device=device.get('class', 'unknown'),
                        confidence=device.get('confidence', 0.0),
                        warning_count=existing_warnings + 1
                    )
                    db.session.add(detection_log)
                
                db.session.commit()
                logger.info(f"Logged {len(result['devices'])} device detection(s) for session {session_id}")
            except Exception as e:
                logger.error(f"Error saving device detection log: {e}")
                db.session.rollback()
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in device detection endpoint: {e}")
        return jsonify({
            'error': 'Detection failed',
            'message': str(e)
        }), 500

@device_detection_bp.route('/status', methods=['GET'])
def detection_status():
    """Check if device detection service is available (no auth required for status check)"""
    try:
        from utils.device_detector import DEPENDENCIES_AVAILABLE
        if not DEPENDENCIES_AVAILABLE:
            logger.warning("Device detection dependencies not available")
            return jsonify({
                'available': False,
                'error': 'Dependencies not available',
                'message': 'Install: pip install opencv-python ultralytics numpy torch torchvision'
            }), 200
        
        detector = get_detector()
        status_info = {
            'available': detector.is_loaded,
            'model_loaded': detector.is_loaded,
            'dependencies_available': True
        }
        
        if not detector.is_loaded:
            status_info['error'] = 'Model not loaded - check server logs for details'
            logger.warning("Device detector model not loaded")
        
        return jsonify(status_info), 200
    except Exception as e:
        logger.error(f"Error checking device detection status: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'available': False,
            'error': str(e),
            'message': 'Error checking detector status'
        }), 200

