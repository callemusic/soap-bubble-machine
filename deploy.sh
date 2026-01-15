#!/bin/bash

# Deploy server to Raspberry Pi
# Usage: ./deploy.sh [restart]
#   - If "restart" is provided, will automatically restart the server

PI_IP="192.168.2.108"
PI_USER="pi"
SERVER_FILE="server_py2.py"
REMOTE_PATH="server.py"
AUTO_RESTART=$1

echo "🚀 Deploying server to Raspberry Pi at $PI_IP..."

# Copy file to Pi
echo "📤 Copying $SERVER_FILE to Pi..."
scp $SERVER_FILE $PI_USER@$PI_IP:~/$REMOTE_PATH

if [ $? -eq 0 ]; then
    echo "✅ File copied successfully!"
    
    if [ "$AUTO_RESTART" = "restart" ]; then
        echo "🔄 Restarting server..."
        ssh $PI_USER@$PI_IP "pkill -f 'python.*server.py'; sleep 1; cd ~ && nohup python server.py > server.log 2>&1 &"
        echo "✅ Server restarted! Check logs with: ssh $PI_USER@$PI_IP 'tail -f server.log'"
    else
        echo ""
        echo "📝 To restart the server, run:"
        echo "   ./deploy.sh restart"
        echo ""
        echo "Or manually:"
        echo "   ssh $PI_USER@$PI_IP"
        echo "   pkill -f 'python.*server.py'"
        echo "   python server.py"
    fi
else
    echo "❌ Failed to copy file. Make sure you can SSH to the Pi."
    exit 1
fi

