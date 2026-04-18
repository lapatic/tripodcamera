# Raspberry Pi Camera Streaming Implementation Plan

## Overview

Build a real-time camera streaming server on Raspberry Pi (meta@192.168.86.32) that broadcasts to 2-5 viewers through a web interface with low latency (100-300ms).

**Technology Stack:**
- **Backend:** Flask (threaded mode) + picamera2 + MJPEG streaming
- **Frontend:** HTML5 with responsive design
- **Protocol:** MJPEG over HTTP (multipart/x-mixed-replace)
- **Deployment:** Systemd service for auto-start

**Why This Stack:**
- Low latency suitable for real-time viewing
- Supports multiple concurrent viewers efficiently
- Universal browser support (no plugins needed)
- Well-documented with proven implementation patterns
- Hardware-accelerated JPEG encoding on Pi

**Quick Start for New Pi Setup:**
1. See "Camera Hardware Setup" section below for Arducam OV5647 configuration
2. Camera MUST be configured before running application code
3. Common mistake: camera_auto_detect does NOT work with Arducam modules

## Camera Hardware Setup

### Camera Compatibility: Official Pi Camera vs Arducam

| Feature | Official Pi Camera | Arducam OV5647 (Third-Party) |
|---------|-------------------|------------------------------|
| Auto-detect | ✅ Works with `camera_auto_detect=1` | ❌ Does NOT work with auto-detect |
| Configuration | Automatic | Requires manual dtoverlay |
| I2C | Auto-enabled | Must enable `dtparam=i2c_arm=on` |
| Detection tool | `libcamera-hello --list-cameras` | Same (after config) |
| Common issue | Usually plug-and-play | Appears "broken" until configured |

**CRITICAL:** If using Arducam cameras, you MUST follow the configuration steps below. Do not assume auto-detect will work.

### Arducam OV5647 Configuration (5MP)

**Hardware Used:**
- Camera: Arducam OV5647 (SKU B0033) - 5MP camera module
- Raspberry Pi: Pi 4 Model B
- Note: IP address meta@192.168.86.31 used for initial setup/testing

**Why Configuration is Needed:**
- Arducam cameras use standard sensors but different board designs than official Pi cameras
- Requires specific device tree overlays to initialize properly
- `camera_auto_detect=1` does NOT work reliably with Arducam modules
- I2C communication must be explicitly enabled for camera detection
- Without proper config, camera appears completely non-functional (not a hardware fault)

**Required Configuration Steps:**

1. **Backup and edit boot configuration**
   ```bash
   # Create backup first (recommended)
   sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.backup.$(date +%Y%m%d)

   # Edit config
   sudo nano /boot/firmware/config.txt

   # Find and comment out this line:
   # camera_auto_detect=1  # Does NOT work with Arducam

   # Add at the end of the file:
   dtparam=i2c_arm=on
   dtoverlay=ov5647

   # Save and exit (Ctrl+O, Enter, Ctrl+X)
   ```

2. **Install required tools**
   ```bash
   sudo apt-get update
   sudo apt-get install -y libcamera-apps i2c-tools
   ```

3. **Load I2C module**
   ```bash
   sudo modprobe i2c-dev
   # Make it permanent:
   echo "i2c-dev" | sudo tee -a /etc/modules
   ```

4. **Reboot to apply changes**
   ```bash
   sudo reboot
   ```

5. **Verify camera detection**
   ```bash
   # Check if camera is detected on I2C bus
   sudo i2cdetect -y 10
   # Should show "UU" at address 0x36 (camera in use by driver)

   # List available cameras
   rpicam-hello --list-cameras
   # Should show: "0 : ov5647 [2592x1944 10-bit GBRG]"

   # Take test photo
   rpicam-still -o test.jpg -t 2000 --width 1920 --height 1080
   ```

**Camera Specifications:**
- Max Resolution: 2592x1944
- Available modes:
  - 640x480 @ 58.92 fps
  - 1296x972 @ 46.34 fps
  - 1920x1080 @ 32.81 fps (recommended for streaming)
  - 2592x1944 @ 15.63 fps

**Other Arducam Models:**
If using different Arducam models, check `/boot/firmware/overlays/` for available overlays:
```bash
ls /boot/firmware/overlays/ | grep -i arducam
# Available overlays:
# - arducam-64mp.dtbo (64MP cameras)
# - arducam-pivariety.dtbo (Pivariety series)
# - ov5647.dtbo (5MP OV5647, used here)
```

