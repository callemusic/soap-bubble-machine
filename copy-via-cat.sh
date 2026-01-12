#!/bin/bash

# Copy file using cat through SSH (will prompt for password)
PI_IP="${1:-192.168.2.108}"
PI_USER="pi"

echo "📤 Copying server.py using cat method..."
echo "You will be prompted for your Pi password."
echo ""

# Read file and pipe through SSH to write it
cat server_py2.py | ssh $PI_USER@$PI_IP "cat > ~/server.py && chmod +x ~/server.py && ls -lh ~/server.py && echo '' && echo '✅ File copied successfully!'"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Server file is now on the Pi!"
    echo ""
    echo "To start the server, run:"
    echo "  ssh $PI_USER@$PI_IP 'cd ~ && nohup python server.py > server.log 2>&1 &'"
else
    echo ""
    echo "❌ Failed to copy file."
    exit 1
fi
