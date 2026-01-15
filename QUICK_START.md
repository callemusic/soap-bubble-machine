# Quick Start - Fresh Pi Setup

## Option 1: Automated Setup (Recommended)

```bash
# Run the setup script
./setup-pi-fresh.sh [PI_IP] [PI_USER]

# Example:
./setup-pi-fresh.sh 192.168.2.108 pi
```

## Option 2: Manual Setup

### 1. Flash Raspberry Pi OS
- Use Raspberry Pi Imager
- Enable SSH in settings
- Flash to SD card and boot Pi

### 2. Run Setup Script
```bash
./setup-pi-fresh.sh
```

### 3. Test Server
```bash
# SSH to Pi
ssh pi@192.168.2.108

# Test server
python server.py

# If it works, start in background
~/start-server.sh
```

### 4. Test from MacBook
```bash
# Check health
curl http://192.168.2.108:8080/health

# Test smoke control (if MIDI connected)
curl -X POST http://192.168.2.108:8080/control_smoke \
  -H "Content-Type: application/json" \
  -d '{"action": "test"}'
```

## What Gets Installed

- Python 2.7
- RPi.GPIO (for motor control)
- pygame (for MIDI support)
- Server code (`server.py`)
- Startup script (`start-server.sh`)

## Troubleshooting

**Can't connect?**
```bash
# Find Pi IP
ping raspberrypi.local
# Or check router admin page
```

**SSH not working?**
- Make sure SSH is enabled in Raspberry Pi Imager settings
- Or create `ssh` file on boot partition: `touch /Volumes/boot/ssh`

**Permission errors?**
```bash
# On Pi
sudo usermod -a -G dialout,gpio pi
# Then log out and back in
```
