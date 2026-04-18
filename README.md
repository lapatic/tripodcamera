# Raspberry Pi Camera Streaming Server

A low-latency camera streaming server for Raspberry Pi that broadcasts video to multiple viewers through a web interface using MJPEG over HTTP.

## Features

- **High Quality**: 1080p at 20 Mbps with quality 95 (configurable)
- **Low Latency**: 100-300ms typical latency for real-time viewing
- **Multiple Viewers**: Supports 2-5 simultaneous viewers efficiently
- **Responsive Web Interface**: Mobile-friendly with fullscreen support
- **Rotation Support**: Software rotation for phones with rotation lock
- **Hardware Accelerated**: Uses MJPEGEncoder for optimal performance
- **Auto-start**: Systemd service for automatic startup on boot
- **Thread-safe**: Multi-client synchronization without blocking
- **Configurable**: Easy configuration via environment variables or config file

## Requirements

### Hardware
- **Raspberry Pi**: Pi 4, Pi 3, Pi Zero W/2W (Pi 4 recommended for 1080p)
- **Camera**: Official Pi Camera (v1/v2/v3/HQ) or Arducam OV5647
- **Network**: Ethernet recommended for best performance (WiFi works)

### Software
- Raspberry Pi OS (Bullseye or later)
- Python 3.7+
- picamera2 library (installed via apt)
- Flask web framework

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/lapatic/tripodcamera.git ~/tripodcamera
cd ~/tripodcamera
```

### 2. Camera Setup (IMPORTANT - READ FIRST!)

**If using Official Raspberry Pi Camera:**
- Camera should auto-detect
- Skip to step 3

**If using Arducam OV5647 or similar third-party camera:**

Arducam cameras require manual configuration. Without this, the camera will appear broken.

```bash
# Backup config
sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.backup

# Edit config
sudo nano /boot/firmware/config.txt

# Comment out this line (add # at the start):
# camera_auto_detect=1

# Add at the end of the file:
dtparam=i2c_arm=on
dtoverlay=ov5647

# Save and exit (Ctrl+O, Enter, Ctrl+X)
```

Install tools and reboot:
```bash
sudo apt-get update
sudo apt-get install -y libcamera-apps i2c-tools
sudo modprobe i2c-dev
echo "i2c-dev" | sudo tee -a /etc/modules
sudo reboot
```

After reboot, verify camera is detected:
```bash
# Check I2C bus (should show "UU" at 0x36)
sudo i2cdetect -y 10

# List cameras (should show ov5647)
rpicam-hello --list-cameras
```

See [Camera Setup Guide](keen-stirring-gosling.md) for detailed troubleshooting.

### 3. Run the Setup Script

```bash
bash deploy/setup_pi.sh
```

This will:
- Install system dependencies (picamera2, Python packages)
- Create Python virtual environment
- Install Flask and requirements
- Create systemd service for auto-start

### 4. Start the Service

```bash
sudo systemctl start camera-stream
```

### 5. Access the Stream

Open a browser and navigate to: `http://<your-pi-ip>:5000`

Find your Pi's IP:
```bash
hostname -I
```

## Pi Zero W Compatibility

The Pi Zero W works but with reduced performance:

**Recommended Settings for Pi Zero W:**
```python
# In config.py or environment variables
CAMERA_RESOLUTION=640,480    # VGA instead of 1080p
CAMERA_FRAMERATE=15          # 15 fps instead of 24
CAMERA_QUALITY=75            # Lower quality to reduce CPU load
```

**Performance Expectations:**
- Resolution: 640×480 max (VGA)
- Framerate: 10-15 fps
- Viewers: 1-2 concurrent
- CPU Usage: 40-60%

**Why Pi Zero is slower:**
- Single-core 1GHz CPU vs Pi 4's quad-core 1.5GHz
- 512MB RAM vs 1-4GB on Pi 4
- Slower WiFi (2.4GHz only)

For best results, use **Ethernet via USB adapter** on Pi Zero W.

## Configuration

Current default settings (optimized for Pi 4):

