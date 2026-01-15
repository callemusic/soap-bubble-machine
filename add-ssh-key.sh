#!/bin/bash

# Add SSH key manually to Pi
# Run this on your Mac, then copy the output to your Pi

PUBLIC_KEY=$(cat ~/.ssh/id_rsa.pub ~/.ssh/id_ed25519.pub 2>/dev/null | head -1)

if [ -z "$PUBLIC_KEY" ]; then
    echo "❌ No SSH public key found"
    echo "Generate one with: ssh-keygen -t ed25519"
    exit 1
fi

echo "=========================================="
echo "SSH Key Setup Instructions"
echo "=========================================="
echo ""
echo "Your public key:"
echo "$PUBLIC_KEY"
echo ""
echo "Copy the key above, then run these commands on your Pi:"
echo ""
echo "mkdir -p ~/.ssh"
echo "chmod 700 ~/.ssh"
echo "echo '$PUBLIC_KEY' >> ~/.ssh/authorized_keys"
echo "chmod 600 ~/.ssh/authorized_keys"
echo ""
echo "Or run this single command on the Pi:"
echo "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$PUBLIC_KEY' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
echo ""
