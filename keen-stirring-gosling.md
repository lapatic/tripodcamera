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

### Testing the Camera (Step-by-Step Guide)

This guide explains how to test your camera setup using the built-in test suite and the Flask application.

#### 1. Quick Camera Hardware Test (On Pi)

**Before running any Python code, verify the camera is working:**

```bash
# SSH to your Pi
ssh meta@192.168.86.31

# Quick test - list cameras
rpicam-hello --list-cameras
# Expected output: "0 : ov5647 [2592x1944 10-bit GBRG]"

# Take a test photo to verify camera works
rpicam-still -o /tmp/camera-test.jpg -t 2000 --width 1920 --height 1080
ls -lh /tmp/camera-test.jpg
# Should show a ~300KB JPEG file

# Optional: Download the photo to verify quality
# On your local machine:
scp meta@192.168.86.31:/tmp/camera-test.jpg ~/Desktop/
```

**If this fails**, the camera hardware is not properly configured. See "Camera Hardware Setup" section.

#### 2. Unit Tests (Local or Pi)

**Test the camera abstraction without hardware:**

```bash
# On Pi or local machine
cd ~/code/tripodcamera  # or wherever you cloned the repo

# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests with verbose output
pytest tests/ -v

# Run specific test files
pytest tests/test_camera.py -v        # Tests camera threading and frame distribution
pytest tests/test_flask_routes.py -v  # Tests Flask routes and API endpoints

# Run a specific test
pytest tests/test_camera.py::TestBaseCamera::test_get_frame_returns_valid_jpeg -v
```

**What the unit tests verify:**
- **test_camera.py**: Thread-safe frame distribution, multi-client synchronization, camera lifecycle
  - `TestCameraEvent`: Event system for client synchronization
  - `TestBaseCamera`: Background thread management, frame delivery
  - `TestFrameGeneration`: Continuous frame updates, concurrent access safety

- **test_flask_routes.py**: Web interface, API endpoints, error handling
  - `TestRoutes`: Index page, video feed route, health check endpoint
  - `TestStreamingBehavior`: Handling camera unavailability, concurrent requests
  - `TestStaticAssets`: CSS and JavaScript file accessibility

**Expected output:**
```
tests/test_camera.py::TestCameraEvent::test_event_creation PASSED
tests/test_camera.py::TestBaseCamera::test_camera_starts_thread PASSED
tests/test_camera.py::TestBaseCamera::test_get_frame_returns_valid_jpeg PASSED
...
==================== 15 passed in 3.52s ====================
```

#### 3. Manual Application Testing (On Pi with Real Camera)

**Run the Flask application directly to test streaming:**

```bash
# SSH to Pi
ssh meta@192.168.86.31

# Navigate to project
cd ~/camera-stream  # or wherever you cloned it

# Install dependencies if not already installed
pip install -r requirements.txt

# Run the application in development mode
python app.py
```

**Expected output:**
```
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.86.31:5000
Press CTRL+C to quit
```

**Test the endpoints:**

```bash
# From another terminal or browser:

# 1. Test health check endpoint
curl http://192.168.86.31:5000/health
# Expected: {"status":"healthy","camera_available":true,"config":{...}}

# 2. Test main page
curl http://192.168.86.31:5000/
# Expected: HTML with "Pi Camera Stream" or "Camera Stream"

# 3. Test video feed (will stream MJPEG data)
curl http://192.168.86.31:5000/video_feed --max-time 5
# Expected: Multipart MJPEG data stream
```

**Test in browser:**
1. Open browser to: `http://192.168.86.31:5000`
2. You should see the web interface with live camera stream
3. Check browser console for errors (F12)
4. Verify stream loads within 2-3 seconds

#### 4. Multi-Client Testing

**Test that multiple viewers can watch simultaneously:**

```bash
# In browser: Open 5 tabs to http://192.168.86.31:5000
# All tabs should show smooth video without stuttering

# Monitor performance while streaming
ssh meta@192.168.86.31

# Terminal 1: Monitor CPU/memory
htop
# Look for python process, should be <50% CPU

# Terminal 2: Monitor network bandwidth
sudo iftop -i eth0
# Should show ~3.5 Mbps per connected viewer

# Terminal 3: Watch application logs
# If running as systemd service:
sudo journalctl -u camera-stream -f

# If running manually, logs appear in the python app.py terminal
```

**Expected behavior:**
- All 5 viewers see synchronized video (same frames)
- No significant frame drops
- Latency <300ms (wave hand in front of camera to test)
- CPU usage <50%
- No errors in logs

#### 5. Testing Specific Features

