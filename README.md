# Raspberry Pi Camera Streaming Server

A low-latency camera streaming server for Raspberry Pi that broadcasts video to multiple viewers through a web interface using MJPEG over HTTP.

## Features

- **Low Latency**: 100-300ms typical latency for real-time viewing
- **Multiple Viewers**: Supports 2-5 simultaneous viewers efficiently
- **Web Interface**: Clean, responsive HTML5 interface with dark theme
- **Hardware Accelerated**: Uses MJPEGEncoder for optimal performance
- **Auto-start**: Systemd service for automatic startup on boot
- **Thread-safe**: Multi-client synchronization without blocking
- **Configurable**: Easy configuration via environment variables or config file

## Requirements

### Hardware
- Raspberry Pi (any model with camera support)
- Raspberry Pi Camera Module (v1, v2, v3, or HQ)
- Network connection (Ethernet recommended for best performance)

### Software
- Raspberry Pi OS (Bullseye or later)
- Python 3.7+
- picamera2 library
- Flask web framework

## Quick Start

### On Raspberry Pi

1. **Clone the repository**
   ```bash
   git clone <your-repo-url> ~/camera-stream
   cd ~/camera-stream
   ```

2. **Run the setup script**
   ```bash
   bash deploy/setup_pi.sh
   ```

3. **Start the service**
   ```bash
   sudo systemctl start camera-stream
   ```

4. **Access the stream**
   - Open a browser and navigate to: `http://192.168.86.32:5000`
   - Replace with your Pi's IP address

### For Development

If you want to run the server manually for testing:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## Configuration

Configuration is managed through `config.py` or environment variables.

### Default Settings

```python
PORT = 5000                    # Web server port
RESOLUTION = (1280, 720)       # 720p
FRAMERATE = 30                 # 30 fps
QUALITY = 85                   # JPEG quality (0-100)
FRAME_TIMEOUT = 10             # Seconds before stopping camera thread
```

### Environment Variables

You can override settings using environment variables:

```bash
export CAMERA_PORT=8080
export CAMERA_RESOLUTION=1920,1080
export CAMERA_FRAMERATE=24
export CAMERA_QUALITY=90
```

### Performance Tuning

Choose settings based on your needs:

| Profile | Resolution | FPS | Quality | Latency | Bandwidth/viewer |
|---------|------------|-----|---------|---------|------------------|
| **Low Latency** | 640×480 | 30 | 75 | ~100ms | ~1.5 Mbps |
| **Balanced** (recommended) | 1280×720 | 30 | 85 | ~150ms | ~3.5 Mbps |
| **High Quality** | 1920×1080 | 24 | 90 | ~250ms | ~6 Mbps |

## Project Structure

```
tripodcamera/
├── app.py                     # Flask application entry point
├── config.py                  # Configuration settings
├── requirements.txt           # Python dependencies
├── camera/
│   ├── base_camera.py        # Thread-safe frame distribution
│   └── pi_camera.py          # Picamera2 implementation
├── static/
│   ├── css/style.css         # Styling
│   └── js/stream.js          # Client-side JavaScript
├── templates/
│   └── index.html            # Web interface
├── tests/                     # Test suite
└── deploy/                    # Deployment scripts
```

## Service Management

### Systemd Commands

```bash
# Start the service
sudo systemctl start camera-stream

# Stop the service
sudo systemctl stop camera-stream

# Restart the service
sudo systemctl restart camera-stream

# Check status
sudo systemctl status camera-stream

# Enable auto-start on boot
sudo systemctl enable camera-stream

# Disable auto-start
sudo systemctl disable camera-stream

# View logs
sudo journalctl -u camera-stream -f
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run specific test file
pytest tests/test_camera.py -v
```

### Code Quality

```bash
# Format code with black
black .

# Check code style with flake8
flake8 camera/ app.py
```

## Deployment Workflow

