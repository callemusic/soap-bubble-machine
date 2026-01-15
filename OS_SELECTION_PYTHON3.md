# OS Selection for Python 3

## Recommended: Raspberry Pi OS Lite (64-bit) or Raspberry Pi OS Lite (32-bit)

**For Raspberry Pi 3:**
- **Raspberry Pi OS Lite (32-bit)** - Recommended for Pi 3
  - Better compatibility with older hardware
  - Still fully supported
  - Includes Python 3.9+

**Alternative (if you want 64-bit):**
- **Raspberry Pi OS Lite (64-bit)** - Also works on Pi 3
  - Better performance on some tasks
  - More modern, but slightly larger

## How to Select in Raspberry Pi Imager

1. Open Raspberry Pi Imager
2. Click "Choose OS"
3. Select **"Raspberry Pi OS Lite"** (the main one, NOT Legacy)
   - This is the latest version with Python 3
   - Available in both 32-bit and 64-bit
   - For Pi 3, 32-bit is safer, but 64-bit also works

4. Click gear icon (⚙️) before flashing:
   - ✅ Enable SSH
   - Set username: `pi` (or your choice)
   - Set password
   - Optional: Set hostname: `bubblebot`

## What Changes in the Code

The server code will be updated to:
- Use Python 3 syntax (`urllib.parse` instead of `urlparse`)
- Use `mido` library for MIDI (better Python 3 support)
- Update all string handling (bytes vs str)
- Use `http.server` instead of `BaseHTTPServer`

## Benefits of Python 3

- ✅ Modern, actively maintained
- ✅ Better library support
- ✅ More secure
- ✅ Future-proof
- ✅ Better MIDI support with `mido`

## After Flashing

Run the updated setup script:
```bash
./setup-pi-python3.sh 192.168.2.108 pi
```

This will install Python 3 dependencies and deploy the updated server code.
