#!/bin/bash

# Complete Pi Access Setup
# Sets up SSH keys and VNC screen sharing

PI_IP="${1:-192.168.0.99}"
PI_USER="${2:-planeight}"

echo "=========================================="
echo "Raspberry Pi Access Setup"
echo "=========================================="
echo "Pi IP: $PI_IP"
echo "Pi User: $PI_USER"
echo ""

# Step 1: Set up SSH keys
echo "Step 1: Setting up SSH keys for passwordless access..."
echo ""

# Check if SSH key exists
if [ ! -f ~/.ssh/id_ed25519.pub ] && [ ! -f ~/.ssh/id_rsa.pub ]; then
    echo "No SSH key found. Generating one..."
    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "pi-access"
    echo "✅ SSH key generated"
fi

# Copy SSH key to Pi
echo "Copying SSH key to Pi..."
echo "You'll be prompted for your password one last time..."
if ssh-copy-id "$PI_USER@$PI_IP" 2>/dev/null; then
    echo "✅ SSH key copied successfully"
else
    echo "⚠️  Could not copy SSH key automatically"
    echo "Please run manually: ssh-copy-id $PI_USER@$PI_IP"
fi

# Test passwordless SSH
echo ""
echo "Testing passwordless SSH..."
if ssh -o ConnectTimeout=5 -o BatchMode=yes "$PI_USER@$PI_IP" "echo 'Passwordless SSH works!'" 2>/dev/null; then
    echo "✅ Passwordless SSH is working!"
else
    echo "⚠️  Passwordless SSH not working yet. You may need to:"
    echo "   1. Run: ssh-copy-id $PI_USER@$PI_IP"
    echo "   2. Or manually copy ~/.ssh/id_ed25519.pub to Pi's ~/.ssh/authorized_keys"
fi

# Step 2: Set up VNC
echo ""
echo "=========================================="
echo "Step 2: Setting up VNC Screen Sharing"
echo "=========================================="
echo ""

echo "Installing VNC server..."
ssh "$PI_USER@$PI_IP" "
    sudo apt-get update -qq && \
    sudo apt-get install -y realvnc-vnc-server realvnc-vnc-viewer 2>/dev/null || \
    sudo apt-get install -y tightvncserver 2>/dev/null || \
    echo 'VNC may already be installed'
"

echo ""
echo "Configuring VNC..."
ssh "$PI_USER@$PI_IP" "
    # Enable VNC via raspi-config (non-interactive)
    sudo raspi-config nonint do_vnc 0 2>/dev/null || \
    echo 'VNC configuration...'
    
    # Or enable systemd service
    sudo systemctl enable vncserver-x11-serviced.service 2>/dev/null || \
    sudo systemctl enable vncserver@:1.service 2>/dev/null || \
    echo 'VNC service configuration...'
    
    # Start VNC service
    sudo systemctl start vncserver-x11-serviced.service 2>/dev/null || \
    sudo systemctl start vncserver@:1.service 2>/dev/null || \
    echo 'VNC service started'
"

echo ""
echo "Setting VNC password..."
echo "You'll be prompted to set a VNC password (can be different from SSH password)"
ssh -t "$PI_USER@$PI_IP" "
    mkdir -p ~/.vnc 2>/dev/null
    if [ ! -f ~/.vnc/passwd ]; then
        echo 'Setting VNC password...'
        vncpasswd
    else
        echo 'VNC password already set. To change it, run: vncpasswd'
    fi
" 2>/dev/null || echo "VNC password setup..."

# Check VNC status
echo ""
echo "Checking VNC status..."
VNC_STATUS=$(ssh "$PI_USER@$PI_IP" "systemctl is-active vncserver-x11-serviced.service 2>/dev/null || systemctl is-active vncserver@:1.service 2>/dev/null || echo 'checking'")
if [ "$VNC_STATUS" = "active" ] || [ "$VNC_STATUS" = "running" ]; then
    echo "✅ VNC server is running"
else
    echo "⚠️  VNC server may need manual start"
    echo "   Try: ssh $PI_USER@$PI_IP 'vncserver :1'"
fi

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "SSH Access:"
echo "  ssh $PI_USER@$PI_IP"
echo "  (No password needed now!)"
echo ""
echo "VNC Screen Sharing:"
echo "  Option 1: Use Screen Sharing app"
echo "    Press Cmd+Space, search 'Screen Sharing'"
echo "    Enter: $PI_IP:5901"
echo ""
echo "  Option 2: Use command line"
echo "    open vnc://$PI_IP:5901"
echo ""
echo "  Option 3: Use VNC Viewer (download from realvnc.com)"
echo "    Connect to: $PI_IP:5901"
echo ""
echo "Note: If VNC doesn't work, try:"
echo "  ssh $PI_USER@$PI_IP 'sudo raspi-config'"
echo "  Then: Interface Options → VNC → Enable"
