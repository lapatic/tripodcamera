# Quick Installation Guide

## For Pi Zero W Setup

Follow these steps to set up the camera streaming server on a fresh Pi Zero W (or any Pi).

### Prerequisites

- Raspberry Pi Zero W (or Pi 3/4) with Raspberry Pi OS installed
- Camera module connected (Official Pi Camera or Arducam OV5647)
- Network connectivity (WiFi or Ethernet)
- SSH access enabled

### Installation Steps

#### 1. Camera Hardware Setup

**If using Arducam OV5647** (MUST DO FIRST):

```bash
# Backup and edit boot config
sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.backup
sudo nano /boot/firmware/config.txt

# Comment out (add # at start):
# camera_auto_detect=1

# Add at end of file:
dtparam=i2c_arm=on
dtoverlay=ov5647

# Save: Ctrl+O, Enter, Ctrl+X
```

```bash
# Install tools
sudo apt-get update
sudo apt-get install -y libcamera-apps i2c-tools

# Load I2C module
sudo modprobe i2c-dev
echo "i2c-dev" | sudo tee -a /etc/modules

# Reboot
sudo reboot
```

After reboot, verify camera:
```bash
# Check I2C (should show "UU" at 0x36)
sudo i2cdetect -y 10

# List cameras (should show ov5647)
rpicam-hello --list-cameras
```

**If using Official Pi Camera**, skip to step 2.

#### 2. Clone Repository

```bash
cd ~
git clone https://github.com/lapatic/tripodcamera.git
cd tripodcamera
```

#### 3. Run Setup Script

```bash
bash deploy/setup_pi.sh
```

This will:
- Install system dependencies (python3-picamera2, etc.)
- Create Python virtual environment with system packages
- Install Flask and requirements
- Create systemd service for auto-start

#### 4. Configure for Pi Zero W (Optional but Recommended)

Edit config for lower resource usage:

```bash
nano config.py
```

Change these lines:
```python
STREAM_CONFIG = {
    'resolution': tuple(map(int, os.environ.get('CAMERA_RESOLUTION', '640,480').split(','))),
    'framerate': int(os.environ.get('CAMERA_FRAMERATE', 15)),
    'quality': int(os.environ.get('CAMERA_QUALITY', 75)),
}
```

Or use environment variables in systemd:
```bash
sudo systemctl edit camera-stream
```

Add:
```ini
[Service]
Environment="CAMERA_RESOLUTION=640,480"
Environment="CAMERA_FRAMERATE=15"
Environment="CAMERA_QUALITY=75"
```

Save and exit: Ctrl+O, Enter, Ctrl+X

#### 5. Start the Service

```bash
sudo systemctl start camera-stream
```

#### 6. Verify It's Working

Check status:
```bash
sudo systemctl status camera-stream
```

Should show "active (running)" in green.

View logs to confirm bitrate:
```bash
sudo journalctl -u camera-stream | grep bitrate
```

#### 7. Access the Stream

Find your Pi's IP address:
```bash
hostname -I
```

Open in a browser:
```
http://<pi-ip-address>:5000
```

For example: `http://192.168.1.100:5000`

### Recommended Settings by Pi Model

| Pi Model | Resolution | FPS | Quality | Expected CPU |
|----------|------------|-----|---------|--------------|
| Pi Zero W | 640×480 | 15 | 75 | 50-70% |
| Pi 3 | 1280×720 | 30 | 85 | 40-50% |
| Pi 4 | 1920×1080 | 24 | 95 | 20-30% |

### Service Management

```bash
# Start
sudo systemctl start camera-stream

# Stop
sudo systemctl stop camera-stream

# Restart (after config changes)
sudo systemctl restart camera-stream

# View logs
sudo journalctl -u camera-stream -f

# Disable auto-start
sudo systemctl disable camera-stream

# Enable auto-start (default)
sudo systemctl enable camera-stream
```

### Updating the Code

When updates are pushed to GitHub:

```bash
cd ~/tripodcamera
git pull
sudo systemctl restart camera-stream
```

### Troubleshooting

**Camera not detected:**
```bash
# For Arducam
sudo i2cdetect -y 10
rpicam-hello --list-cameras

# Verify config.txt has dtoverlay=ov5647
sudo nano /boot/firmware/config.txt
```

**Service fails to start:**
```bash
# Check logs
sudo journalctl -u camera-stream -n 50

# Common issues:
# - picamera2 not installed: sudo apt install python3-picamera2
# - Wrong venv: Check setup script created venv with --system-site-packages
# - Camera not detected: See camera setup steps
```

**Stream won't load in browser:**
```bash
# Check if running
sudo systemctl status camera-stream

# Check port is listening
sudo netstat -tlnp | grep 5000

# Test locally
curl http://localhost:5000
```

**High CPU usage on Pi Zero:**
- Reduce resolution to 640×480 or 320×240
- Lower framerate to 10-15 fps
- Reduce quality to 70-75
- Use Ethernet adapter instead of WiFi

### WiFi Stability (Important for Pi Zero W)

Disable power saving to prevent disconnections:

```bash
# Temporary
sudo iw wlan0 set power_save off

# Permanent
sudo nano /etc/rc.local
# Add before "exit 0":
/sbin/iw wlan0 set power_save off
```

Configure SSH keepalive:
```bash
sudo nano /etc/ssh/sshd_config
# Add or uncomment:
ClientAliveInterval 30
ClientAliveCountMax 3

# Restart SSH
sudo systemctl restart ssh
```

### Complete Fresh Install (One-Liner for Pi 4)

For Pi 4 with official camera (no Arducam config needed):

```bash
cd ~ && \
git clone https://github.com/lapatic/tripodcamera.git && \
cd tripodcamera && \
bash deploy/setup_pi.sh && \
sudo systemctl start camera-stream && \
echo "Stream ready at: http://$(hostname -I | awk '{print $1}'):5000"
```

### Web Interface Features

- **Fullscreen** - F key or button (Chrome on iOS works best)
- **Rotate** - T key or button (works with rotation lock)
- **Reload** - R key or button

---

For detailed information, see [README.md](README.md) and [Camera Setup Guide](keen-stirring-gosling.md).
