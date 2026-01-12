#!/bin/bash

# Start the Pi server (will prompt for password once if SSH key not set up)
PI_IP="${1:-192.168.2.108}"
PI_USER="pi"

echo "🚀 Starting Pi server at $PI_IP..."
echo ""

# Check if server is already running
echo "Checking if server is already running..."
if ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no $PI_USER@$PI_IP "ps aux | grep -E 'python.*server.py' | grep -v grep" 2>/dev/null | grep -q server.py; then
    echo "✅ Server is already running!"
    echo ""
    echo "To restart it, run:"
    echo "  ./restart-pi-server.sh"
    exit 0
fi

echo "Server not running. Starting it now..."
echo ""

# Start the server (will prompt for password if key auth not set up)
echo "You may be prompted for your Pi password..."
ssh -o StrictHostKeyChecking=no $PI_USER@$PI_IP << 'ENDSSH'
cd ~
if [ ! -f server.py ]; then
    echo "❌ server.py not found in home directory!"
    echo "Please deploy it first with: ./deploy.sh"
    exit 1
fi

echo "Starting server..."
nohup python server.py > server.log 2>&1 &
sleep 1

if ps aux | grep -E 'python.*server.py' | grep -v grep > /dev/null; then
    echo "✅ Server started successfully!"
    echo ""
    echo "To view logs:"
    echo "  ssh $PI_USER@$PI_IP 'tail -f server.log'"
    echo ""
    echo "To stop the server:"
    echo "  ssh $PI_USER@$PI_IP 'pkill -f \"python.*server.py\"'"
else
    echo "❌ Failed to start server. Check logs:"
    echo "  ssh $PI_USER@$PI_IP 'cat server.log'"
    exit 1
fi
ENDSSH

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Server should now be running!"
    echo ""
    echo "Testing connection..."
    sleep 1
    if curl -s --max-time 2 http://$PI_IP:8080/health > /dev/null; then
        echo "✅✅✅ Server is responding! ✅✅✅"
    else
        echo "⚠️  Server started but not responding yet. Give it a few seconds."
    fi
fi