**Test camera thread lifecycle:**
```bash
# Run app, access stream, then close browser
# Wait 10 seconds (FRAME_TIMEOUT)
# Check logs - should see camera thread stopping due to inactivity
# Refresh browser - camera thread should restart automatically
```

**Test error handling:**
```bash
# Test with camera disconnected
# Physically disconnect camera cable while Pi is running
python app.py

# Expected: App starts but /video_feed returns 503 error
# /health endpoint should show "camera_available": false
```

**Test configuration changes:**
```bash
# Test different resolutions
export CAMERA_RESOLUTION=640,480
export CAMERA_QUALITY=75
python app.py
# Verify lower latency but lower quality

# Test high quality
export CAMERA_RESOLUTION=1920,1080
export CAMERA_QUALITY=90
export CAMERA_FRAMERATE=24
python app.py
# Verify higher quality but slightly higher latency
```

#### 6. Integration Testing with Systemd Service

**Test the production deployment:**

```bash
# Stop manual app if running (Ctrl+C)

# Install/start service
sudo systemctl start camera-stream
sudo systemctl status camera-stream
# Should show "active (running)"

# Test endpoints
curl http://192.168.86.31:5000/health

# Test in browser
# Open: http://192.168.86.31:5000

# Test auto-restart on failure
sudo systemctl restart camera-stream
# Stream should recover within 5 seconds

# Test boot persistence
sudo systemctl enable camera-stream
sudo reboot

# After reboot, verify service auto-started
sudo systemctl status camera-stream
```

#### 7. Troubleshooting Test Failures

**Unit tests fail:**
```bash
# Check Python version
python --version  # Should be 3.7+

# Reinstall dependencies
pip install -r requirements-dev.txt --force-reinstall

# Run with more verbosity
pytest tests/ -vv -s
```

**Camera not detected during manual test:**
```bash
# Verify camera configuration (see Camera Hardware Setup section)
rpicam-hello --list-cameras
sudo i2cdetect -y 10  # Should show "UU" at 0x36

# Check logs
dmesg | grep -iE 'ov5647|camera'
```

**Web interface shows "Camera not available":**
```bash
# Check picamera2 is installed
pip show picamera2

# If not installed:
sudo apt-get install -y python3-picamera2

# Or in virtualenv:
pip install picamera2
```

**Stream is laggy or stuttering:**
```bash
# Check network
ping 192.168.86.31  # Should be <10ms on local network

# Check CPU usage
htop  # Python process should be <50%

# Reduce resolution temporarily
export CAMERA_RESOLUTION=640,480
python app.py

# Check network bandwidth available
iftop -i eth0
```

### Test Checklist

Before deploying to production, verify:

- [ ] Camera hardware test passes (`rpicam-hello --list-cameras`)
- [ ] Test photo captured successfully (`rpicam-still`)
- [ ] All unit tests pass (`pytest tests/ -v`)
- [ ] Health endpoint returns healthy status
- [ ] Single viewer stream works smoothly
- [ ] 5 concurrent viewers work without issues
- [ ] Latency <300ms (wave hand test)
- [ ] CPU usage <50% with 5 viewers
- [ ] Camera thread stops after 10s of inactivity
- [ ] Camera thread restarts when viewer reconnects
- [ ] Systemd service starts correctly
- [ ] Service auto-starts on boot
- [ ] Stream recovers from service restart

### Performance Benchmarks (Expected Results)

**Single Viewer @ 720p/30fps/85 quality:**
- Latency: 150-200ms
- CPU: 20-25%
- Memory: 150-180MB
- Network: 3-4 Mbps

**5 Viewers @ 720p/30fps/85 quality:**
- Latency: 150-250ms
- CPU: 35-45%
- Memory: 180-220MB
- Network: 15-20 Mbps total (3-4 Mbps each)

### Summary - Testing Phases

**Local Testing (before Pi deployment):**
1. Run unit tests: `pytest tests/` (see Section 2 above)
2. Test Flask routes with mock camera
3. Verify MJPEG format correctness
4. Check HTML/CSS rendering

**Pi Testing:**
1. Camera hardware test (see Section 1 above)
2. Single viewer test - verify smooth stream
3. Multi-viewer test - open 5 browser tabs simultaneously (see Section 4 above)
4. Latency test - wave hand in front of camera, measure delay
5. Performance monitoring:
   - CPU usage: `htop` (should be <50%)
   - Network: `iftop -i eth0`
   - Service logs: `journalctl -u camera-stream -f`
6. Reconnection test - disconnect/reconnect network
7. Long-running test - leave streaming for 24+ hours

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
