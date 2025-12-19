#!/bin/bash

# Test Pi connection and server status
PI_IP="192.168.2.108"
PI_USER="pi"

echo "🔍 Testing Pi Connection..."
echo ""

# Test 1: Ping
echo "1. Testing network connectivity..."
if ping -c 2 -W 2 $PI_IP > /dev/null 2>&1; then
    echo "   ✅ Pi is reachable at $PI_IP"
else
    echo "   ❌ Pi is not reachable"
    exit 1
fi

# Test 2: SSH port
echo "2. Testing SSH port..."
if nc -z -w 2 $PI_IP 22 > /dev/null 2>&1; then
    echo "   ✅ SSH port 22 is open"
else
    echo "   ❌ SSH port 22 is closed"
    exit 1
fi

# Test 3: SSH connection
echo "3. Testing SSH connection..."
if ssh -o BatchMode=yes -o ConnectTimeout=5 $PI_USER@$PI_IP "echo 'Connected'" > /dev/null 2>&1; then
    echo "   ✅ SSH key authentication works!"
    SSH_AUTH=true
else
    echo "   ⚠️  SSH key authentication not set up (password required)"
    SSH_AUTH=false
fi

# Test 4: Server port
echo "4. Testing server port..."
if nc -z -w 2 $PI_IP 8080 > /dev/null 2>&1; then
    echo "   ✅ Server port 8080 is open"
    
    # Test 5: Server health endpoint
    echo "5. Testing server health endpoint..."
    HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" http://$PI_IP:8080/health 2>/dev/null)
    HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
    BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "   ✅ Server is running and healthy!"
        echo "   Response: $BODY"
    else
        echo "   ⚠️  Server responded with HTTP $HTTP_CODE"
    fi
else
    echo "   ⚠️  Server port 8080 is closed (server not running)"
fi

echo ""
if [ "$SSH_AUTH" = false ]; then
    echo "💡 To set up passwordless SSH, run:"
    echo "   ssh-copy-id $PI_USER@$PI_IP"
fi

echo ""
echo "✨ Connection test complete!"

