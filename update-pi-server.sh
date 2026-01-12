#!/bin/bash

# Update server on Pi and restart it
PI_IP="${1:-192.168.2.108}"
PI_USER="pi"

echo "📤 Updating server on Pi..."
echo "You will be prompted for your Pi password."
echo ""

# Copy file using cat (bypasses SFTP issues)
cat server_py2.py | ssh $PI_USER@$PI_IP "cat > ~/server.py && chmod +x ~/server.py && ls -lh ~/server.py && echo '' && echo '✅ File updated!'"

if [ $? -eq 0 ]; then
    echo ""
    echo "🔄 Restarting server..."
    echo ""
    
    # Stop existing server and start new one
    ssh $PI_USER@$PI_IP "pkill -f 'python.*server.py'; sleep 1; cd ~ && nohup python server.py > server.log 2>&1 & sleep 1 && ps aux | grep -E 'python.*server.py' | grep -v grep && echo '' && echo '✅ Server restarted!'"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "Testing connection..."
        sleep 2
        if curl -s --max-time 3 http://$PI_IP:8080/health > /dev/null; then
            echo "✅✅✅ Server is responding! ✅✅✅"
        else
            echo "⚠️  Server restarted but not responding yet. Check logs:"
            echo "   ssh $PI_USER@$PI_IP 'tail -20 server.log'"
        fi
    fi
else
    echo ""
    echo "❌ Failed to copy file."
    exit 1
fi
