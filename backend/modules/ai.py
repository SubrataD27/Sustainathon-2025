"""AI Detection Module (Simulated + Optional Real YOLOv8)

Provides:
 - Simulated detection generation for demo mode (default)
 - Optional real YOLOv8 inference on uploaded webcam frames (base64) or future video feeds

Endpoints:
 GET   /api/ai/detections   -> recent detections
 POST  /api/ai/process      -> simulated frame processing (legacy)
 POST  /api/ai/frame        -> real (or simulated fallback) inference on client webcam frame
 GET   /api/ai/status       -> model statistics
 POST  /api/ai/configure    -> adjust runtime parameters
 POST  /api/ai/reset        -> clear history

Environment toggle:
    ENABLE_YOLO=1  (attempt to load ultralytics YOLOv8 model)

Notes:
 - Uses lightweight yolov8n.pt by default for speed
 - Falls back gracefully to simulated detections if model unavailable or errors occur
 - Bounding boxes returned in percentage coordinates for easy overlay
"""

from flask import Blueprint, jsonify, request
import random
import time
from datetime import datetime
import uuid
import os
import base64
import threading

import numpy as np

# KAVACH system imports
from .threats import THREATS, WHITELIST


try:  # Optional heavy deps
        from ultralytics import YOLO  # type: ignore
        import cv2  # type: ignore
        YOLO_AVAILABLE = True
except Exception:  # pragma: no cover - environment fallback
        YOLO_AVAILABLE = False
        YOLO = None  # type: ignore
        cv2 = None  # type: ignore

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

# In-memory store for rapid MVP iteration
detection_history = []
yolo_status = 'active'  # 'active', 'offline', 'processing', 'error'

# Runtime configurable parameters
runtime_config = {
    'confidence_threshold': 0.45, # Default threshold
    'enable_tracking': True,
    'model_variant': 'yolov8n.pt',
    'inference_enabled': False,  # Toggled true only if model loads & env allows
    'last_model_error': None,
    'threat_fusion_enabled': True,
    'fusion_confidence_threshold': 0.75, # Min confidence to create a threat
}

_yolo_model = None
_model_lock = threading.Lock()

def _load_model_if_enabled():
    """Attempt to load YOLOv8 model once (thread-safe)."""
    global _yolo_model, yolo_status
    if not YOLO_AVAILABLE:
        runtime_config['last_model_error'] = 'ultralytics or opencv not installed'
        return
    if not os.getenv('ENABLE_YOLO', '0') in ('1', 'true', 'True'):
        runtime_config['last_model_error'] = 'ENABLE_YOLO env not set'
        return
    with _model_lock:
        if _yolo_model is None:
            try:
                yolo_status = 'loading'
                _yolo_model = YOLO(runtime_config['model_variant'])
                runtime_config['inference_enabled'] = True
                yolo_status = 'active'
            except Exception as e:  # pragma: no cover
                runtime_config['last_model_error'] = str(e)
                yolo_status = 'error'
                runtime_config['inference_enabled'] = False

def _fuse_detection_into_threat(detection):
    """If a high-confidence drone is detected, create a threat in the main system."""
    if not runtime_config['threat_fusion_enabled']:
        return

    is_drone = 'drone' in detection.get('class', '').lower()
    is_high_confidence = detection.get('confidence', 0) >= runtime_config['fusion_confidence_threshold']

    if is_drone and is_high_confidence:
        # Avoid creating duplicate threats for the same object
        # (simple check based on recent threats)
        for threat in list(THREATS.values())[-5:]:
            if threat.get('source_detection_id') == detection.get('id'):
                return # Already fused

        # Create a new threat
        new_threat_id = str(uuid.uuid4())
        remote_id = f"AI-GEN-{str(uuid.uuid4())[:4]}"
        threat = {
            'id': new_threat_id,
            'class': 'ai_detected_drone',
            'confidence': detection['confidence'],
            # Placeholder location - could be improved with triangulation
            'location': {'lat': 28.50 + random.uniform(-0.005, 0.005), 'lon': 77.60 + random.uniform(-0.005, 0.005)},
            'status': 'detected',
            'created_at': datetime.utcnow().isoformat()+'Z',
            'remote_id': remote_id,
            'authorized': remote_id in WHITELIST,
            'source_detection_id': detection.get('id') # Link back to the AI detection
        }
        THREATS[new_threat_id] = threat