```python
PORT = 5000                    # Web server port
RESOLUTION = (1920, 1080)      # 1080p (Full HD)
FRAMERATE = 24                 # 24 fps
QUALITY = 95                   # High quality JPEG (0-100)
FRAME_TIMEOUT = 10             # Seconds before stopping camera thread
```

### Environment Variables

Override settings without editing code:

```bash
export CAMERA_PORT=8080
export CAMERA_RESOLUTION=1920,1080
export CAMERA_FRAMERATE=24
export CAMERA_QUALITY=95
```

Or edit systemd service:
```bash
sudo systemctl edit camera-stream
```

Add:
```ini
[Service]
Environment="CAMERA_RESOLUTION=1280,720"
Environment="CAMERA_FRAMERATE=30"
Environment="CAMERA_QUALITY=85"
```

### Performance Profiles

| Profile | Resolution | FPS | Quality | Pi Model | Bandwidth/viewer |
|---------|------------|-----|---------|----------|------------------|
| **Pi Zero W** | 640×480 | 15 | 75 | Zero/Zero W | ~1.5 Mbps |
| **Balanced** | 1280×720 | 30 | 85 | Pi 3/4 | ~5 Mbps |
| **High Quality** | 1920×1080 | 24 | 95 | Pi 4 only | ~15-20 Mbps |

## Web Interface Features

### Desktop
- **Fullscreen button** (F key) - Browser native fullscreen
- **Rotate button** (T key) - Rotate stream 90° increments
- **Reload button** (R key) - Reconnect stream

### Mobile/iOS
- **Fullscreen mode** - Works on Chrome (better) and Safari
- **Rotation button** - Software rotation (works with rotation lock)
- **Touch-optimized** - Large buttons, responsive layout

**iOS Note:** Use Chrome for true fullscreen. Safari has limited fullscreen support.

## Project Structure

```
tripodcamera/
├── app.py                     # Flask application entry point
├── config.py                  # Configuration settings
├── requirements.txt           # Python dependencies
├── camera/
│   ├── base_camera.py        # Thread-safe frame distribution
│   └── pi_camera.py          # Picamera2 implementation with MJPEG
├── static/
│   ├── css/style.css         # Responsive styling with dark theme
│   └── js/stream.js          # Client-side controls and fullscreen
├── templates/
│   └── index.html            # Web interface
├── tests/                     # Test suite (pytest)
├── deploy/
│   └── setup_pi.sh           # Automated setup script
└── keen-stirring-gosling.md  # Detailed camera setup guide
```

## Service Management

### Systemd Commands

```bash
# Start the service
sudo systemctl start camera-stream

# Stop the service
sudo systemctl stop camera-stream

# Restart the service (after config changes)
sudo systemctl restart camera-stream

# Check status
sudo systemctl status camera-stream

# Enable auto-start on boot (default)
sudo systemctl enable camera-stream

# Disable auto-start
sudo systemctl disable camera-stream

# View live logs
sudo journalctl -u camera-stream -f

# View logs since boot
sudo journalctl -u camera-stream -b
```

## Development

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Install dev dependencies
pip install pytest

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_camera.py -v
```

### Manual Testing

```bash
# Run without systemd
source venv/bin/activate
python app.py

# Access at http://localhost:5000
```

## Deployment Workflow

1. **Develop locally** - Make changes on your development machine
2. **Test** - Run tests and verify functionality
3. **Commit & Push**
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin main
   ```
4. **Update Pi** - SSH to Pi and pull changes
   ```bash
   ssh user@pi-ip-address
   cd ~/tripodcamera
   git pull
   sudo systemctl restart camera-stream
   ```
5. **Verify** - Check stream at http://pi-ip:5000

## Troubleshooting

### Camera Not Detected

**For Arducam cameras:**
```bash
# Verify I2C detection
sudo i2cdetect -y 10
# Should show "UU" at address 0x36

# Check camera list
rpicam-hello --list-cameras
# Should show: "0 : ov5647 [2592x1944 10-bit GBRG]"

# If not detected, verify config.txt:
sudo nano /boot/firmware/config.txt
# Must have: dtparam=i2c_arm=on and dtoverlay=ov5647
# Must NOT have: camera_auto_detect=1 (comment it out)
```

