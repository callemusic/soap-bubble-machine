#!/bin/bash

# Easy deployment: Start HTTP server, then download on Pi

PI_IP="192.168.2.108"
PI_USER="pi"
FILE="server_py2.py"
PORT=8080

# Get Mac's IP on local network
MAC_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)

if [ -z "$MAC_IP" ]; then
    echo "❌ Could not detect your Mac's IP address"
    echo "Run: ./serve-file.sh and follow the instructions"
    exit 1
fi

echo "🌐 Starting file server on http://$MAC_IP:$PORT..."
echo ""

# Start server in background
python3 -m http.server $PORT > /dev/null 2>&1 &
SERVER_PID=$!

# Wait a moment for server to start
sleep 2

echo "📥 Downloading file to Pi..."
echo ""

# Download file on Pi using Python (works even when curl/wget are broken)
ssh $PI_USER@$PI_IP "python -c \"import urllib2; open('server.py', 'w').write(urllib2.urlopen('http://$MAC_IP:$PORT/$FILE').read())\" && echo '✅ File downloaded!'"

if [ $? -eq 0 ]; then
    echo ""
    echo "🔄 Restarting server on Pi..."
    ssh $PI_USER@$PI_IP "pkill -f 'python.*server.py'; sleep 1; cd ~ && nohup python server.py > server.log 2>&1 &"
    echo "✅ Done! Server restarted on Pi"
else
    echo ""
    echo "⚠️  Could not download automatically. Try this:"
    echo "   1. Keep this terminal open (server is running)"
    echo "   2. SSH to Pi: ssh $PI_USER@$PI_IP"
    echo "   3. Run: python -c \"import urllib2; open('server.py', 'w').write(urllib2.urlopen('http://$MAC_IP:$PORT/$FILE').read())\""
    echo "   4. Run: pkill -f 'python.*server.py' && python server.py"
fi

# Stop the HTTP server
kill $SERVER_PID 2>/dev/null

