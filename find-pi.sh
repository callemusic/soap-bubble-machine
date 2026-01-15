#!/bin/bash

# Find Raspberry Pi on Network
# This script scans the local network to find Raspberry Pi devices

echo "=========================================="
echo "Raspberry Pi Network Discovery"
echo "=========================================="
echo ""

# Method 1: Try common hostnames
echo "Method 1: Trying common hostnames..."
for hostname in raspberrypi.local raspberrypi bubblebot.local bubblebot; do
    if ping -c 1 -W 1 "$hostname" >/dev/null 2>&1; then
        IP=$(ping -c 1 "$hostname" 2>/dev/null | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
        echo "✅ Found Pi at: $hostname ($IP)"
        echo ""
        echo "To connect:"
        echo "  ssh pi@$IP"
        echo "  or"
        echo "  ssh pi@$hostname"
        exit 0
    fi
done
echo "  No Pi found via hostname"
echo ""

# Method 2: Get local network info
echo "Method 2: Scanning local network..."
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "")
if [ -z "$LOCAL_IP" ]; then
    echo "  Could not determine local IP address"
    echo "  Trying common network ranges..."
    NETWORKS=("192.168.1" "192.168.0" "192.168.2" "10.0.0" "172.16.0")
else
    # Extract network prefix (e.g., 192.168.1 from 192.168.1.100)
    NETWORK_PREFIX=$(echo "$LOCAL_IP" | cut -d. -f1-3)
    NETWORKS=("$NETWORK_PREFIX")
fi

# Method 3: Check ARP table for Raspberry Pi MAC addresses
echo "Method 3: Checking ARP table for Raspberry Pi MAC addresses..."
# Raspberry Pi MAC prefixes: B8:27:EB, DC:A6:32, E4:5F:01
PI_MACS=$(arp -a | grep -iE "(b8:27:eb|dc:a6:32|e4:5f:01)" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}')
if [ ! -z "$PI_MACS" ]; then
    echo "  Found potential Pi devices in ARP table:"
    for ip in $PI_MACS; do
        echo "    - $ip"
        # Try to ping and get hostname
        if ping -c 1 -W 1 "$ip" >/dev/null 2>&1; then
            HOSTNAME=$(host "$ip" 2>/dev/null | grep -oE '[a-zA-Z0-9.-]+\.local' | head -1 || echo "")
            if [ ! -z "$HOSTNAME" ]; then
                echo "      Hostname: $HOSTNAME"
            fi
            echo ""
            echo "✅ Found Pi at: $ip"
            echo ""
            echo "To connect:"
            echo "  ssh pi@$ip"
            exit 0
        fi
    done
else
    echo "  No Pi MAC addresses found in ARP table"
fi
echo ""

# Method 4: Ping scan common IP ranges
echo "Method 4: Scanning network range (this may take a minute)..."
FOUND_IPS=()
for network in "${NETWORKS[@]}"; do
    echo "  Scanning $network.0/24..."
    for i in {1..254}; do
        IP="$network.$i"
        # Skip our own IP
        if [ "$IP" != "$LOCAL_IP" ]; then
            if ping -c 1 -W 0.5 "$IP" >/dev/null 2>&1; then
                # Check if it's a Pi by MAC address in ARP
                MAC=$(arp -n "$IP" 2>/dev/null | grep -oE '([0-9a-f]{2}:){5}[0-9a-f]{2}' | tr '[:upper:]' '[:lower:]')
                if [[ "$MAC" =~ ^(b8:27:eb|dc:a6:32|e4:5f:01) ]]; then
                    echo "    ✅ Found Pi at: $IP (MAC: $MAC)"
                    FOUND_IPS+=("$IP")
                fi
            fi
        fi
    done
done

if [ ${#FOUND_IPS[@]} -gt 0 ]; then
    echo ""
    echo "=========================================="
    echo "Found Raspberry Pi devices:"
    echo "=========================================="
    for ip in "${FOUND_IPS[@]}"; do
        echo "  - $ip"
        echo "    ssh pi@$ip"
    done
    exit 0
fi

echo ""
echo "❌ No Raspberry Pi found on the network"
echo ""
echo "Troubleshooting tips:"
echo "  1. Make sure the Pi is powered on"
echo "  2. Check that the Pi is connected to the same network"
echo "  3. Try connecting via USB cable and check IP manually"
echo "  4. Check router admin page for connected devices"
echo "  5. Try: ping raspberrypi.local"
echo ""
echo "If you know the IP, you can test it:"
echo "  ssh pi@<IP_ADDRESS>"