**For official Pi cameras:**
```bash
# Enable camera in raspi-config
sudo raspi-config
# Interface Options -> Legacy Camera -> Disable (use libcamera)
# Finish and reboot

# Verify
libcamera-hello --list-cameras
```

### Stream Not Accessible

```bash
# Check service status
sudo systemctl status camera-stream

# View errors in logs
sudo journalctl -u camera-stream -n 50

# Check if port 5000 is listening
sudo netstat -tlnp | grep 5000

# Test from Pi itself
curl http://localhost:5000
```

### High CPU Usage

- **Pi 4**: CPU should be <30% with 1080p@24fps
- **Pi 3**: Use 720p, expect 40-50% CPU
- **Pi Zero W**: Use 640×480, expect 50-70% CPU

If CPU is higher:
```bash
# Check bitrate in logs
sudo journalctl -u camera-stream | grep bitrate

# Reduce quality/resolution in config.py
# Then restart service
```

### Low Quality / Blocky Image

```bash
# Check current bitrate
sudo journalctl -u camera-stream | grep "MJPEG encoder bitrate"
# Should show: "20.0 Mbps" for 1080p

# If lower than expected, check config.py quality setting
# Quality 95 = ~20 Mbps at 1080p
# Quality 85 = ~10-12 Mbps at 1080p
```

### SSH Disconnections

```bash
# Disable WiFi power saving
sudo iw wlan0 set power_save off

# Make permanent:
sudo nano /etc/rc.local
# Add before "exit 0":
/sbin/iw wlan0 set power_save off

# Check SSH settings
sudo nano /etc/ssh/sshd_config
# Should have:
# ClientAliveInterval 30
# ClientAliveCountMax 3
```

## Performance Monitoring

```bash
# CPU and memory usage
htop

# Network bandwidth
sudo apt install iftop
sudo iftop -i wlan0

# Service resource usage
systemctl status camera-stream

# Check camera logs
sudo journalctl -u camera-stream --since "5 minutes ago"
```

## API Endpoints

### Web Interface
- `GET /` - Main streaming page with controls

### Video Feed
- `GET /video_feed` - MJPEG stream (multipart/x-mixed-replace)

### Health Check
- `GET /health` - Service health status (JSON)
  ```json
  {
    "status": "healthy",
    "camera_available": true,
    "config": {
      "resolution": [1920, 1080],
      "framerate": 24,
      "quality": 95
    }
  }
  ```

## Architecture

The streaming architecture uses a proven multi-threaded pattern:

1. **Background Thread** - Continuously captures frames from camera using picamera2
2. **MJPEG Encoder** - Hardware-accelerated encoding at configured bitrate
3. **Frame Buffer** - Thread-safe storage for latest frame
4. **Client Threads** - Each viewer gets independent access via Flask threads
5. **CameraEvent** - Per-client synchronization prevents blocking

**Bitrate Calculation:**
- Base: 8 Mbps for 720p@85 quality
- Scales with resolution and quality
- 1080p@95 quality → 20 Mbps (Pi 4 limit)
- Lower framerate = higher quality per frame (no penalty)

This design ensures:
- Multiple viewers don't interfere with each other
- Slow clients don't block fast clients
- Camera runs continuously without restart overhead
- Efficient resource usage
- Hardware acceleration when available

## Security Considerations

This is a basic implementation without authentication. For production use, consider:

- Using HTTPS with SSL/TLS certificates
- Adding basic authentication (HTTP Basic Auth)
- Implementing rate limiting
- Restricting access by IP address or VPN
- Using a reverse proxy (nginx) with security headers
- Running on non-standard port

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Based on Miguel Grinberg's [Flask video streaming pattern](https://blog.miguelgrinberg.com/post/flask-video-streaming-revisited)
- Uses the official [picamera2 library](https://github.com/raspberrypi/picamera2)
- Inspired by the Raspberry Pi camera community

## Support

For issues or questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review the [Camera Setup Guide](keen-stirring-gosling.md)
- Check logs: `sudo journalctl -u camera-stream -f`
- Open an issue on GitHub

---

**Raspberry Pi Camera Streaming Server** - High quality, low latency camera streaming for Raspberry Pi
