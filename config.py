"""Configuration settings for the camera streaming server."""
import os

# Flask Configuration
PORT = int(os.environ.get('CAMERA_PORT', 5000))
DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

# Camera Configuration
STREAM_CONFIG = {
    'resolution': tuple(map(int, os.environ.get('CAMERA_RESOLUTION', '1280,720').split(','))),
    'framerate': int(os.environ.get('CAMERA_FRAMERATE', 30)),
    'quality': int(os.environ.get('CAMERA_QUALITY', 85)),
}

# Thread Configuration
FRAME_TIMEOUT = int(os.environ.get('FRAME_TIMEOUT', 10))  # Seconds before stopping camera thread

# Optional: Camera controls (can be tuned for different lighting conditions)
CAMERA_CONTROLS = {
    'brightness': float(os.environ.get('CAMERA_BRIGHTNESS', 0.0)),
    'contrast': float(os.environ.get('CAMERA_CONTRAST', 1.0)),
    'saturation': float(os.environ.get('CAMERA_SATURATION', 1.0)),
}
