#!/bin/bash

# Restart the Pi server
PI_IP="${1:-192.168.2.108}"
PI_USER="pi"

echo "🔄 Restarting Pi server at $PI_IP..."
echo ""

ssh -o StrictHostKeyChecking=no $PI_USER@$PI_IP << 'ENDSSH'
cd ~
echo "Stopping existing server..."
pkill -f 'python.*server.py'
sleep 1

if [ ! -f server.py ]; then
    echo "❌ server.py not found in home directory!"
    echo "Please deploy it first with: ./deploy.sh"
    exit 1
fi

echo "Starting server..."
nohup python server.py > server.log 2>&1 &
sleep 1

if ps aux | grep -E 'python.*server.py' | grep -v grep > /dev/null; then
    echo "✅ Server restarted successfully!"
else
    echo "❌ Failed to start server. Check logs:"
    cat server.log
    exit 1
fi
ENDSSH

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Server restarted!"
    echo ""
    echo "Testing connection..."
    sleep 1
    if curl -s --max-time 2 http://$PI_IP:8080/health > /dev/null; then
        echo "✅✅✅ Server is responding! ✅✅✅"
    else
        echo "⚠️  Server restarted but not responding yet. Give it a few seconds."
    fi
fi
