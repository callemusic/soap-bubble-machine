#!/bin/bash

# Check Pi server status
PI_IP="${1:-192.168.2.108}"
PI_USER="pi"

echo "🔍 Checking Pi server status..."
echo ""

echo "1. Testing network connectivity..."
if ping -c 2 $PI_IP > /dev/null 2>&1; then
    echo "   ✅ Pi is reachable"
else
    echo "   ❌ Pi is not reachable"
    exit 1
fi

echo ""
echo "2. Testing HTTP server..."
if curl -s --max-time 2 http://$PI_IP:8080/health > /dev/null 2>&1; then
    echo "   ✅ Server is responding"
else
    echo "   ❌ Server is not responding"
fi

echo ""
echo "3. To check server logs, run:"
echo "   ssh $PI_USER@$PI_IP 'tail -30 server.log'"
echo ""
echo "4. To restart server, run:"
echo "   ssh $PI_USER@$PI_IP 'cd ~ && nohup python server.py > server.log 2>&1 &'"
