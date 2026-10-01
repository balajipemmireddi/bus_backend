"""
Image processing utilities for enrollment quality checks and encoding.
"""

import base64
import cv2
import numpy as np


def base64_to_cv2(b64_str: str):
    """Decode base64 string to OpenCV image."""
    try:
        img_data = base64.b64decode(b64_str)
        arr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception as e:
        return None


def quality_check_image(image):
    """Validate image quality for enrollment (size, faces, sharpness)."""
    if image is None:
        return False, "Could not decode image"
    
    h, w = image.shape[:2]
    if h < 100 or w < 100:
        return False, f"Image too small: {w}x{h}"
    
    try:
        import face_recognition
        
        # Check for exactly one face
        face_locations = face_recognition.face_locations(image, model="hog")
        if len(face_locations) != 1:
            return False, f"Expected 1 face, found {len(face_locations)}"
        
        # Sharpness check using Laplacian variance
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = laplacian.var()
        if sharpness < 15.0:
            return False, f"Image too blurry (sharpness={sharpness:.1f}, need >15)"
        
        return True, "OK"
    except Exception as e:
        return False, str(e)


def get_encoding_from_image(image):
    """Generate face encoding from image using face_recognition."""
    try:
        import face_recognition
        encodings = face_recognition.face_encodings(image)
        if not encodings:
            return None, "No face detected or encoding failed"
        return encodings[0].tolist(), None
    except Exception as e:
        return None, str(e)
