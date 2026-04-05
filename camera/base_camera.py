"""
Base camera class with thread-safe frame distribution.

This module provides an abstract base class that handles threading and
multi-client synchronization for video streaming. It ensures that multiple
clients can receive frames simultaneously without blocking each other.

Based on Miguel Grinberg's Flask video streaming pattern:
https://blog.miguelgrinberg.com/post/flask-video-streaming-revisited
"""
import time
import threading
from abc import ABC, abstractmethod
import config


class CameraEvent:
    """
    Event-like class that signals when a new frame is available.

    This class manages per-client synchronization, allowing each client
    to wait for new frames independently without affecting other clients.
    """

    def __init__(self):
        self.events = {}

    def wait(self):
        """Wait until a new frame is available."""
        ident = threading.get_ident()
        if ident not in self.events:
            # Create a new event for this client
            self.events[ident] = [threading.Event(), time.time()]
        return self.events[ident][0].wait()

    def set(self):
        """Signal all clients that a new frame is available."""
        now = time.time()
        remove = []
        for ident, event in self.events.items():
            if not event[0].is_set():
                # Signal the event and update timestamp
                event[0].set()
                event[1] = now
            else:
                # Remove events that weren't cleared (stale clients)
                if now - event[1] > 5:
                    remove.append(ident)

        # Clean up stale events
        for ident in remove:
            del self.events[ident]

    def clear(self):
        """Clear the event for the current thread."""
        ident = threading.get_ident()
        if ident in self.events:
            self.events[ident][0].clear()


class BaseCamera(ABC):
    """
    Abstract base camera class with thread-safe frame distribution.

    This class manages a background thread that continuously captures frames
    from the camera. Multiple clients can request frames simultaneously, and
    each receives the latest frame without blocking others.

    The camera thread automatically starts when the first client connects and
    stops after a timeout period with no clients.
    """

    thread = None  # Background thread that captures frames
    frame = None  # Current frame available to clients
    last_access = 0  # Timestamp of last client access
    event = CameraEvent()

    def __init__(self):
        """Start the background camera thread if not already running."""
        if BaseCamera.thread is None:
            BaseCamera.last_access = time.time()

            # Start background thread
            BaseCamera.thread = threading.Thread(target=self._thread)
            BaseCamera.thread.daemon = True
            BaseCamera.thread.start()

            # Wait for first frame to be available
            while self.get_frame() is None:
                time.sleep(0.01)

    def get_frame(self):
        """
        Return the current frame.

        Returns:
            bytes: JPEG encoded frame data, or None if no frame available
        """
        BaseCamera.last_access = time.time()

        # Wait for a new frame
        BaseCamera.event.wait()
        BaseCamera.event.clear()

        return BaseCamera.frame

    @staticmethod
    @abstractmethod
    def frames():
        """
        Generator that yields camera frames.

        This method must be implemented by subclasses to provide the actual
        frame capture mechanism specific to the camera hardware.

        Yields:
            bytes: JPEG encoded frame data
        """
        pass

    @classmethod
    def _thread(cls):
        """
        Background thread that captures frames and distributes to clients.

        This thread runs continuously, capturing frames and making them
        available to all connected clients. It automatically stops after
        a timeout period with no client activity.
        """
        print('Starting camera thread.')
        frames_iterator = cls.frames()

        for frame in frames_iterator:
            BaseCamera.frame = frame
            BaseCamera.event.set()  # Signal all clients
            time.sleep(0)  # Yield to other threads

            # Check if there are any clients
            if time.time() - BaseCamera.last_access > config.FRAME_TIMEOUT:
                frames_iterator.close()
                print('Stopping camera thread due to inactivity.')
                break

        BaseCamera.thread = None
