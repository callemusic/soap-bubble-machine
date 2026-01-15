#!/bin/bash

# Fresh Raspberry Pi Setup Script
# Run this from your MacBook to set up a fresh Pi

PI_IP="${1:-192.168.2.108}"
PI_USER="${2:-pi}"

echo "=========================================="
echo "Fresh Raspberry Pi Setup"
echo "=========================================="
echo "Pi IP: $PI_IP"
echo "Pi User: $PI_USER"
echo ""
echo "⚠️  This will set up a FRESH installation"
echo "Make sure you've flashed Raspberry Pi OS first!"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Test connection
echo ""
echo "Testing SSH connection..."
if ! ssh -o ConnectTimeout=5 "$PI_USER@$PI_IP" "echo 'Connection OK'" 2>/dev/null; then
    echo "❌ Cannot connect to Pi at $PI_IP"
    echo "Make sure:"
    echo "  1. Pi is powered on"
    echo "  2. SSH is enabled"
    echo "  3. You're on the same network"
    echo "  4. IP address is correct"
    exit 1
fi

echo "✅ Connected to Pi"

# Update system
echo ""
echo "Step 1: Updating system packages..."
ssh "$PI_USER@$PI_IP" "
    sudo apt-get update && \
    sudo apt-get upgrade -y && \
    echo '✅ System updated'
"

# Install dependencies
echo ""
echo "Step 2: Installing dependencies..."
ssh "$PI_USER@$PI_IP" "
    sudo apt-get install -y \
        python \
        python-pip \
        python-dev \
        python-rpi.gpio \
        git \
        python-pygame \
    && echo '✅ Dependencies installed'
"

# Add user to dialout group (for serial devices)
echo ""
echo "Step 3: Configuring user permissions..."
ssh "$PI_USER@$PI_IP" "
    sudo usermod -a -G dialout,gpio $PI_USER && \
    echo '✅ User added to dialout and gpio groups'
    echo '⚠️  You may need to log out and back in for groups to take effect'
"

# Create server directory
echo ""
echo "Step 4: Setting up server directory..."
ssh "$PI_USER@$PI_IP" "
    mkdir -p ~/bubblebot && \
    echo '✅ Directory created'
"

# Copy server file
echo ""
echo "Step 5: Copying server code..."
if scp server_py2.py "$PI_USER@$PI_IP:~/server.py"; then
    echo "✅ Server code copied"
else
    echo "❌ Failed to copy server code"
    exit 1
fi

# Copy test script
echo ""
echo "Step 6: Copying test scripts..."
scp test_midi_pi.py "$PI_USER@$PI_IP:~/test_midi_pi.py" 2>/dev/null || echo "⚠️  test_midi_pi.py not found (optional)"

# Test Python and GPIO
echo ""
echo "Step 7: Testing Python setup..."
ssh "$PI_USER@$PI_IP" "
    python --version && \
    python -c 'import RPi.GPIO; print(\"✅ RPi.GPIO works\")' && \
    python -c 'import pygame.midi; pygame.midi.init(); print(\"✅ pygame.midi works\"); pygame.midi.quit()' 2>/dev/null || echo '⚠️  pygame.midi not available (may need to install)' && \
    echo '✅ Python setup verified'
"

# Create startup script
echo ""
echo "Step 8: Creating startup script..."
ssh "$PI_USER@$PI_IP" "cat > ~/start-server.sh << 'EOF'
#!/bin/bash
cd ~
pkill -f 'python.*server.py' 2>/dev/null
sleep 1
nohup python server.py > server.log 2>&1 &
echo \"Server started! PID: \$!\"
echo \"Check logs: tail -f server.log\"
EOF
chmod +x ~/start-server.sh && echo '✅ Startup script created'"

# Summary
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Test the server:"
echo "   ssh $PI_USER@$PI_IP"
echo "   python server.py"
echo ""
echo "2. If it works, start in background:"
echo "   ~/start-server.sh"
echo ""
echo "3. Check logs:"
echo "   tail -f ~/server.log"
echo ""
echo "4. Test MIDI (if DOREMiDi connected):"
echo "   python test_midi_pi.py"
echo ""
echo "5. From your MacBook, test the API:"
echo "   curl http://$PI_IP:8080/health"
echo ""
