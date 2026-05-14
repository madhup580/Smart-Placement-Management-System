"""
Face Verification Utility using InsightFace/OpenCV
Handles face embedding extraction and similarity comparison for selfie verification
"""

import cv2
import numpy as np
import base64
import io
from PIL import Image
import os
from typing import Tuple, Optional
import json
from utils.async_utils import cache_result, run_in_background

# Optional import for ONNX runtime (used by InsightFace)
try:
    import onnxruntime as ort
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False
    print("[Face Verification] ONNX Runtime not available. Using OpenCV fallback.")

# Global model instance (loaded once)
_face_model = None
_face_detector = None

def get_face_model():
    """Lazy load InsightFace model or initialize OpenCV fallback"""
    global _face_model, _face_detector
    
    if _face_model is None:
        if ONNXRUNTIME_AVAILABLE:
            try:
                import insightface
                # Try to load InsightFace model
                _face_model = insightface.app.FaceAnalysis(providers=['CPUExecutionProvider'])
                _face_model.prepare(ctx_id=-1, det_size=(640, 640))
                print("[Face Verification] InsightFace model loaded successfully")
            except Exception as e:
                print(f"[Face Verification] InsightFace failed to load: {e}. Using OpenCV fallback.")
                _face_model = None
        
        # OpenCV fallback for face detection
        if _face_model is None:
            try:
                # Load OpenCV DNN face detector
                model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'opencv_face_detector.pb')
                config_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'opencv_face_detector.pbtxt')
                
                if os.path.exists(model_path) and os.path.exists(config_path):
                    _face_detector = cv2.dnn.readNetFromTensorflow(model_path, config_path)
                    print("[Face Verification] OpenCV DNN face detector loaded")
                else:
                    # Use Haar Cascade as last resort
                    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    _face_detector = cv2.CascadeClassifier(cascade_path)
                    print("[Face Verification] OpenCV Haar Cascade loaded")
            except Exception as e:
                print(f"[Face Verification] OpenCV fallback failed: {e}")
                _face_detector = None
    
    return _face_model, _face_detector