def _run_inference(image_bgr: np.ndarray):
    """Run YOLO inference if enabled, else return simulated placeholder.

    Returns list of detection dicts with: class, confidence, bbox{x,y,width,height} (%), threat_level
    """
    global yolo_status
    if not runtime_config['inference_enabled'] or _yolo_model is None:
        # Fallback simulated single detection occasionally
        if random.random() < 0.4:
            return []
        cls = random.choice(['drone', 'bird'])
        detection = {
            'id': str(uuid.uuid4()),
            'class': cls,
            'confidence': round(random.uniform(0.6, 0.95), 2),
            'bbox': {'x': 30, 'y': 25, 'width': 35, 'height': 30},
            'timestamp': datetime.now().isoformat(),
            'threat_level': THREAT_LEVELS.get(cls, 0.5),
            'camera_source': 'webcam_simulated'
        }
        _fuse_detection_into_threat(detection)
        return [detection]
    try:
        yolo_status = 'processing'
        results = _yolo_model(image_bgr, verbose=False, conf=runtime_config['confidence_threshold'])[0]
        detections = []
        h, w = image_bgr.shape[:2]
        for box in results.boxes:
            conf = float(box.conf[0])
            # This check is now handled by the model call, but double-checking doesn't hurt
            if conf < runtime_config['confidence_threshold']:
                continue
            cls_idx = int(box.cls[0])
            # Get human readable class name (ultralytics stores in model.names)
            name = results.names.get(cls_idx, 'object')
            # Simple mapping to domain classes
            mapped = 'drone' if 'drone' in name.lower() else (
                'bird' if 'bird' in name.lower() else ('person' if 'person' in name.lower() else name)
            )
            x1, y1, x2, y2 = map(float, box.xyxy[0])
            bw = max(1.0, x2 - x1)
            bh = max(1.0, y2 - y1)
            det = {
                'id': str(uuid.uuid4()),
                'class': mapped,
                'raw_class': name,
                'confidence': round(conf, 3),
                'bbox': {
                    'x': round((x1 / w) * 100, 2),
                    'y': round((y1 / h) * 100, 2),
                    'width': round((bw / w) * 100, 2),
                    'height': round((bh / h) * 100, 2),
                },
                'timestamp': datetime.now().isoformat(),
                'threat_level': THREAT_LEVELS.get(mapped, 0.5),
                'camera_source': 'webcam_real'
            }
            detections.append(det)
            _fuse_detection_into_threat(det)
        yolo_status = 'active'
        return detections
    except Exception as e:  # pragma: no cover
        yolo_status = 'error'
        runtime_config['last_model_error'] = str(e)
        return []

# Drone classes that YOLOv8 can detect
DETECTION_CLASSES = [
    'drone', 'quadcopter', 'helicopter', 'bird', 'aircraft', 
    'person', 'vehicle', 'unknown_object'
]

# Threat levels for different classes
THREAT_LEVELS = {
    'drone': 0.9,
    'quadcopter': 0.85,
    'helicopter': 0.7,
    'aircraft': 0.6,
    'bird': 0.1,
    'person': 0.2,
    'vehicle': 0.3,
    'unknown_object': 0.5
}

@ai_bp.route('/detections', methods=['GET'])
def get_detections():
    """Get current AI detection results"""
    global detection_history, yolo_status
    
    # Return last 50 detections
    recent_detections = detection_history[-50:] if detection_history else []
    
    return jsonify({
        'status': 'success',
        'detections': recent_detections,
        'model_status': yolo_status,
        'total_detections': len(detection_history),
        'timestamp': datetime.now().isoformat()
    })

