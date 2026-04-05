"""
Flask application for Raspberry Pi camera streaming.

This application provides a web interface for viewing the camera stream
and serves MJPEG video over HTTP. Supports multiple simultaneous viewers
with low latency.
"""
from flask import Flask, render_template, Response
import config

# Import the appropriate camera implementation
try:
    from camera.pi_camera import PiCamera as Camera
except (ImportError, RuntimeError):
    # Fallback for development/testing without Pi hardware
    print("Warning: picamera2 not available. Camera streaming will not work.")
    Camera = None

app = Flask(__name__)
app.config.from_object(config)


def gen(camera):
    """
    Video streaming generator function.

    Continuously yields MJPEG frames from the camera with proper
    HTTP multipart boundaries for browser display.

    Args:
        camera: Camera instance to get frames from

    Yields:
        bytes: MJPEG frame data with HTTP headers
    """
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
def index():
    """
    Render the main page with the video stream.

    Returns:
        Rendered HTML template with stream configuration
    """
    return render_template('index.html',
                          stream_config=config.STREAM_CONFIG)


@app.route('/video_feed')
def video_feed():
    """
    Video streaming route.

    Returns an MJPEG stream as a multipart HTTP response. Each frame
    is sent as a separate part with JPEG content type.

    Returns:
        Response: Flask response with MJPEG stream
    """
    if Camera is None:
        return "Camera not available. picamera2 library required.", 503

    return Response(gen(Camera()),
                   mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/health')
def health():
    """
    Health check endpoint for monitoring.

    Returns:
        JSON response with service status
    """
    return {
        'status': 'healthy',
        'camera_available': Camera is not None,
        'config': {
            'resolution': config.STREAM_CONFIG['resolution'],
            'framerate': config.STREAM_CONFIG['framerate'],
            'quality': config.STREAM_CONFIG['quality']
        }
    }


if __name__ == '__main__':
    # Run the Flask app
    # threaded=True is essential for handling multiple simultaneous viewers
    app.run(
        host='0.0.0.0',  # Listen on all network interfaces
        port=config.PORT,
        threaded=True,  # Enable threading for concurrent requests
        debug=config.DEBUG
    )