**Quick Health Check (run on any Pi):**
```bash
# One-liner to check camera is properly configured
rpicam-hello --list-cameras && echo "✅ Camera OK" || echo "❌ Camera not detected - check config"

# Detailed diagnostic
echo "=== Camera Diagnostic ===" && \
echo "1. I2C Detection:" && sudo i2cdetect -y 10 2>/dev/null | grep -E "UU|36" && \
echo "2. Config file:" && grep -E "camera_auto|i2c_arm|ov5647" /boot/firmware/config.txt && \
echo "3. Camera list:" && rpicam-hello --list-cameras
```

**Troubleshooting Camera Detection:**
```bash
# Check kernel messages for camera
dmesg | grep -iE 'ov5647|camera'

# Verify I2C buses exist
ls -la /dev/i2c*

# Check loaded overlays
dtoverlay -l | grep -i cam

# Old vcgencmd shows supported=0 with new camera stack - ignore it
vcgencmd get_camera  # Don't use this, it's deprecated
```

**Configuration History:**
- Original config file backed up to: `/boot/firmware/config.txt.backup.20260418`
- Test Pi: meta@192.168.86.31
- Production Pi: meta@192.168.86.32

## Project Structure

```
tripodcamera/
├── README.md                      # Documentation
├── .gitignore                     # Git ignores
├── requirements.txt               # Python dependencies
├── config.py                      # Configuration settings
├── app.py                         # Flask application
├── camera/
│   ├── __init__.py
│   ├── base_camera.py            # Thread-safe frame distribution
│   └── pi_camera.py              # Picamera2 implementation
├── static/
│   ├── css/style.css             # Styling
│   └── js/stream.js              # Client-side connection monitoring
├── templates/
│   └── index.html                # Streaming webpage
├── tests/
│   ├── __init__.py
│   ├── test_camera.py            # Camera unit tests
│   └── test_flask_routes.py     # Flask integration tests
└── deploy/
    ├── setup_pi.sh               # Automated Pi setup script
    └── systemd/
        └── camera-stream.service # Systemd service configuration
```

## Implementation Steps

### 1. Project Foundation
- Create .gitignore (Python, venv, IDE, logs)
- Create requirements.txt (Flask, picamera2, simplejpeg, numpy, Pillow)
- Create config.py with stream settings (resolution: 1280×720, framerate: 30, quality: 85)
- **Commit:** "Initial project structure and dependencies"

### 2. Core Camera Module
**File:** `camera/base_camera.py`
- Implement BaseCamera abstract class with:
  - Background thread for continuous frame capture
  - CameraEvent class for per-client synchronization
  - Thread-safe frame distribution to multiple viewers
  - Automatic thread lifecycle (start on first client, stop after 10s inactivity)
  - Generator pattern for frame delivery

**File:** `camera/pi_camera.py`
- Implement PiCamera class extending BaseCamera:
  - StreamingOutput buffer class (thread-safe JPEG storage)
  - Picamera2 initialization with MJPEGEncoder
  - Frame generation from camera hardware
  - Proper cleanup and error handling

**Architecture:** Single background thread captures frames → all client threads read from shared buffer independently

**Commit:** "Implement camera abstraction and Pi camera driver"

### 3. Flask Application
**File:** `app.py`
- Create Flask app with threaded mode enabled
- Route `/` - renders main HTML page
- Route `/video_feed` - returns MJPEG stream (multipart/x-mixed-replace)
- Generator function yielding frames with proper MIME boundaries
- Bind to 0.0.0.0:5000 for network access

**Commit:** "Add Flask application with streaming routes"

### 4. Web Interface
**File:** `templates/index.html`
- Responsive HTML page with:
  - `<img>` tag for MJPEG stream
  - Connection status indicator
  - Manual reload button
  - Stream metadata display

**File:** `static/css/style.css`
- Dark theme design
- Responsive layout (mobile-friendly)
- Stream container with aspect ratio preservation

**File:** `static/js/stream.js`
- Connection monitoring (onload/onerror handlers)
- Stream reload functionality
- Status indicator updates

**Commit:** "Add web interface for camera streaming"

### 5. Testing
**File:** `tests/test_camera.py`
- Test camera initialization
- Verify frame generation (valid JPEG format)
- Test multiple simultaneous clients
- Check thread safety and resource cleanup

