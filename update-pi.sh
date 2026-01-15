#!/bin/bash

# Simple script to show the server code that needs to be copied
# Run this, then copy-paste the output into nano on the Pi

echo "📋 Copy the code below, then:"
echo "1. SSH to Pi: ssh pi@192.168.2.108"
echo "2. Stop server: pkill -f 'python.*server.py'"
echo "3. Edit file: nano server.py"
echo "4. Paste the code below (Ctrl+Shift+V or right-click paste)"
echo "5. Save: Ctrl+O, Enter, Ctrl+X"
echo "6. Start: python server.py"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cat server_py2.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"





