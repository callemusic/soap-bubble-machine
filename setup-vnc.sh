#!/bin/bash

# Setup VNC Server on Raspberry Pi
# This enables remote desktop access to your Pi

PI_IP="${1:-192.168.0.99}"
PI_USER="${2:-planeight}"

echo "=========================================="
echo "Setting up VNC Server on Raspberry Pi"
echo "=========================================="
echo "Pi IP: $PI_IP"
echo "Pi User: $PI_USER"
echo ""

# Test connection
echo "Testing SSH connection..."
if ! ssh -o ConnectTimeout=5 "$PI_USER@$PI_IP" "echo 'Connection OK'" 2>/dev/null; then
    echo "❌ Cannot connect to Pi at $PI_IP"
    echo "Make sure you can SSH to the Pi first:"
    echo "  ssh $PI_USER@$PI_IP"
    exit 1
fi

echo "✅ Connected to Pi"
echo ""

# Install VNC server if not already installed
echo "Step 1: Installing VNC server..."
ssh "$PI_USER@$PI_IP" "
    sudo apt-get update && \
    sudo apt-get install -y realvnc-vnc-server realvnc-vnc-viewer || \
    sudo apt-get install -y tightvncserver || \
    echo 'VNC may already be installed'
"

# Enable VNC service
echo ""
echo "Step 2: Enabling VNC service..."
ssh "$PI_USER@$PI_IP" "
    sudo systemctl enable vncserver@:1.service 2>/dev/null || \
    sudo systemctl enable vncserver-x11-serviced.service 2>/dev/null || \
    echo 'VNC service setup...'
"

# Start VNC server
echo ""
echo "Step 3: Starting VNC server..."
ssh "$PI_USER@$PI_IP" "
    sudo systemctl start vncserver@:1.service 2>/dev/null || \
    sudo systemctl start vncserver-x11-serviced.service 2>/dev/null || \
    vncserver :1 -geometry 1920x1080 -depth 24 2>/dev/null || \
    echo 'VNC server may already be running'
"

# Set VNC password (if needed)
echo ""
echo "Step 4: Setting VNC password..."
echo "You'll be prompted to set a VNC password (different from SSH password)"
ssh -t "$PI_USER@$PI_IP" "vncpasswd" 2>/dev/null || echo "Password may already be set"

echo ""
echo "=========================================="
echo "✅ VNC Server Setup Complete!"
echo "=========================================="
echo ""
echo "To connect from your Mac:"
echo ""
echo "Option 1: Use built-in Screen Sharing"
echo "  1. Press Cmd+Space and search for 'Screen Sharing'"
echo "  2. Enter: $PI_IP:5901"
echo "  3. Or use: vnc://$PI_IP:5901"
echo ""
echo "Option 2: Use VNC Viewer (download from realvnc.com)"
echo "  Connect to: $PI_IP:5901"
echo ""
echo "Option 3: Use command line"
echo "  open vnc://$PI_IP:5901"
echo ""
echo "Note: Port 5901 = Display :1"
echo "      Port 5900 = Display :0 (if using default)"
