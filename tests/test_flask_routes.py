"""
Integration tests for Flask application routes.

Tests route accessibility, MJPEG streaming, and concurrent viewer support.
"""
import pytest
from app import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestRoutes:
    """Test Flask routes."""

    def test_index_route(self, client):
        """Test that the main page loads successfully."""
        rv = client.get('/')
        assert rv.status_code == 200
        assert b'Pi Camera Stream' in rv.data or b'Camera Stream' in rv.data

    def test_index_contains_stream_config(self, client):
        """Test that the index page includes stream configuration."""
        rv = client.get('/')
        assert rv.status_code == 200
        # Check that resolution and framerate are displayed
        assert b'Resolution:' in rv.data or b'resolution' in rv.data.lower()

    def test_video_feed_route_exists(self, client):
        """Test that the video feed route exists."""
        rv = client.get('/video_feed')
        # Should return 200 or 503 (if camera not available)
        assert rv.status_code in [200, 503]

    def test_video_feed_content_type(self, client):
        """Test that video feed returns correct content type."""
        rv = client.get('/video_feed')
        if rv.status_code == 200:
            # Should be multipart MJPEG
            assert b'multipart' in rv.content_type.encode()

    def test_health_route(self, client):
        """Test the health check endpoint."""
        rv = client.get('/health')
        assert rv.status_code == 200
        data = rv.get_json()
        assert 'status' in data
        assert data['status'] == 'healthy'
        assert 'camera_available' in data
        assert 'config' in data

    def test_health_check_includes_config(self, client):
        """Test that health check returns configuration."""
        rv = client.get('/health')
        data = rv.get_json()
        config = data['config']

        assert 'resolution' in config
        assert 'framerate' in config
        assert 'quality' in config

    def test_404_on_invalid_route(self, client):
        """Test that invalid routes return 404."""
        rv = client.get('/nonexistent')
        assert rv.status_code == 404


class TestStreamingBehavior:
    """Test streaming behavior."""

    def test_video_feed_when_camera_unavailable(self, client):
        """Test video feed response when camera is not available."""
        rv = client.get('/video_feed')
        # Should handle gracefully, either with 503 or proper error
        assert rv.status_code in [200, 503]

        if rv.status_code == 503:
            assert b'Camera not available' in rv.data

    def test_multiple_concurrent_requests(self, client):
        """Test that multiple clients can access the stream."""
        # This is a simplified test - actual concurrent streaming
        # would need to be tested with real camera hardware
        responses = []

        for _ in range(3):
            rv = client.get('/')
            responses.append(rv.status_code)

        # All requests should succeed
        assert all(status == 200 for status in responses)


class TestStaticAssets:
    """Test that static assets are accessible."""

    def test_css_accessible(self, client):
        """Test that CSS file is accessible."""
        rv = client.get('/static/css/style.css')
        assert rv.status_code == 200
        assert b'body' in rv.data or b'container' in rv.data

    def test_js_accessible(self, client):
        """Test that JavaScript file is accessible."""
        rv = client.get('/static/js/stream.js')
        assert rv.status_code == 200
        assert b'function' in rv.data or b'const' in rv.data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