def base64_to_image(base64_string: str) -> np.ndarray:
    """Convert base64 string to OpenCV image"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_string)
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array and then to BGR for OpenCV
        image_array = np.array(image)
        image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        
        return image_bgr
    except Exception as e:
        print(f"[Face Verification] Error converting base64 to image: {e}")
        raise

# Removed cache decorator temporarily to fix embedding extraction issues
# @cache_result(ttl_seconds=7200)  # Cache embeddings for 2 hours
def extract_face_embedding(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Extract face embedding from image
    Returns 512-dimensional embedding vector or None if no face detected
    Optimized for speed and accuracy
    """
    try:
        # Validate input image
        if image is None or image.size == 0:
            print("[Face Verification] Invalid image: None or empty")
            return None
        
        if len(image.shape) < 2:
            print(f"[Face Verification] Invalid image shape: {image.shape}")
            return None
        
        # Optimize: Resize large images for faster processing (maintain aspect ratio)
        original_height, original_width = image.shape[:2]
        if original_width == 0 or original_height == 0:
            print(f"[Face Verification] Invalid image dimensions: {original_width}x{original_height}")
            return None
        
        max_dimension = 640  # Optimal size for speed/accuracy balance
        
        if original_width > max_dimension or original_height > max_dimension:
            scale = min(max_dimension / original_width, max_dimension / original_height)
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            if new_width > 0 and new_height > 0:
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            else:
                print(f"[Face Verification] Invalid resize dimensions: {new_width}x{new_height}")
                return None
        
        model, detector = get_face_model()
        
        # Ensure at least one model is available
        if model is None and detector is None:
            print("[Face Verification] No face detection model available")
            return None
        
        if model is not None and ONNXRUNTIME_AVAILABLE:
            # Use InsightFace (fastest and most accurate)
            try:
                # Use smaller detection size for faster processing
                faces = model.get(image)
                if len(faces) > 0:
                    # Get the largest face (most likely the main subject)
                    largest_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
                    embedding = largest_face.embedding
                    # Normalize embedding for better similarity calculation
                    norm = np.linalg.norm(embedding)
                    if norm > 0:
                        embedding = embedding / norm
                    return embedding
            except Exception as e:
                print(f"[Face Verification] InsightFace extraction failed: {e}")
        
        # OpenCV fallback - optimized feature extraction
        if detector is not None:
            # Ensure image is in correct format
            if len(image.shape) == 2:
                gray = image
            else:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces with multiple attempts for better detection
            faces = []
            
            if isinstance(detector, cv2.CascadeClassifier):
                # Optimized detection: single pass with balanced parameters for speed/accuracy
                faces = detector.detectMultiScale(
                    gray, 
                    scaleFactor=1.15,  # Slightly faster than 1.1, still accurate
                    minNeighbors=4,     # Reduced from 5 for faster detection
                    minSize=(40, 40),   # Larger min size for faster processing
                    flags=cv2.CASCADE_SCALE_IMAGE
                )
            else:
                # DNN detector
                try:
                    blob = cv2.dnn.blobFromImage(image, 1.0, (300, 300), [104, 117, 123])
                    detector.setInput(blob)
                    detections = detector.forward()
                    for i in range(detections.shape[2]):
                        confidence = detections[0, 0, i, 2]
                        if confidence > 0.5:
                            x1 = int(detections[0, 0, i, 3] * image.shape[1])
                            y1 = int(detections[0, 0, i, 4] * image.shape[0])
                            x2 = int(detections[0, 0, i, 5] * image.shape[1])
                            y2 = int(detections[0, 0, i, 6] * image.shape[0])
                            faces.append([x1, y1, x2 - x1, y2 - y1])
                except Exception as e:
                    print(f"[Face Verification] DNN detection failed: {e}")
                    # Fallback to Haar Cascade if DNN fails
                    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    cascade = cv2.CascadeClassifier(cascade_path)
                    if cascade:
                        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            
            if len(faces) > 0:
                # Get largest face
                largest_face = max(faces, key=lambda f: f[2] * f[3] if len(f) >= 4 else 0)
                if len(largest_face) >= 4:
                    x, y, w, h = largest_face[:4]
                    
                    # Ensure coordinates are valid
                    x = max(0, x)
                    y = max(0, y)
                    w = min(w, image.shape[1] - x)
                    h = min(h, image.shape[0] - y)
                    
                    if w > 0 and h > 0:
                        # Extract face region
                        if len(image.shape) == 2:
                            face_roi = image[y:y+h, x:x+w]
                        else:
                            face_roi = image[y:y+h, x:x+w]
                        
                        # Optimized: Resize to smaller size for faster processing (96x96 instead of 128x128)
                        face_resized = cv2.resize(face_roi, (96, 96), interpolation=cv2.INTER_AREA)  # INTER_AREA is faster
                        
                        # Convert to grayscale if needed
                        if len(face_resized.shape) == 3:
                            face_resized = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
                        
                        # Ensure it's single channel before equalizeHist
                        if len(face_resized.shape) != 2:
                            # Force to grayscale if still multi-channel
                            if len(face_resized.shape) == 3:
                                face_resized = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
                            else:
                                # If shape is unexpected, skip equalization
                                print(f"[Face Verification] Unexpected image shape for equalizeHist: {face_resized.shape}")
                        
                        # Enhanced feature extraction with histogram equalization for better accuracy
                        # Only apply if image is single channel (grayscale)
                        if len(face_resized.shape) == 2:
                            try:
                                face_resized = cv2.equalizeHist(face_resized)  # Improve contrast for better features
                            except cv2.error as e:
                                print(f"[Face Verification] equalizeHist failed: {e}. Continuing without equalization.")
                        else:
                            print(f"[Face Verification] Skipping equalizeHist - image not grayscale: {face_resized.shape}")
                        
                        # Simple feature extraction (flatten and normalize)
                        features = face_resized.flatten()
                        features = features.astype(np.float32)
                        
                        # Normalize
                        norm = np.linalg.norm(features)
                        if norm > 0:
                            features = features / norm
                        else:
                            return None
                        
                        # Pad or truncate to 512 dimensions
                        if len(features) < 512:
                            # Use mean padding instead of zero padding for better accuracy
                            mean_val = np.mean(features)
                            features = np.pad(features, (0, 512 - len(features)), 'constant', constant_values=mean_val)
                        else:
                            features = features[:512]
                        
                        return features
        
        print("[Face Verification] No face detected with any method")
        return None
        
    except Exception as e:
        print(f"[Face Verification] Error extracting face embedding: {e}")
        import traceback
        traceback.print_exc()
        return None

