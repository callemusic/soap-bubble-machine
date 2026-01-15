# Fresh Raspberry Pi 3 Setup Guide

## Step 1: Flash Raspberry Pi OS

1. **Download Raspberry Pi Imager** from https://www.raspberrypi.com/software/
2. **Flash Raspberry Pi OS Lite** (32-bit) to SD card
   - Choose "Raspberry Pi OS (other)" → "Raspberry Pi OS Lite (Legacy)"
   - Enable SSH: Click gear icon → Enable SSH → Set password
   - Set hostname: `bubblebot` (optional)
   - Set username/password (or use default `pi`/`raspberry`)
3. **Insert SD card** into Pi and boot

## Step 2: Initial Pi Setup

```bash
# SSH to Pi (use the IP you know, or find it)
ssh pi@192.168.2.108

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install essential packages
sudo apt-get install -y python python-pip python-dev python-rpi.gpio git

# Install pygame for MIDI support (Python 2)
sudo apt-get install -y python-pygame

# OR if pygame not available via apt:
pip install pygame

# Add user to dialout group (for serial devices)
sudo usermod -a -G dialout pi
```

## Step 3: Deploy Server Code

From your MacBook:

```bash
# Make sure you're in the project directory
cd /Users/carlstenqvist/dev/soap-bubble-machine

# Copy server to Pi
scp server_py2.py pi@192.168.2.108:~/server.py

# Or use the deploy script
./deploy.sh
```

## Step 4: Test Server

```bash
# SSH to Pi
ssh pi@192.168.2.108

# Test server manually first
cd ~
python server.py

# If it works, run in background
nohup python server.py > server.log 2>&1 &

# Check logs
tail -f server.log
```

## Step 5: Connect Hardware

1. **DOREMiDi MIDI-to-DMX converter** via USB
2. **Test MIDI connection**:
   ```bash
   # On Pi
   python test_midi_pi.py
   ```

## Step 6: Configure Auto-start (Optional)

Create systemd service:

```bash
sudo nano /etc/systemd/system/bubblebot.service
```

Add:
```ini
[Unit]
Description=BubbleBot Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python /home/pi/server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable bubblebot.service
sudo systemctl start bubblebot.service
sudo systemctl status bubblebot.service
```

## Troubleshooting

- **Can't SSH?** Check IP: `ping raspberrypi.local` or check router
- **GPIO errors?** Make sure user is in `gpio` group: `sudo usermod -a -G gpio pi`
- **MIDI not found?** Check USB: `lsusb` and `ls -l /dev/tty*`
- **Port already in use?** Kill old process: `pkill -f 'python.*server.py'`