@ai_bp.route('/process', methods=['POST'])
def process_camera_frame():
    """Process camera frame through YOLOv8 model"""
    global detection_history, yolo_status
    
    try:
        data = request.get_json() or {}
        camera_url = data.get('camera_url', 'http://192.168.137.189/mjpeg/1')
        timestamp = data.get('timestamp', time.time() * 1000)
        
        # Set status to processing
        yolo_status = 'processing'
        
        # Simulate YOLOv8 processing time
        time.sleep(0.1)
        
        # Generate simulated detections (in real implementation, this would be YOLOv8)
        num_detections = random.choices([0, 1, 2, 3], weights=[40, 30, 20, 10])[0]
        new_detections = []
        
        for i in range(num_detections):
            detection_class = random.choices(
                list(DETECTION_CLASSES), 
                weights=[10, 8, 3, 2, 15, 20, 25, 17]  # Weighted probabilities
            )[0]
            
            detection = {
                'id': str(uuid.uuid4()),
                'class': detection_class,
                'confidence': min(0.99, max(0.3, random.gauss(0.75, 0.15))),
                'bbox': {
                    'x': random.randint(10, 80),
                    'y': random.randint(10, 70),
                    'width': random.randint(20, 100),
                    'height': random.randint(15, 80)
                },
                'timestamp': datetime.now().isoformat(),
                'threat_level': THREAT_LEVELS.get(detection_class, 0.5),
                'camera_source': camera_url
            }
            
            new_detections.append(detection)
            detection_history.append(detection)
            _fuse_detection_into_threat(detection)
        
        # Keep only last 1000 detections in memory
        if len(detection_history) > 1000:
            detection_history = detection_history[-1000:]
        
        # Reset status to active
        yolo_status = 'active'
        
        return jsonify({
            'status': 'success',
            'detections': new_detections,
            'processed_frame': {
                'timestamp': timestamp,
                'camera_url': camera_url,
                'processing_time_ms': 100
            },
            'model_info': {
                'model': 'YOLOv8',
                'version': '8.0.196',
                'status': yolo_status,
                'mode': 'simulated'
            }
        })
        
    except Exception as e:
        yolo_status = 'error'
        return jsonify({
            'status': 'error',
            'message': str(e),
            'model_status': yolo_status
        }), 500

@ai_bp.route('/status', methods=['GET'])
def get_ai_status():
    """Get AI model status and statistics"""
    global detection_history, yolo_status
    
    # Calculate statistics
    total_detections = len(detection_history)
    recent_detections = [d for d in detection_history if 
                        (datetime.now() - datetime.fromisoformat(d['timestamp'])).seconds < 300]
    
    class_distribution = {}
    threat_detections = 0
    
    for detection in recent_detections:
        class_name = detection['class']
        class_distribution[class_name] = class_distribution.get(class_name, 0) + 1
        if detection['threat_level'] > 0.7:
            threat_detections += 1
    
    return jsonify({
        'status': 'success',
        'model_status': yolo_status,
        'statistics': {
            'total_detections': total_detections,
            'recent_detections': len(recent_detections),
            'threat_detections': threat_detections,
            'class_distribution': class_distribution,
            'detection_rate': len(recent_detections) / 5.0  # per minute (5min window)
        },
        'model_info': {
            'name': 'YOLOv8',
            'version': '8.0.196',
            'confidence_threshold': runtime_config['confidence_threshold'],
            'classes_detected': len(DETECTION_CLASSES),
            'inference_enabled': runtime_config['inference_enabled'],
            'last_model_error': runtime_config['last_model_error']
        },
        'camera_info': {
            'source': 'ESP32-CAM',
            'url': 'http://192.168.137.189/mjpeg/1',
            'resolution': '640x480',
            'fps': 15
        }
    })

