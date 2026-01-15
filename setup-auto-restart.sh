#!/bin/bash

# Setup auto-restart for the bubblebot server
PI_IP="${1:-192.168.0.99}"
PI_USER="${2:-planeight}"

echo "=========================================="
echo "Setting up Auto-Restart for BubbleBot Server"
echo "=========================================="
echo "Pi IP: $PI_IP"
echo "Pi User: $PI_USER"
echo ""

# Create a systemd service file
echo "Creating systemd service..."
ssh "$PI_USER@$PI_IP" "cat > /tmp/bubblebot.service << 'EOF'
[Unit]
Description=BubbleBot Server
After=network.target

[Service]
Type=simple
User=$PI_USER
WorkingDirectory=/home/$PI_USER
ExecStart=/usr/bin/python3 /home/$PI_USER/server.py
Restart=always
RestartSec=5
StandardOutput=append:/home/$PI_USER/server.log
StandardError=append:/home/$PI_USER/server.log

[Install]
WantedBy=multi-user.target
EOF
"

# Copy service file to systemd directory
echo "Installing service..."
ssh "$PI_USER@$PI_IP" "sudo mv /tmp/bubblebot.service /etc/systemd/system/bubblebot.service && sudo chmod 644 /etc/systemd/system/bubblebot.service"

# Reload systemd
echo "Reloading systemd..."
ssh "$PI_USER@$PI_IP" "sudo systemctl daemon-reload"

# Stop any running server processes
echo "Stopping existing server processes..."
ssh "$PI_USER@$PI_IP" "pkill -f 'python.*server.py' || true"
sleep 2

# Enable and start the service
echo "Enabling and starting service..."
ssh "$PI_USER@$PI_IP" "sudo systemctl enable bubblebot.service && sudo systemctl start bubblebot.service"

# Check status
echo ""
echo "Checking service status..."
ssh "$PI_USER@$PI_IP" "sudo systemctl status bubblebot.service --no-pager | head -15"

echo ""
echo "=========================================="
echo "✅ Auto-restart setup complete!"
echo "=========================================="
echo ""
echo "The server will now:"
echo "  - Start automatically on boot"
echo "  - Restart automatically if it crashes"
echo "  - Restart automatically after 5 seconds if it stops"
echo ""
echo "Useful commands:"
echo "  Check status: ssh $PI_USER@$PI_IP 'sudo systemctl status bubblebot'"
echo "  View logs: ssh $PI_USER@$PI_IP 'tail -f server.log'"
echo "  Restart: ssh $PI_USER@$PI_IP 'sudo systemctl restart bubblebot'"
echo "  Stop: ssh $PI_USER@$PI_IP 'sudo systemctl stop bubblebot'"
