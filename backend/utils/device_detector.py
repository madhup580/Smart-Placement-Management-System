"""
Device Detection Service using YOLOv8
Detects electronic devices (cell phone, laptop, tablet, watch) in video frames
"""
import base64
from datetime import datetime
import logging

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import optional dependencies
DEPENDENCIES_AVAILABLE = False
cv2 = None
np = None
YOLO = None

try:
    import cv2
    import numpy as np
    logger.info("OpenCV and NumPy imported successfully")
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"OpenCV/NumPy not available: {e}. Device detection will be disabled.")
except Exception as e:
    logger.warning(f"Error importing OpenCV/NumPy: {e}. Device detection will be disabled.")

# Try to import YOLO separately (may fail due to torch DLL issues)
if DEPENDENCIES_AVAILABLE:
    try:
        from ultralytics import YOLO
        logger.info("Ultralytics YOLO imported successfully")
    except ImportError as e:
        DEPENDENCIES_AVAILABLE = False
        YOLO = None
        logger.warning(f"Ultralytics not available: {e}. Device detection will be disabled.")
    except Exception as e:
        DEPENDENCIES_AVAILABLE = False
        YOLO = None
        error_msg = str(e)
        if "DLL load failed" in error_msg or "_C" in error_msg:
            logger.error(f"Torch DLL error: {e}")
            logger.error("This usually means Visual C++ Redistributables are missing.")
            logger.error("Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe")
        else:
            logger.warning(f"Error importing Ultralytics: {e}. Device detection will be disabled.")