@ai_bp.route('/frame', methods=['POST'])
def process_uploaded_frame():
    """Accept a base64 webcam frame from browser, run YOLO if available, return detections.

    Expected JSON: { image_base64: 'data:image/jpeg;base64,...' | '...rawbase64...', client_timestamp: <ms> }
    """
    global detection_history
    try:
        payload = request.get_json() or {}
        img_b64 = payload.get('image_base64')
        client_ts = payload.get('client_timestamp', int(time.time()*1000))
        if not img_b64:
            return jsonify({'status':'error','message':'image_base64 missing'}), 400
        # Strip data URL header if present
        if ',' in img_b64:
            img_b64 = img_b64.split(',',1)[1]
        try:
            raw = base64.b64decode(img_b64)
        except Exception:
            return jsonify({'status':'error','message':'invalid base64'}), 400
        if cv2 is not None:
            np_arr = np.frombuffer(raw, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None:
                return jsonify({'status':'error','message':'could not decode image'}), 400
            # Resize for speed (keep aspect)
            h, w = frame.shape[:2]
            if w > 960:
                scale = 960 / w
                frame = cv2.resize(frame, (960, int(h*scale)))
        else:
            frame = np.zeros((480,640,3), dtype=np.uint8)
        detections = _run_inference(frame)
        # Append to history
        detection_history.extend(detections)
        if len(detection_history) > 1000:
            detection_history[:] = detection_history[-1000:]
        return jsonify({
            'status': 'success',
            'detections': detections,
            'inference': {
                'model_active': runtime_config['inference_enabled'],
                'yolo_status': yolo_status,
                'frame_received_ms': client_ts,
                'server_time_ms': int(time.time()*1000)
            }
        })
    except Exception as e:  # pragma: no cover
        return jsonify({'status':'error','message':str(e)}), 500

@ai_bp.route('/configure', methods=['POST'])
def configure_ai_model():
    """Configure AI model parameters"""
    global yolo_status
    
    try:
        data = request.get_json() or {}
        confidence_threshold = data.get('confidence_threshold', runtime_config['confidence_threshold'])
        enable_tracking = data.get('enable_tracking', True)
        model_status = data.get('status', 'active')
        reload_model = data.get('reload', False)
        
        # Validate parameters
        if not 0.1 <= confidence_threshold <= 0.99:
            return jsonify({
                'status': 'error',
                'message': 'Confidence threshold must be between 0.1 and 0.99'
            }), 400
        
        if model_status not in ['active', 'offline', 'maintenance']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid status. Must be active, offline, or maintenance'
            }), 400
        
        yolo_status = model_status
        runtime_config['confidence_threshold'] = confidence_threshold
        runtime_config['enable_tracking'] = enable_tracking
        if reload_model:
            # Force reload attempt
            with _model_lock:
                global _yolo_model
                _yolo_model = None
            _load_model_if_enabled()
        
        return jsonify({
            'status': 'success',
            'message': 'AI model configured successfully',
            'configuration': {
                'confidence_threshold': confidence_threshold,
                'enable_tracking': enable_tracking,
                'model_status': yolo_status,
                'inference_enabled': runtime_config['inference_enabled'],
                'last_model_error': runtime_config['last_model_error'],
                'updated_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@ai_bp.route('/reset', methods=['POST'])
def reset_ai_system():
    """Reset AI detection system"""
    global detection_history, yolo_status
    
    try:
        detection_history.clear()
        yolo_status = 'active'
        
        return jsonify({
            'status': 'success',
            'message': 'AI detection system reset successfully',
            'reset_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Initialize with some demo data
def init_demo_data():
    """Initialize with demonstration detection data"""
    global detection_history
    
    demo_detections = [
        {
            'id': str(uuid.uuid4()),
            'class': 'drone',
            'confidence': 0.92,
            'bbox': {'x': 45, 'y': 30, 'width': 80, 'height': 60},
            'timestamp': datetime.now().isoformat(),
            'threat_level': 0.9,
            'camera_source': 'http://192.168.137.189/mjpeg/1'
        },
        {
            'id': str(uuid.uuid4()),
            'class': 'bird',
            'confidence': 0.78,
            'bbox': {'x': 70, 'y': 20, 'width': 30, 'height': 25},
            'timestamp': datetime.now().isoformat(),
            'threat_level': 0.1,
            'camera_source': 'http://192.168.137.189/mjpeg/1'
        }
    ]
    
    detection_history.extend(demo_detections)

# Initialize model on startup
_load_model_if_enabled()

# Initialize demo data when module loads
init_demo_data()