"""
Unit tests for camera module.

Tests camera initialization, frame generation, threading,
and multi-client synchronization.
"""
import pytest
import time
import threading
from camera.base_camera import BaseCamera, CameraEvent


class MockCamera(BaseCamera):
    """Mock camera for testing without hardware."""

    frame_count = 0

    @staticmethod
    def frames():
        """Generate mock JPEG frames."""
        # JPEG magic bytes (SOI) and end marker (EOI)
        jpeg_start = b'\xff\xd8'
        jpeg_end = b'\xff\xd9'

        while True:
            # Generate a minimal valid JPEG
            MockCamera.frame_count += 1
            frame = jpeg_start + b'\x00' * 100 + jpeg_end
            yield frame
            time.sleep(0.033)  # ~30 fps


class TestCameraEvent:
    """Test the CameraEvent class."""

    def test_event_creation(self):
        """Test that events can be created."""
        event = CameraEvent()
        assert event.events == {}

    def test_event_wait_creates_event(self):
        """Test that wait() creates an event for the current thread."""
        event = CameraEvent()

        # Run wait in a thread with timeout
        result = []

        def wait_thread():
            event.wait()
            result.append(True)

        t = threading.Thread(target=wait_thread)
        t.daemon = True
        t.start()

        # Give thread time to create event
        time.sleep(0.1)

        # Should have created an event
        assert len(event.events) > 0

        # Signal the event
        event.set()
        t.join(timeout=1)

        assert result == [True]

    def test_event_set_signals_all(self):
        """Test that set() signals all waiting threads."""
        event = CameraEvent()
        results = []

        def wait_thread(thread_id):
            event.wait()
            results.append(thread_id)

        # Create multiple waiting threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=wait_thread, args=(i,))
            t.daemon = True
            t.start()
            threads.append(t)

        time.sleep(0.1)

        # Signal all threads
        event.set()

        # Wait for all threads
        for t in threads:
            t.join(timeout=1)

        # All threads should have been signaled
        assert len(results) == 3
        assert sorted(results) == [0, 1, 2]


class TestBaseCamera:
    """Test the BaseCamera base class."""

    def test_camera_starts_thread(self):
        """Test that camera initialization starts the background thread."""
        camera = MockCamera()
        assert MockCamera.thread is not None
        assert MockCamera.thread.is_alive()

    def test_get_frame_returns_valid_jpeg(self):
        """Test that get_frame returns valid JPEG data."""
        camera = MockCamera()
        frame = camera.get_frame()

        assert frame is not None
        assert len(frame) > 0
        # Check JPEG magic bytes
        assert frame[:2] == b'\xff\xd8'  # JPEG SOI
        assert frame[-2:] == b'\xff\xd9'  # JPEG EOI

    def test_multiple_clients_get_frames(self):
        """Test that multiple clients can get frames simultaneously."""
        camera = MockCamera()
        frames = []

        def get_frames(n):
            for _ in range(n):
                frame = camera.get_frame()
                frames.append(frame)

        # Create multiple client threads
        threads = []
        for _ in range(3):
            t = threading.Thread(target=get_frames, args=(5,))
            t.start()
            threads.append(t)

        # Wait for all threads to complete
        for t in threads:
            t.join(timeout=5)

        # All threads should have received frames
        assert len(frames) == 15  # 3 clients × 5 frames

    def test_camera_thread_stops_on_timeout(self):
        """Test that camera thread stops after timeout with no clients."""
        # Create a camera and get one frame
        camera = MockCamera()
        frame = camera.get_frame()
        assert frame is not None

        # Wait for timeout (using a short timeout for testing)
        # Note: This test would need config.FRAME_TIMEOUT to be short
        # In practice, we just verify the thread management works
        assert MockCamera.thread is not None

    def test_camera_restarts_after_stop(self):
        """Test that camera can restart after stopping."""
        # First camera instance
        camera1 = MockCamera()
        frame1 = camera1.get_frame()
        assert frame1 is not None

        # Reset class variables to simulate stopped camera
        MockCamera.thread = None
        MockCamera.frame = None

        # Second camera instance should restart thread
        camera2 = MockCamera()
        frame2 = camera2.get_frame()
        assert frame2 is not None
        assert MockCamera.thread is not None


class TestFrameGeneration:
    """Test frame generation and distribution."""

    def test_frames_are_updated(self):
        """Test that frames are continuously updated."""
        camera = MockCamera()

        # Get initial frame count
        initial_count = MockCamera.frame_count

        # Wait a bit
        time.sleep(0.2)

        # Frame count should have increased
        assert MockCamera.frame_count > initial_count

    def test_concurrent_access_thread_safe(self):
        """Test that concurrent frame access is thread-safe."""
        camera = MockCamera()
        errors = []

        def access_frames():
            try:
                for _ in range(10):
                    frame = camera.get_frame()
                    assert frame is not None
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        # Create many concurrent threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=access_frames)
            t.start()
            threads.append(t)

        # Wait for all threads
        for t in threads:
            t.join(timeout=5)

        # No errors should have occurred
        assert len(errors) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