class DeviceDetector:
    """Real-time device detection using YOLOv8"""
    
    # COCO class IDs for devices (YOLOv8 uses COCO dataset)
    DEVICE_CLASSES = {
        'cell phone': 67,      # COCO class 67: cell phone
        'laptop': 63,          # COCO class 63: laptop
        'tablet': None,        # Not in COCO, will use custom model or fallback
        'watch': None,         # Not in COCO, will use custom model or fallback
    }
    
    # Alternative: Use class names directly (YOLOv8 supports this)
    # Expanded list for better detection accuracy
    DEVICE_NAMES = [
        'cell phone', 'mobile phone', 'phone', 'smartphone',
        'laptop', 'notebook', 'computer',
        'tablet', 'ipad',
        'watch', 'smartwatch', 'apple watch',
        'headphones', 'earphones', 'earbuds',
        'mouse', 'keyboard'
    ]
    
    def __init__(self, model_path='yolov8n.pt', confidence_threshold=0.2):
        """
        Initialize device detector
        
        Args:
            model_path: Path to YOLO model file (default: yolov8n.pt - nano model)
            confidence_threshold: Minimum confidence for detection (0.0-1.0)
        """
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.is_loaded = False
        self.inference_size = 512  # Reduced from 640 for faster inference (still accurate)
        self.use_half_precision = False  # Will be set if GPU available
        
        if not DEPENDENCIES_AVAILABLE:
            logger.warning("Device detection dependencies not available. Install: pip install opencv-python ultralytics numpy")
            return
        
        try:
            logger.info(f"Loading YOLO model from {model_path}...")
            # Load YOLOv8 model (will download automatically if not present)
            self.model = YOLO(model_path)
            self.is_loaded = True
            logger.info("YOLO model loaded successfully")
            
            # Check if GPU is available and enable optimizations
            try:
                import torch
                if torch.cuda.is_available():
                    self.use_half_precision = True
                    logger.info("GPU detected - using optimized inference")
                else:
                    logger.info("Using CPU inference")
            except:
                pass
            
            # Test the model with a dummy inference to ensure it's working
            try:
                import numpy as np
                test_image = np.zeros((640, 640, 3), dtype=np.uint8)
                _ = self.model(test_image, verbose=False, imgsz=640)
                logger.info("YOLO model test inference successful")
            except Exception as test_error:
                logger.warning(f"YOLO model loaded but test inference failed: {test_error}")
                # Don't fail - model might still work
        except ImportError as e:
            logger.error(f"Failed to import YOLO dependencies: {e}")
            logger.warning("Device detection will be disabled. Install: pip install ultralytics torch torchvision")
            self.is_loaded = False
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.warning("Device detection will be disabled")
            self.is_loaded = False
    
    def is_device_class(self, class_name):
        """
        Check if detected class is a device
        
        Args:
            class_name: Detected class name from YOLO
            
        Returns:
            bool: True if class is a device
        """
        if not class_name:
            return False
        
        class_name_lower = class_name.lower().strip()
        
        # Exact match first (more accurate)
        if class_name_lower in self.DEVICE_NAMES:
            return True
        
        # Partial match (for variations like "cell phone" vs "mobile phone")
        for device_name in self.DEVICE_NAMES:
            # Check if device name is contained in class name or vice versa
            if device_name in class_name_lower or class_name_lower in device_name:
                return True
        
        # Additional checks for common variations
        device_keywords = ['phone', 'laptop', 'tablet', 'watch', 'headphone', 'earphone', 'mouse', 'keyboard', 'computer', 'mobile']
        for keyword in device_keywords:
            if keyword in class_name_lower:
                return True
        
        return False
    
    def detect_devices(self, frame):
        """
        Detect devices in a video frame
        
        Args:
            frame: numpy array (BGR image) or base64 encoded image string
            
        Returns:
            dict: {
                'detected': bool,
                'devices': list of detected devices,
                'count': int,
                'timestamp': str
            }
        """
        if not DEPENDENCIES_AVAILABLE:
            return {
                'detected': False,
                'devices': [],
                'count': 0,
                'timestamp': datetime.now().isoformat(),
                'error': 'Dependencies not available. Install: pip install opencv-python ultralytics numpy'
            }
        
        if not self.is_loaded or self.model is None:
            return {
                'detected': False,
                'devices': [],
                'count': 0,
                'timestamp': datetime.now().isoformat(),
                'error': 'Model not loaded'
            }
        
        try:
            # Convert base64 to numpy array if needed
            if isinstance(frame, str):
                # Remove data URL prefix if present
                if ',' in frame:
                    frame = frame.split(',')[1]
                # Assume base64 encoded image
                image_data = base64.b64decode(frame)
                nparr = np.frombuffer(image_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None or frame.size == 0:
                return {
                    'detected': False,
                    'devices': [],
                    'count': 0,
                    'timestamp': datetime.now().isoformat(),
                    'error': 'Invalid frame'
                }
            
            # Store original dimensions for bounding box scaling
            original_height, original_width = frame.shape[:2]
            processed_frame = frame.copy()  # Work with a copy
            max_size = self.inference_size
            
            # Optimized resizing: Use faster interpolation and ensure we don't upscale
            scale_x = 1.0
            scale_y = 1.0
            if original_width > max_size or original_height > max_size:
                scale = min(max_size / original_width, max_size / original_height)
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
                # Use INTER_AREA for downscaling (faster and better quality than INTER_LINEAR)
                processed_frame = cv2.resize(processed_frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
                scale_x = original_width / new_width
                scale_y = original_height / new_height
                logger.debug(f"Resized frame from {original_width}x{original_height} to {new_width}x{new_height}")
            elif original_width < max_size * 0.8 or original_height < max_size * 0.8:
                # If image is much smaller, upscale slightly for better detection (but not too much)
                scale = min(max_size * 0.8 / original_width, max_size * 0.8 / original_height)
                if scale > 1.0:
                    new_width = int(original_width * scale)
                    new_height = int(original_height * scale)
                    processed_frame = cv2.resize(processed_frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                    scale_x = original_width / new_width
                    scale_y = original_height / new_height
            
            # Run YOLO inference with optimizations for speed and accuracy
            inference_kwargs = {
                'conf': self.confidence_threshold,
                'iou': 0.35,  # Slightly lower for better accuracy (fewer false positives)
                'verbose': False,
                'imgsz': self.inference_size,
                'agnostic_nms': False,  # Class-agnostic NMS (False = use class info for better accuracy)
                'max_det': 30,  # Reduced from 50 for faster processing (still enough for device detection)
                'half': self.use_half_precision,  # Use half precision if GPU available
                'device': 'cuda' if self.use_half_precision else 'cpu'  # Explicit device selection
            }
            
            # Add half precision if GPU available
            if self.use_half_precision:
                inference_kwargs['half'] = True
            
            results = self.model(processed_frame, **inference_kwargs)
            
            detected_devices = []
            
            # Process results
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    # Get class name and confidence
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = result.names[class_id]
                    
                    logger.debug(f"Detected class: {class_name} (confidence: {confidence:.2f})")
                    
                    # Additional confidence boost for device-like objects
                    # If confidence is close to threshold, apply stricter check
                    device_confidence_threshold = self.confidence_threshold
                    if confidence < device_confidence_threshold + 0.1:  # Within 0.1 of threshold
                        # Require higher confidence for borderline cases
                        device_confidence_threshold = self.confidence_threshold + 0.05
                    
                    # Check if it's a device and meets confidence threshold
                    if confidence >= device_confidence_threshold and self.is_device_class(class_name):
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        
                        # Scale bounding box back to original image size if we resized
                        x1 = x1 * scale_x
                        y1 = y1 * scale_y
                        x2 = x2 * scale_x
                        y2 = y2 * scale_y
                        
                        logger.info(f"Device detected: {class_name} (confidence: {confidence:.2f})")
                        
                        detected_devices.append({
                            'class': str(class_name),  # Ensure string type
                            'confidence': float(round(confidence, 3)),  # Ensure float type
                            'bbox': {
                                'x1': float(x1),
                                'y1': float(y1),
                                'x2': float(x2),
                                'y2': float(y2)
                            }
                        })
            
            # Ensure all return values are JSON-serializable
            return {
                'detected': bool(len(detected_devices) > 0),  # Convert to Python bool
                'devices': detected_devices,
                'count': int(len(detected_devices)),  # Ensure int type
                'timestamp': str(datetime.now().isoformat())  # Ensure string type
            }
            
        except Exception as e:
            logger.error(f"Error in device detection: {e}")
            return {
                'detected': False,
                'devices': [],
                'count': 0,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def detect_from_base64(self, base64_image):
        """
        Detect devices from base64 encoded image
        
        Args:
            base64_image: Base64 encoded image string (with or without data URL prefix)
            
        Returns:
            dict: Detection results
        """
        try:
            # Remove data URL prefix if present
            if ',' in base64_image:
                base64_image = base64_image.split(',')[1]
            
            # Decode base64
            image_data = base64.b64decode(base64_image)
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            return self.detect_devices(frame)
            
        except Exception as e:
            logger.error(f"Error decoding base64 image: {e}")
            return {
                'detected': False,
                'devices': [],
                'count': 0,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }


# Global detector instance (singleton pattern)
_detector_instance = None

def get_detector():
    """Get or create detector instance (singleton)"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = DeviceDetector()
    return _detector_instance

