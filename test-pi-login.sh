#!/bin/bash

# Test Pi Login - Try common usernames and check SSH config

PI_IP="${1:-192.168.0.99}"

echo "=========================================="
echo "Testing Pi Login Options"
echo "=========================================="
echo "Pi IP: $PI_IP"
echo ""

# Check if SSH is even accessible
echo "1. Testing SSH connectivity..."
if ! nc -z -w 2 "$PI_IP" 22 2>/dev/null; then
    echo "   ❌ Cannot connect to port 22"
    echo "   Make sure SSH is enabled on the Pi"
    exit 1
fi
echo "   ✅ SSH port is open"
echo ""

# Try to get SSH banner/info
echo "2. Checking SSH server info..."
ssh -o ConnectTimeout=3 -o PreferredAuthentications=none "$PI_IP" 2>&1 | grep -i "openssh\|raspbian\|raspberry" || echo "   (Could not get server info)"
echo ""

# Common usernames to try
echo "3. Common Raspberry Pi usernames:"
echo "   - pi (classic default)"
echo "   - raspberry (sometimes used)"
echo "   - admin (some setups)"
echo "   - [custom username you set during Pi Imager setup]"
echo ""

echo "4. Password options:"
echo "   - raspberry (classic default)"
echo "   - [password you set during Pi Imager setup]"
echo ""

echo "=========================================="
echo "Troubleshooting Steps:"
echo "=========================================="
echo ""
echo "If you used Raspberry Pi Imager:"
echo "  1. Check what username/password you set in the settings"
echo "  2. The username might not be 'pi' if you customized it"
echo ""
echo "To try connecting manually:"
echo "  ssh <username>@$PI_IP"
echo ""
echo "If you forgot the password:"
echo "  1. You may need to reflash the SD card"
echo "  2. Or access the Pi directly (keyboard/monitor) to reset password"
echo ""
echo "To check if password auth is enabled (from Pi directly):"
echo "  sudo grep -E '^PasswordAuthentication|^PubkeyAuthentication' /etc/ssh/sshd_config"
echo ""
