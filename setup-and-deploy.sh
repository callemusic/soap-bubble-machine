#!/bin/bash

# Setup SSH and deploy server to Pi
PI_IP="192.168.2.108"
PI_USER="pi"

echo "🔧 Setting up SSH and deploying server..."
echo ""

# Step 1: Check if SSH key is already authorized
echo "Step 1: Testing SSH connection..."
if ssh -o BatchMode=yes -o ConnectTimeout=5 $PI_USER@$PI_IP "echo 'SSH key already configured'" 2>/dev/null; then
    echo "✅ SSH key is already set up!"
    SSH_SETUP=true
else
    echo "⚠️  SSH key not set up yet."
    echo ""
    echo "📝 Please run this command to set up passwordless SSH:"
    echo "   ssh-copy-id $PI_USER@$PI_IP"
    echo ""
    read -p "Press Enter after you've run the command above, or type 'skip' to continue with password: " answer
    
    if [ "$answer" != "skip" ]; then
        # Try again
        if ssh -o BatchMode=yes -o ConnectTimeout=5 $PI_USER@$PI_IP "echo 'SSH key configured'" 2>/dev/null; then
            echo "✅ SSH key is now configured!"
            SSH_SETUP=true
        else
            echo "⚠️  SSH key setup may have failed. Continuing with password authentication..."
            SSH_SETUP=false
        fi
    else
        SSH_SETUP=false
    fi
fi

echo ""
echo "Step 2: Deploying server..."

# Deploy the server
if [ "$SSH_SETUP" = true ]; then
    # Passwordless deployment
    echo "📤 Copying server_py2.py to Pi..."
    cat server_py2.py | ssh $PI_USER@$PI_IP "cat > server.py"
    
    if [ $? -eq 0 ]; then
        echo "✅ File copied successfully!"
        echo ""
        echo "🔄 Restarting server on Pi..."
        ssh $PI_USER@$PI_IP "pkill -f 'python.*server.py'; sleep 1; cd ~ && nohup python server.py > server.log 2>&1 &"
        echo "✅ Server restarted!"
        echo ""
        echo "📊 Checking server status..."
        sleep 2
        if curl -s http://$PI_IP:8080/health > /dev/null 2>&1; then
            echo "✅ Server is running and responding!"
            curl -s http://$PI_IP:8080/health | python -m json.tool 2>/dev/null || curl -s http://$PI_IP:8080/health
        else
            echo "⚠️  Server may still be starting. Check logs with:"
            echo "   ssh $PI_USER@$PI_IP 'tail -f server.log'"
        fi
    else
        echo "❌ Failed to copy file."
    fi
else
    # Manual deployment instructions
    echo ""
    echo "📋 Manual deployment steps:"
    echo ""
    echo "1. Copy the server file:"
    echo "   scp server_py2.py $PI_USER@$PI_IP:~/server.py"
    echo ""
    echo "2. SSH to Pi:"
    echo "   ssh $PI_USER@$PI_IP"
    echo ""
    echo "3. Stop any running server:"
    echo "   pkill -f 'python.*server.py'"
    echo ""
    echo "4. Start the server:"
    echo "   python server.py"
    echo ""
    echo "   Or run in background:"
    echo "   nohup python server.py > server.log 2>&1 &"
fi

echo ""
echo "✨ Done!"