def calculate_cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Calculate cosine similarity between two embeddings"""
    try:
        # Ensure embeddings are numpy arrays and convert to float32
        if not isinstance(embedding1, np.ndarray):
            embedding1 = np.array(embedding1, dtype=np.float32)
        if not isinstance(embedding2, np.ndarray):
            embedding2 = np.array(embedding2, dtype=np.float32)
        
        # Normalize embeddings
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Calculate cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        
        # Convert numpy scalar to Python float explicitly
        if isinstance(similarity, np.ndarray):
            similarity = float(similarity.item())
        elif isinstance(similarity, (np.float32, np.float64, np.float_)):
            similarity = float(similarity)
        else:
            similarity = float(similarity)
        
        # Clamp to [0, 1] range
        similarity = max(0.0, min(1.0, similarity))
        
        return float(similarity)
    except Exception as e:
        print(f"[Face Verification] Error calculating similarity: {e}")
        return 0.0

def verify_face_match(selfie_embedding: np.ndarray, live_embedding: np.ndarray) -> dict:
    """
    Verify if live face matches selfie face
    Optimized thresholds for better accuracy
    Returns: {
        'matched': bool,
        'similarity': float,
        'status': 'match' | 'warning' | 'mismatch'
    }
    """
    try:
        similarity = calculate_cosine_similarity(selfie_embedding, live_embedding)
        
        # Improved thresholds for better accuracy:
        # - Higher match threshold (0.78) reduces false positives
        # - Warning zone (0.65-0.78) gives more tolerance for lighting/angle changes
        # - Lower mismatch threshold (0.65) reduces false negatives
        if similarity >= 0.78:  # Increased from 0.75 for better accuracy
            status = 'match'
            matched = True
        elif similarity >= 0.65:  # Increased from 0.6 for better warning zone
            status = 'warning'
            matched = False
        else:
            status = 'mismatch'
            matched = False
        
        # Ensure all values are JSON-serializable
        similarity_float = float(similarity) if not isinstance(similarity, float) else similarity
        matched_bool = bool(matched) if not isinstance(matched, bool) else matched
        
        return {
            'matched': matched_bool,
            'similarity': round(similarity_float, 4),
            'status': str(status)
        }
    except Exception as e:
        print(f"[Face Verification] Error verifying face match: {e}")
        return {
            'matched': False,
            'similarity': 0.0,
            'status': 'error'
        }

def embedding_to_base64(embedding: np.ndarray) -> str:
    """Convert numpy embedding to base64 string for storage"""
    try:
        if embedding is None:
            print("[Face Verification] embedding_to_base64: embedding is None")
            return ""
        
        # Ensure embedding is a numpy array
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding, dtype=np.float32)
        
        # Flatten if needed
        if len(embedding.shape) > 1:
            embedding = embedding.flatten()
        
        # Validate embedding
        if embedding.shape[0] == 0:
            print("[Face Verification] embedding_to_base64: empty embedding")
            return ""
        
        # Convert to list (this converts numpy types to Python types)
        embedding_list = embedding.tolist()
        
        # Ensure all values are Python native types (not numpy types)
        # This prevents JSON serialization errors
        try:
            # Use .item() for numpy scalars to convert to Python native types
            embedding_list = [float(x.item() if hasattr(x, 'item') and isinstance(x, (np.number, np.integer)) else x) for x in embedding_list]
        except (TypeError, ValueError) as e:
            print(f"[Face Verification] Error converting embedding values: {e}")
            # Fallback: convert each element individually
            new_list = []
            for x in embedding_list:
                try:
                    if hasattr(x, 'item') and isinstance(x, (np.number, np.integer)):
                        new_list.append(float(x.item()))
                    elif isinstance(x, (np.float32, np.float64, np.float_, np.number, np.integer)):
                        new_list.append(float(x))
                    elif isinstance(x, (list, tuple, np.ndarray)):
                        new_list.append(float(np.array(x).item()))
                    else:
                        new_list.append(float(x))
                except (TypeError, ValueError) as e2:
                    print(f"[Face Verification] Error converting element {x} (type: {type(x)}): {e2}")
                    new_list.append(0.0)  # Default value
            embedding_list = new_list
        
        # Validate the list before encoding
        if not embedding_list or len(embedding_list) == 0:
            print("[Face Verification] embedding_to_base64: empty embedding list after conversion")
            return ""
        
        # Convert to JSON string
        try:
            json_str = json.dumps(embedding_list)
            # Encode to base64
            base64_str = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            print(f"[Face Verification] Successfully encoded embedding to base64. Length: {len(base64_str)}")
            return base64_str
        except (TypeError, ValueError) as json_error:
            print(f"[Face Verification] JSON serialization error: {json_error}")
            print(f"[Face Verification] First few embedding values: {embedding_list[:5]}")
            print(f"[Face Verification] Embedding types: {[type(x) for x in embedding_list[:5]]}")
            import traceback
            traceback.print_exc()
            return ""
    except Exception as e:
        print(f"[Face Verification] Error encoding embedding: {e}")
        import traceback
        traceback.print_exc()
        return ""

def base64_to_embedding(base64_string: str) -> Optional[np.ndarray]:
    """Convert base64 string back to numpy embedding"""
    try:
        # Decode base64
        json_str = base64.b64decode(base64_string).decode('utf-8')
        # Parse JSON
        embedding_list = json.loads(json_str)
        # Convert to numpy array
        embedding = np.array(embedding_list, dtype=np.float32)
        return embedding
    except Exception as e:
        print(f"[Face Verification] Error decoding embedding: {e}")
        return None

