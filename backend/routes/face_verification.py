"""
Face Verification API Routes
Handles selfie registration and live face verification
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, InterviewSession
from utils.face_verification import (
    base64_to_image,
    extract_face_embedding,
    verify_face_match,
    embedding_to_base64,
    base64_to_embedding,
    get_face_model
)
from datetime import datetime
import json
import numpy as np

# WebSocket support (optional)
try:
    from utils.websocket_handler import emit_proctoring_status, emit_warning
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    def emit_proctoring_status(*args, **kwargs): pass
    def emit_warning(*args, **kwargs): pass

face_verification_bp = Blueprint('face_verification', __name__)

@face_verification_bp.route('/register-selfie', methods=['POST'])
@jwt_required()
def register_selfie():
    """
    Register selfie face embedding
    POST /api/face/register-selfie
    Body: {
        "selfie_image": "base64_string"
    }
    Returns: {
        "success": true,
        "message": "Selfie registered successfully",
        "session_id": int (temporary session for selfie storage)
    }
    """
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        selfie_image_base64 = data.get('selfie_image', '')
        if not selfie_image_base64:
            return jsonify({'error': 'Selfie image is required'}), 400
        
        # Convert base64 to image
        try:
            # Remove data URL prefix if present
            if ',' in selfie_image_base64:
                 selfie_image_base64 = selfie_image_base64.split(',')[1]

            image = base64_to_image(selfie_image_base64)
            if image is None or image.size == 0:
                return jsonify({'error': 'Invalid image: Could not decode image data. Please try again.'}), 400
            print(f"[Face Verification] Image converted successfully. Shape: {image.shape}")
        except Exception as e:
            print(f"[Face Verification] Error converting base64 to image: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Invalid image format: {str(e)}. Please ensure the image is valid and try again.'}), 400
        
        # Extract face embedding
        print("[Face Verification] Extracting face embedding...")
        try:
            embedding = extract_face_embedding(image)
            if embedding is None:
                print("[Face Verification] No face detected in image")
                return jsonify({'error': 'No face detected in selfie. Please ensure your face is clearly visible and well-lit.'}), 400
            
            print(f"[Face Verification] Face embedding extracted. Shape: {embedding.shape if embedding is not None else 'None'}")
            
            # Ensure embedding is a numpy array (not already converted)
            if embedding is not None and not isinstance(embedding, np.ndarray):
                embedding = np.array(embedding, dtype=np.float32)
            
            # Validate embedding shape
            if embedding is not None:
                if len(embedding.shape) != 1:
                    print(f"[Face Verification] Invalid embedding shape: {embedding.shape}. Flattening...")
                    embedding = embedding.flatten()
                if embedding.shape[0] == 0:
                    print("[Face Verification] Empty embedding")
                    return jsonify({'error': 'Failed to extract face features. Please try again with a clearer image.'}), 400
            
            # Convert embedding to base64 for storage
            print("[Face Verification] Converting embedding to base64...")
            embedding_base64 = embedding_to_base64(embedding)
            if not embedding_base64:
                print("[Face Verification] Failed to encode embedding to base64")
                return jsonify({'error': 'Failed to encode face embedding. Please try again.'}), 500
            print(f"[Face Verification] Embedding encoded successfully. Base64 length: {len(embedding_base64)}")
        except Exception as embed_error:
            print(f"[Face Verification] Error in embedding extraction/encoding: {embed_error}")
            print(f"[Face Verification] Error type: {type(embed_error).__name__}")
            import traceback
            traceback.print_exc()
            # Provide more specific error message
            error_msg = str(embed_error)
            if "equalizeHist" in error_msg or "cv2.error" in error_msg:
                return jsonify({'error': 'Error processing image. Please try again with a clearer, well-lit selfie.'}), 500
            elif "JSON" in error_msg or "serialization" in error_msg.lower():
                return jsonify({'error': 'Error encoding face data. Please try again.'}), 500
            else:
                return jsonify({'error': 'Error processing face embedding. Please ensure your face is clearly visible and try again.'}), 500
        
        # Create a temporary session to store selfie (will be linked to actual interview session later)
        try:
            temp_session = InterviewSession(
                user_id=user_id,
                interview_type='TR',  # Temporary, will be updated
                selfie_embedding=embedding_base64,
                selfie_registered_at=datetime.utcnow()
            )
            db.session.add(temp_session)
            db.session.flush()  # Get session.id
            
            db.session.commit()
            print(f"[Face Verification] Selfie registered successfully. Session ID: {temp_session.id}")
            
            return jsonify({
                'success': True,
                'message': 'Selfie registered successfully',
                'session_id': temp_session.id
            }), 200
        except Exception as db_error:
            db.session.rollback()
            print(f"[Face Verification] Database error: {db_error}")
            import traceback
            traceback.print_exc()
            # Check if it's a column error
            if 'selfie_embedding' in str(db_error) or 'selfie_registered_at' in str(db_error):
                return jsonify({
                    'error': 'Database schema error. Please run: python backend/migrate_interview_selfie.py',
                    'details': str(db_error)
                }), 500
            return jsonify({'error': f'Database error: {str(db_error)}'}), 500
    
    except Exception as e:
        db.session.rollback()
        print(f"[Face Verification] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        # Ensure error message is JSON-serializable (convert any numpy types)
        error_msg = str(e)
        # Remove any numpy array representations from error message
        if 'ndarray' in error_msg:
            error_msg = 'Error processing face embedding. Please try again with a clearer image.'
        return jsonify({'error': error_msg}), 500

@face_verification_bp.route('/verify-face', methods=['POST'])
@jwt_required()
def verify_face():
    """
    Verify live face against registered selfie
    POST /api/face/verify-face
    Body: {
        "live_image": "base64_string",
        "session_id": int (session with stored selfie)
    }
    Returns: {
        "matched": bool,
        "similarity": float,
        "status": "match" | "warning" | "mismatch"
    }
    """
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        live_image_base64 = data.get('live_image', '')
        session_id = data.get('session_id')
        
        if not live_image_base64:
            return jsonify({'error': 'Live image is required'}), 400
        
        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400
        
        print(f"[Face Verification] Verifying face for session_id: {session_id}, user_id: {user_id}")
        
        # Get session with selfie embedding - allow any session for this user (temp or interview session)
        session = InterviewSession.query.filter_by(id=session_id).first()
        if not session:
            print(f"[Face Verification] Session not found: session_id={session_id}")
            return jsonify({'error': 'Session not found. Please capture selfie again.'}), 404
        
        # Verify user owns this session (security check)
        if int(session.user_id) != int(user_id):
            print(f"[Face Verification] Access denied: session.user_id={session.user_id}, request.user_id={user_id}")
            return jsonify({'error': 'Access denied'}), 403
        
        if not session.selfie_embedding:
            print(f"[Face Verification] No selfie embedding found for session_id: {session_id}")
            return jsonify({'error': 'No selfie registered for this session. Please capture selfie first.'}), 400
        
        print(f"[Face Verification] Selfie embedding found. Length: {len(session.selfie_embedding)}")
        
        # Convert base64 to image (handle data URL prefix)
        try:
            # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
            if ',' in live_image_base64:
                live_image_base64 = live_image_base64.split(',')[1]
            
            live_image = base64_to_image(live_image_base64)
            print(f"[Face Verification] Live image converted. Shape: {live_image.shape}")
        except Exception as e:
            print(f"[Face Verification] Error converting base64 to image: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Invalid image format: {str(e)}'}), 400
        
        # Extract face embedding from live image
        print("[Face Verification] Extracting face embedding from live image...")
        live_embedding = extract_face_embedding(live_image)
        if live_embedding is None:
            print("[Face Verification] No face detected in live image")
            return jsonify({
                'matched': False,
                'similarity': 0.0,
                'status': 'mismatch',
                'error': 'No face detected in live image. Please ensure your face is clearly visible.'
            }), 200
        
        print(f"[Face Verification] Live embedding extracted. Shape: {live_embedding.shape}")
        
        # Get selfie embedding
        print("[Face Verification] Decoding selfie embedding...")
        selfie_embedding = base64_to_embedding(session.selfie_embedding)
        if selfie_embedding is None:
            print("[Face Verification] Failed to decode selfie embedding")
            return jsonify({'error': 'Invalid selfie embedding. Please register selfie again.'}), 500
        
        print(f"[Face Verification] Selfie embedding decoded. Shape: {selfie_embedding.shape}")
        
        # Verify face match
        print("[Face Verification] Calculating similarity...")
        result = verify_face_match(selfie_embedding, live_embedding)
        print(f"[Face Verification] Verification result: {result}")
        
        return jsonify(result), 200
    
    except Exception as e:
        print(f"[Face Verification] Unexpected error in verify_face: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error verifying face: {str(e)}'}), 500

@face_verification_bp.route('/status', methods=['GET'])
@jwt_required()
def get_status():
    """Check if face verification is enabled"""
    try:
        model, detector = get_face_model()
        available = model is not None or detector is not None
        
        return jsonify({
            'enabled': available,
            'model_type': 'insightface' if model is not None else 'opencv' if detector is not None else 'none'
        }), 200
    except Exception as e:
        return jsonify({
            'enabled': False,
            'error': str(e)
        }), 200

