"""
Audio Detection API Routes
Handles background noise detection during interviews
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.audio_detection import process_audio_chunk
import time

audio_detection_bp = Blueprint('audio_detection', __name__)


@audio_detection_bp.route('/detect', methods=['POST'])
@jwt_required()
def detect_noise():
    """
    Detect background noise in audio chunk
    POST /api/audio-detect
    Body: {
        "audio_chunk": "base64_encoded_audio",
        "sample_rate": 16000 (optional)
    }
    Returns: {
        "noise": bool,
        "confidence": float,
        "noise_type": str,
        "features": dict
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        audio_chunk = data.get('audio_chunk', '')
        if not audio_chunk:
            return jsonify({'error': 'Audio chunk is required'}), 400
        
        sample_rate = data.get('sample_rate', 16000)
        
        # Process audio chunk
        start_time = time.time()
        result = process_audio_chunk(audio_chunk, sample_rate)
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Add processing time to result
        result['processing_time_ms'] = round(processing_time, 2)
        
        # Get session_id if provided
        session_id = data.get('session_id')
        
        # Emit WebSocket status update
        if session_id and WEBSOCKET_AVAILABLE:
            emit_proctoring_status(session_id, 'audio', {
                'noise': result.get('noise', False),
                'confidence': result.get('confidence', 0),
                'noise_type': result.get('noise_type', 'clean')
            })
        
        # Log if noise detected
        if result.get('noise', False):
            print(f"[Audio Detection] Noise detected for user {user_id}: {result.get('noise_type', 'unknown')} (confidence: {result.get('confidence', 0):.2f})")
            # Emit warning via WebSocket
            if session_id and WEBSOCKET_AVAILABLE:
                emit_warning(session_id, 'audio', 
                           f'Background noise detected: {result.get("noise_type", "unknown")}')
        
        return jsonify(result), 200
    
    except Exception as e:
        print(f"[Audio Detection] Error in detect_noise endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'noise': False,
            'confidence': 0.0,
            'error': str(e)
        }), 500


@audio_detection_bp.route('/status', methods=['GET'])
@jwt_required()
def get_status():
    """Check if audio detection is enabled"""
    try:
        from utils.audio_detection import LIBROSA_AVAILABLE
        
        return jsonify({
            'enabled': True,
            'librosa_available': LIBROSA_AVAILABLE,
            'features': ['rms', 'zcr', 'spectral_flux', 'vad']
        }), 200
    except Exception as e:
        return jsonify({
            'enabled': False,
            'error': str(e)
        }), 200

