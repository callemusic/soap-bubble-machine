#!/bin/bash

# Quick deploy - just copy and restart
PI_IP="${1:-192.168.2.108}"
PI_USER="pi"

echo "🚀 Quick Deploy to $PI_USER@$PI_IP"
echo ""

# Copy file
echo "📤 Copying server_py2.py..."
cat server_py2.py | ssh $PI_USER@$PI_IP "cat > server.py" && echo "✅ Copied!" || { echo "❌ Failed. Make sure SSH works: ssh $PI_USER@$PI_IP"; exit 1; }

# Restart server
echo ""
echo "🔄 Restarting server..."
ssh $PI_USER@$PI_IP "pkill -f 'python.*server.py'; sleep 1; cd ~ && nohup python server.py > server.log 2>&1 &" && echo "✅ Server restarted!" || echo "⚠️  Server restart may have failed"

echo ""
echo "✨ Done! Server should be running on port 8080"