**File:** `tests/test_flask_routes.py`
- Test route accessibility (/, /video_feed)
- Verify MJPEG content-type and boundaries
- Test concurrent viewer connections

**Commit:** "Add test suite for camera and Flask routes"

### 6. Deployment Infrastructure
**File:** `deploy/setup_pi.sh`
- Automated setup script:
  - System updates
  - Install dependencies (python3-pip, git, libcamera-apps, i2c-tools)
  - Verify camera is detected (rpicam-hello --list-cameras)
  - Enable I2C module (i2c-dev)
  - Create virtual environment
  - Install Python packages
  - Set up systemd service
  - **Note:** Camera hardware config must be done manually first (see Camera Hardware Setup)

**File:** `deploy/systemd/camera-stream.service`
- Systemd service configuration:
  - Auto-start on boot
  - Run as 'meta' user
  - Resource limits (50% CPU, 512MB RAM)
  - Automatic restart on failure
  - Journal logging

**Commit:** "Add deployment scripts and systemd service"

### 7. Documentation
**Update:** `README.md`
- Project overview
- Setup instructions (local + Pi deployment)
- Configuration options
- Accessing the stream
- Troubleshooting guide
- Performance tuning tips

**Commit:** "Complete project documentation"

## Critical Files

These files are essential for the implementation:

1. **camera/base_camera.py** - Multi-client synchronization and threading logic
2. **camera/pi_camera.py** - Picamera2 integration with hardware encoding
3. **app.py** - Flask application with MJPEG streaming
4. **config.py** - Performance tuning (resolution, framerate, quality)
5. **templates/index.html** - Web interface for viewing stream

## Configuration

**Default Settings (config.py):**
- Resolution: 1280×720 (720p)
- Framerate: 30 fps
- JPEG Quality: 85
- Port: 5000

**Performance Tuning:**
- **Low latency:** 640×480 @ 30fps, quality=75 (~100ms latency)
- **Balanced:** 1280×720 @ 30fps, quality=85 (~150ms latency) ← Recommended
- **High quality:** 1920×1080 @ 24fps, quality=90 (~250ms latency)

**Network Usage:** ~3.5 Mbps per viewer at 720p/85 quality

## Deployment Workflow

**Initial Deployment:**

**Step 0: Camera Hardware Configuration (REQUIRED FIRST)**
```bash
# SSH to Pi
ssh meta@192.168.86.32

# Configure camera (see "Camera Hardware Setup" section above)
sudo nano /boot/firmware/config.txt
# Disable: camera_auto_detect=1
# Add: dtparam=i2c_arm=on
# Add: dtoverlay=ov5647

# Install camera tools
sudo apt-get update
sudo apt-get install -y libcamera-apps i2c-tools

# Enable I2C module
sudo modprobe i2c-dev
echo "i2c-dev" | sudo tee -a /etc/modules

# Reboot
sudo reboot

# After reboot, verify camera works
rpicam-hello --list-cameras
rpicam-still -o test.jpg
```

**Step 1-5: Application Deployment**
1. SSH to Pi: `ssh meta@192.168.86.32`
2. Clone repo: `git clone <repo-url> ~/camera-stream`
3. Run setup: `bash deploy/setup_pi.sh`
4. Start service: `sudo systemctl start camera-stream`
5. Access stream: `http://192.168.86.32:5000`

**Ongoing Updates:**
1. Develop and test locally
2. Commit changes with descriptive messages
3. Push to GitHub: `git push origin main`
4. SSH to Pi
5. Pull changes: `cd ~/camera-stream && git pull`
6. Restart service: `sudo systemctl restart camera-stream`
7. Verify stream still works

**Service Management:**
```bash
sudo systemctl start camera-stream   # Start
sudo systemctl stop camera-stream    # Stop
sudo systemctl restart camera-stream # Restart
sudo systemctl status camera-stream  # Check status
sudo journalctl -u camera-stream -f  # View logs
```

## Testing Strategy

**Local Testing (before Pi deployment):**
1. Run unit tests: `pytest tests/`
2. Test Flask routes with mock camera
3. Verify MJPEG format correctness
4. Check HTML/CSS rendering

**Pi Testing:**
1. Single viewer test - verify smooth stream
2. Multi-viewer test - open 5 browser tabs simultaneously
3. Latency test - wave hand in front of camera, measure delay
4. Performance monitoring:
   - CPU usage: `htop` (should be <50%)
   - Network: `iftop -i eth0`
   - Service logs: `journalctl -u camera-stream -f`
