#!/bin/bash
# setup_pi.sh - Initial Raspberry Pi camera streaming setup
#
# This script sets up the camera streaming server on a Raspberry Pi.
# It should be run on the Raspberry Pi after cloning the repository.
#
# Usage: bash deploy/setup_pi.sh

set -e  # Exit on error

echo "========================================"
echo "Raspberry Pi Camera Streaming Setup"
echo "========================================"
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "Warning: This doesn't appear to be a Raspberry Pi."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "[1/7] Updating system packages..."
sudo apt update
echo ""

# Install system dependencies
echo "[2/7] Installing system dependencies..."
sudo apt install -y python3-pip python3-venv git python3-libcamera python3-kms++
echo ""

# Enable camera interface (if not already enabled)
echo "[3/7] Enabling camera interface..."
if ! grep -q "^camera_auto_detect=1" /boot/config.txt 2>/dev/null && \
   ! grep -q "^camera_auto_detect=1" /boot/firmware/config.txt 2>/dev/null; then
    echo "Camera interface may not be enabled."
    echo "Run: sudo raspi-config"
    echo "Then: Interface Options -> Camera -> Enable"
    read -p "Press Enter to continue..."
fi
echo ""

# Set project directory
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
echo "[4/7] Using project directory: $PROJECT_DIR"

# Create virtual environment
echo "[5/7] Creating Python virtual environment..."
cd "$PROJECT_DIR"
python3 -m venv venv
echo ""

# Install Python dependencies
echo "[6/7] Installing Python packages..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo ""

# Create systemd service
echo "[7/7] Setting up systemd service..."

# Get the current user
CURRENT_USER="${SUDO_USER:-$USER}"

# Create service file with actual paths
sudo tee /etc/systemd/system/camera-stream.service > /dev/null <<EOF
[Unit]
Description=Raspberry Pi Camera Streaming Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/app.py
Restart=always
RestartSec=10

# Resource limits
CPUQuota=50%
MemoryLimit=512M

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload
sudo systemctl enable camera-stream.service

echo ""
echo "========================================"
echo "✓ Setup complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Start the stream:  sudo systemctl start camera-stream"
echo "  2. Check status:      sudo systemctl status camera-stream"
echo "  3. View logs:         sudo journalctl -u camera-stream -f"
echo ""
echo "Access the stream at: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "To test the camera manually:"
echo "  source venv/bin/activate"
echo "  python app.py"
echo ""
