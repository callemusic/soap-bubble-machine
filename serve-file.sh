#!/bin/bash

# Start a simple HTTP server to serve the server file
# The Pi can download it directly without SSH password

PORT=8080
FILE="server_py2.py"
MAC_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")

echo "🌐 Starting file server..."
echo ""
echo "On your Pi, run this command:"
echo "  curl http://$MAC_IP:$PORT/$FILE -o server.py"
echo ""
echo "Or with wget:"
echo "  wget http://$MAC_IP:$PORT/$FILE -O server.py"
echo ""
echo "Press Ctrl+C to stop the server when done"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start Python HTTP server
python3 -m http.server $PORT 2>/dev/null || python -m SimpleHTTPServer $PORT