5. Reconnection test - disconnect/reconnect network
6. Long-running test - leave streaming for 24+ hours

**Success Criteria:**
- ✓ Latency under 300ms
- ✓ Supports 5 simultaneous viewers without frame drops
- ✓ CPU usage under 50% on Pi
- ✓ Stream recovers automatically from temporary disconnections
- ✓ Service auto-starts on Pi reboot

## Git Commit Strategy

**Phase-Based Commits:**
1. Initial structure → "Initial project structure and dependencies"
2. Camera implementation → "Implement camera abstraction and Pi camera driver"
3. Flask app → "Add Flask application with streaming routes"
4. Frontend → "Add web interface for camera streaming"
5. Tests → "Add test suite for camera and Flask routes"
6. Deployment → "Add deployment scripts and systemd service"
7. Documentation → "Complete project documentation"
8. Tag release → `git tag -a v1.0.0 -m "First production release"`

**Commit Convention:**
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation only
- `test:` - Adding tests
- `chore:` - Maintenance

**Regular Sync:**
- Commit after completing each logical unit of work
- Push to GitHub at end of each work session
- Pull on Pi and restart service after deployment

## Troubleshooting

### Camera Issues

**Camera not detected (Arducam OV5647):**

1. **Verify physical connection**
   - Camera ribbon cable fully inserted at both ends
   - Cable contacts facing correct direction (toward HDMI ports on Pi side)
   - Using CAMERA port (not DISPLAY port on Pi 4)
   - Power off Pi before adjusting cable

2. **Check I2C detection**
   ```bash
   # Install i2c-tools if not present
   sudo apt-get install -y i2c-tools

   # Load I2C module
   sudo modprobe i2c-dev

   # Scan for camera on I2C bus 10
   sudo i2cdetect -y 10
   # Should show "UU" at 0x36 if camera connected properly
   # "UU" means a driver has claimed the device
   ```

3. **Verify configuration in /boot/firmware/config.txt**
   ```bash
   cat /boot/firmware/config.txt | grep -E "camera|i2c|ov5647"

   # Should see:
   # #camera_auto_detect=1  (commented out)
   # dtparam=i2c_arm=on
   # dtoverlay=ov5647
   ```

4. **Check kernel messages**
   ```bash
   dmesg | grep -iE 'ov5647|camera|i2c.*36'
   # Should show i2c bus registration and ov5647 device
   ```

5. **Test with libcamera tools**
   ```bash
   # List cameras (new camera stack)
   rpicam-hello --list-cameras

   # DON'T use vcgencmd - it's for old camera stack
   # vcgencmd get_camera will show "supported=0" even when working

   # Take test photo
   rpicam-still -o test.jpg -t 2000
   ```

**If camera still not detected:**
- Verify /boot/firmware/overlays/ov5647.dtbo exists
- Try disabling camera_auto_detect completely (comment it out)
- Check dmesg for errors: `dmesg | grep -i error`
- Test with known-good ribbon cable
- Ensure sufficient power supply (5V 3A minimum for Pi 4)

**Camera worked before but stopped:**
- Configuration may have been overwritten by system update
- Check /boot/firmware/config.txt still has correct settings
- Reboot after any config changes

**High latency:**
- Reduce resolution to 640×480
- Lower JPEG quality to 70
- Use Ethernet instead of WiFi
- Check bandwidth: `iftop`

**High CPU usage:**
- Verify using MJPEGEncoder (not JpegEncoder)
- Reduce framerate to 24
- Lower resolution
- Check for other processes: `htop`

**Stream freezes:**
- Check FRAME_TIMEOUT in config.py
- Verify camera thread restarts correctly
- Review logs: `journalctl -u camera-stream -f`

## Expected Performance

**Target Metrics:**
- Latency: <200ms (acceptable: 200-400ms)
- CPU Usage: <30% (acceptable: 30-50%)
- Frame Rate: 30 fps (acceptable: 24-30 fps)
- Memory: <200MB (acceptable: 200-300MB)
- Network: <4 Mbps per viewer

## Future Enhancements

After successful initial deployment:
- Basic authentication for viewer access
- Video recording capability
- Motion detection with alerts
- Multiple camera support
- WebRTC for lower latency
- Mobile app integration
- Analytics dashboard
