#!/bin/bash

# Simplest deployment: pipe file through SSH
PI_IP="${1:-192.168.0.99}"
PI_USER="${2:-planeight}"
FILE="server.py"

echo "📤 Copying $FILE to Pi..."
cat $FILE | ssh $PI_USER@$PI_IP "cat > server.py"

if [ $? -eq 0 ]; then
    echo "✅ File copied successfully!"
    echo ""
    echo "🔄 Restarting server on Pi..."
    ssh $PI_USER@$PI_IP "pkill -f 'python.*server.py'; sleep 1; cd ~ && nohup python server.py > server.log 2>&1 &"
    echo "✅ Done! Server restarted."
    echo ""
    echo "View logs: ssh $PI_USER@$PI_IP 'tail -f server.log'"
else
    echo "❌ Failed to copy. Make sure SSH works: ssh $PI_USER@$PI_IP"
fi





