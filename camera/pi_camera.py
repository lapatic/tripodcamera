"""
Raspberry Pi camera implementation using picamera2.

This module provides a concrete implementation of the BaseCamera class
for Raspberry Pi camera modules. It uses the picamera2 library with
hardware-accelerated MJPEG encoding for optimal performance.
"""
import io
import time
import threading
from camera.base_camera import BaseCamera
import config

try:
    from picamera2 import Picamera2
    from picamera2.encoders import MJPEGEncoder
    from picamera2.outputs import FileOutput
except ImportError:
    # Allow import to succeed even without picamera2 (for local development)
    Picamera2 = None
    MJPEGEncoder = None
    FileOutput = None


class StreamingOutput(io.BufferedIOBase):
    """
    Thread-safe buffer for MJPEG stream frames.

    This class acts as an output target for the MJPEGEncoder, storing the
    latest frame and notifying waiting threads when a new frame arrives.
    """

    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        """
        Write a new frame to the buffer.

        Called by the encoder when a new frame is ready. Notifies all
        waiting threads that a new frame is available.

        Args:
            buf: Frame data as bytes
        """
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class PiCamera(BaseCamera):
    """
    Raspberry Pi camera implementation.

    Uses picamera2 with MJPEGEncoder for hardware-accelerated encoding.
    Provides low-latency streaming suitable for 2-5 simultaneous viewers.
    """

    @staticmethod
    def frames():
        """
        Generator that yields frames from the Pi camera.

        Initializes the camera with the configured resolution and framerate,
        then continuously yields JPEG frames as they become available.

        Yields:
            bytes: JPEG encoded frame data
        """
        if Picamera2 is None:
            raise RuntimeError(
                'picamera2 library not found. '
                'This module can only be used on a Raspberry Pi with picamera2 installed.'
            )

        # Initialize camera
        picam2 = Picamera2()

        # Configure camera for video streaming
        resolution = config.STREAM_CONFIG['resolution']
        framerate = config.STREAM_CONFIG['framerate']

        # Create video configuration
        video_config = picam2.create_video_configuration(
            main={"size": resolution, "format": "RGB888"},
            controls={
                "FrameRate": framerate,
            }
        )

        picam2.configure(video_config)

        # Apply optional camera controls if specified
        if config.CAMERA_CONTROLS:
            # Note: picamera2 controls are applied differently than picamera
            # Brightness, Contrast, Saturation ranges vary by camera model
            # These should be tuned based on your specific camera and conditions
            pass

        # Create streaming output buffer
        output = StreamingOutput()

        # Create MJPEG encoder
        # Note: Newer picamera2 versions (0.3.34+) use bitrate instead of quality (q)
        # For MJPEG, bitrate determines per-frame quality
        quality = config.STREAM_CONFIG.get('quality', 85)

        if quality:
            # MJPEG bitrate calculation for high quality
            # Higher resolution and quality need more bits per frame
            resolution = config.STREAM_CONFIG['resolution']
            pixels = resolution[0] * resolution[1]
            framerate = config.STREAM_CONFIG['framerate']

            # More aggressive bitrate for better quality:
            # - Base: 8 Mbps for 720p at quality 85 (was too low at 5 Mbps)
            # - Scale up with resolution and quality
            # - DON'T reduce for lower framerate (fewer frames = higher quality per frame)
            reference_pixels = 1280 * 720  # 720p
            reference_quality = 85
            reference_bitrate = 8_000_000  # 8 Mbps base (increased from 5)

            # Calculate without framerate penalty
            pixel_scale = pixels / reference_pixels
            quality_scale = quality / reference_quality

            # For very high quality (95+), boost even more
            if quality >= 95:
                quality_scale *= 1.25  # 25% boost for quality 95+

            bitrate = int(reference_bitrate * pixel_scale * quality_scale)

            # Ensure good bitrate range for 1080p
            if pixels >= 1920 * 1080:
                bitrate = max(bitrate, 15_000_000)  # Minimum 15 Mbps
                bitrate = min(bitrate, 20_000_000)  # Maximum 20 Mbps (Pi4 limit)

            print(f'MJPEG encoder bitrate: {bitrate / 1_000_000:.1f} Mbps '
                  f'(Resolution: {resolution[0]}x{resolution[1]}, Quality: {quality}, '
                  f'Framerate: {framerate} fps)')
        else:
            bitrate = None  # Use encoder default

        encoder = MJPEGEncoder(bitrate=bitrate)

        # Start camera with encoder
        picam2.start_recording(encoder, FileOutput(output))

        try:
            while True:
                with output.condition:
                    # Wait for a new frame
                    output.condition.wait()
                    frame = output.frame

                if frame:
                    yield frame
                else:
                    time.sleep(0.01)

        finally:
            # Clean up camera resources
            picam2.stop_recording()
            picam2.close()
            print('Camera resources cleaned up.')