1. **Develop locally** - Make changes on your development machine
2. **Test** - Run tests and verify functionality
3. **Commit** - Commit changes with descriptive messages
4. **Push to GitHub** - `git push origin main`
5. **Update Pi** - SSH to Pi and pull changes
   ```bash
   ssh meta@192.168.86.32
   cd ~/camera-stream
   git pull
   sudo systemctl restart camera-stream
   ```
6. **Verify** - Check that the stream works at http://192.168.86.32:5000

## Troubleshooting

### Camera Not Detected

```bash
# Check if camera is connected
libcamera-hello --list-cameras

# Enable camera interface
sudo raspi-config
# Navigate to: Interface Options -> Camera -> Enable

# Reboot
sudo reboot
```

### High Latency (>500ms)

- Reduce resolution to 640×480
- Lower JPEG quality to 70
- Use Ethernet instead of WiFi
- Check network bandwidth: `iftop -i eth0`

### High CPU Usage (>80%)

- Verify using MJPEGEncoder (check logs)
- Reduce framerate to 24 fps
- Lower resolution
- Check for other processes: `htop`

### Stream Freezes

- Check `FRAME_TIMEOUT` in config.py
- Verify camera thread restarts correctly
- Review logs: `sudo journalctl -u camera-stream -f`

### Multiple Viewers Cause Frame Drops

- Ensure Flask threaded mode is enabled (default)
- Check network upload bandwidth
- Reduce resolution or quality

## Performance Monitoring

### Expected Performance Metrics

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Latency | <200ms | 200-400ms | >400ms |
| CPU Usage | <30% | 30-50% | >50% |
| Frame Rate | 30 fps | 24-30 fps | <24 fps |
| Memory | <200MB | 200-300MB | >300MB |

### Monitoring Commands

```bash
# CPU and memory usage
htop

# Network bandwidth
iftop -i eth0

# Service status and resource usage
systemctl status camera-stream

# Real-time logs
sudo journalctl -u camera-stream -f
```

## API Endpoints

### Web Interface
- `GET /` - Main streaming page

### Video Feed
- `GET /video_feed` - MJPEG stream (multipart/x-mixed-replace)

### Health Check
- `GET /health` - Service health status (JSON)
  ```json
  {
    "status": "healthy",
    "camera_available": true,
    "config": {
      "resolution": [1280, 720],
      "framerate": 30,
      "quality": 85
    }
  }
  ```

## Architecture

The streaming architecture uses a proven multi-threaded pattern:

1. **Background Thread** - Continuously captures frames from camera
2. **Frame Buffer** - Thread-safe storage for latest frame
3. **Client Threads** - Each viewer gets independent access via Flask threads
4. **CameraEvent** - Per-client synchronization prevents blocking

This design ensures:
- Multiple viewers don't interfere with each other
- Slow clients don't block fast clients
- Camera runs continuously without restart overhead
- Efficient resource usage

## Security Considerations

This is a basic implementation without authentication. For production use, consider:

- Adding basic authentication (HTTP Basic Auth)
- Using HTTPS with SSL/TLS certificates
- Implementing rate limiting
- Restricting access by IP address
- Using a reverse proxy (nginx) with security headers

## Future Enhancements

Potential improvements:

- [ ] Basic authentication for viewer access
- [ ] Video recording to file
- [ ] Motion detection with alerts
- [ ] Support for multiple cameras
- [ ] WebRTC for ultra-low latency
- [ ] Mobile app integration
- [ ] Analytics dashboard
- [ ] RESTful API for programmatic access

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Based on Miguel Grinberg's [Flask video streaming pattern](https://blog.miguelgrinberg.com/post/flask-video-streaming-revisited)
- Uses the official [picamera2 library](https://github.com/raspberrypi/picamera2)
- Inspired by the Raspberry Pi camera community

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the troubleshooting section
- Review the deployment logs: `sudo journalctl -u camera-stream -f`

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

**Raspberry Pi Camera Streaming Server** - Low latency camera streaming for Raspberry Pi
